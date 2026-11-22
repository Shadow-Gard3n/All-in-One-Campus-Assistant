from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import conversations_collection

from schemas.conversation import SendMessageRequest

from utils.dependencies import require_roles

from services.orchestrator import process_user_question


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)


# ============================================================
# HELPER
# ============================================================

def to_object_id(value):
    """
    Safely convert a value to MongoDB ObjectId.
    """

    if isinstance(value, ObjectId):
        return value

    try:
        return ObjectId(str(value))
    except Exception:
        return None


# ============================================================
# CREATE EMPTY CONVERSATION
# ============================================================

@router.post("")
async def create_conversation(
    current_user=Depends(
        require_roles(
            "user",
            "support_agent"
        )
    )
):

    organisation_id = current_user.get(
        "organisation_id"
    )

    if not organisation_id:
        raise HTTPException(
            status_code=403,
            detail="User is not part of an organisation"
        )

    now = datetime.now(timezone.utc)

    conversation = {
        "user_id": current_user["_id"],
        "organisation_id": organisation_id,

        "status": "open",

        "assigned_agent_id": None,

        "routes": [],

        "tasks": [],

        "messages": [],

        "created_at": now,
        "updated_at": now
    }

    result = await conversations_collection.insert_one(
        conversation
    )

    return {
        "id": str(result.inserted_id),
        "status": "open",
        "messages": [],
        "tasks": [],
        "created_at": now,
        "updated_at": now
    }


# ============================================================
# GET ALL CONVERSATIONS
# ============================================================

@router.get("")
async def get_conversations(
    current_user=Depends(
        require_roles(
            "user",
            "support_agent"
        )
    )
):

    cursor = (
        conversations_collection
        .find({
            "user_id": current_user["_id"]
        })
        .sort(
            "updated_at",
            -1
        )
    )

    conversations = []

    async for conversation in cursor:

        messages = conversation.get(
            "messages",
            []
        )

        first_message = (
            messages[0]["message"]
            if messages
            else ""
        )

        conversations.append({
            "id": str(
                conversation["_id"]
            ),

            "status": conversation.get(
                "status",
                "open"
            ),

            "title": (
                first_message[:80]
                if first_message
                else "New Conversation"
            ),

            "created_at": conversation.get(
                "created_at"
            ),

            "updated_at": conversation.get(
                "updated_at"
            )
        })

    return conversations


# ============================================================
# GET ONE CONVERSATION
# ============================================================

@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,

    current_user=Depends(
        require_roles(
            "user",
            "support_agent"
        )
    )
):

    conversation_object_id = to_object_id(
        conversation_id
    )

    if not conversation_object_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID"
        )

    conversation = (
        await conversations_collection.find_one({
            "_id": conversation_object_id,
            "user_id": current_user["_id"]
        })
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    return {
        "id": str(
            conversation["_id"]
        ),

        "status": conversation.get(
            "status",
            "open"
        ),

        "messages": conversation.get(
            "messages",
            []
        ),

        "tasks": conversation.get(
            "tasks",
            []
        ),

        "routes": conversation.get(
            "routes",
            []
        ),

        "created_at": conversation.get(
            "created_at"
        ),

        "updated_at": conversation.get(
            "updated_at"
        )
    }


# ============================================================
# SEND MESSAGE
# ============================================================

@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,

    data: SendMessageRequest,

    current_user=Depends(
        require_roles(
            "user",
            "support_agent"
        )
    )
):

    print("\n")
    print("=" * 80)
    print("🚀 NEW MESSAGE")
    print("=" * 80)

    print(
        f"Question: {data.message}"
    )

    print(
        f"Conversation ID: "
        f"{conversation_id}"
    )

    # ========================================================
    # 1. VALIDATE CONVERSATION ID
    # ========================================================

    conversation_object_id = to_object_id(
        conversation_id
    )

    if not conversation_object_id:

        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID"
        )

    # ========================================================
    # 2. FIND CONVERSATION
    # ========================================================

    conversation = (
        await conversations_collection.find_one({
            "_id": conversation_object_id,
            "user_id": current_user["_id"]
        })
    )

    if not conversation:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    # ========================================================
    # 3. CHECK STATUS
    # ========================================================

    if conversation.get(
        "status"
    ) == "waiting_for_agent":

        raise HTTPException(
            status_code=400,
            detail=(
                "This conversation is waiting "
                "for a support agent."
            )
        )

    # ========================================================
    # 4. ORGANISATION
    # ========================================================

    organisation_id = conversation.get(
        "organisation_id"
    )

    if not organisation_id:

        raise HTTPException(
            status_code=400,
            detail=(
                "Conversation does not have "
                "an organisation."
            )
        )

    print(
        f"Organisation ID: "
        f"{organisation_id}"
    )

    # ========================================================
    # 5. GET CONVERSATION HISTORY
    # ========================================================

    history = conversation.get(
        "messages",
        []
    )

    print(
        f"Conversation history messages: "
        f"{len(history)}"
    )

    # ========================================================
    # 6. SAVE USER MESSAGE
    # ========================================================

    now = datetime.now(
        timezone.utc
    )

    user_message = {
        "sender": "user",
        "message": data.message,
        "created_at": now
    }

    await conversations_collection.update_one(
        {
            "_id": conversation_object_id
        },
        {
            "$push": {
                "messages": user_message
            },
            "$set": {
                "status": "processing",
                "updated_at": now
            }
        }
    )

    # ========================================================
    # 7. RUN ORCHESTRATOR
    # ========================================================

    print("\n")
    print("=" * 80)
    print("🧠 STARTING ORCHESTRATOR")
    print("=" * 80)

    try:

        result = await process_user_question(
            question=data.message,

            organisation_id=organisation_id,

            conversation_history=history
        )

    except Exception as error:

        print("\n❌ ORCHESTRATOR ERROR")
        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        # ----------------------------------------------------
        # Save failure state
        # ----------------------------------------------------

        error_message = (
            "I couldn't process your request "
            "right now. Please try again."
        )

        await conversations_collection.update_one(
            {
                "_id": conversation_object_id
            },
            {
                "$push": {
                    "messages": {
                        "sender": "ai",
                        "message": error_message,
                        "created_at": datetime.now(
                            timezone.utc
                        ),
                        "confidence": 0.0,
                        "needs_human": True,
                        "type": "error"
                    }
                },

                "$set": {
                    "status": "waiting_for_agent",
                    "updated_at": datetime.now(
                        timezone.utc
                    )
                }
            }
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process the message."
            )
        )

    # ========================================================
    # 8. RESULT FROM ORCHESTRATOR
    # ========================================================

    final_answer = result.get(
        "answer",
        ""
    )

    final_confidence = float(
        result.get(
            "confidence",
            0.0
        )
    )

    needs_human = bool(
        result.get(
            "needs_human",
            False
        )
    )

    needs_clarification = bool(
        result.get(
            "needs_clarification",
            False
        )
    )

    status = result.get(
        "status",
        "resolved"
    )

    tasks = result.get(
        "tasks",
        []
    )

    department_results = result.get(
        "department_results",
        []
    )

    sources = result.get(
        "sources",
        []
    )

    print("\n")
    print("=" * 80)
    print("✅ ORCHESTRATOR RESULT")
    print("=" * 80)

    print(
        f"Status: {status}"
    )

    print(
        f"Confidence: {final_confidence}"
    )

    print(
        f"Needs human: {needs_human}"
    )

    print(
        f"Needs clarification: "
        f"{needs_clarification}"
    )

    print(
        f"Tasks: {len(tasks)}"
    )

    # ========================================================
    # 9. BUILD AI MESSAGE
    # ========================================================

    ai_message = {
        "sender": "ai",

        "message": final_answer,

        "created_at": datetime.now(
            timezone.utc
        ),

        "confidence": final_confidence,

        "needs_human": needs_human,

        "needs_clarification":
            needs_clarification,

        "type": (
            "clarification"
            if needs_clarification
            else (
                "handoff"
                if needs_human
                else "answer"
            )
        ),

        "sources": sources
    }

    # ========================================================
    # 10. SAVE AI RESULT
    # ========================================================

    update_data = {
        "status": status,

        "tasks": tasks,

        "department_results":
            department_results,

        "updated_at":
            datetime.now(timezone.utc)
    }

    # Keep routes for backwards compatibility
    update_data["routes"] = [
        {
            "department_id":
                task.get("department_id"),

            "department_name":
                task.get("department_name"),

            "confidence":
                task.get("confidence", 0.0)
        }

        for task in tasks
    ]

    await conversations_collection.update_one(
        {
            "_id": conversation_object_id
        },
        {
            "$push": {
                "messages": ai_message
            },

            "$set": update_data
        }
    )

    # ========================================================
    # 11. GET UPDATED CONVERSATION
    # ========================================================

    updated_conversation = (
        await conversations_collection.find_one({
            "_id": conversation_object_id
        })
    )

    # ========================================================
    # 12. LOG
    # ========================================================

    print("\n")
    print("=" * 80)
    print("🏁 FINAL ONEDESK RESULT")
    print("=" * 80)

    print(
        f"Status: {status}"
    )

    print(
        f"Confidence: {final_confidence}"
    )

    print(
        f"Needs human: {needs_human}"
    )

    print(
        f"Tasks: {len(tasks)}"
    )

    print(
        f"Sources: {len(sources)}"
    )

    print(
        f"\nAnswer:\n{final_answer}"
    )

    print("=" * 80)

    # ========================================================
    # 13. RETURN TO FRONTEND
    # ========================================================

    return {
        "id": str(
            conversation_object_id
        ),

        "message": final_answer,

        "status": status,

        "needs_human":
            needs_human,

        "needs_clarification":
            needs_clarification,

        "confidence":
            final_confidence,

        "tasks":
            tasks,

        "department_results":
            department_results,

        "routes":
            update_data["routes"],

        "sources":
            sources,

        "messages":
            updated_conversation.get(
                "messages",
                []
            )
    }


# ============================================================
# GET PENDING CONVERSATIONS
# ============================================================

@router.get("/pending")
async def get_pending_conversations(
    current_user=Depends(
        require_roles(
            "user",
            "support_agent"
        )
    )
):

    cursor = (
        conversations_collection
        .find({
            "user_id":
                current_user["_id"],

            "status":
                "waiting_for_agent"
        })
        .sort(
            "updated_at",
            -1
        )
    )

    conversations = []

    async for conversation in cursor:

        messages = conversation.get(
            "messages",
            []
        )

        first_question = ""

        for message in messages:

            if message.get(
                "sender"
            ) == "user":

                first_question = message.get(
                    "message",
                    ""
                )

                break

        conversations.append({

            "id": str(
                conversation["_id"]
            ),

            "title": conversation.get(
                "title",
                first_question[:80]
                or "Support Request"
            ),

            "first_question":
                first_question,

            "status":
                conversation.get(
                    "status",
                    "waiting_for_agent"
                ),

            "created_at":
                conversation.get(
                    "created_at"
                ),

            "updated_at":
                conversation.get(
                    "updated_at"
                )
        })

    return {
        "conversations":
            conversations
    }

    
# from datetime import datetime, timezone

# from bson import ObjectId
# from fastapi import APIRouter, Depends, HTTPException

# from database import (
#     conversations_collection,
#     departments_collection
# )

# from schemas.conversation import (
#     SendMessageRequest
# )

# from utils.dependencies import (
#     require_roles
# )

# from services.gemini import (
#     route_user_question,
#     generate_department_response,
#     synthesize_department_responses
# )

# from services.department_skills import (
#     DEPARTMENT_SKILLS,
#     GENERIC_DEPARTMENT_PROMPT
# )

# # ============================================================
# # RAG
# # ============================================================

# try:

#     from services.rag import search_knowledge

#     RAG_AVAILABLE = True

# except ImportError:

#     search_knowledge = None

#     RAG_AVAILABLE = False


# router = APIRouter(
#     prefix="/conversations",
#     tags=["Conversations"]
# )


# # ============================================================
# # HELPER: OBJECT ID
# # ============================================================

# def to_object_id(value):

#     if isinstance(value, ObjectId):

#         return value

#     try:

#         return ObjectId(
#             str(value)
#         )

#     except Exception:

#         return None


# # ============================================================
# # HELPER: DEPARTMENT SKILL
# # ============================================================

# def get_department_skill(
#     department_name: str,
#     department_description: str = ""
# ):

#     skill = DEPARTMENT_SKILLS.get(
#         department_name.upper()
#     )

#     if skill:

#         return skill

#     return {

#         "description": (
#             department_description
#             or
#             f"Handles requests related to "
#             f"{department_name}."
#         ),

#         "prompt":
#             GENERIC_DEPARTMENT_PROMPT.format(

#                 department_name=
#                     department_name,

#                 department_description=(
#                     department_description
#                     or
#                     f"Handles requests related to "
#                     f"{department_name}."
#                 )

#             )

#     }


# # ============================================================
# # HELPER: RAG SEARCH
# # ============================================================

# async def get_knowledge_context(
#     question: str,
#     organisation_id,
#     department_id
# ):

#     print("\n")
#     print("=" * 80)
#     print("📚 KNOWLEDGE CONTEXT")
#     print("=" * 80)

#     print(
#         f"Department ID: {department_id}"
#     )

#     print(
#         f"Question: {question}"
#     )

#     # --------------------------------------------------------
#     # RAG unavailable
#     # --------------------------------------------------------

#     if not RAG_AVAILABLE:

#         print(
#             "⚠️ RAG is not available."
#         )

#         return "", []

#     # --------------------------------------------------------
#     # Execute RAG
#     # --------------------------------------------------------

#     try:

#         results = await search_knowledge(

#             question=question,

#             organisation_id=
#                 organisation_id,

#             department_id=
#                 department_id,

#             limit=5

#         )

#     except Exception as error:

#         print(
#             "\n❌ RAG ERROR"
#         )

#         print(
#             f"{type(error).__name__}: "
#             f"{error}"
#         )

#         return "", []

#     # --------------------------------------------------------
#     # No results
#     # --------------------------------------------------------

#     if not results:

#         print(
#             "\n⚠️ RAG found no relevant "
#             "knowledge."
#         )

#         return "", []

#     # --------------------------------------------------------
#     # Build Gemini context
#     # --------------------------------------------------------

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

#         if not text:

#             continue

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

#         # ----------------------------------------------------
#         # Source label
#         # ----------------------------------------------------

#         source_text = (
#             f"Source {index}: "
#             f"{filename}"
#         )

#         if page_number is not None:

#             source_text += (
#                 f", Page {page_number}"
#             )

#         source_text += (
#             f", Similarity: {score:.4f}"
#         )

#         # ----------------------------------------------------
#         # Context
#         # ----------------------------------------------------

#         context_parts.append(

#             f"{source_text}\n"
#             f"{text}"

#         )

#         # ----------------------------------------------------
#         # Metadata
#         # ----------------------------------------------------

#         sources.append({

#             "document":
#                 filename,

#             "page":
#                 page_number,

#             "score":
#                 score

#         })

#     # --------------------------------------------------------
#     # Nothing usable
#     # --------------------------------------------------------

#     if not context_parts:

#         print(
#             "⚠️ RAG returned results, "
#             "but no usable text."
#         )

#         return "", []

#     # --------------------------------------------------------
#     # Final context
#     # --------------------------------------------------------

#     knowledge_context = (
#         "\n\n".join(
#             context_parts
#         )
#     )

#     print("\n✅ KNOWLEDGE CONTEXT CREATED")

#     print(
#         f"Chunks used: "
#         f"{len(context_parts)}"
#     )

#     print(
#         f"Context size: "
#         f"{len(knowledge_context)} characters"
#     )

#     print("\n📄 SOURCES USED:")

#     for source in sources:

#         print(
#             f"  → {source['document']} "
#             f"| Page: {source['page']} "
#             f"| Score: {source['score']}"
#         )

#     print("=" * 80)

#     return (
#         knowledge_context,
#         sources
#     )


# # ============================================================
# # CREATE EMPTY CONVERSATION
# # ============================================================

# @router.post("")
# async def create_conversation(

#     current_user=Depends(
#         require_roles(
#             "user",
#             "support_agent"
#         )
#     )

# ):

#     organisation_id = (
#         current_user.get(
#             "organisation_id"
#         )
#     )

#     if not organisation_id:

#         raise HTTPException(

#             status_code=403,

#             detail=(
#                 "User is not part of an organisation"
#             )

#         )

#     now = datetime.now(
#         timezone.utc
#     )

#     conversation = {

#         "user_id":
#             current_user["_id"],

#         "organisation_id":
#             organisation_id,

#         "status":
#             "open",

#         "assigned_agent_id":
#             None,

#         "routes":
#             [],

#         "messages":
#             [],

#         "created_at":
#             now,

#         "updated_at":
#             now

#     }

#     result = (
#         await conversations_collection.insert_one(
#             conversation
#         )
#     )

#     return {

#         "id":
#             str(result.inserted_id),

#         "status":
#             "open",

#         "messages":
#             [],

#         "created_at":
#             now,

#         "updated_at":
#             now

#     }


# # ============================================================
# # GET ALL CONVERSATIONS
# # ============================================================

# @router.get("")
# async def get_conversations(

#     current_user=Depends(
#         require_roles(
#             "user",
#             "support_agent"
#         )
#     )

# ):

#     cursor = (
#         conversations_collection
#         .find({
#             "user_id":
#                 current_user["_id"]
#         })
#         .sort(
#             "updated_at",
#             -1
#         )
#     )

#     conversations = []

#     async for conversation in cursor:

#         messages = conversation.get(
#             "messages",
#             []
#         )

#         first_message = (

#             messages[0]["message"]

#             if messages

#             else ""

#         )

#         conversations.append({

#             "id":
#                 str(conversation["_id"]),

#             "status":
#                 conversation.get(
#                     "status",
#                     "open"
#                 ),

#             "title": (

#                 first_message[:80]

#                 if first_message

#                 else "New Conversation"

#             ),

#             "created_at":
#                 conversation[
#                     "created_at"
#                 ],

#             "updated_at":
#                 conversation[
#                     "updated_at"
#                 ]

#         })

#     return conversations


# # ============================================================
# # GET ONE CONVERSATION
# # ============================================================

# @router.get("/{conversation_id}")
# async def get_conversation(

#     conversation_id: str,

#     current_user=Depends(
#         require_roles(
#             "user",
#             "support_agent"
#         )
#     )

# ):

#     try:

#         conversation_object_id = ObjectId(
#             conversation_id
#         )

#     except Exception:

#         raise HTTPException(

#             status_code=400,

#             detail="Invalid conversation ID"

#         )

#     conversation = (
#         await conversations_collection.find_one({

#             "_id":
#                 conversation_object_id,

#             "user_id":
#                 current_user["_id"]

#         })
#     )

#     if not conversation:

#         raise HTTPException(

#             status_code=404,

#             detail="Conversation not found"

#         )

#     return {

#         "id":
#             str(conversation["_id"]),

#         "status":
#             conversation.get(
#                 "status",
#                 "open"
#             ),

#         "messages":
#             conversation.get(
#                 "messages",
#                 []
#             ),

#         "routes":
#             conversation.get(
#                 "routes",
#                 []
#             ),

#         "created_at":
#             conversation[
#                 "created_at"
#             ],

#         "updated_at":
#             conversation[
#                 "updated_at"
#             ]

#     }


# # ============================================================
# # SEND MESSAGE
# # ============================================================

# @router.post("/{conversation_id}/messages")
# async def send_message(

#     conversation_id: str,

#     data: SendMessageRequest,

#     current_user=Depends(
#         require_roles(
#             "user",
#             "support_agent"
#         )
#     )

# ):

#     print("\n\n")
#     print("#" * 80)
#     print("🚀 NEW MESSAGE")
#     print("#" * 80)

#     print(
#         f"Question: {data.message}"
#     )

#     print(
#         f"Conversation ID: "
#         f"{conversation_id}"
#     )

#     # ========================================================
#     # 1. VALIDATE CONVERSATION ID
#     # ========================================================

#     try:

#         conversation_object_id = ObjectId(
#             conversation_id
#         )

#     except Exception:

#         raise HTTPException(

#             status_code=400,

#             detail="Invalid conversation ID"

#         )

#     # ========================================================
#     # 2. FIND CONVERSATION
#     # ========================================================

#     conversation = (
#         await conversations_collection.find_one({

#             "_id":
#                 conversation_object_id,

#             "user_id":
#                 current_user["_id"]

#         })
#     )

#     if not conversation:

#         raise HTTPException(

#             status_code=404,

#             detail="Conversation not found"

#         )

#     # ========================================================
#     # 3. CHECK STATUS
#     # ========================================================

#     if conversation.get(
#         "status"
#     ) == "waiting_for_agent":

#         raise HTTPException(

#             status_code=400,

#             detail=(
#                 "This conversation is waiting "
#                 "for a support agent."
#             )

#         )

#     # ========================================================
#     # 4. ORGANISATION
#     # ========================================================

#     organisation_id = (
#         conversation.get(
#             "organisation_id"
#         )
#     )

#     if not organisation_id:

#         raise HTTPException(

#             status_code=400,

#             detail=(
#                 "Conversation does not have "
#                 "an organisation."
#             )

#         )

#     print(
#         f"Organisation ID: "
#         f"{organisation_id}"
#     )

#     # ========================================================
#     # 5. CURRENT TIME
#     # ========================================================

#     now = datetime.now(
#         timezone.utc
#     )

#     # ========================================================
#     # 6. CONVERSATION HISTORY
#     # ========================================================

#     history = conversation.get(
#         "messages",
#         []
#     )

#     print(
#         f"Conversation history messages: "
#         f"{len(history)}"
#     )

#     # ========================================================
#     # 7. LOAD ACTIVE DEPARTMENTS
#     # ========================================================

#     print("\n")
#     print("=" * 80)
#     print("🏢 LOADING AI DEPARTMENTS")
#     print("=" * 80)

#     department_cursor = (
#         departments_collection.find({

#             "organisation_id":
#                 organisation_id,

#             "bot_enabled":
#                 True

#         })
#     )

#     departments = []

#     async for department in department_cursor:

#         departments.append({

#             "id":
#                 str(department["_id"]),

#             "name":
#                 department.get(
#                     "name",
#                     "Department"
#                 ),

#             "description":
#                 department.get(
#                     "description",
#                     ""
#                 )

#         })

#     for department in departments:

#         print(
#             f"  • {department['name']} "
#             f"({department['id']})"
#         )

#     print(
#         f"\nTotal AI departments: "
#         f"{len(departments)}"
#     )

#     # ========================================================
#     # 8. CHECK DEPARTMENTS
#     # ========================================================

#     if not departments:

#         raise HTTPException(

#             status_code=400,

#             detail=(
#                 "No AI-enabled departments are "
#                 "available for this organisation."
#             )

#         )

#     # ========================================================
#     # 9. ROUTER
#     # ========================================================

#     print("\n")
#     print("=" * 80)
#     print("🔀 ROUTING QUESTION")
#     print("=" * 80)

#     print(
#         f"Question:\n"
#         f"  {data.message}"
#     )

#     print("\n🤖 Calling Gemini Router...")

#     routing_result = (
#         await route_user_question(

#             question=data.message,

#             departments=departments

#         )
#     )

#     routes = routing_result.get(
#         "routes",
#         []
#     )

#     overall_routing_confidence = (
#         routing_result.get(
#             "overall_confidence",
#             0
#         )
#     )

#     needs_clarification = (
#         routing_result.get(
#             "needs_clarification",
#             False
#         )
#     )

#     print("\n")
#     print("✅ ROUTER RESULT")
#     print("-" * 80)

#     print(
#         f"Overall confidence: "
#         f"{overall_routing_confidence}"
#     )

#     print(
#         f"Needs clarification: "
#         f"{needs_clarification}"
#     )

#     print(
#         f"Routes selected: "
#         f"{len(routes)}"
#     )

#     for index, route in enumerate(
#         routes,
#         start=1
#     ):

#         print(
#             f"\n[{index}] "
#             f"{route.get('department_name')}"
#         )

#         print(
#             f"    Department ID: "
#             f"{route.get('department_id')}"
#         )

#         print(
#             f"    Sub-question: "
#             f"{route.get('sub_question')}"
#         )

#         print(
#             f"    Confidence: "
#             f"{route.get('confidence')}"
#         )

#     print("-" * 80)

#     # ========================================================
#     # 10. CLARIFICATION
#     # ========================================================

#     if (
#         needs_clarification
#         or
#         not routes
#     ):

#         print(
#             "\n⚠️ ROUTER REQUESTED "
#             "CLARIFICATION"
#         )

#         ai_message = (
#             "I'm not completely sure which department "
#             "can best help with that. Could you provide "
#             "a little more detail about what you need?"
#         )

#         new_messages = [

#             {
#                 "sender":
#                     "user",

#                 "message":
#                     data.message,

#                 "created_at":
#                     now

#             },

#             {
#                 "sender":
#                     "ai",

#                 "message":
#                     ai_message,

#                 "created_at":
#                     now,

#                 "type":
#                     "clarification",

#                 "confidence":
#                     overall_routing_confidence,

#                 "needs_human":
#                     False

#             }

#         ]

#         await conversations_collection.update_one(

#             {
#                 "_id":
#                     conversation_object_id
#             },

#             {

#                 "$push": {

#                     "messages": {

#                         "$each":
#                             new_messages

#                     }

#                 },

#                 "$set": {

#                     "updated_at":
#                         now

#                 }

#             }

#         )

#         return {

#             "id":
#                 str(
#                     conversation_object_id
#                 ),

#             "message":
#                 ai_message,

#             "status":
#                 "open",

#             "needs_human":
#                 False,

#             "needs_clarification":
#                 True,

#             "confidence":
#                 overall_routing_confidence,

#             "routes":
#                 routes,

#             "sources":
#                 []

#         }

#     # ========================================================
#     # 11. PROCESS EACH DEPARTMENT
#     # ========================================================

#     department_responses = []

#     conversation_routes = []

#     print("\n")
#     print("#" * 80)
#     print("🏢 PROCESSING DEPARTMENT ROUTES")
#     print("#" * 80)

#     for route_index, route in enumerate(
#         routes,
#         start=1
#     ):

#         department_id = (
#             route.get(
#                 "department_id"
#             )
#         )

#         department_name = (
#             route.get(
#                 "department_name",
#                 "Department"
#             )
#         )

#         sub_question = (
#             route.get(
#                 "sub_question",
#                 data.message
#             )
#         )

#         routing_confidence = (
#             route.get(
#                 "confidence",
#                 0
#             )
#         )

#         # ----------------------------------------------------
#         # Department header
#         # ----------------------------------------------------

#         print("\n")
#         print("-" * 80)
#         print(
#             f"🏢 DEPARTMENT ROUTE "
#             f"{route_index}/{len(routes)}"
#         )
#         print("-" * 80)

#         print(
#             f"Department: "
#             f"{department_name}"
#         )

#         print(
#             f"Department ID: "
#             f"{department_id}"
#         )

#         print(
#             f"Sub-question: "
#             f"{sub_question}"
#         )

#         print(
#             f"Routing confidence: "
#             f"{routing_confidence}"
#         )

#         # ----------------------------------------------------
#         # Find department
#         # ----------------------------------------------------

#         department_object_id = (
#             to_object_id(
#                 department_id
#             )
#         )

#         if not department_object_id:

#             print(
#                 "❌ Invalid department ID"
#             )

#             continue

#         department = (
#             await departments_collection.find_one({

#                 "_id":
#                     department_object_id,

#                 "organisation_id":
#                     organisation_id,

#                 "bot_enabled":
#                     True

#             })
#         )

#         if not department:

#             print(
#                 "❌ Department not found "
#                 "or bot disabled"
#             )

#             continue

#         actual_department_name = (
#             department.get(
#                 "name",
#                 department_name
#             )
#         )

#         # ----------------------------------------------------
#         # Department skill
#         # ----------------------------------------------------

#         skill = get_department_skill(

#             department_name=
#                 actual_department_name,

#             department_description=
#                 department.get(
#                     "description",
#                     ""
#                 )

#         )

#         print(
#             f"\n🧠 Department skill: "
#             f"{actual_department_name}"
#         )

#         # ----------------------------------------------------
#         # RAG SEARCH
#         # ----------------------------------------------------

#         print(
#             f"\n📚 Searching knowledge "
#             f"for {actual_department_name}..."
#         )

#         (
#             knowledge_context,
#             sources
#         ) = await get_knowledge_context(

#             question=
#                 sub_question,

#             organisation_id=
#                 organisation_id,

#             department_id=
#                 department_object_id

#         )

#         print(
#             f"\nRAG chunks supplied to AI: "
#             f"{len(sources)}"
#         )

#         # ----------------------------------------------------
#         # Department AI
#         # ----------------------------------------------------

#         print("\n")
#         print("-" * 80)
#         print("🤖 DEPARTMENT AI")
#         print("-" * 80)

#         print(
#             f"Department: "
#             f"{actual_department_name}"
#         )

#         print(
#             f"Question: "
#             f"{sub_question}"
#         )

#         print(
#             f"RAG sources: "
#             f"{len(sources)}"
#         )

#         print(
#             f"Knowledge context size: "
#             f"{len(knowledge_context)} characters"
#         )

#         print(
#             "\n🤖 Calling Gemini..."
#         )

#         ai_result = (
#             await generate_department_response(

#                 question=
#                     sub_question,

#                 department_name=
#                     actual_department_name,

#                 department_prompt=
#                     skill["prompt"],

#                 knowledge_context=
#                     knowledge_context,

#                 conversation_history=
#                     history

#             )
#         )

#         # ----------------------------------------------------
#         # Department result
#         # ----------------------------------------------------

#         answer_confidence = (
#             ai_result.get(
#                 "confidence",
#                 0
#             )
#         )

#         needs_human = (
#             ai_result.get(
#                 "needs_human",
#                 False
#             )
#         )

#         if routing_confidence < 0.50:

#             needs_human = True

#         model_sources = (
#             ai_result.get(
#                 "sources",
#                 []
#             )
#         )

#         if not isinstance(
#             model_sources,
#             list
#         ):

#             model_sources = []

#         # Actual RAG sources are more trustworthy
#         # than sources invented by the model.

#         if sources:

#             model_sources = sources

#         print("\n")
#         print("✅ DEPARTMENT RESPONSE")
#         print("-" * 80)

#         print(
#             f"Department: "
#             f"{actual_department_name}"
#         )

#         print(
#             f"Answer:\n"
#             f"{ai_result.get('answer', '')}"
#         )

#         print(
#             f"\nConfidence: "
#             f"{answer_confidence}"
#         )

#         print(
#             f"Needs human: "
#             f"{needs_human}"
#         )

#         print(
#             f"Reason: "
#             f"{ai_result.get('reason', '')}"
#         )

#         print(
#             "\nSources:"
#         )

#         for source in model_sources:

#             print(
#                 f"  → {source}"
#             )

#         print("-" * 80)

#         # ----------------------------------------------------
#         # Save result
#         # ----------------------------------------------------

#         department_response = {

#             "department_id":
#                 str(
#                     department_object_id
#                 ),

#             "department_name":
#                 actual_department_name,

#             "sub_question":
#                 sub_question,

#             "routing_confidence":
#                 routing_confidence,

#             "answer":
#                 ai_result.get(
#                     "answer",
#                     ""
#                 ),

#             "confidence":
#                 answer_confidence,

#             "needs_human":
#                 needs_human,

#             "reason":
#                 ai_result.get(
#                     "reason",
#                     ""
#                 ),

#             "sources":
#                 model_sources

#         }

#         department_responses.append(
#             department_response
#         )

#         conversation_routes.append({

#             "department_id":
#                 str(
#                     department_object_id
#                 ),

#             "department_name":
#                 actual_department_name,

#             "confidence":
#                 routing_confidence

#         })

#     # ========================================================
#     # 12. NO DEPARTMENT RESPONSE
#     # ========================================================

#     if not department_responses:

#         print(
#             "\n❌ NO DEPARTMENT COULD "
#             "GENERATE A RESPONSE"
#         )

#         ai_message = (
#             "I couldn't find a suitable department "
#             "to handle your question."
#         )

#         new_messages = [

#             {
#                 "sender":
#                     "user",

#                 "message":
#                     data.message,

#                 "created_at":
#                     now

#             },

#             {
#                 "sender":
#                     "ai",

#                 "message":
#                     ai_message,

#                 "created_at":
#                     now,

#                 "type":
#                     "handoff",

#                 "confidence":
#                     0.0,

#                 "needs_human":
#                     True

#             }

#         ]

#         await conversations_collection.update_one(

#             {
#                 "_id":
#                     conversation_object_id
#             },

#             {

#                 "$push": {

#                     "messages": {

#                         "$each":
#                             new_messages

#                     }

#                 },

#                 "$set": {

#                     "status":
#                         "waiting_for_agent",

#                     "updated_at":
#                         now

#                 }

#             }

#         )

#         return {

#             "id":
#                 str(
#                     conversation_object_id
#                 ),

#             "message":
#                 ai_message,

#             "status":
#                 "waiting_for_agent",

#             "needs_human":
#                 True,

#             "needs_clarification":
#                 False,

#             "confidence":
#                 0.0,

#             "routes":
#                 [],

#             "sources":
#                 []

#         }

#     # ========================================================
#     # 13. SINGLE DEPARTMENT
#     # ========================================================

#     if len(
#         department_responses
#     ) == 1:

#         print("\n")
#         print("=" * 80)
#         print("🎯 SINGLE DEPARTMENT RESPONSE")
#         print("=" * 80)

#         final_result = (
#             department_responses[0]
#         )

#         final_answer = (
#             final_result.get(
#                 "answer",
#                 ""
#             )
#         )

#         final_confidence = (
#             final_result.get(
#                 "confidence",
#                 0
#             )
#         )

#         final_needs_human = (
#             final_result.get(
#                 "needs_human",
#                 False
#             )
#         )

#         final_reason = (
#             final_result.get(
#                 "reason",
#                 ""
#             )
#         )

#         final_sources = (
#             final_result.get(
#                 "sources",
#                 []
#             )
#         )

#     # ========================================================
#     # 14. MULTIPLE DEPARTMENTS
#     # ========================================================

#     else:

#         print("\n")
#         print("=" * 80)
#         print("🔗 MULTI-DEPARTMENT SYNTHESIS")
#         print("=" * 80)

#         print(
#             f"Original question:\n"
#             f"{data.message}"
#         )

#         print(
#             f"\nDepartment responses: "
#             f"{len(department_responses)}"
#         )

#         for index, response in enumerate(
#             department_responses,
#             start=1
#         ):

#             print("\n")
#             print(
#                 f"--- RESPONSE {index} ---"
#             )

#             print(
#                 f"Department: "
#                 f"{response.get('department_name')}"
#             )

#             print(
#                 f"Sub-question: "
#                 f"{response.get('sub_question')}"
#             )

#             print(
#                 f"Answer:\n"
#                 f"{response.get('answer')}"
#             )

#             print(
#                 f"Confidence: "
#                 f"{response.get('confidence')}"
#             )

#             print(
#                 f"Needs human: "
#                 f"{response.get('needs_human')}"
#             )

#             print(
#                 f"Sources: "
#                 f"{response.get('sources')}"
#             )

#         print("\n🤖 Sending responses to Gemini for synthesis...")

#         final_result = (
#             await synthesize_department_responses(

#                 question=
#                     data.message,

#                 department_responses=
#                     department_responses,

#                 conversation_history=
#                     history

#             )
#         )

#         final_answer = (
#             final_result.get(
#                 "answer",
#                 ""
#             )
#         )

#         final_confidence = (
#             final_result.get(
#                 "confidence",
#                 0
#             )
#         )

#         final_needs_human = (
#             final_result.get(
#                 "needs_human",
#                 False
#             )
#         )

#         final_reason = (
#             final_result.get(
#                 "reason",
#                 ""
#             )
#         )

#         final_sources = (
#             final_result.get(
#                 "sources",
#                 []
#             )
#         )

#         # ----------------------------------------------------
#         # Combine real RAG sources
#         # ----------------------------------------------------

#         all_sources = []

#         for response in (
#             department_responses
#         ):

#             for source in response.get(
#                 "sources",
#                 []
#             ):

#                 all_sources.append(
#                     source
#                 )

#         if all_sources:

#             final_sources = (
#                 all_sources
#             )

#         print("\n")
#         print("✅ SYNTHESIS RESULT")
#         print("-" * 80)

#         print(
#             f"Final answer:\n"
#             f"{final_answer}"
#         )

#         print(
#             f"\nConfidence: "
#             f"{final_confidence}"
#         )

#         print(
#             f"Needs human: "
#             f"{final_needs_human}"
#         )

#         print(
#             f"Reason: "
#             f"{final_reason}"
#         )

#         print(
#             "\nFinal sources:"
#         )

#         for source in final_sources:

#             print(
#                 f"  → {source}"
#             )

#         print("=" * 80)

#     # ========================================================
#     # 15. FINAL SAFETY CHECK
#     # ========================================================

#     try:

#         final_confidence = float(
#             final_confidence
#         )

#     except (
#         TypeError,
#         ValueError
#     ):

#         final_confidence = 0.0

#     final_confidence = max(

#         0.0,

#         min(
#             1.0,
#             final_confidence
#         )

#     )

#     if final_confidence < 0.50:

#         final_needs_human = True

#     # ========================================================
#     # 16. DETERMINE STATUS
#     # ========================================================

#     if final_needs_human:

#         status = (
#             "waiting_for_agent"
#         )

#         if final_answer:

#             ai_message = (
#                 final_answer
#                 + "\n\n"
#                 + "I couldn't verify all of the "
#                 "information reliably, so this "
#                 "question needs human review."
#             )

#         else:

#             ai_message = (
#                 "I couldn't find enough reliable "
#                 "information to answer this accurately. "
#                 "This question needs human review."
#             )

#     else:

#         status = "open"

#         ai_message = (
#             final_answer
#             or
#             "I couldn't generate a reliable answer."
#         )

#     # ========================================================
#     # 17. SAVE USER + AI MESSAGES
#     # ========================================================

#     new_messages = [

#         {
#             "sender":
#                 "user",

#             "message":
#                 data.message,

#             "created_at":
#                 now

#         },

#         {
#             "sender":
#                 "ai",

#             "message":
#                 ai_message,

#             "created_at":
#                 now,

#             "type": (
#                 "handoff"
#                 if final_needs_human
#                 else "answer"
#             ),

#             "confidence":
#                 final_confidence,

#             "needs_human":
#                 final_needs_human,

#             "needs_clarification":
#                 False,

#             "reason":
#                 final_reason,

#             "routes":
#                 conversation_routes,

#             "sources":
#                 final_sources

#         }

#     ]

#     # ========================================================
#     # 18. UPDATE CONVERSATION
#     # ========================================================

#     await conversations_collection.update_one(

#         {
#             "_id":
#                 conversation_object_id
#         },

#         {

#             "$push": {

#                 "messages": {

#                     "$each":
#                         new_messages

#                 }

#             },

#             "$set": {

#                 "status":
#                     status,

#                 "routes":
#                     conversation_routes,

#                 "updated_at":
#                     now

#             }

#         }

#     )

#     # ========================================================
#     # 19. GET UPDATED CONVERSATION
#     # ========================================================

#     updated_conversation = (
#         await conversations_collection.find_one(
#             {
#                 "_id":
#                     conversation_object_id
#             }
#         )
#     )

#     # ========================================================
#     # 20. FINAL LOG
#     # ========================================================

#     print("\n")
#     print("#" * 80)
#     print("🏁 FINAL ONEDESK RESULT")
#     print("#" * 80)

#     print(
#         f"Status: {status}"
#     )

#     print(
#         f"Confidence: "
#         f"{final_confidence}"
#     )

#     print(
#         f"Needs human: "
#         f"{final_needs_human}"
#     )

#     print(
#         f"Departments: "
#         f"{[r['department_name'] for r in conversation_routes]}"
#     )

#     print(
#         f"Sources: "
#         f"{len(final_sources)}"
#     )

#     print(
#         f"\nAnswer:\n"
#         f"{ai_message}"
#     )

#     print("#" * 80)
#     print("🏁 REQUEST COMPLETE")
#     print("#" * 80)
#     print("\n")

#     # ========================================================
#     # 21. RETURN TO FRONTEND
#     # ========================================================

#     return {

#         "id":
#             str(
#                 conversation_object_id
#             ),

#         "message":
#             ai_message,

#         "status":
#             status,

#         "needs_human":
#             final_needs_human,

#         "needs_clarification":
#             False,

#         "confidence":
#             final_confidence,

#         "routes":
#             conversation_routes,

#         "sources":
#             final_sources,

#         "messages":
#             updated_conversation.get(
#                 "messages",
#                 []
#             )

#     }

# @router.get("/conversations/pending")
# async def get_pending_conversations(
#     current_user=Depends(get_current_user)
# ):
#     user_id = str(current_user["_id"])

#     cursor = conversations_collection.find({
#         "user_id": user_id,
#         "status": "waiting_for_agent"
#     }).sort(
#         "updated_at",
#         -1
#     )

#     conversations = []

#     async for conversation in cursor:

#         messages = conversation.get(
#             "messages",
#             []
#         )

#         first_question = ""

#         for message in messages:
#             if message.get("sender") == "user":
#                 first_question = message.get(
#                     "message",
#                     ""
#                 )
#                 break

#         conversations.append({
#             "id": str(conversation["_id"]),

#             "title": conversation.get(
#                 "title",
#                 first_question[:80] or "Support Request"
#             ),

#             "first_question": first_question,

#             "status": conversation.get(
#                 "status",
#                 "waiting_for_agent"
#             ),

#             "created_at": conversation.get(
#                 "created_at"
#             ),

#             "updated_at": conversation.get(
#                 "updated_at"
#             )
#         })

#     return {
#         "conversations": conversations
#     }