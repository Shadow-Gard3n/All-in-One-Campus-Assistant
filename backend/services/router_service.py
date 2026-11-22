from bson import ObjectId

from database import departments_collection
from services.llm import generate_json


# ============================================================
# GET AI DEPARTMENTS
# ============================================================

async def get_ai_departments(
    organisation_id
):
    """
    Get all AI-enabled departments belonging
    to this organisation.
    """

    # --------------------------------------------------------
    # Convert organisation ID to ObjectId
    # --------------------------------------------------------

    if isinstance(
        organisation_id,
        str
    ):
        try:
            organisation_id = ObjectId(
                organisation_id
            )
        except Exception:
            return []

    # --------------------------------------------------------
    # MongoDB query
    # --------------------------------------------------------

    cursor = departments_collection.find({

        "organisation_id":
            organisation_id,

        "bot_enabled":
            True,

        "is_active":
            True
    })

    departments = []

    async for department in cursor:

        print(
            "✅ FOUND DEPARTMENT:",
            department
        )

        departments.append({

            "id":
                str(department["_id"]),

            "name":
                department["name"],

            "description":
                department.get(
                    "description",
                    ""
                ),

            "rules":
                department.get(
                    "rules",
                    []
                )
        })

    print(
        "📋 FINAL AI DEPARTMENTS:",
        departments
    )

    return departments


# ============================================================
# ROUTE QUESTION
# ============================================================

async def route_question(
    question: str,
    organisation_id
):
    """
    USER QUESTION
          ↓
       ROUTER
          ↓
    Department-specific tasks
    """

    print("\n")
    print("=" * 80)
    print("🔀 ROUTER")
    print("=" * 80)

    # --------------------------------------------------------
    # Get departments
    # --------------------------------------------------------

    departments = await get_ai_departments(
        organisation_id
    )

    # --------------------------------------------------------
    # No departments
    # --------------------------------------------------------

    if not departments:

        print(
            "❌ No AI-enabled departments found"
        )

        return {

            "routes": [],

            "overall_confidence":
                0.0,

            "needs_clarification":
                True
        }

    # --------------------------------------------------------
    # Department information
    # --------------------------------------------------------

    department_information = []

    for department in departments:

        department_information.append({

            "id":
                department["id"],

            "name":
                department["name"],

            "description":
                department.get(
                    "description",
                    ""
                )
        })

    # --------------------------------------------------------
    # Router prompt
    # --------------------------------------------------------

    prompt = f"""
You are the routing and planning agent
for OneDesk AI.

Your job is NOT to answer the user's question.

Your job is to:

1. Understand the user's complete question.
2. Split it into separate tasks if necessary.
3. Decide which department should handle each task.
4. A single question can belong to multiple departments.
5. Give every route a confidence score from 0 to 1.
6. If the question is too ambiguous, set
   needs_clarification to true.

AVAILABLE DEPARTMENTS:

{department_information}

USER QUESTION:

{question}

IMPORTANT RULES:

- Do not answer the question.
- Do not invent departments.
- Use ONLY the provided department IDs.
- If multiple departments are required,
  create multiple routes.
- Preserve the meaning of the user's question.
- Do not duplicate the same task.
- A password reset / computer / software /
  account access question normally belongs to IT.
- HR-related employee policy questions belong to HR.
- Salary, reimbursement, payment and financial
  questions belong to Finance.
- Greetings such as "hi" alone should not be routed.
- Confidence must be between 0 and 1.

Return ONLY valid JSON.

Required format:

{{
    "routes": [
        {{
            "department_id": "...",
            "department_name": "...",
            "question": "...",
            "confidence": 0.95
        }}
    ],
    "overall_confidence": 0.95,
    "needs_clarification": false
}}
"""

    # --------------------------------------------------------
    # Call LLM abstraction
    # --------------------------------------------------------

    try:

        result = await generate_json(
            prompt=prompt,
            temperature=0.0
        )

        print(
            "🔀 ROUTER RESULT:",
            result
        )

        return result

    except Exception as error:

        print(
            "❌ Router LLM error:",
            error
        )

        return {

            "routes": [],

            "overall_confidence":
                0.0,

            "needs_clarification":
                True
        }

# from database import departments_collection
# from services.gemini import route_user_question
# from bson import ObjectId


# async def get_ai_departments(organisation_id):
#     cursor = departments_collection.find({
#         "organisation_id": ObjectId(organisation_id),
#         "bot_enabled": True
#     })

#     departments = []

#     async for department in cursor:
#         print("✅ FOUND DEPARTMENT:", department)

#         departments.append({
#             "id": str(department["_id"]),
#             "name": department["name"],
#             "description": department.get("description", "")
#         })

#     print("📋 FINAL AI DEPARTMENTS:", departments)

#     return departments


# async def route_question(
#     question: str,
#     organisation_id: str
# ):
#     """
#     USER QUESTION
#         ↓
#     ROUTER
#         ↓
#     Department-specific tasks
#     """

#     departments = await get_ai_departments(
#         organisation_id
#     )

#     if not departments:

#         return {
#             "routes": [],
#             "overall_confidence": 0.0,
#             "needs_clarification": True
#         }

#     result = await route_user_question(
#         question=question,
#         departments=departments
#     )

#     return result