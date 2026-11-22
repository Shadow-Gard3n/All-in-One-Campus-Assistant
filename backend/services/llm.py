from config import settings

from services import ollama
from services import gemini


# ============================================================
# GENERATE TEXT
# ============================================================

async def generate_text(
    *,
    prompt: str,
    temperature: float = 0.1
) -> str:

    if settings.LLM_PROVIDER == "ollama":

        return await ollama.generate_text(

            prompt=prompt,

            temperature=
                temperature
        )

    if settings.LLM_PROVIDER == "gemini":

        return await gemini.generate_text(

            prompt=prompt,

            temperature=
                temperature
        )

    raise ValueError(
        f"Unsupported LLM provider: "
        f"{settings.LLM_PROVIDER}"
    )


# ============================================================
# GENERATE JSON
# ============================================================

async def generate_json(
    *,
    prompt: str,
    temperature: float = 0.1
) -> dict:

    if settings.LLM_PROVIDER == "ollama":

        return await ollama.generate_json(

            prompt=prompt,

            temperature=
                temperature
        )

    if settings.LLM_PROVIDER == "gemini":

        return await gemini.generate_json(

            prompt=prompt,

            temperature=
                temperature
        )

    raise ValueError(
        f"Unsupported LLM provider: "
        f"{settings.LLM_PROVIDER}"
    )