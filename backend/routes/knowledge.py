from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from database import (
    departments_collection,
    knowledge_documents_collection,
    knowledge_chunks_collection,
)

from schemas.knowledge import KnowledgeDocumentResponse

from services.rag import ingest_document

from utils.dependencies import require_roles
from utils.supabase_storage import upload_file, delete_file


router = APIRouter(
    prefix="/knowledge",
    tags=["Knowledge Base"]
)


# ============================================================
# CONFIG
# ============================================================

ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ============================================================
# UPLOAD KNOWLEDGE DOCUMENT
# ============================================================

@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_knowledge_document(
    department_id: str = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(require_roles("org_admin"))
):

    print("\n" + "=" * 80)
    print("📚 KNOWLEDGE DOCUMENT UPLOAD")
    print("=" * 80)

    # --------------------------------------------------------
    # 1. Validate department ID
    # --------------------------------------------------------

    try:
        department_object_id = ObjectId(department_id)

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid department ID"
        )

    # --------------------------------------------------------
    # 2. Get organisation ID
    # --------------------------------------------------------

    organisation_id = current_user.get("organisation_id")

    if not organisation_id:
        raise HTTPException(
            status_code=400,
            detail="User is not associated with an organisation"
        )

    try:
        organisation_object_id = ObjectId(organisation_id)

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid organisation ID"
        )

    # --------------------------------------------------------
    # 3. Check department belongs to organisation
    # --------------------------------------------------------

    department = await departments_collection.find_one({
        "_id": department_object_id,
        "organisation_id": organisation_object_id,
        "is_active": True
    })

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found in your organisation"
        )

    print("🏢 Organisation:", organisation_id)
    print("🏢 Department:", department["name"])
    print("🆔 Department ID:", department_id)

    # --------------------------------------------------------
    # 4. Validate file extension
    # --------------------------------------------------------

    original_filename = file.filename or ""

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX and TXT files are allowed"
        )

    expected_content_type = ALLOWED_EXTENSIONS[extension]

    print("📄 Filename:", original_filename)
    print("📄 Extension:", extension)

    # --------------------------------------------------------
    # 5. Read file
    # --------------------------------------------------------

    file_bytes = await file.read()

    file_size = len(file_bytes)

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size cannot exceed 50 MB"
        )

    print("📦 File size:", file_size, "bytes")

    # --------------------------------------------------------
    # 6. Generate document ID
    # --------------------------------------------------------

    document_id = ObjectId()

    print("🆔 Document ID:", document_id)

    # --------------------------------------------------------
    # 7. Create safe storage filename
    # --------------------------------------------------------

    safe_filename = Path(original_filename).name

    storage_filename = (
        f"{uuid4().hex}_{safe_filename}"
    )

    storage_path = (
        f"organisations/"
        f"{organisation_id}/"
        f"departments/"
        f"{department_id}/"
        f"{document_id}/"
        f"{storage_filename}"
    )

    # --------------------------------------------------------
    # 8. Upload original file to Supabase
    # --------------------------------------------------------

    print("\n☁️ Uploading file to Supabase...")

    try:

        upload_file(
            file_path=storage_path,
            file_bytes=file_bytes,
            content_type=expected_content_type
        )

        print("✅ Supabase upload successful")

    except Exception as e:

        print("❌ Supabase upload failed:", e)

        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file to Supabase: {str(e)}"
        )

    # --------------------------------------------------------
    # 9. Save document metadata in MongoDB
    # --------------------------------------------------------

    now = datetime.now(timezone.utc)

    document = {
        "_id": document_id,
        "organisation_id": organisation_object_id,
        "department_id": department_object_id,
        "uploaded_by": current_user["_id"],
        "filename": safe_filename,
        "storage_path": storage_path,
        "file_type": extension.lstrip("."),
        "mime_type": expected_content_type,
        "file_size": file_size,
        "status": "processing",
        "created_at": now
    }

    print("\n💾 Saving document metadata...")

    try:

        await knowledge_documents_collection.insert_one(
            document
        )

        print("✅ Document metadata saved")

    except Exception as e:

        print("❌ MongoDB metadata save failed:", e)

        # Delete Supabase file because MongoDB failed
        try:
            delete_file(storage_path)
            print("🗑️ Supabase file cleaned up")
        except Exception as cleanup_error:
            print(
                "⚠️ Failed to cleanup Supabase file:",
                cleanup_error
            )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save document metadata: {str(e)}"
        )

    # --------------------------------------------------------
    # 10. INGEST DOCUMENT INTO RAG
    # --------------------------------------------------------

    print("\n" + "-" * 80)
    print("🧠 STARTING RAG INGESTION")
    print("-" * 80)

    try:

        rag_result = await ingest_document(
            file_bytes=file_bytes,
            filename=safe_filename,
            organisation_id=organisation_id,
            department_id=department_id,
            document_id=document_id
        )

        chunks_created = rag_result.get(
            "chunks_created",
            0
        )

        print("\n✅ RAG INGESTION COMPLETE")
        print("📚 Chunks created:", chunks_created)

    except Exception as e:

        print("\n❌ RAG INGESTION FAILED")
        print("Error:", e)

        # ----------------------------------------------------
        # Mark document as failed
        # ----------------------------------------------------

        try:

            await knowledge_documents_collection.update_one(
                {
                    "_id": document_id
                },
                {
                    "$set": {
                        "status": "failed",
                        "error": str(e),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

        except Exception as update_error:

            print(
                "⚠️ Failed to update document status:",
                update_error
            )

        # ----------------------------------------------------
        # Delete any chunks that may have been inserted
        # before the failure
        # ----------------------------------------------------

        try:

            await knowledge_chunks_collection.delete_many({
                "document_id": str(document_id)
            })

            print("🗑️ Partial RAG chunks cleaned up")

        except Exception as cleanup_error:

            print(
                "⚠️ Failed to cleanup RAG chunks:",
                cleanup_error
            )

        # ----------------------------------------------------
        # Delete Supabase file
        # ----------------------------------------------------

        try:

            delete_file(storage_path)

            print("🗑️ Supabase file cleaned up")

        except Exception as cleanup_error:

            print(
                "⚠️ Failed to cleanup Supabase file:",
                cleanup_error
            )

        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {str(e)}"
        )

    # --------------------------------------------------------
    # 11. Mark document as completed
    # --------------------------------------------------------

    try:

        await knowledge_documents_collection.update_one(
            {
                "_id": document_id
            },
            {
                "$set": {
                    "status": "completed",
                    "chunks_created": chunks_created,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

    except Exception as e:

        print(
            "⚠️ Failed to update document completion status:",
            e
        )

    # --------------------------------------------------------
    # 12. Return response
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("✅ DOCUMENT PROCESSING COMPLETE")
    print("=" * 80)
    print("📄 File:", safe_filename)
    print("🏢 Department:", department["name"])
    print("📚 Chunks:", chunks_created)
    print("=" * 80)

    return KnowledgeDocumentResponse(
        id=str(document_id),
        organisation_id=str(organisation_id),
        department_id=str(department_object_id),
        filename=safe_filename,
        file_type=extension.lstrip("."),
        file_size=file_size,
        status="completed",
        created_at=now
    )


# ============================================================
# GET KNOWLEDGE DOCUMENTS
# ============================================================

@router.get(
    "/documents",
    response_model=list[KnowledgeDocumentResponse]
)
async def get_knowledge_documents(
    department_id: str | None = None,
    current_user=Depends(require_roles("org_admin"))
):

    organisation_id = current_user.get("organisation_id")

    if not organisation_id:
        raise HTTPException(
            status_code=400,
            detail="User is not associated with an organisation"
        )

    try:
        organisation_object_id = ObjectId(organisation_id)

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid organisation ID"
        )

    # --------------------------------------------------------
    # Build query
    # --------------------------------------------------------

    query = {
        "organisation_id": organisation_object_id
    }

    # --------------------------------------------------------
    # Optional department filter
    # --------------------------------------------------------

    if department_id:

        try:
            department_object_id = ObjectId(
                department_id
            )

        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid department ID"
            )

        query["department_id"] = department_object_id

    # --------------------------------------------------------
    # Fetch documents
    # --------------------------------------------------------

    documents = []

    cursor = knowledge_documents_collection.find(
        query
    ).sort(
        "created_at",
        -1
    )

    async for document in cursor:

        documents.append(
            KnowledgeDocumentResponse(
                id=str(document["_id"]),
                organisation_id=str(
                    document["organisation_id"]
                ),
                department_id=str(
                    document["department_id"]
                ),
                filename=document["filename"],
                file_type=document["file_type"],
                file_size=document["file_size"],
                status=document["status"],
                created_at=document["created_at"]
            )
        )

    return documents


# ============================================================
# DELETE KNOWLEDGE DOCUMENT
# ============================================================

@router.delete(
    "/documents/{document_id}"
)
async def delete_knowledge_document(
    document_id: str,
    current_user=Depends(require_roles("org_admin"))
):

    organisation_id = current_user.get("organisation_id")

    if not organisation_id:
        raise HTTPException(
            status_code=400,
            detail="User is not associated with an organisation"
        )

    # --------------------------------------------------------
    # Validate document ID
    # --------------------------------------------------------

    try:

        document_object_id = ObjectId(
            document_id
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid document ID"
        )

    # --------------------------------------------------------
    # Find document belonging to this organisation
    # --------------------------------------------------------

    document = await knowledge_documents_collection.find_one({
        "_id": document_object_id,
        "organisation_id": ObjectId(organisation_id)
    })

    if not document:

        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    # --------------------------------------------------------
    # Delete from Supabase
    # --------------------------------------------------------

    try:

        delete_file(
            document["storage_path"]
        )

        print(
            "🗑️ Deleted file from Supabase:",
            document["storage_path"]
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file from Supabase: {str(e)}"
        )

    # --------------------------------------------------------
    # Delete RAG chunks
    # --------------------------------------------------------

    try:

        chunk_delete_result = (
            await knowledge_chunks_collection.delete_many({
                "document_id": str(document_object_id)
            })
        )

        print(
            "🗑️ Deleted RAG chunks:",
            chunk_delete_result.deleted_count
        )

    except Exception as e:

        print(
            "⚠️ Failed to delete RAG chunks:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document chunks: {str(e)}"
        )

    # --------------------------------------------------------
    # Delete MongoDB document metadata
    # --------------------------------------------------------

    await knowledge_documents_collection.delete_one({
        "_id": document_object_id,
        "organisation_id": ObjectId(organisation_id)
    })

    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------

    return {
        "message": "Document and its knowledge chunks deleted successfully"
    }

# from datetime import datetime, timezone
# from pathlib import Path
# from uuid import uuid4

# from bson import ObjectId
# from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

# from database import (
#     departments_collection,
#     knowledge_documents_collection
# )
# from schemas.knowledge import KnowledgeDocumentResponse
# from utils.dependencies import require_roles
# from utils.supabase_storage import upload_file, delete_file


# router = APIRouter(
#     prefix="/knowledge",
#     tags=["Knowledge Base"]
# )


# ALLOWED_EXTENSIONS = {
#     ".pdf": "application/pdf",
#     ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#     ".txt": "text/plain"
# }

# MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# @router.post(
#     "/documents",
#     response_model=KnowledgeDocumentResponse,
#     status_code=status.HTTP_201_CREATED
# )
# async def upload_knowledge_document(
#     department_id: str = Form(...),
#     file: UploadFile = File(...),
#     current_user=Depends(require_roles("org_admin"))
# ):
#     # -----------------------------------------
#     # 1. Validate department ID
#     # -----------------------------------------

#     try:
#         department_object_id = ObjectId(department_id)
#     except Exception:
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid department ID"
#         )

#     # -----------------------------------------
#     # 2. Check department belongs to org
#     # -----------------------------------------

#     organisation_id = current_user.get("organisation_id")

#     if not organisation_id:
#         raise HTTPException(
#             status_code=400,
#             detail="User is not associated with an organisation"
#         )

#     department = await departments_collection.find_one({
#         "_id": department_object_id,
#         "organisation_id": ObjectId(organisation_id),
#         "is_active": True
#     })

#     if not department:
#         raise HTTPException(
#             status_code=404,
#             detail="Department not found in your organisation"
#         )

#     # -----------------------------------------
#     # 3. Validate file extension
#     # -----------------------------------------

#     original_filename = file.filename or ""

#     extension = Path(original_filename).suffix.lower()

#     if extension not in ALLOWED_EXTENSIONS:
#         raise HTTPException(
#             status_code=400,
#             detail="Only PDF, DOCX and TXT files are allowed"
#         )

#     expected_content_type = ALLOWED_EXTENSIONS[extension]

#     # -----------------------------------------
#     # 4. Read file
#     # -----------------------------------------

#     file_bytes = await file.read()

#     file_size = len(file_bytes)

#     if file_size == 0:
#         raise HTTPException(
#             status_code=400,
#             detail="File is empty"
#         )

#     if file_size > MAX_FILE_SIZE:
#         raise HTTPException(
#             status_code=400,
#             detail="File size cannot exceed 50 MB"
#         )

#     # -----------------------------------------
#     # 5. Generate document ID
#     # -----------------------------------------

#     document_id = ObjectId()

#     # -----------------------------------------
#     # 6. Create safe storage filename
#     # -----------------------------------------

#     safe_filename = Path(original_filename).name

#     storage_filename = (
#         f"{uuid4().hex}_{safe_filename}"
#     )

#     storage_path = (
#         f"organisations/"
#         f"{organisation_id}/"
#         f"departments/"
#         f"{department_id}/"
#         f"{document_id}/"
#         f"{storage_filename}"
#     )

#     # -----------------------------------------
#     # 7. Upload to Supabase
#     # -----------------------------------------

#     try:
#         upload_file(
#             file_path=storage_path,
#             file_bytes=file_bytes,
#             content_type=expected_content_type
#         )

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to upload file to Supabase: {str(e)}"
#         )

#     # -----------------------------------------
#     # 8. Save metadata in MongoDB
#     # -----------------------------------------

#     now = datetime.now(timezone.utc)

#     document = {
#         "_id": document_id,
#         "organisation_id": ObjectId(organisation_id),
#         "department_id": department_object_id,
#         "uploaded_by": current_user["_id"],
#         "filename": safe_filename,
#         "storage_path": storage_path,
#         "file_type": extension.lstrip("."),
#         "mime_type": expected_content_type,
#         "file_size": file_size,
#         "status": "processing",
#         "created_at": now
#     }

#     try:
#         await knowledge_documents_collection.insert_one(document)

#     except Exception as e:

#         # If MongoDB fails after Supabase upload,
#         # remove the uploaded file to avoid orphan files.

#         try:
#             delete_file(storage_path)
#         except Exception:
#             pass

#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to save document metadata: {str(e)}"
#         )

#     # -----------------------------------------
#     # 9. Return response
#     # -----------------------------------------

#     return KnowledgeDocumentResponse(
#         id=str(document_id),
#         organisation_id=str(organisation_id),
#         department_id=str(department_object_id),
#         filename=safe_filename,
#         file_type=extension.lstrip("."),
#         file_size=file_size,
#         status="processing",
#         created_at=now
#     )


# @router.get(
#     "/documents",
#     response_model=list[KnowledgeDocumentResponse]
# )
# async def get_knowledge_documents(
#     department_id: str | None = None,
#     current_user=Depends(require_roles("org_admin"))
# ):
#     organisation_id = current_user.get("organisation_id")

#     if not organisation_id:
#         raise HTTPException(
#             status_code=400,
#             detail="User is not associated with an organisation"
#         )

#     query = {
#         "organisation_id": ObjectId(organisation_id)
#     }

#     # Optional department filter

#     if department_id:

#         try:
#             department_object_id = ObjectId(department_id)
#         except Exception:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid department ID"
#             )

#         query["department_id"] = department_object_id

#     documents = []

#     cursor = knowledge_documents_collection.find(
#         query
#     ).sort(
#         "created_at",
#         -1
#     )

#     async for document in cursor:

#         documents.append(
#             KnowledgeDocumentResponse(
#                 id=str(document["_id"]),
#                 organisation_id=str(
#                     document["organisation_id"]
#                 ),
#                 department_id=str(
#                     document["department_id"]
#                 ),
#                 filename=document["filename"],
#                 file_type=document["file_type"],
#                 file_size=document["file_size"],
#                 status=document["status"],
#                 created_at=document["created_at"]
#             )
#         )

#     return documents


# @router.delete(
#     "/documents/{document_id}"
# )
# async def delete_knowledge_document(
#     document_id: str,
#     current_user=Depends(require_roles("org_admin"))
# ):
#     organisation_id = current_user.get("organisation_id")

#     if not organisation_id:
#         raise HTTPException(
#             status_code=400,
#             detail="User is not associated with an organisation"
#         )

#     try:
#         document_object_id = ObjectId(document_id)
#     except Exception:
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid document ID"
#         )

#     # -----------------------------------------
#     # Find document belonging to this org
#     # -----------------------------------------

#     document = await knowledge_documents_collection.find_one({
#         "_id": document_object_id,
#         "organisation_id": ObjectId(organisation_id)
#     })

#     if not document:
#         raise HTTPException(
#             status_code=404,
#             detail="Document not found"
#         )

#     # -----------------------------------------
#     # Delete from Supabase
#     # -----------------------------------------

#     try:
#         delete_file(
#             document["storage_path"]
#         )

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to delete file from Supabase: {str(e)}"
#         )

#     # -----------------------------------------
#     # Delete MongoDB metadata
#     # -----------------------------------------

#     await knowledge_documents_collection.delete_one({
#         "_id": document_object_id
#     })

#     return {
#         "message": "Document deleted successfully"
#     }