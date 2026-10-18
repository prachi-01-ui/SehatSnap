
from datetime import date, datetime
from typing import Any


REQUIRED_FIELDS = ("patient_name", "report_date", "report_type")


def validate_report_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Validate required metadata fields for a medical report.

    Returns the validated metadata if it is valid.
    Raises ValueError with a helpful message if validation fails.
    """
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a dictionary.")

    # Check that all required fields are present and non-empty.
    missing_fields = [
        field
        for field in REQUIRED_FIELDS
        if field not in metadata
        or metadata[field] is None
        or (
            isinstance(metadata[field], str)
            and not metadata[field].strip()
        )
    ]

    if missing_fields:
        raise ValueError(
            "Missing or empty required metadata fields: "
            f"{', '.join(missing_fields)}"
        )

    # Validate and normalize the patient name.
    patient_name = metadata["patient_name"]
    if not isinstance(patient_name, str):
        raise ValueError("patient_name must be a string.")

    patient_name = patient_name.strip()

    # Validate and normalize the report type.
    report_type = metadata["report_type"]
    if not isinstance(report_type, str):
        raise ValueError("report_type must be a string.")

    report_type = report_type.strip()

    # Parse the report date.
    report_date = metadata["report_date"]

    if isinstance(report_date, datetime):
        parsed_date = report_date.date()
    elif isinstance(report_date, date):
        parsed_date = report_date
    elif isinstance(report_date, str):
        try:
            parsed_date = date.fromisoformat(report_date.strip())
        except ValueError as exc:
            raise ValueError(
                "report_date must be a valid date in YYYY-MM-DD format."
            ) from exc
    else:
        raise ValueError(
            "report_date must be a date or a YYYY-MM-DD string."
        )

    # Reject report dates in the future.
    if parsed_date > date.today():
        raise ValueError("report_date cannot be in the future.")

    # Return a normalized copy without modifying the original dictionary.
    validated_metadata = metadata.copy()
    validated_metadata["patient_name"] = patient_name
    validated_metadata["report_type"] = report_type
    validated_metadata["report_date"] = parsed_date.isoformat()

    return validated_metadata

