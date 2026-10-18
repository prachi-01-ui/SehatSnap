
import pytest

from backend.app.services.metadata_validator import validate_report_metadata


def test_valid_metadata_is_returned():
    metadata = {
        "patient_name": " Rahul Sharma ",
        "report_date": "2026-10-18",
        "report_type": " Blood Test ",
    }

    result = validate_report_metadata(metadata)

    assert result["patient_name"] == "Rahul Sharma"
    assert result["report_date"] == "2026-10-18"
    assert result["report_type"] == "Blood Test"


@pytest.mark.parametrize(
    "field",
    ["patient_name", "report_date", "report_type"],
)
def test_missing_required_field_raises_error(field):
    metadata = {
        "patient_name": "Rahul Sharma",
        "report_date": "2026-10-18",
        "report_type": "Blood Test",
    }
    del metadata[field]

    with pytest.raises(ValueError, match="Missing or empty"):
        validate_report_metadata(metadata)


@pytest.mark.parametrize("report_date", ["invalid-date", "2026-02-30", ""])
def test_invalid_report_date_raises_error(report_date):
    metadata = {
        "patient_name": "Rahul Sharma",
        "report_date": report_date,
        "report_type": "Blood Test",
    }

    with pytest.raises(ValueError):
        validate_report_metadata(metadata)


def test_non_dictionary_metadata_raises_error():
    with pytest.raises(ValueError, match="dictionary"):
        validate_report_metadata(None)


def test_original_metadata_is_not_modified():
    metadata = {
        "patient_name": " Rahul Sharma ",
        "report_date": "2026-10-18",
        "report_type": " Blood Test ",
    }
    original = metadata.copy()

    validate_report_metadata(metadata)

    assert metadata == original

