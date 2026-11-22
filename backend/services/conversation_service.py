from datetime import datetime, timezone

from database import conversations_collection


async def save_user_message(
    conversation_id,
    message: str
):

    now = datetime.now(
        timezone.utc
    )

    await conversations_collection.update_one(
        {
            "_id": conversation_id
        },
        {
            "$push": {
                "messages": {
                    "sender": "user",
                    "message": message,
                    "created_at": now
                }
            },

            "$set": {
                "updated_at": now
            }
        }
    )


async def save_ai_result(
    conversation_id,
    result
):

    now = datetime.now(
        timezone.utc
    )

    ai_message = {
        "sender": "ai",

        "message": result[
            "answer"
        ],

        "created_at": now,

        "confidence": result.get(
            "confidence",
            0.0
        ),

        "needs_human": result.get(
            "needs_human",
            False
        )
    }

    await conversations_collection.update_one(
        {
            "_id": conversation_id
        },
        {
            "$push": {
                "messages": ai_message
            },

            "$set": {
                "tasks": result.get(
                    "tasks",
                    []
                ),

                "status": result.get(
                    "status",
                    "resolved"
                ),

                "updated_at": now
            }
        }
    )


async def update_conversation_tasks(
    conversation_id,
    tasks
):

    await conversations_collection.update_one(
        {
            "_id": conversation_id
        },
        {
            "$set": {
                "tasks": tasks,

                "updated_at":
                    datetime.now(
                        timezone.utc
                    )
            }
        }
    )