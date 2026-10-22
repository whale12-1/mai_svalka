import io
from minio import Minio
from .config import settings

_client: Minio | None = None

def client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
        )
        if not _client.bucket_exists(settings.minio_bucket):
            _client.make_bucket(settings.minio_bucket)
    return _client

def upload(key: str, data: bytes, content_type: str) -> None:
    client().put_object(settings.minio_bucket, key, io.BytesIO(data), len(data), content_type=content_type)

def presigned_url(key: str, expires_seconds: int = 3600) -> str:
    from datetime import timedelta
    return client().presigned_get_object(
        settings.minio_bucket, key, expires=timedelta(seconds=expires_seconds)
    )