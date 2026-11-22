from services.llm import generate_json


async def synthesize_department_results(
    *,
    original_question: str,
    department_results: list
):
    """
    Merge all department responses into
    one user-facing response.
    """

    print("\n")
    print("=" * 80)
    print("🧩 SYNTHESIZER")
    print("=" * 80)

    print(
        f"Original question: "
        f"{original_question}"
    )

    print(
        f"Department results: "
        f"{len(department_results)}"
    )

    # --------------------------------------------------------
    # Clean department responses
    # --------------------------------------------------------

    responses = []

    for result in department_results:

        responses.append({

            "department_id":
                result.get(
                    "department_id"
                ),

            "department_name":
                result.get(
                    "department_name"
                ),

            "question":
                result.get(
                    "question"
                ),

            "answer":
                result.get(
                    "answer"
                ),

            "confidence":
                result.get(
                    "confidence",
                    0
                ),

            "needs_human":
                result.get(
                    "needs_human",
                    False
                ),

            "reason":
                result.get(
                    "reason"
                ),

            "sources":
                result.get(
                    "sources",
                    []
                )
        })

    # --------------------------------------------------------
    # Synthesizer prompt
    # --------------------------------------------------------

    prompt = f"""
You are the final response synthesizer
for OneDesk AI.

ORIGINAL USER QUESTION:

{original_question}

DEPARTMENT RESPONSES:

{responses}

Your job is to create ONE clear
user-facing response.

RULES:

1. Answer every part that was successfully
   answered.

2. Preserve information provided by
   department agents.

3. Do not invent organisation policies.

4. Do not contradict department answers.

5. If one or more departments require
   human support, clearly tell the user
   which part requires support.

6. Do not hide unresolved parts.

7. Do not mention:
   - routing
   - prompts
   - RAG
   - embeddings
   - internal agents
   - implementation details
   - models

8. Keep the answer concise and useful.

9. Return ONLY valid JSON.

Required format:

{{
    "answer": "final user-facing answer",
    "confidence": 0.90,
    "sources": []
}}
"""

    try:

        result = await generate_json(

            prompt=
                prompt,

            temperature=
                0.1
        )

        # ----------------------------------------------------
        # Use actual department sources
        # ----------------------------------------------------

        all_sources = []

        for response in responses:

            all_sources.extend(
                response.get(
                    "sources",
                    []
                )
            )

        result["sources"] = (
            all_sources
        )

        return result

    except Exception as error:

        print(
            "❌ Synthesizer LLM error:",
            error
        )

        # ----------------------------------------------------
        # Safe fallback
        # ----------------------------------------------------

        answers = []

        for item in department_results:

            answer = item.get(
                "answer"
            )

            if answer:

                answers.append(
                    answer
                )

        return {

            "answer":
                "\n\n".join(
                    answers
                ),

            "confidence":
                0.0,

            "sources":
                []
        }

# from services.gemini import synthesize_response


# async def synthesize_department_results(
#     *,
#     original_question: str,
#     department_results: list
# ):
#     """
#     Merge all department responses into one
#     user-facing response.
#     """

#     print("\n")
#     print("=" * 80)
#     print("🧩 SYNTHESIZER")
#     print("=" * 80)

#     print(
#         f"Original question: {original_question}"
#     )

#     print(
#         f"Department results: "
#         f"{len(department_results)}"
#     )

#     # --------------------------------------------------------
#     # Build clean input for Gemini
#     # --------------------------------------------------------

#     responses = []

#     for result in department_results:

#         responses.append({
#             "department_id": result.get(
#                 "department_id"
#             ),

#             "department_name": result.get(
#                 "department_name"
#             ),

#             "question": result.get(
#                 "question"
#             ),

#             "answer": result.get(
#                 "answer"
#             ),

#             "confidence": result.get(
#                 "confidence",
#                 0
#             ),

#             "needs_human": result.get(
#                 "needs_human",
#                 False
#             ),

#             "reason": result.get(
#                 "reason"
#             ),

#             "sources": result.get(
#                 "sources",
#                 []
#             )
#         })

#     # --------------------------------------------------------
#     # Call existing Gemini synthesizer
#     # --------------------------------------------------------

#     result = await synthesize_response(
#         original_question=original_question,
#         department_responses=responses
#     )

#     return result