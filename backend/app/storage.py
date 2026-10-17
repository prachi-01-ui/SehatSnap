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
    2. Streams in 64 KiB chunks enforcing 20 MiB limit.
    3. Verifies file signature (magic bytes) from first chunk.
    4. Computes SHA-256 hash.
    5. Stores file with random UUID filename.
    6. Ensures partial cleanup on any failure.

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
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    stored_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = UPLOADS_DIR / stored_filename

    hasher = hashlib.sha256()
    total_bytes = 0
    first_chunk = True

    try:
        with open(target_path, "wb") as f:
            while True:
                chunk = await upload_file.read(64 * 1024)  # 64 KiB chunks
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum upload size of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MiB",
                    )

                if first_chunk:
                    # Validate file signature (magic bytes)
                    expected_signatures = FILE_SIGNATURES.get(ext, [])
                    signature_matched = any(chunk.startswith(sig) for sig in expected_signatures)
                    if not signature_matched:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid file signature for extension '{ext}'. File content does not match expected format.",
                        )
                    first_chunk = False

                hasher.update(chunk)
                f.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    except Exception:
        # Guarantee cleanup of partial/corrupted files
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        raise

    sha256_hash = hasher.hexdigest()
    relative_path = f"data/uploads/{stored_filename}"

    return stored_filename, relative_path, total_bytes, sha256_hash
