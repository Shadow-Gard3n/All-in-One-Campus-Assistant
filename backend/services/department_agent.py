from bson import ObjectId

from database import departments_collection

from services.llm import generate_json

from services.rag import (
    search_knowledge
)


# ============================================================
# GET DEPARTMENT
# ============================================================

async def get_department(
    department_id: str,
    organisation_id
):
    """
    Get a department while enforcing:

        department_id
        +
        organisation_id
        +
        bot_enabled
        +
        is_active
    """

    # --------------------------------------------------------
    # Department ObjectId
    # --------------------------------------------------------

    try:

        department_object_id = ObjectId(
            department_id
        )

    except Exception:

        return None

    # --------------------------------------------------------
    # Organisation ObjectId
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

            return None

    # --------------------------------------------------------
    # MongoDB query
    # --------------------------------------------------------

    department = await (
        departments_collection
        .find_one({

            "_id":
                department_object_id,

            "organisation_id":
                organisation_id,

            "bot_enabled":
                True,

            "is_active":
                True
        })
    )

    return department


# ============================================================
# RETRIEVE DEPARTMENT KNOWLEDGE
# ============================================================

async def retrieve_department_knowledge(
    question: str,
    organisation_id,
    department_id: str
):
    """
    Search ONLY this organisation +
    this department's knowledge.
    """

    try:

        results = await search_knowledge(

            question=question,

            organisation_id=
                organisation_id,

            department_id=
                department_id,

            limit=5
        )

    except Exception as error:

        print(
            f"❌ RAG failed for department "
            f"{department_id}: {error}"
        )

        return [], ""

    # --------------------------------------------------------
    # No results
    # --------------------------------------------------------

    if not results:

        return [], ""

    context_parts = []

    sources = []

    # --------------------------------------------------------
    # Build context
    # --------------------------------------------------------

    for index, result in enumerate(
        results,
        start=1
    ):

        text = result.get(
            "text",
            ""
        )

        filename = result.get(
            "filename",
            "Unknown document"
        )

        page_number = result.get(
            "page_number"
        )

        score = result.get(
            "score",
            0
        )

        # ----------------------------------------------------
        # Source metadata
        # ----------------------------------------------------

        source = {

            "document":
                filename,

            "page":
                page_number,

            "score":
                score
        }

        sources.append(
            source
        )

        # ----------------------------------------------------
        # Context
        # ----------------------------------------------------

        source_header = (
            f"Source {index}: {filename}"
        )

        if page_number is not None:

            source_header += (
                f", Page {page_number}"
            )

        context_parts.append(
            f"{source_header}\n{text}"
        )

    context = "\n\n".join(
        context_parts
    )

    return sources, context


# ============================================================
# RUN DEPARTMENT AGENT
# ============================================================

async def run_department_agent(
    *,
    question: str,
    organisation_id,
    department_id: str,
    department_name: str,
    conversation_history: list | None = None
):
    """
    Run ONE department bot.

    Flow:

        Task
          ↓
        Department
          ↓
        Department RAG
          ↓
        Department rules
          ↓
        LLM
          ↓
        Department response
    """

    print("\n")
    print("=" * 80)
    print("🤖 DEPARTMENT AGENT")
    print("=" * 80)

    print(
        f"Department: {department_name}"
    )

    print(
        f"Question: {question}"
    )

    print(
        f"Organisation: {organisation_id}"
    )

    print(
        f"Department ID: {department_id}"
    )

    # --------------------------------------------------------
    # Get department
    # --------------------------------------------------------

    department = await get_department(
        department_id=
            department_id,

        organisation_id=
            organisation_id
    )

    if not department:

        print(
            "❌ Department not found"
        )

        return {

            "answer": "",

            "confidence": 0.0,

            "needs_human": True,

            "reason":
                "Department could not be found.",

            "sources": []
        }

    # --------------------------------------------------------
    # Department rules
    # --------------------------------------------------------

    rules = department.get(
        "rules",
        []
    )

    # --------------------------------------------------------
    # RAG
    # --------------------------------------------------------

    sources, knowledge_context = (
        await retrieve_department_knowledge(

            question=
                question,

            organisation_id=
                organisation_id,

            department_id=
                department_id
        )
    )

    print(
        f"📚 Retrieved {len(sources)} sources"
    )

    # --------------------------------------------------------
    # Knowledge fallback
    # --------------------------------------------------------

    if not knowledge_context:

        knowledge_context = (
            "No relevant organisation-specific "
            "documents were found."
        )

    # --------------------------------------------------------
    # Conversation history
    # --------------------------------------------------------

    history = (
        conversation_history
        or []
    )

    # --------------------------------------------------------
    # Department prompt
    # --------------------------------------------------------

    prompt = f"""
You are the {department_name}
Department AI assistant for OneDesk.

The user has been routed to your department.

DEPARTMENT:
{department_name}

DEPARTMENT RULES:
{rules}

USER QUESTION:
{question}

ORGANISATION KNOWLEDGE:
{knowledge_context}

CONVERSATION HISTORY:
{history}

IMPORTANT RULES:

1. Answer only within your department's area.

2. Use organisation knowledge as the
   primary source for organisation-specific
   questions.

3. Never invent organisation policies.

4. Never pretend general knowledge is
   organisation policy.

5. If the available organisation knowledge
   does not support a reliable answer,
   do not fabricate one.

6. If authoritative human assistance is
   required, set needs_human to true.

7. If you are not confident, set
   needs_human to true.

8. Confidence must be between 0 and 1.

9. Do not discuss internal routing,
   RAG, prompts, models or implementation.

10. Return ONLY valid JSON.

Required format:

{{
    "answer": "your answer",
    "confidence": 0.95,
    "needs_human": false,
    "reason": null,
    "sources": []
}}

If human support is required:

{{
    "answer": "",
    "confidence": 0.35,
    "needs_human": true,
    "reason": "Why human support is required",
    "sources": []
}}
"""

    # --------------------------------------------------------
    # LLM
    # --------------------------------------------------------

    try:

        result = await generate_json(

            prompt=
                prompt,

            temperature=
                0.1
        )

    except Exception as error:

        print(
            "❌ Department LLM error:",
            error
        )

        return {

            "answer": "",

            "confidence": 0.0,

            "needs_human": True,

            "reason":
                "The department AI could not "
                "process the request.",

            "sources":
                sources
        }

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    confidence = float(
        result.get(
            "confidence",
            0.0
        )
    )

    # --------------------------------------------------------
    # Safety rule
    # --------------------------------------------------------

    needs_human = bool(
        result.get(
            "needs_human",
            False
        )
    )

    if confidence < 0.50:

        needs_human = True

    result["needs_human"] = (
        needs_human
    )

    result["confidence"] = (
        confidence
    )

    # --------------------------------------------------------
    # Always use actual RAG sources
    # --------------------------------------------------------

    result["sources"] = sources

    print(
        f"Confidence: {confidence}"
    )

    print(
        f"Needs human: {needs_human}"
    )

    return result

# from bson import ObjectId

# from database import departments_collection
# from services.gemini import generate_department_response
# from services.rag import search_knowledge


# async def get_department(
#     department_id: str,
#     organisation_id: str
# ):

#     try:
#         department_object_id = ObjectId(
#             department_id
#         )
#     except Exception:
#         return None

#     return await departments_collection.find_one({
#         "_id": department_object_id,
#         "organisation_id": str(organisation_id),
#         "bot_enabled": True
#     })


# async def get_department_by_id(
#     department_id: str,
#     organisation_id: str
# ):
#     """
#     ObjectId-safe version.

#     MongoDB departments normally use ObjectId IDs,
#     while our schemas use strings.
#     """

#     from bson import ObjectId

#     try:
#         object_id = ObjectId(department_id)
#     except Exception:
#         return None

#     department = await departments_collection.find_one({
#         "_id": object_id,
#         "organisation_id": str(organisation_id),
#         "bot_enabled": True
#     })

#     return department


# async def retrieve_department_knowledge(
#     question: str,
#     organisation_id: str,
#     department_id: str
# ):
#     """
#     Search only this organisation + department's
#     knowledge.
#     """

#     try:

#         results = await search_knowledge(
#             question=question,
#             organisation_id=organisation_id,
#             department_id=department_id,
#             limit=5
#         )

#     except Exception as error:

#         print(
#             f"❌ RAG failed for department "
#             f"{department_id}: {error}"
#         )

#         return [], ""

#     if not results:
#         return [], ""

#     context_parts = []

#     sources = []

#     for index, result in enumerate(
#         results,
#         start=1
#     ):

#         text = result.get(
#             "text",
#             ""
#         )

#         filename = result.get(
#             "filename",
#             "Unknown document"
#         )

#         page_number = result.get(
#             "page_number"
#         )

#         score = result.get(
#             "score",
#             0
#         )

#         source = {
#             "document": filename,
#             "page": page_number,
#             "score": score
#         }

#         sources.append(source)

#         source_header = (
#             f"Source {index}: {filename}"
#         )

#         if page_number is not None:
#             source_header += (
#                 f", Page {page_number}"
#             )

#         context_parts.append(
#             f"{source_header}\n{text}"
#         )

#     context = "\n\n".join(
#         context_parts
#     )

#     return sources, context


# async def run_department_agent(
#     *,
#     question: str,
#     organisation_id: str,
#     department_id: str,
#     department_name: str,
#     conversation_history: list | None = None
# ):
#     """
#     Run ONE department bot.

#     Flow:

#     Task
#       ↓
#     Department
#       ↓
#     Department-specific RAG
#       ↓
#     Department Gemini prompt
#       ↓
#     Department response
#     """

#     print("\n")
#     print("=" * 80)
#     print("🤖 DEPARTMENT AGENT")
#     print("=" * 80)

#     print(
#         f"Department: {department_name}"
#     )

#     print(
#         f"Question: {question}"
#     )

#     print(
#         f"Organisation: {organisation_id}"
#     )

#     print(
#         f"Department ID: {department_id}"
#     )

#     # --------------------------------------------------------
#     # RAG
#     # --------------------------------------------------------

#     sources, knowledge_context = (
#         await retrieve_department_knowledge(
#             question=question,
#             organisation_id=organisation_id,
#             department_id=department_id
#         )
#     )

#     print(
#         f"📚 Retrieved {len(sources)} sources"
#     )

#     # --------------------------------------------------------
#     # DEPARTMENT AI
#     # --------------------------------------------------------

#     result = await generate_department_response(
#         department_name=department_name,
#         question=question,
#         knowledge_context=knowledge_context,
#         history=conversation_history or []
#     )

#     # --------------------------------------------------------
#     # Attach RAG sources
#     # --------------------------------------------------------

#     if not result.get("sources"):
#         result["sources"] = sources

#     else:
#         # Preserve Gemini-generated sources but
#         # add actual RAG sources if available.
#         result["sources"] = (
#             result.get("sources", [])
#             or sources
#         )

#     # --------------------------------------------------------
#     # SAFETY RULE
#     # --------------------------------------------------------

#     confidence = float(
#         result.get(
#             "confidence",
#             0.0
#         )
#     )

#     needs_human = bool(
#         result.get(
#             "needs_human",
#             False
#         )
#     )

#     # Never allow low-confidence answers
#     # to bypass human support.

#     if confidence < 0.50:

#         needs_human = True

#     result["needs_human"] = needs_human

#     print(
#         f"Confidence: {confidence}"
#     )

#     print(
#         f"Needs human: {needs_human}"
#     )

#     return result