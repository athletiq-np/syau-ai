import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import structlog

from core.config import settings

log = structlog.get_logger()

_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        scheme = "https" if settings.minio_secure else "http"
        endpoint_url = f"{scheme}://{settings.minio_endpoint}"
        _s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
    return _s3_client


def ensure_bucket_exists() -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.minio_bucket)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=settings.minio_bucket)
            # Set public read policy for output files
            policy = f"""{{
                "Version": "2012-10-17",
                "Statement": [{{
                    "Effect": "Allow",
                    "Principal": {{"AWS": "*"}},
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::{settings.minio_bucket}/*"
                }}]
            }}"""
            client.put_bucket_policy(Bucket=settings.minio_bucket, Policy=policy)
            log.info("minio_bucket_created", bucket=settings.minio_bucket)
        else:
            raise


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload bytes to MinIO. Returns the object key."""
    client = get_s3_client()
    client.put_object(
        Bucket=settings.minio_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    log.info("minio_upload", key=key, size=len(data))
    return key


def upload_file(key: str, file_path: str, content_type: str = "application/octet-stream") -> str:
    """Upload a file from disk to MinIO. Returns the object key."""
    client = get_s3_client()
    client.upload_file(
        Filename=file_path,
        Bucket=settings.minio_bucket,
        Key=key,
        ExtraArgs={"ContentType": content_type},
    )
    log.info("minio_upload_file", key=key, path=file_path)
    return key


def get_presigned_url(key: str, expiry_seconds: int = 3600) -> str:
    """Generate a presigned GET URL. Uses public endpoint for browser access."""
    # Build client pointing at the public endpoint (accessible from browser)
    scheme = "https" if settings.minio_secure else "http"
    public_endpoint = settings.minio_public_endpoint
    client = boto3.client(
        "s3",
        endpoint_url=public_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": key},
        ExpiresIn=expiry_seconds,
    )
    return url


def download_text(key: str, encoding: str = "utf-8") -> str:
    """Read a text object from MinIO."""
    client = get_s3_client()
    response = client.get_object(Bucket=settings.minio_bucket, Key=key)
    body = response["Body"].read()
    return body.decode(encoding)


def download_bytes(key: str) -> bytes:
    """Read a binary object from MinIO."""
    client = get_s3_client()
    response = client.get_object(Bucket=settings.minio_bucket, Key=key)
    body = response["Body"].read()
    log.info("minio_download", key=key, size=len(body))
    return body
