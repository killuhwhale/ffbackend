from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from gyms.models import TokenQuota
from .ai_helpers import (
    LLM,
    LLM_ANTHROPIC,
    LLM_GEMINI,
    LLM_OPENAI,
    base_schema,
    claude_client,
    client,
    count_message_tokens,
    generate_workout_with_claude,
    generate_workout_with_gemini,
    generate_workout_with_openai,
    tools,
)
from .permissions import SelfActionPermission


class AIViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['POST'], permission_classes=[SelfActionPermission])
    def create_workout(self, request, pk=None):

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
            {"role": "system", "content": "You are a helpful super awesome Sports Strength and Conditioning Coach, your athlete needs a tailored workout plan that will map to their workout app so only structure output in json."},
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
