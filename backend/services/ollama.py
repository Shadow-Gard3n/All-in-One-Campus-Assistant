import json
from ollama import AsyncClient

from config import settings


client = AsyncClient(
    host=settings.OLLAMA_HOST
)


async def generate_text(
    *,
    prompt: str,
    temperature: float = 0.1
) -> str:

    response = await client.chat(
        model=settings.OLLAMA_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": temperature
        }
    )

    return response["message"]["content"]


async def generate_json(
    *,
    prompt: str,
    temperature: float = 0.1
) -> dict:

    response = await client.chat(
        model=settings.OLLAMA_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        format="json",
        options={
            "temperature": temperature
        }
    )

    content = response["message"]["content"]

    try:
        return json.loads(content)

    except json.JSONDecodeError as error:

        print("❌ Ollama returned invalid JSON:")
        print(content)

        raise ValueError(
            "Ollama returned invalid JSON"
        ) from error