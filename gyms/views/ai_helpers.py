import copy
import json
import anthropic
import tiktoken
from openai import OpenAI
import google.generativeai as genai

from instafitAPI import settings

LLM_ANTHROPIC = "anthropic"
LLM_GEMINI = "gemini"
LLM_OPENAI = "openai"
LLM = LLM_OPENAI  # TODO() GET User Choice

with open("gyms/create_workout_schema.json") as f:
    base_schema = json.load(f)

# Initialize the Anthropic client
claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
genai.configure(api_key=settings.GEMINI_API_KEY)

tools = [
    {
        "type": "function",
        "function": {
           "name": base_schema["name"],  # make sure your JSON includes this
            "description": base_schema.get("description", "No description."),
            "parameters": base_schema["parameters"]
        }
    }
]

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_workout_with_claude(claude_client, base_schema, max_tokens, prompt, scheme_type_text, userMaxes, lastWorkoutGroups) -> dict:
    claude_tools = [
        {
            "name": base_schema["name"],
            "description": base_schema.get("description", "Generate workout items."),
            "input_schema": base_schema["parameters"]
        }
    ]

    system_prompt = "You are a helpful super awesome Sports Strength and Conditioning Coach, your athlete needs a tailored workout plan that will map to their workout app so only structure output in json."

    user_content = (
        f"Workout maxes: {userMaxes}\n"
        f"My Last Couple of Workouts: {lastWorkoutGroups}\n"
        f"Workout Scheme Style: {scheme_type_text}\n"
        f"User Goal: {prompt}"
    )

    response = claude_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        tools=claude_tools,
        tool_choice={"type": "tool", "name": base_schema["name"]},
        messages=[
            {"role": "user", "content": user_content}
        ]
    )

    # Extract Token Usage
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    total_tokens = input_tokens + output_tokens

    # Extract Data
    workout_data = {}
    for content_block in response.content:
        if content_block.type == "tool_use" and content_block.name == base_schema["name"]:
            workout_data = content_block.input
            break

    return {
        "data": workout_data,
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens
        }
    }


def clean_gemini_schema(schema):
    """Recursively removes unsupported keys like 'default' for Gemini."""
    if isinstance(schema, dict):
        schema.pop("default", None)
        for key, value in schema.items():
            clean_gemini_schema(value)
    elif isinstance(schema, list):
        for item in schema:
            clean_gemini_schema(item)
    return schema


def generate_workout_with_gemini(base_schema, max_tokens, prompt, scheme_type_text, userMaxes, lastWorkoutGroups) -> dict:
    # 1. Create a deep copy so we don't break the schema for OpenAI/Claude
    gemini_schema = copy.deepcopy(base_schema["parameters"])

    # 2. Fix the "unhashable type: 'list'" error (if it still exists in your schema)
    try:
        gemini_schema["properties"]["items"]["items"]["properties"]["name"]["type"] = "string"
    except KeyError:
        pass

    # 3. FIX: Strip out all the "default" keys recursively
    gemini_schema = clean_gemini_schema(gemini_schema)

    system_instruction = "You are a helpful super awesome Sports Strength and Conditioning Coach, your athlete needs a tailored workout plan that will map to their workout app so only structure output in json. " + base_schema.get("description", "")

    model = genai.GenerativeModel(
        'gemini-2.0-flash',
        system_instruction=system_instruction
    )

    config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=gemini_schema,
        temperature=0.7,
        max_output_tokens=max_tokens
    )

    user_content = (
        f"Workout maxes: {userMaxes}\n"
        f"My Last Couple of Workouts: {lastWorkoutGroups}\n"
        f"Workout Scheme Style: {scheme_type_text}\n"
        f"User Goal: {prompt}"
    )

    response = model.generate_content(
        user_content,
        generation_config=config
    )

    # Extract Token Usage
    input_tokens = response.usage_metadata.prompt_token_count
    output_tokens = response.usage_metadata.candidates_token_count
    total_tokens = response.usage_metadata.total_token_count

    # Extract Data
    try:
        workout_data = json.loads(response.text)
    except json.JSONDecodeError as e:
        print("Error parsing Gemini JSON:", e)
        workout_data = {}

    return {
        "data": workout_data,
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens
        }
    }


def generate_workout_with_openai(client, tools, max_tokens, prompt, scheme_type_text, userMaxes, lastWorkoutGroups) -> dict:
    messages = [
        {"role": "system", "content": "You are a helpful super awesome Sports Strength and Conditioning Coach, your athlete needs a tailored workout plan that will map to their workout app so only structure output in json."},
        {"role": "user", "content": f"Workout maxes: {userMaxes}"},
        {"role": "user", "content": f"MyLast Couple of Workouts: {lastWorkoutGroups}"},
        {"role": "user", "content": f"Workout Scheme Style: {scheme_type_text}"},
        {"role": "user", "content": f"User Goal: {prompt}"},
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        messages=messages,
        max_tokens=max_tokens,
        tools=tools,
        tool_choice="auto",
    )

    # Extract Token Usage
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens

    # Extract Data
    tool_call = response.choices[0].message.tool_calls[0]
    workout_data = json.loads(tool_call.function.arguments)

    return {
        "data": workout_data,
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens
        }
    }


def count_tokens(text: str, model="gpt-3.5-turbo") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


def count_message_tokens(messages: list, model="gpt-3.5-turbo") -> int:
    enc = tiktoken.encoding_for_model(model)
    tokens = 0
    for m in messages:
        tokens += 4  # base cost per message (OpenAI rule of thumb)
        tokens += len(enc.encode(m["content"]))
    tokens += 2  # for assistant priming
    return tokens + 2  ## Good measure
