from uuid import uuid4

from services.router_service import route_question
from services.department_agent import run_department_agent
from services.synthesizer import synthesize_department_results


async def process_user_question(
    *,
    question: str,
    organisation_id: str,
    conversation_history: list | None = None
):
    """
    COMPLETE ONE-DESK AI PIPELINE

    USER
      ↓
    ROUTER
      ↓
    TASKS
      ↓
    DEPARTMENT AGENTS
      ↓
    RAG
      ↓
    DEPARTMENT RESPONSES
      ↓
    HUMAN CHECK
      ↓
    SYNTHESIZER
    """

    print("\n")
    print("#" * 80)
    print("🚀 ONEDESK ORCHESTRATOR")
    print("#" * 80)

    print(
        f"Question: {question}"
    )

    # ========================================================
    # STEP 1 — ROUTER
    # ========================================================

    routing_result = await route_question(
        question=question,
        organisation_id=organisation_id
    )

    print("\n")
    print("🔀 ROUTER RESULT")
    print(
        routing_result
    )

    # ========================================================
    # STEP 2 — CLARIFICATION
    # ========================================================

    if routing_result.get(
        "needs_clarification",
        False
    ):

        return {
            "answer": (
                "I need a little more information "
                "to understand which department can "
                "help with this."
            ),

            "needs_clarification": True,

            "needs_human": False,

            "status": "open",

            "tasks": [],

            "department_results": []
        }

    # ========================================================
    # STEP 3 — GET ROUTED TASKS
    # ========================================================

    routes = routing_result.get(
        "routes",
        []
    )

    if not routes:

        return {
            "answer": (
                "I couldn't determine which department "
                "should handle your question."
            ),

            "needs_clarification": True,

            "needs_human": False,

            "status": "open",

            "tasks": [],

            "department_results": []
        }

    # ========================================================
    # STEP 4 — RUN DEPARTMENT AGENTS
    # ========================================================

    tasks = []

    department_results = []

    for route in routes:

        task_id = str(
            uuid4()
        )

        department_id = str(
            route["department_id"]
        )

        department_name = route[
            "department_name"
        ]

        task_question = route[
            "question"
        ]

        router_confidence = float(
            route.get(
                "confidence",
                0.0
            )
        )

        # ----------------------------------------------------
        # Create initial task
        # ----------------------------------------------------

        task = {
            "task_id": task_id,

            "department_id":
                department_id,

            "department_name":
                department_name,

            "question":
                task_question,

            "status":
                "processing",

            "confidence":
                router_confidence,

            "answer":
                None,

            "needs_human":
                False,

            "assigned_agent_id":
                None,

            "sources":
                []
        }

        tasks.append(task)

        # ----------------------------------------------------
        # Run department bot
        # ----------------------------------------------------

        try:

            result = await run_department_agent(
                question=task_question,

                organisation_id=organisation_id,

                department_id=department_id,

                department_name=department_name,

                conversation_history=(
                    conversation_history or []
                )
            )

        except Exception as error:

            print(
                f"❌ Department agent failed: "
                f"{department_name}"
            )

            print(error)

            result = {
                "answer": "",
                "confidence": 0.0,
                "needs_human": True,
                "reason": (
                    "The department assistant "
                    "could not process this request."
                ),
                "sources": []
            }

        # ----------------------------------------------------
        # Update task
        # ----------------------------------------------------

        answer = result.get(
            "answer",
            ""
        )

        confidence = float(
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

        sources = result.get(
            "sources",
            []
        )

        if needs_human:

            task_status = (
                "waiting_for_agent"
            )

        else:

            task_status = "answered"

        task.update({

            "status":
                task_status,

            "confidence":
                confidence,

            "answer":
                answer,

            "needs_human":
                needs_human,

            "sources":
                sources
        })

        department_result = {

            "task_id":
                task_id,

            "department_id":
                department_id,

            "department_name":
                department_name,

            "question":
                task_question,

            "answer":
                answer,

            "confidence":
                confidence,

            "needs_human":
                needs_human,

            "reason":
                result.get(
                    "reason"
                ),

            "sources":
                sources
        }

        department_results.append(
            department_result
        )

    # ========================================================
    # STEP 5 — CHECK HUMAN ESCALATION
    # ========================================================

    needs_human = any(
        task["needs_human"]
        for task in tasks
    )

    waiting_tasks = [
        task
        for task in tasks
        if task["needs_human"]
    ]

    answered_tasks = [
        task
        for task in tasks
        if not task["needs_human"]
    ]

    print("\n")
    print("📊 TASK STATUS")

    print(
        f"Answered tasks: "
        f"{len(answered_tasks)}"
    )

    print(
        f"Waiting for human: "
        f"{len(waiting_tasks)}"
    )

    # ========================================================
    # STEP 6 — SYNTHESIZE
    # ========================================================

    synthesis = await synthesize_department_results(
        original_question=question,
        department_results=department_results
    )

    final_answer = synthesis.get(
        "answer",
        ""
    )

    # ========================================================
    # STEP 7 — FINAL STATUS
    # ========================================================

    if needs_human:

        conversation_status = (
            "waiting_for_agent"
        )

    else:

        conversation_status = (
            "resolved"
        )

    return {

        "answer":
            final_answer,

        "confidence":
            synthesis.get(
                "confidence",
                0.0
            ),

        "needs_clarification":
            False,

        "needs_human":
            needs_human,

        "status":
            conversation_status,

        "tasks":
            tasks,

        "department_results":
            department_results,

        "sources":
            synthesis.get(
                "sources",
                []
            )
    }