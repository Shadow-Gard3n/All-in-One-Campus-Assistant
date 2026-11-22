from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from database import (
    users_collection,
    organisations_collection,
    departments_collection,
    join_requests_collection,
)
from utils.dependencies import require_roles
from datetime import datetime, timezone

router = APIRouter(
    prefix="/organisation-admin",
    tags=["Organisation Admin"]
)


def get_object_id(value: str):
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid ID"
        )


# ============================================================
# DASHBOARD
# ============================================================

@router.get("/dashboard")
async def get_dashboard(
    current_user=Depends(require_roles("org_admin"))
):
    organisation_id = current_user["organisation_id"]

    organisation = await organisations_collection.find_one({
        "_id": organisation_id
    })

    if not organisation:
        raise HTTPException(
            status_code=404,
            detail="Organisation not found"
        )

    department_count = await departments_collection.count_documents({
        "organisation_id": organisation_id,
        "is_active": True
    })

    user_count = await users_collection.count_documents({
        "organisation_id": organisation_id,
        "is_active": True
    })

    support_agent_count = await users_collection.count_documents({
        "organisation_id": organisation_id,
        "role": "support_agent",
        "is_active": True
    })

    pending_requests = await join_requests_collection.count_documents({
        "organisation_id": organisation_id,
        "status": "pending"
    })

    return {
        "organisation": {
            "id": str(organisation["_id"]),
            "name": organisation["name"],
            "status": organisation["status"]
        },
        "stats": {
            "departments": department_count,
            "users": user_count,
            "support_agents": support_agent_count,
            "pending_requests": pending_requests
        }
    }


# ============================================================
# USERS
# ============================================================

@router.get("/users")
async def get_users(
    current_user=Depends(require_roles("org_admin"))
):
    organisation_id = current_user["organisation_id"]

    users = []

    cursor = users_collection.find({
        "organisation_id": organisation_id,
        "is_active": True
    })

    async for user in cursor:
        users.append({
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "department_id": (
                str(user["department_id"])
                if user.get("department_id")
                else None
            ),
            "is_active": user.get("is_active", True)
        })

    return users


# ============================================================
# DEPARTMENTS
# ============================================================

@router.get("/departments")
async def get_departments(
    current_user=Depends(require_roles("org_admin"))
):
    organisation_id = current_user["organisation_id"]

    departments = []

    cursor = departments_collection.find({
        "organisation_id": organisation_id,
        "is_active": True
    })

    async for department in cursor:
        departments.append({
            "id": str(department["_id"]),
            "name": department["name"],
            "bot_enabled": department.get("bot_enabled", True),
            "human_support_enabled": department.get(
                "human_support_enabled",
                True
            ),
            "rules": department.get("rules", [])
        })

    return departments


# ============================================================
# CREATE DEPARTMENT
# ============================================================

@router.post("/departments")
async def create_department(
    data: dict,
    current_user=Depends(require_roles("org_admin"))
):
    organisation_id = current_user["organisation_id"]

    name = data.get("name", "").strip()

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Department name is required"
        )

    existing = await departments_collection.find_one({
        "organisation_id": organisation_id,
        "name": name,
        "is_active": True
    })

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Department already exists"
        )

    department = {
        "organisation_id": organisation_id,
        "name": name,
        "bot_enabled": data.get("bot_enabled", True),
        "human_support_enabled": data.get(
            "human_support_enabled",
            True
        ),
        "rules": [],
        "is_active": True
    }

    result = await departments_collection.insert_one(department)

    return {
        "message": "Department created",
        "department": {
            "id": str(result.inserted_id),
            "name": name,
            "bot_enabled": department["bot_enabled"],
            "human_support_enabled": department[
                "human_support_enabled"
            ]
        }
    }


# ============================================================
# UPDATE DEPARTMENT
# ============================================================

@router.patch("/departments/{department_id}")
async def update_department(
    department_id: str,
    data: dict,
    current_user=Depends(require_roles("org_admin"))
):
    organisation_id = current_user["organisation_id"]

    department_object_id = get_object_id(department_id)

    department = await departments_collection.find_one({
        "_id": department_object_id,
        "organisation_id": organisation_id,
        "is_active": True
    })

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    update_data = {}

    if "name" in data:
        name = data["name"].strip()

        if len(name) < 2:
            raise HTTPException(
                status_code=400,
                detail="Department name is invalid"
            )

        update_data["name"] = name

    if "bot_enabled" in data:
        update_data["bot_enabled"] = bool(
            data["bot_enabled"]
        )

    if "human_support_enabled" in data:
        update_data["human_support_enabled"] = bool(
            data["human_support_enabled"]
        )

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No changes provided"
        )

    await departments_collection.update_one(
        {"_id": department_object_id},
        {"$set": update_data}
    )

    updated = await departments_collection.find_one({
        "_id": department_object_id
    })

    return {
        "message": "Department updated",
        "department": {
            "id": str(updated["_id"]),
            "name": updated["name"],
            "bot_enabled": updated.get("bot_enabled", True),
            "human_support_enabled": updated.get(
                "human_support_enabled",
                True
            )
        }
    }


# ============================================================
# DELETE DEPARTMENT
# ============================================================

@router.delete("/departments/{department_id}")
async def delete_department(
    department_id: str,
    current_user=Depends(require_roles("org_admin"))
):
    organisation_id = current_user["organisation_id"]

    department_object_id = get_object_id(department_id)

    department = await departments_collection.find_one({
        "_id": department_object_id,
        "organisation_id": organisation_id,
        "is_active": True
    })

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    await departments_collection.update_one(
        {"_id": department_object_id},
        {
            "$set": {
                "is_active": False
            }
        }
    )

    return {
        "message": "Department deleted"
    }


# ============================================================
# JOIN REQUESTS
# ============================================================

@router.get("/join-requests")
async def get_join_requests(
    current_user=Depends(
        require_roles("org_admin")
    )
):
    organisation_id = current_user["organisation_id"]

    cursor = join_requests_collection.find({
        "organisation_id": organisation_id,
        "status": "pending"
    }).sort(
        "created_at",
        -1
    )

    requests = []

    async for request in cursor:

        # Find the user who submitted the request
        user = await users_collection.find_one({
            "_id": request["user_id"]
        })

        # User may have been deleted
        if not user:
            continue

        requests.append({
            "id": str(request["_id"]),

            "user": {
                "id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"]
            },

            "requested_role": request["requested_role"],

            "department_id": (
                str(request["department_id"])
                if request.get("department_id")
                else None
            ),

            "status": request["status"],

            "created_at": request.get("created_at")
        })

    return requests



# ============================================================
# UPDATE USER
# ============================================================

@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    data: dict,
    current_user=Depends(
        require_roles("org_admin")
    )
):

    organisation_id = current_user["organisation_id"]

    # --------------------------------------------------------
    # Validate user ID
    # --------------------------------------------------------

    try:

        user_object_id = ObjectId(user_id)

    except InvalidId:

        raise HTTPException(
            status_code=400,
            detail="Invalid user ID"
        )

    # --------------------------------------------------------
    # Find user inside this organisation
    # --------------------------------------------------------

    user = await users_collection.find_one({
        "_id": user_object_id,
        "organisation_id": organisation_id
    })

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # --------------------------------------------------------
    # Do not allow organisation admin to modify themselves
    # through this endpoint
    # --------------------------------------------------------

    if user["_id"] == current_user["_id"]:

        raise HTTPException(
            status_code=400,
            detail="You cannot modify your own account here"
        )

    # --------------------------------------------------------
    # Allowed fields
    # --------------------------------------------------------

    update_data = {}

    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    if "name" in data:

        name = str(
            data["name"]
        ).strip()

        if len(name) < 2:

            raise HTTPException(
                status_code=400,
                detail="Name must contain at least 2 characters"
            )

        update_data["name"] = name

    # --------------------------------------------------------
    # ROLE
    # --------------------------------------------------------

    if "role" in data:

        role = data["role"]

        if role not in [
            "user",
            "support_agent"
        ]:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Organisation admin can only assign "
                    "user or support_agent role"
                )
            )

        update_data["role"] = role

    # --------------------------------------------------------
    # DEPARTMENT
    # --------------------------------------------------------

    if "department_id" in data:

        department_value = data["department_id"]

        # Normal user
        if update_data.get(
            "role",
            user["role"]
        ) == "user":

            if department_value not in [
                None,
                "",
                "null"
            ]:

                raise HTTPException(
                    status_code=400,
                    detail="User role cannot have a department"
                )

            update_data["department_id"] = None

        # Support agent
        else:

            if not department_value:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Support agent must have "
                        "a department"
                    )
                )

            try:

                department_object_id = ObjectId(
                    department_value
                )

            except InvalidId:

                raise HTTPException(
                    status_code=400,
                    detail="Invalid department ID"
                )

            department = await departments_collection.find_one({
                "_id": department_object_id,
                "organisation_id": organisation_id,
                "is_active": True
            })

            if not department:

                raise HTTPException(
                    status_code=404,
                    detail="Department not found"
                )

            update_data[
                "department_id"
            ] = department_object_id

    # --------------------------------------------------------
    # If changing role to support_agent
    # department MUST be provided
    # --------------------------------------------------------

    new_role = update_data.get(
        "role",
        user["role"]
    )

    if new_role == "support_agent":

        department_id = update_data.get(
            "department_id",
            user.get("department_id")
        )

        if not department_id:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Support agent must have "
                    "a department"
                )
            )

    # --------------------------------------------------------
    # If changing role to user
    # department MUST become null
    # --------------------------------------------------------

    if new_role == "user":

        update_data["department_id"] = None

    # --------------------------------------------------------
    # Nothing to update
    # --------------------------------------------------------

    if not update_data:

        raise HTTPException(
            status_code=400,
            detail="No changes provided"
        )

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    await users_collection.update_one(
        {
            "_id": user_object_id,
            "organisation_id": organisation_id
        },
        {
            "$set": update_data
        }
    )

    # --------------------------------------------------------
    # Get updated user
    # --------------------------------------------------------

    updated_user = await users_collection.find_one({
        "_id": user_object_id
    })

    return {
        "message": "User updated successfully",

        "user": {
            "id": str(updated_user["_id"]),
            "name": updated_user["name"],
            "email": updated_user["email"],
            "role": updated_user["role"],

            "department_id": (
                str(updated_user["department_id"])
                if updated_user.get("department_id")
                else None
            ),

            "is_active": updated_user.get(
                "is_active",
                True
            )
        }
    }


# ============================================================
# DELETE USER
# ============================================================

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user=Depends(
        require_roles("org_admin")
    )
):

    organisation_id = current_user["organisation_id"]

    # --------------------------------------------------------
    # Validate ID
    # --------------------------------------------------------

    try:

        user_object_id = ObjectId(user_id)

    except InvalidId:

        raise HTTPException(
            status_code=400,
            detail="Invalid user ID"
        )

    # --------------------------------------------------------
    # Find user
    # --------------------------------------------------------

    user = await users_collection.find_one({
        "_id": user_object_id,
        "organisation_id": organisation_id
    })

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # --------------------------------------------------------
    # Cannot delete yourself
    # --------------------------------------------------------

    if user["_id"] == current_user["_id"]:

        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account"
        )

    # --------------------------------------------------------
    # Cannot delete another organisation admin
    # --------------------------------------------------------

    if user["role"] == "org_admin":

        raise HTTPException(
            status_code=403,
            detail=(
                "Organisation admin accounts "
                "cannot be deleted here"
            )
        )

    # --------------------------------------------------------
    # Soft delete
    # --------------------------------------------------------

    await users_collection.update_one(
        {
            "_id": user_object_id,
            "organisation_id": organisation_id
        },
        {
            "$set": {
                "is_active": False,
                "deleted_at": datetime.now(timezone.utc),
                "deleted_by": current_user["_id"]
            }
        }
    )

    return {
        "message": "User deleted successfully"
    }


