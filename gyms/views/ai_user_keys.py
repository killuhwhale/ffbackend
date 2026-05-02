import logging
import traceback

import anthropic
import google.generativeai as genai
from openai import OpenAI
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..coach_personalities import get_coach_profile
from .ai import COACH_CHAT_RULES, _JSON_FORMAT_INSTRUCTION, _parse_chat_response
from .ai_helpers import (
    LLM_ANTHROPIC,
    LLM_GEMINI,
    LLM_OPENAI,
    base_schema,
    generate_workout_with_claude,
    generate_workout_with_gemini,
    generate_workout_with_openai,
    tools,
)
from .helpers import check_users_workouts_and_completed_today, is_member
from .permissions import SelfActionPermission

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {
    "claude": LLM_ANTHROPIC,
    "anthropic": LLM_ANTHROPIC,
    "gemini": LLM_GEMINI,
    "gpt": LLM_OPENAI,
    "openai": LLM_OPENAI,
}


def _provider_from_request(request):
    provider = (request.data.get("provider") or "").strip().lower()
    api_key = (request.data.get("api_key") or "").strip()

    if provider not in SUPPORTED_PROVIDERS:
        return None, None, Response({"error": "Unsupported AI provider"}, status=400)

    if not api_key:
        return None, None, Response({"error": "API key is required"}, status=400)

    return SUPPORTED_PROVIDERS[provider], api_key, None


def _claude_client(api_key):
    return anthropic.Anthropic(api_key=api_key)


def _openai_client(api_key):
    return OpenAI(api_key=api_key)


class AIUserKeyViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["POST"], permission_classes=[SelfActionPermission])
    def create_workout(self, request, pk=None):
        if not is_member(request) and not check_users_workouts_and_completed_today(request):
            return Response(
                {"error": "Daily workout limit reached. Upgrade your membership to create more workouts."},
                status=403,
            )

        provider, api_key, error = _provider_from_request(request)
        if error:
            return error

        prompt = request.data.get("prompt")
        scheme_type_text = request.data.get("scheme_type_text")
        userMaxes = request.data.get("userMaxes")
        lastWorkoutGroups = request.data.get("lastWorkoutGroups")

        if not prompt:
            return Response({"error": "No prompt given"}, status=400)

        try:
            if provider == LLM_OPENAI:
                result = generate_workout_with_openai(
                    client=_openai_client(api_key),
                    tools=tools,
                    max_tokens=16_384,
                    prompt=prompt,
                    scheme_type_text=scheme_type_text,
                    userMaxes=userMaxes,
                    lastWorkoutGroups=lastWorkoutGroups,
                )
            elif provider == LLM_ANTHROPIC:
                result = generate_workout_with_claude(
                    claude_client=_claude_client(api_key),
                    base_schema=base_schema,
                    max_tokens=16_384,
                    prompt=prompt,
                    scheme_type_text=scheme_type_text,
                    userMaxes=userMaxes,
                    lastWorkoutGroups=lastWorkoutGroups,
                )
            elif provider == LLM_GEMINI:
                result = generate_workout_with_gemini(
                    base_schema=base_schema,
                    max_tokens=16_384,
                    prompt=prompt,
                    scheme_type_text=scheme_type_text,
                    userMaxes=userMaxes,
                    lastWorkoutGroups=lastWorkoutGroups,
                    api_key=api_key,
                )
            else:
                return Response({"error": "Unsupported AI provider"}, status=400)

            return Response({"data": result["data"]})
        except Exception as e:
            logger.error("[user-key/create_workout] provider=%s\n%s", provider, traceback.format_exc())
            return Response({"data": "", "error": str(e)}, status=500)

    @action(detail=False, methods=["POST"], permission_classes=[SelfActionPermission])
    def chat(self, request, pk=None):
        provider, api_key, error = _provider_from_request(request)
        if error:
            return error

        message = request.data.get("message", "").strip()
        history = request.data.get("history", [])
        coach_type = request.data.get("coach_type", "Fitness Coach")
        goals = request.data.get("goals", [])
        fitness_info = request.data.get("fitness_info", "")
        memory_context = request.data.get("memory_context", "").strip()

        if not message:
            return Response({"error": "No message provided"}, status=400)

        coach_profile = get_coach_profile(coach_type)
        memory_section = (
            f"\n\n## What you know about this athlete\n{memory_context}"
            if memory_context
            else ""
        )
        system_prompt = (
            f"{COACH_CHAT_RULES}\n\n"
            f"---\n\n"
            f"{coach_profile}\n\n"
            f"---\n\n"
            f"## This Athlete\n"
            f"Goals: {', '.join(goals) if goals else 'general fitness'}.\n"
            f"Background: {fitness_info}."
            f"{memory_section}"
            f"{_JSON_FORMAT_INSTRUCTION}"
        )

        try:
            if provider == LLM_OPENAI:
                messages = [{"role": "system", "content": system_prompt}]
                messages += [{"role": m["role"], "content": m["content"]} for m in history]
                messages.append({"role": "user", "content": message})
                resp = _openai_client(api_key).chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.6,
                    messages=messages,
                    max_tokens=450,
                    response_format={"type": "json_object"},
                )
                raw = resp.choices[0].message.content.strip()

            elif provider == LLM_ANTHROPIC:
                claude_messages = [{"role": m["role"], "content": m["content"]} for m in history]
                claude_messages.append({"role": "user", "content": message})
                resp = _claude_client(api_key).messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2000,
                    system=system_prompt,
                    messages=claude_messages,
                )
                raw = resp.content[0].text.strip() if resp.content else ""

            elif provider == LLM_GEMINI:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    "gemini-2.0-flash",
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
                chat_session = model.start_chat(history=gemini_history)
                resp = chat_session.send_message(message, generation_config=config)
                raw = resp.text.strip()

            else:
                return Response({"error": "Unsupported AI provider"}, status=400)

            reply, memory_update = _parse_chat_response(raw)
            if not reply:
                return Response({"error": "Coach returned an empty response. Please try again."}, status=500)

            return Response({"reply": reply, "memory_update": memory_update})
        except Exception as e:
            logger.error("[user-key/chat] provider=%s\n%s", provider, traceback.format_exc())
            return Response({"error": f"Chat error: {str(e)}"}, status=500)
