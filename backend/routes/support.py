from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import conversations_collection

from schemas.support import (
    SupportQuestionResponse,
    SupportConversationResponse,
    SupportReplyRequest,
    TakeConversationResponse,
    ResolveConversationResponse,
)

from utils.dependencies import require_roles


router = APIRouter(
    prefix="/support",
    tags=["Support"]
)


# ============================================================
# HELPERS
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


def get_agent_organisation_id(current_user):
    """
    Get organisation ID of the support agent.
    """

    organisation_id = current_user.get(
        "organisation_id"
    )

    if not organisation_id:
        raise HTTPException(
            status_code=403,
            detail="Support agent is not part of an organisation."
        )

    return str(organisation_id)


def get_agent_department_id(current_user):
    """
    Get department ID of the support agent.
    """

    department_id = current_user.get(
        "department_id"
    )

    if not department_id:
        raise HTTPException(
            status_code=403,
            detail="Support agent is not assigned to a department."
        )

    return str(department_id)


def task_belongs_to_agent_department(
    task,
    department_id
):
    """
    Check whether a task belongs to
    the support agent's department.
    """

    return str(
        task.get("department_id")
    ) == str(department_id)


# ============================================================
# GET SUPPORT QUEUE
# ============================================================

@router.get("/conversations")
async def get_support_conversations(
    current_user=Depends(
        require_roles("support_agent")
    )
):

    organisation_id = get_agent_organisation_id(
        current_user
    )

    department_id = get_agent_department_id(
        current_user
    )

    cursor = conversations_collection.find({
        "organisation_id": organisation_id,

        "status": "waiting_for_agent",

        "tasks": {
            "$elemMatch": {
                "department_id": department_id,
                "status": "waiting_for_agent",
                "needs_human": True
            }
        }
    }).sort(
        "updated_at",
        -1
    )

    conversations = []

    async for conversation in cursor:

        tasks = conversation.get(
            "tasks",
            []
        )

        # ----------------------------------------------------
        # Only expose tasks for this agent's department
        # ----------------------------------------------------

        department_tasks = [
            task
            for task in tasks
            if task_belongs_to_agent_department(
                task,
                department_id
            )
            and task.get("needs_human") is True
            and task.get("status") == "waiting_for_agent"
        ]

        if not department_tasks:
            continue

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

            "tasks":
                department_tasks,

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


# ============================================================
# GET ONE SUPPORT CONVERSATION
# ============================================================

@router.get(
    "/conversations/{conversation_id}"
)
async def get_support_conversation(
    conversation_id: str,

    current_user=Depends(
        require_roles("support_agent")
    )
):

    organisation_id = get_agent_organisation_id(
        current_user
    )

    department_id = get_agent_department_id(
        current_user
    )

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
            "_id":
                conversation_object_id,

            "organisation_id":
                organisation_id
        })
    )

    if not conversation:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    # --------------------------------------------------------
    # Filter tasks by support agent department
    # --------------------------------------------------------

    tasks = conversation.get(
        "tasks",
        []
    )

    department_tasks = [
        task
        for task in tasks
        if task_belongs_to_agent_department(
            task,
            department_id
        )
    ]

    if not department_tasks:

        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access to "
                "this department's tasks."
            )
        )

    return {

        "id": str(
            conversation["_id"]
        ),

        "status":
            conversation.get(
                "status",
                "open"
            ),

        "tasks":
            department_tasks,

        "messages":
            conversation.get(
                "messages",
                []
            ),

        "created_at":
            conversation.get(
                "created_at"
            ),

        "updated_at":
            conversation.get(
                "updated_at"
            )
    }


# ============================================================
# TAKE A SUPPORT TASK
# ============================================================

@router.post(
    "/conversations/{conversation_id}/take"
)
async def take_conversation(
    conversation_id: str,

    current_user=Depends(
        require_roles("support_agent")
    )
):

    organisation_id = get_agent_organisation_id(
        current_user
    )

    department_id = get_agent_department_id(
        current_user
    )

    agent_id = str(
        current_user["_id"]
    )

    conversation_object_id = to_object_id(
        conversation_id
    )

    if not conversation_object_id:

        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID"
        )

    # --------------------------------------------------------
    # Find conversation
    # --------------------------------------------------------

    conversation = (
        await conversations_collection.find_one({
            "_id":
                conversation_object_id,

            "organisation_id":
                organisation_id
        })
    )

    if not conversation:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    tasks = conversation.get(
        "tasks",
        []
    )

    # --------------------------------------------------------
    # Find first waiting task belonging
    # to this agent's department
    # --------------------------------------------------------

    target_task = None

    for task in tasks:

        if not task_belongs_to_agent_department(
            task,
            department_id
        ):
            continue

        if task.get(
            "status"
        ) != "waiting_for_agent":
            continue

        if not task.get(
            "needs_human",
            False
        ):
            continue

        target_task = task
        break

    if not target_task:

        raise HTTPException(
            status_code=404,
            detail=(
                "No pending support task found "
                "for your department."
            )
        )

    task_id = target_task.get(
        "task_id"
    )

    # --------------------------------------------------------
    # Atomically assign the task
    # --------------------------------------------------------

    result = await conversations_collection.update_one(
        {
            "_id":
                conversation_object_id,

            "organisation_id":
                organisation_id,

            "tasks": {
                "$elemMatch": {
                    "task_id": task_id,

                    "department_id":
                        department_id,

                    "status":
                        "waiting_for_agent",

                    "needs_human":
                        True,

                    "$or": [
                        {
                            "assigned_agent_id":
                                None
                        },
                        {
                            "assigned_agent_id": {
                                "$exists": False
                            }
                        }
                    ]
                }
            }
        },

        {
            "$set": {
                "tasks.$[task].status":
                    "assigned",

                "tasks.$[task].assigned_agent_id":
                    agent_id,

                "status":
                    "assigned",

                "assigned_agent_id":
                    agent_id,

                "updated_at":
                    datetime.now(
                        timezone.utc
                    )
            }
        },

        array_filters=[
            {
                "task.task_id":
                    task_id,

                "task.department_id":
                    department_id
            }
        ]
    )

    if result.modified_count == 0:

        raise HTTPException(
            status_code=409,
            detail=(
                "This support task has already "
                "been taken by another agent."
            )
        )

    updated_conversation = (
        await conversations_collection.find_one({
            "_id":
                conversation_object_id
        })
    )

    updated_tasks = [
        task
        for task in updated_conversation.get(
            "tasks",
            []
        )
        if task_belongs_to_agent_department(
            task,
            department_id
        )
    ]

    return {
        "message":
            "Support task assigned successfully.",

        "conversation_id":
            str(conversation_object_id),

        "agent_id":
            agent_id,

        "tasks":
            updated_tasks
    }


# ============================================================
# REPLY TO SUPPORT TASK
# ============================================================

@router.post(
    "/conversations/{conversation_id}/messages"
)
async def reply_to_conversation(
    conversation_id: str,

    data: SupportReplyRequest,

    current_user=Depends(
        require_roles("support_agent")
    )
):

    organisation_id = get_agent_organisation_id(
        current_user
    )

    department_id = get_agent_department_id(
        current_user
    )

    agent_id = str(
        current_user["_id"]
    )

    conversation_object_id = to_object_id(
        conversation_id
    )

    if not conversation_object_id:

        raise HTTPException(
            status_code=400,
            detail="Invalid conversation ID"
        )

    # --------------------------------------------------------
    # Load conversation
    # --------------------------------------------------------

    conversation = (
        await conversations_collection.find_one({
            "_id":
                conversation_object_id,

            "organisation_id":
                organisation_id
        })
    )

    if not conversation:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    tasks = conversation.get(
        "tasks",
        []
    )

    # --------------------------------------------------------
    # Find task assigned to this agent
    # --------------------------------------------------------

    target_task = None

    for task in tasks:

        if not task_belongs_to_agent_department(
            task,
            department_id
        ):
            continue

        if str(
            task.get(
                "assigned_agent_id"
            )
        ) != agent_id:
            continue

        if task.get(
            "status"
        ) != "assigned":
            continue

        target_task = task
        break

    if not target_task:

        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have an assigned "
                "support task in this conversation."
            )
        )

    task_id = target_task.get(
        "task_id"
    )

    now = datetime.now(
        timezone.utc
    )

    # --------------------------------------------------------
    # Agent message
    # --------------------------------------------------------

    agent_message = {
        "sender": "agent",

        "message":
            data.message,

        "created_at":
            now,

        "agent_id":
            agent_id,

        "department_id":
            department_id,

        "task_id":
            task_id
    }

    # --------------------------------------------------------
    # Update task
    # --------------------------------------------------------

    result = await conversations_collection.update_one(
        {
            "_id":
                conversation_object_id,

            "organisation_id":
                organisation_id,

            "tasks": {
                "$elemMatch": {
                    "task_id":
                        task_id,

                    "department_id":
                        department_id,

                    "assigned_agent_id":
                        agent_id,

                    "status":
                        "assigned"
                }
            }
        },

        {
            "$push": {
                "messages":
                    agent_message
            },

            "$set": {
                "tasks.$[task].status":
                    "resolved",

                "tasks.$[task].answer":
                    data.message,

                "tasks.$[task].needs_human":
                    False,

                "tasks.$[task].assigned_agent_id":
                    agent_id,

                "updated_at":
                    now
            }
        },

        array_filters=[
            {
                "task.task_id":
                    task_id,

                "task.department_id":
                    department_id
            }
        ]
    )

    if result.modified_count == 0:

        raise HTTPException(
            status_code=409,
            detail=(
                "The support task could not "
                "be updated."
            )
        )

    # ========================================================
    # CHECK WHETHER OTHER HUMAN TASKS REMAIN
    # ========================================================

    updated_conversation = (
        await conversations_collection.find_one({
            "_id":
                conversation_object_id
        })
    )

    remaining_human_tasks = [

        task

        for task in updated_conversation.get(
            "tasks",
            []
        )

        if task.get(
            "needs_human",
            False
        )
        and task.get(
            "status"
        ) in [
            "waiting_for_agent",
            "assigned"
        ]
    ]

    # --------------------------------------------------------
    # If no human tasks remain, conversation is resolved
    # --------------------------------------------------------

    new_status = (
        "waiting_for_agent"
        if remaining_human_tasks
        else "resolved"
    )

    await conversations_collection.update_one(
        {
            "_id":
                conversation_object_id
        },

        {
            "$set": {
                "status":
                    new_status,

                "updated_at":
                    datetime.now(
                        timezone.utc
                    )
            }
        }
    )

    return {
        "message":
            "Support response submitted successfully.",

        "conversation_id":
            str(conversation_object_id),

        "task_id":
            task_id,

        "status":
            new_status
    }


# ============================================================
# RESOLVE SUPPORT TASK
# ============================================================

@router.post(
    "/conversations/{conversation_id}/resolve"
)
async def resolve_conversation(
    conversation_id: str,

    current_user=Depends(
        require_roles("support_agent")
    )
):

    organisation_id = get_agent_organisation_id(
        current_user
    )

    department_id = get_agent_department_id(
        current_user
    )

    agent_id = str(
        current_user["_id"]
    )

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
            "_id":
                conversation_object_id,

            "organisation_id":
                organisation_id
        })
    )

    if not conversation:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    tasks = conversation.get(
        "tasks",
        []
    )

    target_task = None

    for task in tasks:

        if not task_belongs_to_agent_department(
            task,
            department_id
        ):
            continue

        if str(
            task.get(
                "assigned_agent_id"
            )
        ) != agent_id:
            continue

        if task.get(
            "status"
        ) != "assigned":
            continue

        target_task = task
        break

    if not target_task:

        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have an assigned "
                "support task to resolve."
            )
        )

    task_id = target_task.get(
        "task_id"
    )

    # --------------------------------------------------------
    # Resolve task
    # --------------------------------------------------------

    result = await conversations_collection.update_one(
        {
            "_id":
                conversation_object_id,

            "organisation_id":
                organisation_id
        },

        {
            "$set": {
                "tasks.$[task].status":
                    "resolved",

                "tasks.$[task].needs_human":
                    False,

                "updated_at":
                    datetime.now(
                        timezone.utc
                    )
            }
        },

        array_filters=[
            {
                "task.task_id":
                    task_id,

                "task.department_id":
                    department_id,

                "task.assigned_agent_id":
                    agent_id
            }
        ]
    )

    if result.modified_count == 0:

        raise HTTPException(
            status_code=409,
            detail=(
                "Unable to resolve the support task."
            )
        )

    # --------------------------------------------------------
    # Check remaining tasks
    # --------------------------------------------------------

    updated_conversation = (
        await conversations_collection.find_one({
            "_id":
                conversation_object_id
        })
    )

    remaining_human_tasks = [

        task

        for task in updated_conversation.get(
            "tasks",
            []
        )

        if task.get(
            "needs_human",
            False
        )
        and task.get(
            "status"
        ) in [
            "waiting_for_agent",
            "assigned"
        ]
    ]

    new_status = (
        "waiting_for_agent"
        if remaining_human_tasks
        else "resolved"
    )

    await conversations_collection.update_one(
        {
            "_id":
                conversation_object_id
        },

        {
            "$set": {
                "status":
                    new_status,

                "updated_at":
                    datetime.now(
                        timezone.utc
                    )
            }
        }
    )

    return {
        "message":
            "Support task resolved successfully.",

        "conversation_id":
            str(conversation_object_id),

        "task_id":
            task_id,

        "status":
            new_status
    }

# from datetime import datetime, timezone

# from bson import ObjectId
# from fastapi import APIRouter, Depends, HTTPException, status
# from pydantic import BaseModel, Field

# from database import conversations_collection, users_collection
# from auth import get_current_user


# router = APIRouter(
#     prefix="/support",
#     tags=["Support"]
# )


# # ============================================================
# # REQUEST SCHEMAS
# # ============================================================

# class SupportMessageRequest(BaseModel):
#     message: str = Field(
#         min_length=1,
#         max_length=5000
#     )


# # ============================================================
# # HELPERS
# # ============================================================

# def require_support_agent(current_user):
#     if current_user.get("role") != "support_agent":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Support agent access required."
#         )


# def get_org_and_department(current_user):
#     organisation_id = current_user.get("organisation_id")
#     department_id = current_user.get("department_id")

#     if not organisation_id:
#         raise HTTPException(
#             status_code=403,
#             detail="Support agent has no organisation."
#         )

#     if not department_id:
#         raise HTTPException(
#             status_code=403,
#             detail="Support agent has no department."
#         )

#     return str(organisation_id), str(department_id)


# def serialize_conversation(conversation):
#     return {
#         "id": str(conversation["_id"]),
#         "user_id": str(conversation.get("user_id", "")),
#         "title": conversation.get("title", "Support Request"),
#         "status": conversation.get("status", "open"),
#         "assigned_agent_id": (
#             str(conversation["assigned_agent_id"])
#             if conversation.get("assigned_agent_id")
#             else None
#         ),
#         "messages": conversation.get("messages", []),
#         "created_at": conversation.get("created_at"),
#         "updated_at": conversation.get("updated_at"),
#     }


# async def get_support_conversation(
#     conversation_id: str,
#     current_user
# ):
#     require_support_agent(current_user)

#     organisation_id, department_id = get_org_and_department(
#         current_user
#     )

#     try:
#         conversation_object_id = ObjectId(conversation_id)
#     except Exception:
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid conversation ID."
#         )

#     conversation = await conversations_collection.find_one({
#         "_id": conversation_object_id,
#         "organisation_id": organisation_id,
#         "department_id": department_id,
#     })

#     if not conversation:
#         raise HTTPException(
#             status_code=404,
#             detail="Conversation not found."
#         )

#     return conversation


# # ============================================================
# # GET PENDING SUPPORT CONVERSATIONS
# # ============================================================

# @router.get("/conversations")
# async def get_support_conversations(
#     current_user=Depends(get_current_user)
# ):
#     require_support_agent(current_user)

#     organisation_id, department_id = get_org_and_department(
#         current_user
#     )

#     cursor = conversations_collection.find({
#         "organisation_id": organisation_id,
#         "department_id": department_id,
#         "status": "waiting_for_agent"
#     }).sort(
#         "updated_at",
#         -1
#     )

#     conversations = []

#     async for conversation in cursor:

#         user = None

#         user_id = conversation.get("user_id")

#         if user_id:
#             try:
#                 user = await users_collection.find_one({
#                     "_id": ObjectId(str(user_id))
#                 })
#             except Exception:
#                 user = None

#         messages = conversation.get("messages", [])

#         first_question = ""

#         for message in messages:
#             if message.get("sender") == "user":
#                 first_question = message.get("message", "")
#                 break

#         conversations.append({
#             "id": str(conversation["_id"]),
#             "user_id": str(user_id) if user_id else None,

#             "user_name": (
#                 user.get("name", "Unknown User")
#                 if user
#                 else "Unknown User"
#             ),

#             "user_email": (
#                 user.get("email", "")
#                 if user
#                 else ""
#             ),

#             "title": conversation.get(
#                 "title",
#                 first_question[:80] or "Support Request"
#             ),

#             "first_question": first_question,

#             "status": conversation.get(
#                 "status",
#                 "waiting_for_agent"
#             ),

#             "assigned_agent_id": (
#                 str(conversation["assigned_agent_id"])
#                 if conversation.get("assigned_agent_id")
#                 else None
#             ),

#             "created_at": conversation.get("created_at"),
#             "updated_at": conversation.get("updated_at"),
#         })

#     return {
#         "conversations": conversations
#     }


# # ============================================================
# # GET ONE SUPPORT CONVERSATION
# # ============================================================

# @router.get("/conversations/{conversation_id}")
# async def get_support_conversation_endpoint(
#     conversation_id: str,
#     current_user=Depends(get_current_user)
# ):
#     conversation = await get_support_conversation(
#         conversation_id,
#         current_user
#     )

#     user = None

#     user_id = conversation.get("user_id")

#     if user_id:
#         try:
#             user = await users_collection.find_one({
#                 "_id": ObjectId(str(user_id))
#             })
#         except Exception:
#             user = None

#     return {
#         "conversation": serialize_conversation(conversation),
#         "user": {
#             "id": str(user["_id"]) if user else None,
#             "name": user.get("name", "Unknown User") if user else "Unknown User",
#             "email": user.get("email", "") if user else "",
#         }
#     }


# # ============================================================
# # TAKE CONVERSATION
# # ============================================================

# @router.post("/conversations/{conversation_id}/take")
# async def take_conversation(
#     conversation_id: str,
#     current_user=Depends(get_current_user)
# ):
#     require_support_agent(current_user)

#     organisation_id, department_id = get_org_and_department(
#         current_user
#     )

#     try:
#         conversation_object_id = ObjectId(conversation_id)
#         agent_id = ObjectId(str(current_user["_id"]))
#     except Exception:
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid ID."
#         )

#     # IMPORTANT:
#     #
#     # assigned_agent_id must NOT already exist.
#     #
#     # This makes the update atomic.
#     #

#     result = await conversations_collection.update_one(
#         {
#             "_id": conversation_object_id,

#             "organisation_id": organisation_id,
#             "department_id": department_id,

#             "status": "waiting_for_agent",

#             "$or": [
#                 {
#                     "assigned_agent_id": {
#                         "$exists": False
#                     }
#                 },
#                 {
#                     "assigned_agent_id": None
#                 }
#             ]
#         },
#         {
#             "$set": {
#                 "assigned_agent_id": agent_id,
#                 "status": "assigned",
#                 "updated_at": datetime.now(timezone.utc)
#             }
#         }
#     )

#     if result.modified_count == 0:

#         conversation = await conversations_collection.find_one({
#             "_id": conversation_object_id,
#             "organisation_id": organisation_id,
#             "department_id": department_id
#         })

#         if not conversation:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Conversation not found."
#             )

#         if conversation.get("assigned_agent_id"):
#             raise HTTPException(
#                 status_code=409,
#                 detail="This conversation has already been taken."
#             )

#         raise HTTPException(
#             status_code=409,
#             detail="Conversation is no longer waiting for support."
#         )

#     return {
#         "message": "Conversation assigned successfully.",
#         "conversation_id": conversation_id,
#         "status": "assigned"
#     }


# # ============================================================
# # SUPPORT AGENT SEND MESSAGE
# # ============================================================

# @router.post("/conversations/{conversation_id}/messages")
# async def send_support_message(
#     conversation_id: str,
#     request: SupportMessageRequest,
#     current_user=Depends(get_current_user)
# ):
#     require_support_agent(current_user)

#     organisation_id, department_id = get_org_and_department(
#         current_user
#     )

#     try:
#         conversation_object_id = ObjectId(conversation_id)
#         agent_id = ObjectId(str(current_user["_id"]))
#     except Exception:
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid ID."
#         )

#     conversation = await conversations_collection.find_one({
#         "_id": conversation_object_id,
#         "organisation_id": organisation_id,
#         "department_id": department_id
#     })

#     if not conversation:
#         raise HTTPException(
#             status_code=404,
#             detail="Conversation not found."
#         )

#     assigned_agent_id = conversation.get(
#         "assigned_agent_id"
#     )

#     if not assigned_agent_id:
#         raise HTTPException(
#             status_code=409,
#             detail="Take the conversation before replying."
#         )

#     if str(assigned_agent_id) != str(agent_id):
#         raise HTTPException(
#             status_code=403,
#             detail="This conversation is assigned to another support agent."
#         )

#     now = datetime.now(timezone.utc)

#     message = {
#         "sender": "agent",
#         "message": request.message.strip(),
#         "agent_id": str(agent_id),
#         "created_at": now
#     }

#     result = await conversations_collection.update_one(
#         {
#             "_id": conversation_object_id,
#             "organisation_id": organisation_id,
#             "department_id": department_id,
#             "assigned_agent_id": agent_id
#         },
#         {
#             "$push": {
#                 "messages": message
#             },
#             "$set": {
#                 "status": "resolved",
#                 "updated_at": now
#             }
#         }
#     )

#     if result.modified_count == 0:
#         raise HTTPException(
#             status_code=409,
#             detail="Conversation could not be updated."
#         )

#     return {
#         "message": "Support response sent.",
#         "conversation_id": conversation_id,
#         "status": "resolved"
#     }


# # ============================================================
# # RESOLVE
# # ============================================================

# @router.post("/conversations/{conversation_id}/resolve")
# async def resolve_conversation(
#     conversation_id: str,
#     current_user=Depends(get_current_user)
# ):
#     require_support_agent(current_user)

#     organisation_id, department_id = get_org_and_department(
#         current_user
#     )

#     try:
#         conversation_object_id = ObjectId(conversation_id)
#         agent_id = ObjectId(str(current_user["_id"]))
#     except Exception:
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid ID."
#         )

#     result = await conversations_collection.update_one(
#         {
#             "_id": conversation_object_id,
#             "organisation_id": organisation_id,
#             "department_id": department_id,
#             "assigned_agent_id": agent_id
#         },
#         {
#             "$set": {
#                 "status": "resolved",
#                 "updated_at": datetime.now(timezone.utc)
#             }
#         }
#     )

#     if result.modified_count == 0:
#         raise HTTPException(
#             status_code=404,
#             detail="Conversation not found or not assigned to you."
#         )

#     return {
#         "message": "Conversation resolved.",
#         "status": "resolved"
#     }


# # from datetime import datetime, timezone

# # from bson import ObjectId
# # from fastapi import APIRouter, Depends, HTTPException

# # from database import (
# #     conversations_collection,
# #     users_collection,
# #     departments_collection
# # )

# # from schemas.conversation import SendMessageRequest

# # from utils.dependencies import require_roles

# # from services.gemini import generate_ai_response, generate_final_response


# # router = APIRouter(
# #     prefix="/support",
# #     tags=["Support Agent"]
# # )

# # @router.get("/conversations")
# # async def get_support_conversations(
# #     current_user=Depends(
# #         require_roles("support_agent")
# #     )
# # ):

# #     organisation_id = current_user.get(
# #         "organisation_id"
# #     )

# #     department_id = current_user.get(
# #         "department_id"
# #     )

# #     if not organisation_id:
# #         raise HTTPException(
# #             status_code=403,
# #             detail="Support agent is not part of an organisation"
# #         )

# #     if not department_id:
# #         raise HTTPException(
# #             status_code=403,
# #             detail="Support agent has no department"
# #         )

# #     cursor = conversations_collection.find({
# #         "organisation_id": organisation_id,

# #         "department_id": department_id,

# #         "status": {
# #             "$in": [
# #                 "waiting_for_agent",
# #                 "agent_responded"
# #             ]
# #         }
# #     }).sort(
# #         "updated_at",
# #         -1
# #     )

# #     conversations = []

# #     async for conversation in cursor:

# #         user = await users_collection.find_one({
# #             "_id": conversation["user_id"]
# #         })

# #         messages = conversation.get(
# #             "messages",
# #             []
# #         )

# #         first_user_message = ""

# #         for message in messages:

# #             if message["sender"] == "user":

# #                 first_user_message = message["message"]

# #                 break

# #         conversations.append({

# #             "id": str(
# #                 conversation["_id"]
# #             ),

# #             "status": conversation["status"],

# #             "title": first_user_message[:100],

# #             "user": {
# #                 "id": str(user["_id"]),
# #                 "name": user["name"],
# #                 "email": user["email"]
# #             } if user else None,

# #             "assigned_agent_id": (
# #                 str(conversation["assigned_agent_id"])
# #                 if conversation.get("assigned_agent_id")
# #                 else None
# #             ),

# #             "created_at": conversation["created_at"],

# #             "updated_at": conversation["updated_at"]
# #         })

# #     return conversations


# # @router.get("/conversations/{conversation_id}")
# # async def get_support_conversation(
# #     conversation_id: str,
# #     current_user=Depends(
# #         require_roles("support_agent")
# #     )
# # ):

# #     try:

# #         conversation_object_id = ObjectId(
# #             conversation_id
# #         )

# #     except Exception:

# #         raise HTTPException(
# #             status_code=400,
# #             detail="Invalid conversation ID"
# #         )

# #     conversation = await conversations_collection.find_one({

# #         "_id": conversation_object_id,

# #         "organisation_id": current_user[
# #             "organisation_id"
# #         ],

# #         "department_id": current_user[
# #             "department_id"
# #         ]

# #     })

# #     if not conversation:

# #         raise HTTPException(
# #             status_code=404,
# #             detail="Conversation not found"
# #         )

# #     user = await users_collection.find_one({
# #         "_id": conversation["user_id"]
# #     })

# #     return {

# #         "id": str(
# #             conversation["_id"]
# #         ),

# #         "status": conversation["status"],

# #         "user": {

# #             "id": str(user["_id"]),

# #             "name": user["name"],

# #             "email": user["email"]

# #         } if user else None,

# #         "messages": conversation.get(
# #             "messages",
# #             []
# #         ),

# #         "assigned_agent_id": (
# #             str(conversation["assigned_agent_id"])
# #             if conversation.get("assigned_agent_id")
# #             else None
# #         ),

# #         "created_at": conversation["created_at"],

# #         "updated_at": conversation["updated_at"]
# #     }

# # @router.post("/conversations/{conversation_id}/take")
# # async def take_conversation(
# #     conversation_id: str,
# #     current_user=Depends(
# #         require_roles("support_agent")
# #     )
# # ):

# #     try:

# #         conversation_object_id = ObjectId(
# #             conversation_id
# #         )

# #     except Exception:

# #         raise HTTPException(
# #             status_code=400,
# #             detail="Invalid conversation ID"
# #         )

# #     conversation = await conversations_collection.find_one({

# #         "_id": conversation_object_id,

# #         "organisation_id": current_user[
# #             "organisation_id"
# #         ],

# #         "department_id": current_user[
# #             "department_id"
# #         ]

# #     })

# #     if not conversation:

# #         raise HTTPException(
# #             status_code=404,
# #             detail="Conversation not found"
# #         )

# #     # --------------------------------------------
# #     # Already assigned
# #     # --------------------------------------------

# #     if conversation.get("assigned_agent_id"):

# #         if (
# #             conversation["assigned_agent_id"]
# #             != current_user["_id"]
# #         ):

# #             raise HTTPException(
# #                 status_code=409,
# #                 detail="Conversation is already assigned to another agent"
# #             )

# #         return {
# #             "message": "Conversation already assigned to you"
# #         }

# #     # --------------------------------------------
# #     # Only waiting conversations can be taken
# #     # --------------------------------------------

# #     if conversation["status"] != "waiting_for_agent":

# #         raise HTTPException(
# #             status_code=400,
# #             detail="Conversation is not waiting for an agent"
# #         )

# #     # --------------------------------------------
# #     # Assign atomically
# #     # --------------------------------------------

# #     result = await conversations_collection.update_one(

# #         {
# #             "_id": conversation_object_id,

# #             "assigned_agent_id": None,

# #             "status": "waiting_for_agent"
# #         },

# #         {
# #             "$set": {
# #                 "assigned_agent_id": current_user["_id"],
# #                 "updated_at": datetime.now(timezone.utc)
# #             }
# #         }
# #     )

# #     if result.modified_count == 0:

# #         raise HTTPException(
# #             status_code=409,
# #             detail="Conversation was already taken by another agent"
# #         )

# #     return {

# #         "message": "Conversation assigned to you",

# #         "conversation_id": conversation_id
# #     }


# # @router.post("/conversations/{conversation_id}/messages")
# # async def support_agent_message(
# #     conversation_id: str,
# #     data: SendMessageRequest,
# #     current_user=Depends(
# #         require_roles("support_agent")
# #     )
# # ):

# #     # --------------------------------------------
# #     # Validate conversation ID
# #     # --------------------------------------------

# #     try:

# #         conversation_object_id = ObjectId(
# #             conversation_id
# #         )

# #     except Exception:

# #         raise HTTPException(
# #             status_code=400,
# #             detail="Invalid conversation ID"
# #         )

# #     # --------------------------------------------
# #     # Find conversation
# #     # --------------------------------------------

# #     conversation = await conversations_collection.find_one({

# #         "_id": conversation_object_id,

# #         "organisation_id": current_user[
# #             "organisation_id"
# #         ],

# #         "department_id": current_user[
# #             "department_id"
# #         ]

# #     })

# #     if not conversation:

# #         raise HTTPException(
# #             status_code=404,
# #             detail="Conversation not found"
# #         )

# #     # --------------------------------------------
# #     # Agent must own the conversation
# #     # --------------------------------------------

# #     assigned_agent_id = conversation.get(
# #         "assigned_agent_id"
# #     )

# #     if not assigned_agent_id:

# #         raise HTTPException(
# #             status_code=400,
# #             detail="Take the conversation before replying"
# #         )

# #     if assigned_agent_id != current_user["_id"]:

# #         raise HTTPException(
# #             status_code=403,
# #             detail="This conversation is assigned to another agent"
# #         )

# #     # --------------------------------------------
# #     # Conversation must be waiting
# #     # --------------------------------------------

# #     if conversation["status"] != "waiting_for_agent":

# #         raise HTTPException(
# #             status_code=400,
# #             detail="This conversation is not waiting for an agent"
# #         )

# #     now = datetime.now(timezone.utc)

# #     # --------------------------------------------
# #     # Existing conversation history
# #     # --------------------------------------------

# #     history = conversation.get(
# #         "messages",
# #         []
# #     )

# #     # --------------------------------------------
# #     # Save agent message
# #     # --------------------------------------------

# #     agent_message = {

# #         "sender": "agent",

# #         "message": data.message,

# #         "agent_id": current_user["_id"],

# #         "created_at": now
# #     }

# #     # --------------------------------------------
# #     # Send agent answer to Gemini
# #     # --------------------------------------------

# #     # --------------------------------------------
# # # Send agent answer to Gemini
# # # --------------------------------------------

# #     ai_answer = await generate_final_response(
# #         conversation_history=history,
# #         agent_answer=data.message
# #     )

# #     if not ai_answer:
# #         ai_answer = data.message

# #     # ai_result = await generate_ai_response(

# #     #     question=(
# #     #         "The support agent has provided an "
# #     #         "authoritative answer to the user's question. "
# #     #         "Use the agent's answer to generate the final "
# #     #         "response that should be shown to the user."
# #     #     ),

# #     #     conversation_history=history + [
# #     #         agent_message
# #     #     ]
# #     # )

# #     # ai_answer = ai_result.get(
# #     #     "answer"
# #     # )

# #     # if not ai_answer:

# #     #     ai_answer = data.message

# #     # --------------------------------------------
# #     # AI final response
# #     # --------------------------------------------

# #     ai_message = {

# #         "sender": "ai",

# #         "message": ai_answer,

# #         "created_at": datetime.now(timezone.utc)
# #     }

# #     # --------------------------------------------
# #     # Update conversation
# #     # --------------------------------------------

# #     await conversations_collection.update_one(

# #         {
# #             "_id": conversation_object_id,

# #             "assigned_agent_id": current_user[
# #                 "_id"
# #             ],

# #             "status": "waiting_for_agent"
# #         },

# #         {
# #             "$push": {

# #                 "messages": {

# #                     "$each": [
# #                         agent_message,
# #                         ai_message
# #                     ]

# #                 }

# #             },

# #             "$set": {

# #                 "status": "resolved",

# #                 "updated_at": datetime.now(
# #                     timezone.utc
# #                 )

# #             }

# #         }
# #     )

# #     return {

# #         "message": ai_answer,

# #         "status": "resolved",

# #         "agent_message": data.message,

# #         "ai_message": ai_answer

# #     }


# # @router.post("/conversations/{conversation_id}/resolve")
# # async def resolve_conversation(
# #     conversation_id: str,
# #     current_user=Depends(
# #         require_roles("support_agent")
# #     )
# # ):

# #     try:

# #         conversation_object_id = ObjectId(
# #             conversation_id
# #         )

# #     except Exception:

# #         raise HTTPException(
# #             status_code=400,
# #             detail="Invalid conversation ID"
# #         )

# #     result = await conversations_collection.update_one(

# #         {
# #             "_id": conversation_object_id,

# #             "organisation_id": current_user[
# #                 "organisation_id"
# #             ],

# #             "department_id": current_user[
# #                 "department_id"
# #             ],

# #             "assigned_agent_id": current_user[
# #                 "_id"
# #             ]
# #         },

# #         {
# #             "$set": {

# #                 "status": "resolved",

# #                 "updated_at": datetime.now(
# #                     timezone.utc
# #                 )

# #             }

# #         }
# #     )

# #     if result.modified_count == 0:

# #         raise HTTPException(
# #             status_code=404,
# #             detail="Conversation not found"
# #         )

# #     return {
# #         "message": "Conversation resolved"
# #     }

