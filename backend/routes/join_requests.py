from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import (
    organisations_collection,
    departments_collection,
    join_requests_collection,
    users_collection,
)

from schemas.auth import JoinOrganisationRequest

from utils.dependencies import (
    get_current_user,
    require_roles,
)


router = APIRouter(
    prefix="/join-requests",
    tags=["Join Requests"],
)


# ============================================================
# CREATE JOIN REQUEST
# ============================================================

@router.post("")
async def create_join_request(
    data: JoinOrganisationRequest,
    current_user=Depends(get_current_user),
):
    """
    Logged-in user requests to join an organisation.

    The user's organisation_id remains NULL until
    an organisation admin approves this request.
    """

    # --------------------------------------------------------
    # 1. User must not already belong to an organisation
    # --------------------------------------------------------

    if current_user.get("organisation_id"):

        raise HTTPException(
            status_code=400,
            detail="You already belong to an organisation",
        )

    # --------------------------------------------------------
    # 2. Validate role
    # --------------------------------------------------------

    if data.role not in [
        "user",
        "support_agent",
    ]:

        raise HTTPException(
            status_code=400,
            detail="Invalid organisation role",
        )

    # --------------------------------------------------------
    # 3. Validate organisation ID
    # --------------------------------------------------------

    try:

        organisation_id = ObjectId(
            data.organisation_id
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid organisation ID",
        )

    # --------------------------------------------------------
    # 4. Organisation must exist and be active
    # --------------------------------------------------------

    organisation = await organisations_collection.find_one({
        "_id": organisation_id,
        "status": "active",
    })

    if not organisation:

        raise HTTPException(
            status_code=404,
            detail="Organisation not found or inactive",
        )

    # --------------------------------------------------------
    # 5. Department handling
    # --------------------------------------------------------

    department_id = None

    if data.role == "support_agent":

        # Support agent MUST select department

        if not data.department_id:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Support agent must select a department"
                ),
            )

        try:

            department_id = ObjectId(
                data.department_id
            )

        except Exception:

            raise HTTPException(
                status_code=400,
                detail="Invalid department ID",
            )

        # Department must belong to organisation

        department = await departments_collection.find_one({
            "_id": department_id,
            "organisation_id": organisation_id,
            "is_active": True,
        })

        if not department:

            raise HTTPException(
                status_code=404,
                detail="Department not found",
            )

    else:

        # Normal user cannot select department

        if data.department_id not in [
            None,
            "",
            "null",
        ]:

            raise HTTPException(
                status_code=400,
                detail="User role cannot have a department",
            )

    # --------------------------------------------------------
    # 6. Prevent duplicate pending request
    # --------------------------------------------------------

    existing = await join_requests_collection.find_one({
        "user_id": current_user["_id"],
        "organisation_id": organisation_id,
        "status": "pending",
    })

    if existing:

        raise HTTPException(
            status_code=400,
            detail="Join request already exists",
        )

    # --------------------------------------------------------
    # 7. Create request
    # --------------------------------------------------------

    request = {
        "user_id": current_user["_id"],
        "organisation_id": organisation_id,
        "requested_role": data.role,
        "department_id": department_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }

    result = await join_requests_collection.insert_one(
        request
    )

    return {
        "message": "Join request submitted successfully",
        "request_id": str(result.inserted_id),
    }


# ============================================================
# GET PENDING REQUESTS
# ============================================================

@router.get("")
async def get_join_requests(
    current_user=Depends(
        require_roles("org_admin")
    ),
):
    """
    Get pending join requests for the
    organisation of the logged-in org admin.
    """

    organisation_id = current_user[
        "organisation_id"
    ]

    cursor = join_requests_collection.find({
        "organisation_id": organisation_id,
        "status": "pending",
    }).sort(
        "created_at",
        -1,
    )

    requests = []

    async for request in cursor:

        # ----------------------------------------------------
        # Get requesting user
        # ----------------------------------------------------

        user = await users_collection.find_one({
            "_id": request["user_id"],
        })

        if not user:
            continue

        # ----------------------------------------------------
        # Get department name
        # ----------------------------------------------------

        department = None

        if request.get("department_id"):

            department = await departments_collection.find_one({
                "_id": request["department_id"],
            })

        requests.append({
            "id": str(request["_id"]),

            "user": {
                "id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"],
            },

            "requested_role": request[
                "requested_role"
            ],

            "department": (
                {
                    "id": str(department["_id"]),
                    "name": department["name"],
                }
                if department
                else None
            ),

            "created_at": request[
                "created_at"
            ],
        })

    return requests


# ============================================================
# APPROVE JOIN REQUEST
# ============================================================

@router.post("/{request_id}/approve")
async def approve_join_request(
    request_id: str,
    current_user=Depends(
        require_roles("org_admin")
    ),
):
    """
    Approve a pending join request.

    Only after approval does the user's
    organisation_id / role / department_id
    get updated.
    """

    # --------------------------------------------------------
    # 1. Validate request ID
    # --------------------------------------------------------

    try:

        request_object_id = ObjectId(
            request_id
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid request ID",
        )

    # --------------------------------------------------------
    # 2. Find pending request belonging
    #    to this organisation
    # --------------------------------------------------------

    request = await join_requests_collection.find_one({
        "_id": request_object_id,
        "organisation_id": current_user[
            "organisation_id"
        ],
        "status": "pending",
    })

    if not request:

        raise HTTPException(
            status_code=404,
            detail="Join request not found",
        )

    # --------------------------------------------------------
    # 3. Make sure user still exists
    # --------------------------------------------------------

    user = await users_collection.find_one({
        "_id": request["user_id"],
    })

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User no longer exists",
        )

    # --------------------------------------------------------
    # 4. Update user's organisation membership
    # --------------------------------------------------------

    update = {
        "organisation_id": request[
            "organisation_id"
        ],

        "role": request[
            "requested_role"
        ],

        "department_id": request.get(
            "department_id"
        ),
    }

    await users_collection.update_one(
        {
            "_id": request["user_id"],
        },
        {
            "$set": update,
        },
    )

    # --------------------------------------------------------
    # 5. Mark request as approved
    # --------------------------------------------------------

    await join_requests_collection.update_one(
        {
            "_id": request_object_id,
        },
        {
            "$set": {
                "status": "approved",

                "approved_by": current_user[
                    "_id"
                ],

                "approved_at": datetime.now(
                    timezone.utc
                ),
            },
        },
    )

    return {
        "message": "Join request approved",
    }


# ============================================================
# REJECT JOIN REQUEST
# ============================================================

@router.post("/{request_id}/reject")
async def reject_join_request(
    request_id: str,
    current_user=Depends(
        require_roles("org_admin")
    ),
):
    """
    Reject a pending join request.
    """

    # --------------------------------------------------------
    # 1. Validate request ID
    # --------------------------------------------------------

    try:

        request_object_id = ObjectId(
            request_id
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid request ID",
        )

    # --------------------------------------------------------
    # 2. Reject only pending request
    #    belonging to this organisation
    # --------------------------------------------------------

    result = await join_requests_collection.update_one(
        {
            "_id": request_object_id,

            "organisation_id": current_user[
                "organisation_id"
            ],

            "status": "pending",
        },

        {
            "$set": {
                "status": "rejected",

                "rejected_by": current_user[
                    "_id"
                ],

                "rejected_at": datetime.now(
                    timezone.utc
                ),
            },
        },
    )

    if result.modified_count == 0:

        raise HTTPException(
            status_code=404,
            detail="Join request not found",
        )

    return {
        "message": "Join request rejected",
    }