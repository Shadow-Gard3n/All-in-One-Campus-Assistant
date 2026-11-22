from sentence_transformers import SentenceTransformer


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = "BAAI/bge-small-en-v1.5"

model = SentenceTransformer(
    MODEL_NAME
)


# ============================================================
# CREATE EMBEDDING
# ============================================================

def create_embedding(
    text: str
):
    """
    Convert text into a normalized vector.
    """

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()