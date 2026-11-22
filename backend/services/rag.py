from database import knowledge_chunks_collection

from services.embeddings import (
    create_embedding
)


# ============================================================
# CHUNK TEXT
# ============================================================

def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100
):
    """
    Split document text into overlapping chunks.
    """

    text = text.strip()

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        if chunk.strip():

            chunks.append(
                chunk.strip()
            )

        start += (
            chunk_size - overlap
        )

    return chunks


# ============================================================
# SEARCH KNOWLEDGE
# ============================================================

async def search_knowledge(
    *,
    question,
    organisation_id,
    department_id,
    limit=5
):
    organisation_id = str(organisation_id)
    department_id = str(department_id)

    print("\n" + "=" * 80)
    print("🔎 RAG SEARCH")
    print("=" * 80)

    print("Question:", question)
    print("Organisation ID:", organisation_id)
    print("Department ID:", department_id)

    # ---------------------------------------------------------
    # STEP 1: Check whether matching chunks exist at all
    # ---------------------------------------------------------

    metadata_query = {
        "organisation_id": organisation_id,
        "department_id": department_id
    }

    matching_count = await knowledge_chunks_collection.count_documents(
        metadata_query
    )

    print(
        "📦 Matching chunks in MongoDB:",
        matching_count
    )

    # ---------------------------------------------------------
    # STEP 2: Inspect one matching chunk
    # ---------------------------------------------------------

    sample_chunk = await knowledge_chunks_collection.find_one(
        metadata_query,
        {
            "_id": 1,
            "filename": 1,
            "text": 1,
            "organisation_id": 1,
            "department_id": 1,
            "embedding": 1
        }
    )

    if sample_chunk:

        print("✅ Found matching chunk")

        print(
            "📄 Filename:",
            sample_chunk.get("filename")
        )

        print(
            "🏢 Organisation:",
            sample_chunk.get("organisation_id")
        )

        print(
            "🏢 Department:",
            sample_chunk.get("department_id")
        )

        print(
            "📝 Text preview:",
            sample_chunk.get("text", "")[:300]
        )

        embedding = sample_chunk.get("embedding")

        if embedding:
            print(
                "🧠 Embedding dimensions:",
                len(embedding)
            )
        else:
            print("❌ Embedding is missing")

    else:

        print(
            "❌ NO CHUNK MATCHES ORGANISATION + DEPARTMENT"
        )

    # ---------------------------------------------------------
    # STEP 3: Create query embedding
    # ---------------------------------------------------------

    query_embedding = create_embedding(question)

    print(
        "🧠 Query embedding dimensions:",
        len(query_embedding)
    )

    # ---------------------------------------------------------
    # STEP 4: Vector search
    # ---------------------------------------------------------

    pipeline = [
        {
            "$vectorSearch": {
                "index": "knowledge_vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 50,
                "limit": limit
            }
        },
        {
            "$project": {
                "_id": 0,
                "text": 1,
                "document_id": 1,
                "filename": 1,
                "page_number": 1,
                "chunk_index": 1,
                "score": {
                    "$meta": "vectorSearchScore"
                }
            }
        }
    ]

    results = []

    try:

        cursor = await knowledge_chunks_collection.aggregate(
            pipeline
        )

        async for item in cursor:
            results.append(item)

    except Exception as error:

        print("❌ RAG VECTOR SEARCH ERROR:")
        print(error)

        raise

    # ---------------------------------------------------------
    # STEP 5: Print results
    # ---------------------------------------------------------

    print(
        "🎯 Vector search results:",
        len(results)
    )

    for index, result in enumerate(
        results,
        start=1
    ):

        print(
            f"  {index}. "
            f"{result.get('filename')} "
            f"| score={result.get('score')} "
            f"| page={result.get('page_number')}"
        )

    print("=" * 80)

    return results


# ============================================================
# INGEST DOCUMENT
# ============================================================

async def ingest_document(
    *,
    file_bytes: bytes,
    filename: str,
    organisation_id: str,
    department_id: str,
    document_id: str
):
    """
    Full ingestion:

    File
      ↓
    Extract text
      ↓
    Chunk
      ↓
    Embedding
      ↓
    MongoDB
    """

    from services.document_parser import (
        extract_document_text
    )

    pages = extract_document_text(
        file_bytes,
        filename
    )

    inserted_chunks = []

    chunk_counter = 0

    for page in pages:

        page_text = page.get(
            "text",
            ""
        )

        page_number = page.get(
            "page_number"
        )

        chunks = chunk_text(
            page_text
        )

        for chunk in chunks:

            # ------------------------------------------------
            # Create embedding
            # ------------------------------------------------

            embedding = create_embedding(
                chunk
            )

            # ------------------------------------------------
            # Store chunk
            # ------------------------------------------------

            document = {

                "organisation_id":
                    str(organisation_id),

                "department_id":
                    str(department_id),

                "document_id":
                    str(document_id),

                "filename":
                    filename,

                "text":
                    chunk,

                "chunk_index":
                    chunk_counter,

                "page_number":
                    page_number,

                "embedding":
                    embedding
            }

            result = await (
                knowledge_chunks_collection
                .insert_one(
                    document
                )
            )

            inserted_chunks.append(
                str(
                    result.inserted_id
                )
            )

            chunk_counter += 1

    return {

        "chunks_created":
            len(inserted_chunks),

        "chunk_ids":
            inserted_chunks
    }

# from database import knowledge_chunks_collection

# from services.embeddings import (
#     create_embedding
# )


# # ============================================================
# # CHUNK TEXT
# # ============================================================

# def chunk_text(
#     text: str,
#     chunk_size: int = 800,
#     overlap: int = 100
# ):
#     """
#     Split document text into overlapping chunks.
#     """

#     text = text.strip()

#     if not text:
#         return []

#     chunks = []

#     start = 0

#     while start < len(text):

#         end = start + chunk_size

#         chunk = text[start:end]

#         if chunk.strip():

#             chunks.append(
#                 chunk.strip()
#             )

#         start += (
#             chunk_size - overlap
#         )

#     return chunks


# # ============================================================
# # SEARCH KNOWLEDGE
# # ============================================================

# async def search_knowledge(
#     *,
#     question: str,
#     organisation_id: str,
#     department_id: str,
#     limit: int = 5
# ):
#     """
#     Search organisation + department knowledge.

#     IMPORTANT:

#     organisation_id AND department_id
#     are both mandatory filters.

#     This prevents cross-organisation retrieval.
#     """

#     organisation_id = str(
#         organisation_id
#     )

#     department_id = str(
#         department_id
#     )

#     # --------------------------------------------------------
#     # Query embedding
#     # --------------------------------------------------------

#     query_embedding = create_embedding(
#         question
#     )

#     # --------------------------------------------------------
#     # Vector search
#     # --------------------------------------------------------

#     pipeline = [

#         {
#             "$vectorSearch": {

#                 "index":
#                     "knowledge_vector_index",

#                 "path":
#                     "embedding",

#                 "queryVector":
#                     query_embedding,

#                 "numCandidates":
#                     50,

#                 "limit":
#                     limit,

#                 "filter": {

#                     "organisation_id":
#                         organisation_id,

#                     "department_id":
#                         department_id
#                 }
#             }
#         },

#         {
#             "$project": {

#                 "_id": 0,

#                 "text": 1,

#                 "document_id": 1,

#                 "filename": 1,

#                 "page_number": 1,

#                 "chunk_index": 1,

#                 "score": {
#                     "$meta":
#                         "vectorSearchScore"
#                 }
#             }
#         }
#     ]

#     results = []

#     try:

#         cursor = (
#             knowledge_chunks_collection
#             .aggregate(
#                 pipeline
#             )
#         )

#         async for item in cursor:

#             results.append(
#                 item
#             )

#     except Exception as error:

#         print(
#             "❌ RAG search error:",
#             error
#         )

#         raise

#     return results


# # ============================================================
# # INGEST DOCUMENT
# # ============================================================

# async def ingest_document(
#     *,
#     file_bytes: bytes,
#     filename: str,
#     organisation_id: str,
#     department_id: str,
#     document_id: str
# ):
#     """
#     Full ingestion:

#     File
#       ↓
#     Extract text
#       ↓
#     Chunk
#       ↓
#     Embedding
#       ↓
#     MongoDB
#     """

#     from services.document_parser import (
#         extract_document_text
#     )

#     pages = extract_document_text(
#         file_bytes,
#         filename
#     )

#     inserted_chunks = []

#     chunk_counter = 0

#     for page in pages:

#         page_text = page.get(
#             "text",
#             ""
#         )

#         page_number = page.get(
#             "page_number"
#         )

#         chunks = chunk_text(
#             page_text
#         )

#         for chunk in chunks:

#             embedding = create_embedding(
#                 chunk
#             )

#             document = {

#                 "organisation_id":
#                     str(organisation_id),

#                 "department_id":
#                     str(department_id),

#                 "document_id":
#                     str(document_id),

#                 "filename":
#                     filename,

#                 "text":
#                     chunk,

#                 "chunk_index":
#                     chunk_counter,

#                 "page_number":
#                     page_number,

#                 "embedding":
#                     embedding
#             }

#             result = await (
#                 knowledge_chunks_collection
#                 .insert_one(
#                     document
#                 )
#             )

#             inserted_chunks.append(
#                 str(result.inserted_id)
#             )

#             chunk_counter += 1

#     return {
#         "chunks_created":
#             len(inserted_chunks),

#         "chunk_ids":
#             inserted_chunks
#     }