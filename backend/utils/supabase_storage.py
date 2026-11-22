from supabase import create_client, Client

from config import settings


supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SECRET_KEY
)


def upload_file(
    file_path: str,
    file_bytes: bytes,
    content_type: str
):
    return supabase.storage.from_(
        settings.SUPABASE_BUCKET
    ).upload(
        file_path,
        file_bytes,
        {
            "content-type": content_type,
            "upsert": False
        }
    )


def delete_file(file_path: str):
    return supabase.storage.from_(
        settings.SUPABASE_BUCKET
    ).remove(
        [file_path]
    )