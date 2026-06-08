"""스토리지 추상화 — R2(S3 호환, private) 또는 로컬 디스크.

- R2 환경변수(R2_ENDPOINT/R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY/R2_BUCKET)가 모두 있으면 R2,
  없으면 기존 로컬 `app/storage` 를 사용한다(로컬 개발 폴백).
- 저장 URL은 항상 내부 경로 `/storage/{key}` 로 유지한다(브라우저는 백엔드 /storage 프록시로만 접근,
  R2 버킷은 비공개). 실제 객체는 `key`(= /storage 접두어를 뗀 경로, 예: voices/{id}/sample.wav)로 다룬다.
- boto3 는 R2 모드에서만 지연 import (로컬 폴백은 boto3 없이도 동작).
"""

import mimetypes
import os
import shutil
from pathlib import Path

from .config import STORAGE_ROOT, STORAGE_URL_PREFIX

_PREFIX = STORAGE_URL_PREFIX.rstrip("/") + "/"  # "/storage/"

# mimetypes 가 환경마다 달라서 핵심 확장자는 직접 보정.
_CONTENT_TYPES = {
    ".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
    ".webm": "audio/webm", ".ogg": "audio/ogg",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".mp4": "video/mp4",
}

_R2_KEYS = ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")


def r2_enabled() -> bool:
    """R2 접근에 필요한 env 가 모두 있으면 True (없으면 로컬 디스크 폴백)."""
    return all(os.getenv(k) for k in _R2_KEYS)


_client = None


def _r2():
    global _client
    if _client is None:
        import boto3
        from botocore.config import Config

        _client = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            region_name=os.getenv("R2_REGION", "auto"),
            config=Config(signature_version="s3v4"),
        )
    return _client


def _bucket() -> str:
    return os.getenv("R2_BUCKET", "")


def normalize_storage_key(key_or_url: str) -> str:
    """'/storage/voices/x.wav' 또는 'voices/x.wav' → 'voices/x.wav' (접두어/앞슬래시 제거)."""
    k = (key_or_url or "").strip()
    if k.startswith(_PREFIX):
        k = k[len(_PREFIX):]
    elif k.startswith(STORAGE_URL_PREFIX):  # "/storage" 만 온 경우
        k = k[len(STORAGE_URL_PREFIX):]
    return k.lstrip("/")


def storage_url_to_key(url: str) -> str:
    """내부 URL(/storage/...) → R2/로컬 key."""
    return normalize_storage_key(url)


def get_storage_url(key: str) -> str:
    """key → 내부 서비스 URL(/storage/{key}). DB 에 저장하는 값(공개 R2 URL 아님)."""
    return f"{STORAGE_URL_PREFIX}/{normalize_storage_key(key)}"


# 동일 의미(공개 URL 미사용 — 내부 프록시 URL). 호출부 호환용 별칭.
get_public_url = get_storage_url


def content_type_for(key: str) -> str:
    ext = Path(key).suffix.lower()
    return _CONTENT_TYPES.get(ext) or mimetypes.guess_type(key)[0] or "application/octet-stream"


def _local_path(key: str) -> Path:
    return STORAGE_ROOT / normalize_storage_key(key)


def save_bytes(key: str, data: bytes, content_type: str | None = None) -> None:
    """파일 저장. R2 모드면 put_object, 아니면 로컬 디스크."""
    key = normalize_storage_key(key)
    if r2_enabled():
        _r2().put_object(
            Bucket=_bucket(), Key=key, Body=data,
            ContentType=content_type or content_type_for(key),
        )
    else:
        p = _local_path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


def read_bytes(key: str) -> bytes | None:
    """파일 바이트. 없으면 None. R2 모드면 get_object, 아니면 로컬."""
    key = normalize_storage_key(key)
    if r2_enabled():
        from botocore.exceptions import ClientError

        try:
            return _r2().get_object(Bucket=_bucket(), Key=key)["Body"].read()
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code in ("NoSuchKey", "NoSuchBucket", "404"):
                return None
            raise
    p = _local_path(key)
    return p.read_bytes() if p.is_file() else None


def delete(key: str) -> None:
    """파일 삭제(없어도 에러 없음)."""
    key = normalize_storage_key(key)
    if r2_enabled():
        from botocore.exceptions import ClientError

        try:
            _r2().delete_object(Bucket=_bucket(), Key=key)
        except ClientError:
            pass
    else:
        _local_path(key).unlink(missing_ok=True)


def delete_prefix(prefix: str) -> None:
    """prefix 하위 모든 객체/파일 삭제(없어도 에러 없음). 폴더 단위 삭제용(예: 'voices/{id}/').

    경계 안전: 'voices/abc' 가 'voices/abcd' 까지 지우지 않도록 끝에 '/' 를 보장한다.
    """
    prefix = normalize_storage_key(prefix)
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    if not prefix:
        return  # 전체 삭제 방지
    if r2_enabled():
        from botocore.exceptions import ClientError

        try:
            paginator = _r2().get_paginator("list_objects_v2")
            batch: list[dict] = []
            for page in paginator.paginate(Bucket=_bucket(), Prefix=prefix):
                for obj in page.get("Contents", []):
                    batch.append({"Key": obj["Key"]})
                    if len(batch) == 1000:  # delete_objects 1회 한도
                        _r2().delete_objects(Bucket=_bucket(), Delete={"Objects": batch})
                        batch = []
            if batch:
                _r2().delete_objects(Bucket=_bucket(), Delete={"Objects": batch})
        except ClientError:
            pass
    else:
        d = STORAGE_ROOT / prefix
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)


def exists(key: str) -> bool:
    key = normalize_storage_key(key)
    if r2_enabled():
        from botocore.exceptions import ClientError

        try:
            _r2().head_object(Bucket=_bucket(), Key=key)
            return True
        except ClientError:
            return False
    return _local_path(key).is_file()
