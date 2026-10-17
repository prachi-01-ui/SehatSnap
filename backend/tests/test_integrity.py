
from backend.app.services.integrity import (
    calculate_content_sha256,
    is_duplicate,
)


def test_same_content_produces_same_hash():
    content = b"Sample medical report"
    first_hash = calculate_content_sha256(content)
    second_hash = calculate_content_sha256(content)

    assert first_hash == second_hash


def test_different_content_produces_different_hash():
    first_hash = calculate_content_sha256(b"Report A")
    second_hash = calculate_content_sha256(b"Report B")

    assert first_hash != second_hash


def test_duplicate_is_detected():
    report_hash = calculate_content_sha256(b"Sample medical report")

    assert is_duplicate(report_hash, {report_hash})


def test_new_report_is_not_duplicate():
    report_hash = calculate_content_sha256(b"New report")

    assert not is_duplicate(report_hash, {"some-other-hash"})
