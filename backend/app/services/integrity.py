
import hashlib
from pathlib import Path


def calculate_sha256(file_path: str | Path) -> str:
    """Calculate the SHA-256 hash of a file without loading it all into memory."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def calculate_content_sha256(content: bytes) -> str:
    """Calculate the SHA-256 hash of bytes already in memory."""
    return hashlib.sha256(content).hexdigest()


def is_duplicate(
    new_file_hash: str,
    existing_hashes: set[str] | list[str],
) -> bool:
    """Return True if the same file hash already exists."""
    return new_file_hash in existing_hashes
