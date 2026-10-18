
import hashlib
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile, HTTPException

from backend.app.config import (
    UPLOADS_DIR,
    MAX_UPLOAD_SIZE_BYTES,
    ALLOWED_EXTENSIONS,
    FILE_SIGNATURES,
)


async def process_and_save_upload(
    upload_file: UploadFile,
) -> Tuple[str, str, int, str]:
    """
    Safely streams an uploaded file to storage:
    1. Validates extension.
    2. Streams in 64 KiB chunks enforcing the upload size limit.
    3. Verifies file signature (magic bytes).
    4. Computes SHA-256 hash while streaming.
    5. Verifies the saved file against the original hash.
    6. Stores the file with a random UUID filename.
    7. Cleans up partial or invalid files on failure.

    Returns:
        (stored_filename, relative_path, file_size_bytes, sha256_hash)
    """
    if not upload_file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    filename = upload_file.filename.strip()
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file extension '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    stored_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = UPLOADS_DIR / stored_filename

    hasher = hashlib.sha256()
    total_bytes = 0
    first_chunk = True

    try:
        with open(target_path, "wb") as f:
            while True:
                chunk = await upload_file.read(64 * 1024)

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File exceeds maximum upload size of "
                            f"{MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MiB"
                        ),
                    )

                if first_chunk:
                    expected_signatures = FILE_SIGNATURES.get(ext, [])
                    signature_matched = any(
                        chunk.startswith(sig) for sig in expected_signatures
                    )

                    if not signature_matched:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Invalid file signature for extension '{ext}'. "
                                "File content does not match expected format."
                            ),
                        )

                    first_chunk = False

                hasher.update(chunk)
                f.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty (0 bytes).",
            )

        # Calculate the SHA-256 hash of the uploaded content.
        sha256_hash = hasher.hexdigest()

        # Verify that the saved file matches the uploaded content.
        stored_hasher = hashlib.sha256()

        with open(target_path, "rb") as saved_file:
            for chunk in iter(lambda: saved_file.read(64 * 1024), b""):
                stored_hasher.update(chunk)

        stored_sha256_hash = stored_hasher.hexdigest()

        if stored_sha256_hash != sha256_hash:
            raise HTTPException(
                status_code=500,
                detail="File integrity verification failed after storage.",
            )

    except Exception:
        # Remove partial or invalid files if any operation fails.
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        raise

    relative_path = f"data/uploads/{stored_filename}"

    return stored_filename, relative_path, total_bytes, sha256_hash
