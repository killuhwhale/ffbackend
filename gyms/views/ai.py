import json
import logging
import traceback
from pathlib import Path
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from gyms.models import TokenQuota, TokenPurchase
from .ai_helpers import (
    LLM,
    LLM_ANTHROPIC,
    LLM_GEMINI,
    LLM_OPENAI,
    WORKOUT_GENERATION_RULES,
    base_schema,
    claude_client,
    client,
    count_message_tokens,
    generate_workout_with_claude,
    generate_workout_with_gemini,
    generate_workout_with_openai,
    tools,
)
from ..coach_personalities import get_coach_profile
from .permissions import SelfActionPermission
from .helpers import is_member, check_users_workouts_and_completed_today
import google.generativeai as genai

# Load guardrail rules once at import time
_rules_path = Path(__file__).resolve().parent.parent / "system_coach_chat_rules.md"
COACH_CHAT_RULES = _rules_path.read_text(encoding="utf-8") if _rules_path.exists() else ""

# Injected into system prompt for all LLMs — same format, no tool_use needed.
# Claude 3.x follows this just as reliably as OpenAI without the fragility of forced tool_use.
_JSON_FORMAT_INSTRUCTION = """
## Response Format
You MUST respond with ONLY a valid JSON object — no extra text before or after it:
{"reply": "your message", "memory_update": null}

If the user revealed new personal information (height, weight, diet, injuries, equipment, \
training schedule, or any specific preference/limitation), set memory_update to an object \
containing ONLY the newly revealed or changed fields:
{"reply": "your message", "memory_update": {"weight": "185lbs", "diet": "mostly carnivore"}}

Omit any memory_update fields the user did NOT mention this turn.
"""


def _parse_chat_response(raw):
    # type: (str) -> tuple
    """
    Extract the JSON object from the LLM response, handling markdown code fences,
    trailing text, and nested braces.
    Returns (reply: str, memory_update: dict or None).
    """
    # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
    text = raw.strip()
    if text.startswith("```"):
        # Remove opening fence (with optional language tag)
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        # Remove closing fence
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()

    # Find the outermost JSON object by matching braces
    brace = text.find("{")
    if brace == -1:
        logger.warning("[chat] no JSON object found in response len=%d", len(raw))
        return raw, None

    depth = 0
    end = brace
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    candidate = text[brace:end]

    try:
        parsed = json.loads(candidate)
        reply = parsed.get("reply", "").strip() or raw
        raw_update = parsed.get("memory_update")
        memory_update = None
        if isinstance(raw_update, dict) and any(v for v in raw_update.values()):
            memory_update = {k: v for k, v in raw_update.items() if v}
        return reply, memory_update
    except (json.JSONDecodeError, ValueError):
        logger.warning("[chat] JSON parse failed — candidate=%r", candidate[:200])
        return raw, None

# ── Token packages ─────────────────────────────────────────────────────────────
# 1 credit ≈ 1 workout generation (~18k tokens) or ~8-10 coaching chat messages.
#
# Two purchase paths — keep these IDs in sync with stripeHooks/views.py:
#   Mobile : Apple App Store / Google Play via RevenueCat (IAP)
#   Web    : Stripe Checkout (one-time payment)
TOKENS_PER_CREDIT = 18_000

TOKEN_PACKAGES = [
    {
        "name":             "Starter",
        "credits":          5,
        "tokens":           5 * TOKENS_PER_CREDIT,   # 90,000
        "price_usd":        3.99,
        "description":      "5 AI Credits",
        # Mobile IAP — create these in App Store Connect & Google Play Console
        "apple_product_id":  "ai_credits_5",
        "google_product_id": "ai_credits_5",
        # Web — Stripe price ID (test mode)
        "stripe_price_id":   "price_1TDsVQGjKlPKN3XK7wY16yQb",
    },
    {
        "name":             "Popular",
        "credits":          15,
        "tokens":           15 * TOKENS_PER_CREDIT,  # 270,000
        "price_usd":        9.99,
        "description":      "15 AI Credits",
        "apple_product_id":  "ai_credits_15",
        "google_product_id": "ai_credits_15",
        "stripe_price_id":   "price_1TDsVQGjKlPKN3XKyGB2Vhft",
    },
    {
        "name":             "Pro",
        "credits":          35,
        "tokens":           35 * TOKENS_PER_CREDIT,  # 630,000
        "price_usd":        19.99,
        "description":      "35 AI Credits",
        "apple_product_id":  "ai_credits_35",
        "google_product_id": "ai_credits_35",
        "stripe_price_id":   "price_1TDsVRGjKlPKN3XKDOWj1CQ8",
    },
]

# Mobile IAP lookup — keyed by store-native product ID (Apple or Google).
# Used by the purchase_tokens endpoint when the app confirms an IAP.
TOKEN_PACKAGES_MAP: dict = {}
for _p in TOKEN_PACKAGES:
    TOKEN_PACKAGES_MAP[_p["apple_product_id"]]  = _p
    TOKEN_PACKAGES_MAP[_p["google_product_id"]] = _p


class AIViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def create_workout(self, request, pk=None):

        # ── Enforce workout creation limits before burning tokens ─────────────
        if not is_member(request) and not check_users_workouts_and_completed_today(request):
            return Response(
                {"error": "Daily workout limit reached. Upgrade your membership to create more workouts."},
                status=403
            )

        quota, newly_created = TokenQuota.objects.get_or_create(user_id=request.user.id)
        prompt = request.data.get('prompt')  # Goal
        scheme_type_text = request.data.get('scheme_type_text')
        userMaxes = request.data.get('userMaxes')
        lastWorkoutGroups = request.data.get('lastWorkoutGroups')
        remaining = quota.remaining_tokens
        print(f"{quota=}, {prompt=}, {scheme_type_text=}, {userMaxes=}, {lastWorkoutGroups=}, {remaining=}")

        if not prompt:
            print("Error No prompt given")
            return Response({"error": ' No prompt given'})

        if remaining <= 0:
            print("Error: Out of tokens")
            return Response({"error": 'Out of tokens'})

        messages = [
            {"role": "system", "content": (
                WORKOUT_GENERATION_RULES + "\n\n"
                "Structure your output as JSON only — no extra text."
            )},
            {"role": "user", "content": f"Workout maxes: {userMaxes}"},
            {"role": "user", "content": f"MyLast Couple of Workouts: {lastWorkoutGroups}"},
            {"role": "user", "content": f"Workout Scheme Style: {scheme_type_text}"},
            {"role": "user", "content": f"User Goal: {prompt}"},
        ]

        input_tokens = count_message_tokens(messages)
        if input_tokens >= remaining:
            return Response({"error": "Token quota exceeded"}, status=403)

        print("Input token: ", input_tokens)
        max_output_tokens = remaining - input_tokens

        if max_output_tokens <= 1500:
            quota.remaining_tokens = 0
            quota.save()
            return Response({"error": 'Not enough tokens left'})
        try:
            result = None
            if LLM == LLM_OPENAI:
                result = generate_workout_with_openai(
                    client=client,
                    tools=tools,
                    max_tokens=min(16_384, max_output_tokens),
                    prompt=prompt,
                    scheme_type_text=scheme_type_text,
                    userMaxes=userMaxes,
                    lastWorkoutGroups=lastWorkoutGroups
                )
            elif LLM == LLM_ANTHROPIC:
                result = generate_workout_with_claude(
                    claude_client=claude_client,
                    base_schema=base_schema,
                    max_tokens=min(16_384, max_output_tokens),
                    prompt=prompt,
                    scheme_type_text=scheme_type_text,
                    userMaxes=userMaxes,
                    lastWorkoutGroups=lastWorkoutGroups
                )
            elif LLM == LLM_GEMINI:
                result = generate_workout_with_gemini(
                    base_schema=base_schema,
                    max_tokens=min(16_384, max_output_tokens),
                    prompt=prompt,
                    scheme_type_text=scheme_type_text,
                    userMaxes=userMaxes,
                    lastWorkoutGroups=lastWorkoutGroups
                )

            # Update Quotas using the standardized return block
            input_tokens_used = result["tokens"]["input"]
            output_tokens_used = result["tokens"]["output"]
            total_tokens = result["tokens"]["total"]

            quota.use_tokens(total_tokens)
            print(f"Tokens used this request: {input_tokens_used} + {output_tokens_used} = {total_tokens}")
            print(f"Token Usage: {quota.remaining_tokens}/1,750,000")

            return Response({'data': result["data"]})
        except Exception as e:
            print("Error AI create_workout", e)
            return Response({'data': "", "error": str(e)})

    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def chat(self, request, pk=None):
        # ── Parse incoming payload ────────────────────────────────────────────
        message        = request.data.get('message', '').strip()
        history        = request.data.get('history', [])
        coach_type     = request.data.get('coach_type', 'Fitness Coach')
        goals          = request.data.get('goals', [])
        fitness_info   = request.data.get('fitness_info', '')
        memory_context = request.data.get('memory_context', '').strip()

        logger.info(
            "[chat] user=%s llm=%s coach=%r goals=%r "
            "history_len=%d memory_len=%d msg_len=%d",
            getattr(request.user, 'id', '?'),
            LLM, coach_type, goals,
            len(history), len(memory_context), len(message),
        )

        if not message:
            logger.warning("[chat] rejected — empty message")
            return Response({"error": "No message provided"}, status=400)

        # ── Token quota ───────────────────────────────────────────────────────
        try:
            quota, _ = TokenQuota.objects.get_or_create(user_id=request.user.id)
        except Exception:
            logger.error("[chat] quota lookup failed\n%s", traceback.format_exc())
            return Response({"error": "Could not retrieve token quota"}, status=500)

        if quota.remaining_tokens <= 0:
            logger.warning("[chat] user=%s out of tokens", request.user.id)
            return Response({"error": "Out of tokens"}, status=403)

        logger.info("[chat] tokens remaining=%d", quota.remaining_tokens)

        # ── Build system prompt ───────────────────────────────────────────────
        coach_profile = get_coach_profile(coach_type)
        memory_section = (
            f"\n\n## What you know about this athlete\n{memory_context}"
            if memory_context else ""
        )
        base_system_prompt = (
            f"{COACH_CHAT_RULES}\n\n"
            f"---\n\n"
            f"{coach_profile}\n\n"
            f"---\n\n"
            f"## This Athlete\n"
            f"Goals: {', '.join(goals) if goals else 'general fitness'}.\n"
            f"Background: {fitness_info}."
            f"{memory_section}"
        )

        try:
            reply         = ""
            memory_update = None
            tokens_used   = 0

            # ── OpenAI ───────────────────────────────────────────────────────
            if LLM == LLM_OPENAI:
                logger.info("[chat/openai] building messages history_len=%d", len(history))
                system_prompt = base_system_prompt + _JSON_FORMAT_INSTRUCTION
                messages = [{"role": "system", "content": system_prompt}]
                messages += [{"role": m["role"], "content": m["content"]} for m in history]
                messages.append({"role": "user", "content": message})

                logger.info("[chat/openai] calling API messages=%d", len(messages))
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.6,
                    messages=messages,
                    max_tokens=450,
                    response_format={"type": "json_object"},
                )
                raw = resp.choices[0].message.content.strip()
                tokens_used = resp.usage.total_tokens
                logger.info("[chat/openai] raw=%r tokens=%d", raw[:120], tokens_used)
                reply, memory_update = _parse_chat_response(raw)
                logger.info("[chat/openai] reply_len=%d memory_update=%s", len(reply), bool(memory_update))

            # ── Anthropic / Claude ────────────────────────────────────────────
            # Plain JSON-in-prompt — no tool_use. Simpler, cheaper, and avoids
            # Anthropic's safety layer blocking forced tool_choice responses.
            elif LLM == LLM_ANTHROPIC:
                system_prompt = base_system_prompt + _JSON_FORMAT_INSTRUCTION
                claude_messages = [{"role": m["role"], "content": m["content"]} for m in history]
                claude_messages.append({"role": "user", "content": message})
                logger.info("[chat/claude] calling API messages=%d", len(claude_messages))

                resp = claude_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=600,
                    system=system_prompt,
                    messages=claude_messages,
                )
                tokens_used = resp.usage.input_tokens + resp.usage.output_tokens
                raw = resp.content[0].text.strip() if resp.content else ""
                logger.info(
                    "[chat/claude] stop_reason=%r tokens=%d raw=%r",
                    resp.stop_reason, tokens_used, raw[:120],
                )
                reply, memory_update = _parse_chat_response(raw)
                logger.info("[chat/claude] reply_len=%d memory_update=%s", len(reply), bool(memory_update))

            # ── Gemini ────────────────────────────────────────────────────────
            elif LLM == LLM_GEMINI:
                logger.info("[chat/gemini] building history history_len=%d", len(history))
                system_prompt = base_system_prompt + _JSON_FORMAT_INSTRUCTION
                model = genai.GenerativeModel(
                    'gemini-2.0-flash',
                    system_instruction=system_prompt,
                )
                gemini_history = [
                    {
                        "role": m["role"] if m["role"] != "assistant" else "model",
                        "parts": [m["content"]],
                    }
                    for m in history
                ]
                config = genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.6,
                    max_output_tokens=450,
                )
                logger.info("[chat/gemini] calling API")
                chat_session = model.start_chat(history=gemini_history)
                resp = chat_session.send_message(message, generation_config=config)
                raw = resp.text.strip()
                tokens_used = resp.usage_metadata.total_token_count
                logger.info("[chat/gemini] raw=%r tokens=%d", raw[:120], tokens_used)
                reply, memory_update = _parse_chat_response(raw)
                logger.info("[chat/gemini] reply_len=%d memory_update=%s", len(reply), bool(memory_update))

            else:
                logger.error("[chat] unknown LLM value: %r", LLM)
                return Response({"error": f"Unknown LLM backend: {LLM}"}, status=500)

            # ── Final guard: make sure we have something to return ────────────
            if not reply:
                logger.error("[chat] reply is empty after LLM call — tokens_used=%d", tokens_used)
                return Response({"error": "Coach returned an empty response. Please try again."}, status=500)

            # ── Deduct tokens ─────────────────────────────────────────────────
            logger.info("[chat] deducting tokens=%d", tokens_used)
            quota.use_tokens(tokens_used)

            logger.info("[chat] success reply_len=%d memory_update=%s", len(reply), bool(memory_update))
            return Response({"reply": reply, "memory_update": memory_update})

        except Exception as e:
            logger.error(
                "[chat] UNHANDLED EXCEPTION user=%s llm=%s\n%s",
                getattr(request.user, 'id', '?'),
                LLM,
                traceback.format_exc(),
            )
            return Response({"error": f"Chat error: {str(e)}"}, status=500)

    @action(detail=False, methods=['GET'], permission_classes=[SelfActionPermission])
    def token_status(self, request, pk=None):
        quota, _ = TokenQuota.objects.get_or_create(user_id=request.user.id)

        history = TokenPurchase.objects.filter(
            user_id=request.user.id
        ).values("package_id", "tokens_added", "price_paid_usd", "method", "created_at")[:10]

        return Response({
            "remaining_tokens":  quota.remaining_tokens,
            "total_tokens_used": quota.total_tokens_used,
            "reset_at":          quota.reset_at,
            "packages":          TOKEN_PACKAGES,
            "purchase_history":  list(history),
        })

    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def purchase_tokens(self, request, pk=None):
        package_id      = request.data.get("package_id")
        method          = request.data.get("method", TokenPurchase.MOCK)
        transaction_ref = request.data.get("transaction_ref", "").strip()

        package = TOKEN_PACKAGES_MAP.get(package_id)
        if not package:
            return Response({"error": f"Unknown package: {package_id}"}, status=400)

        ALLOWED_METHODS = [TokenPurchase.MOCK, TokenPurchase.APPLE, TokenPurchase.GOOGLE]
        if method not in ALLOWED_METHODS:
            return Response({"error": f"Unknown purchase method: {method}"}, status=400)

        # Idempotency: RevenueCat webhook and the client may both call this.
        # If we've already processed this transaction, return success without double-crediting.
        if transaction_ref and TokenPurchase.objects.filter(transaction_ref=transaction_ref).exists():
            quota, _ = TokenQuota.objects.get_or_create(user_id=request.user.id)
            return Response({
                "success":          True,
                "tokens_added":     0,
                "remaining_tokens": quota.remaining_tokens,
                "package":          package,
                "duplicate":        True,
            })

        quota, _ = TokenQuota.objects.get_or_create(user_id=request.user.id)
        quota.add_tokens(package["tokens"])

        TokenPurchase.objects.create(
            user_id=request.user.id,
            package_id=package_id,
            tokens_added=package["tokens"],
            price_paid_usd=package["price_usd"],
            method=method,
            transaction_ref=transaction_ref,
        )

        return Response({
            "success":          True,
            "tokens_added":     package["tokens"],
            "remaining_tokens": quota.remaining_tokens,
            "package":          package,
        })
