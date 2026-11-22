import json

from google import genai
from google.genai import types

from config import settings


# ============================================================
# CONFIGURATION
# ============================================================

MODEL = settings.GEMINI_MODEL


# ============================================================
# CLIENT
# ============================================================

if not settings.GEMINI_API_KEY:

    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set."
    )


client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)


# ============================================================
# JSON HELPER
# ============================================================

def extract_json(
    text: str
):
    """
    Convert model response into JSON.

    Handles responses such as:

    ```json
    {...}
    ```
    """

    text = text.strip()

    if text.startswith("```"):

        lines = text.splitlines()

        if (
            lines
            and lines[0].startswith("```")
        ):
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip()
            == "```"
        ):
            lines = lines[:-1]

        text = "\n".join(
            lines
        )

    return json.loads(
        text
    )


# ============================================================
# GENERATE TEXT
# ============================================================

async def generate_text(
    *,
    prompt: str,
    temperature: float = 0.1
) -> str:

    response = await (
        client.aio.models
        .generate_content(

            model=MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                temperature=
                    temperature
            )
        )
    )

    return response.text


# ============================================================
# GENERATE JSON
# ============================================================

async def generate_json(
    *,
    prompt: str,
    temperature: float = 0.1
) -> dict:

    response = await (
        client.aio.models
        .generate_content(

            model=MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                temperature=
                    temperature,

                response_mime_type=
                    "application/json"
            )
        )
    )

    return extract_json(
        response.text
    )

# import json
# import os

# from google import genai
# from google.genai import types


# # ============================================================
# # CONFIGURATION
# # ============================================================

# MODEL = "gemini-3.7-flash"

# from config import settings

# client = genai.Client(
#     api_key=settings.GEMINI_API_KEY
# )
# if not settings.GEMINI_API_KEY:
#     raise RuntimeError(
#         "GEMINI_API_KEY environment variable is not set."
#     )


# client = genai.Client(
#     api_key=settings.GEMINI_API_KEY
# )


# # ============================================================
# # HELPER
# # ============================================================

# def extract_json(text: str):
#     """
#     Convert Gemini's response into JSON.

#     Handles responses that are wrapped in:
#     ```json
#     {...}
#     ```
#     """

#     text = text.strip()

#     if text.startswith("```"):
#         lines = text.splitlines()

#         if lines[0].startswith("```"):
#             lines = lines[1:]

#         if lines and lines[-1].strip() == "```":
#             lines = lines[:-1]

#         text = "\n".join(lines)

#     return json.loads(text)


# # ============================================================
# # ROUTER
# # ============================================================

# async def route_user_question(
#     *,
#     question: str,
#     departments: list
# ):
#     """
#     Decide which departments should handle the question.

#     The router can split one user question into
#     multiple department-specific tasks.
#     """

#     department_information = []

#     for department in departments:

#         department_information.append({
#             "id": department["id"],
#             "name": department["name"],
#             "description": department.get(
#                 "description",
#                 ""
#             )
#         })

#     prompt = f"""
# You are the routing and planning agent for OneDesk AI.

# Your job is NOT to answer the user's question.

# Your job is to:

# 1. Understand the user's complete question.
# 2. Split it into separate tasks if necessary.
# 3. Decide which department should answer each task.
# 4. A single user question can belong to multiple departments.
# 5. Give each route a confidence score from 0 to 1.
# 6. If the question is too ambiguous to determine the department,
#    set needs_clarification to true.

# Available departments:

# {json.dumps(
#     department_information,
#     indent=2
# )}

# User question:

# {question}

# Return ONLY valid JSON.

# Required format:

# {{
#     "routes": [
#         {{
#             "department_id": "department id",
#             "department_name": "department name",
#             "question": "specific question for this department",
#             "confidence": 0.95
#         }}
#     ],
#     "overall_confidence": 0.95,
#     "needs_clarification": false
# }}

# Rules:

# - Do not answer the question.
# - Do not invent departments.
# - Use only the provided department IDs.
# - If multiple departments are required, create multiple routes.
# - Preserve the meaning of the user's original question.
# - Do not duplicate the same task unnecessarily.
# - Confidence must be between 0 and 1.
# """

#     try:

#         response = await client.aio.models.generate_content(
#             model=MODEL,
#             contents=prompt,
#             config=types.GenerateContentConfig(
#                 temperature=0.1
#             )
#         )

#         result = extract_json(
#             response.text
#         )

#         return result

#     except Exception as error:

#         print(
#             "❌ Router Gemini error:",
#             error
#         )

#         return {
#             "routes": [],
#             "overall_confidence": 0.0,
#             "needs_clarification": True
#         }


# # ============================================================
# # DEPARTMENT AGENT
# # ============================================================

# async def generate_department_response(
#     *,
#     department_name: str,
#     question: str,
#     knowledge_context: str,
#     history: list
# ):
#     """
#     Generate an answer using a specific department's
#     knowledge.

#     This is the actual department bot.
#     """

#     if knowledge_context:

#         knowledge_section = f"""
# ORGANISATION KNOWLEDGE:

# {knowledge_context}

# Use this organisation knowledge as the PRIMARY
# SOURCE for organisation-specific questions.
# """

#     else:

#         knowledge_section = """
# ORGANISATION KNOWLEDGE:

# No relevant organisation-specific documents were found.

# You may provide general guidance when appropriate,
# but DO NOT claim that general information is an
# organisation policy.
# """

#     prompt = f"""
# You are the {department_name} Department AI assistant
# for OneDesk AI.

# The user has been routed to your department.

# Department:
# {department_name}

# User question:
# {question}

# {knowledge_section}

# Conversation history:

# {json.dumps(history, default=str, indent=2)}

# Rules:

# 1. Answer only within your department's area.
# 2. Use organisation knowledge when available.
# 3. Never invent organisation policies.
# 4. Never pretend general knowledge is an organisation policy.
# 5. If the available knowledge does not support a reliable
#    answer, say so.
# 6. If the question requires an authoritative human decision,
#    set needs_human to true.
# 7. If you are not confident in the answer, set needs_human
#    to true.
# 8. Confidence must be between 0 and 1.
# 9. Do not discuss internal routing or implementation.

# Return ONLY valid JSON.

# Format:

# {{
#     "answer": "your answer",
#     "confidence": 0.95,
#     "needs_human": false,
#     "reason": null,
#     "sources": []
# }}

# If human support is required:

# {{
#     "answer": "",
#     "confidence": 0.35,
#     "needs_human": true,
#     "reason": "Why human support is required",
#     "sources": []
# }}
# """

#     try:

#         response = await client.aio.models.generate_content(
#             model=MODEL,
#             contents=prompt,
#             config=types.GenerateContentConfig(
#                 temperature=0.2
#             )
#         )

#         result = extract_json(
#             response.text
#         )

#         confidence = float(
#             result.get(
#                 "confidence",
#                 0.0
#             )
#         )

#         # Safety rule
#         if confidence < 0.50:
#             result["needs_human"] = True

#         return result

#     except Exception as error:

#         print(
#             "❌ Department Gemini error:",
#             error
#         )

#         return {
#             "answer": "",
#             "confidence": 0.0,
#             "needs_human": True,
#             "reason": (
#                 "The department AI could not "
#                 "process the request."
#             ),
#             "sources": []
#         }


# # ============================================================
# # SYNTHESIS
# # ============================================================

# async def synthesize_response(
#     *,
#     original_question: str,
#     department_responses: list
# ):
#     """
#     Combine department responses into one final
#     user-facing answer.
#     """

#     prompt = f"""
# You are the final response synthesizer for OneDesk AI.

# The user asked:

# {original_question}

# The following department agents processed
# different parts of the question:

# {json.dumps(
#     department_responses,
#     default=str,
#     indent=2
# )}

# Your job is to create ONE clear response for the user.

# Rules:

# 1. Answer every part that was successfully answered.
# 2. Preserve information provided by department agents.
# 3. Do not invent organisation policies.
# 4. Do not contradict department answers.
# 5. If one or more departments require human support,
#    clearly tell the user which part requires support.
# 6. Do not hide unresolved parts.
# 7. Do not mention:
#    - routing
#    - prompts
#    - RAG
#    - embeddings
#    - internal agents
#    - implementation details
# 8. Keep the response concise and useful.

# Return ONLY valid JSON.

# Format:

# {{
#     "answer": "final user-facing answer",
#     "confidence": 0.90,
#     "sources": []
# }}
# """

#     try:

#         response = await client.aio.models.generate_content(
#             model=MODEL,
#             contents=prompt,
#             config=types.GenerateContentConfig(
#                 temperature=0.2
#             )
#         )

#         result = extract_json(
#             response.text
#         )

#         return result

#     except Exception as error:

#         print(
#             "❌ Synthesis Gemini error:",
#             error
#         )

#         # Safe fallback
#         answers = []

#         for item in department_responses:

#             if item.get("answer"):
#                 answers.append(
#                     item["answer"]
#                 )

#         return {
#             "answer": "\n\n".join(
#                 answers
#             ),

#             "confidence": 0.0,

#             "sources": []
#         }