"""
Modular Medicine Verification Service for SehatSnap.

Provides verification of medicine packaging label metadata (brand name,
active ingredient, strength, formulation/dosage form, and manufacturer)
against an explicitly identified synthetic demonstration dataset modeled on CDSCO/SUGAM.

Key principles:
1. Compares medicine name, active ingredient, strength, formulation, and manufacturer.
2. Returns structured findings, source, timestamp, and verified, not_verified, mismatch, or inconclusive status.
3. Does not claim official regulatory approval without supporting source data.
4. Distinguishes missing evidence from a confirmed mismatch.
5. Strictly avoids prescribing, recommending medicines, diagnosing conditions, or altering prescriptions.
6. Clearly labels all demonstration data and explains limitations.
"""

from typing import Optional, Dict, Any, List, Tuple
import datetime
import re

from backend.app.schemas import (
    MedicineVerificationRequest,
    MedicineVerificationResponse,
    MedicineCheckItem,
    VerifiedMedicineProduct,
    MedicineSourceReference,
)

# Clearly labelled synthetic demonstration dataset based on simulated CDSCO/SUGAM regulatory records
SYNTHETIC_SUGAM_REGISTRY: List[Dict[str, Any]] = [
    {
        "brand": "Glycomet 500",
        "aliases": ["Glycomet", "Glycomet-500", "Glycomet 500mg"],
        "standardizedTitle": "Metformin Hydrochloride Tablets IP",
        "activeIngredient": "Metformin Hydrochloride",
        "strength": "500 mg",
        "strengthNumeric": 500.0,
        "strengthUnit": "mg",
        "dosageForm": "Immediate-release uncoated tablet IP",
        "genericDosageForm": "Tablet",
        "manufacturer": "USV Private Limited",
        "manufacturerAliases": ["USV Pvt Ltd", "USV Ltd", "USV"],
        "route": "Oral",
        "regulatoryStatus": "Cataloged in demo SUGAM database",
        "licenseNumber": "G/25/1042",
        "formulationNotes": (
            "The checked regulatory source lists an immediate-release tablet; the uploaded label image "
            "does not clearly show release type (IR vs SR/ER). Verify with a registered pharmacist or clinician."
        ),
    },
    {
        "brand": "Augmentin 625 Duo",
        "aliases": ["Augmentin 625", "Augmentin Duo", "Augmentin"],
        "standardizedTitle": "Amoxicillin and Potassium Clavulanate Tablets IP",
        "activeIngredient": "Amoxicillin and Potassium Clavulanate",
        "strength": "625 mg",
        "strengthNumeric": 625.0,
        "strengthUnit": "mg",
        "dosageForm": "Film-coated tablet",
        "genericDosageForm": "Tablet",
        "manufacturer": "GlaxoSmithKline Pharmaceuticals Ltd.",
        "manufacturerAliases": ["GSK", "GlaxoSmithKline", "GSK India"],
        "route": "Oral",
        "regulatoryStatus": "Cataloged in demo SUGAM database",
        "licenseNumber": "MH/DRUG/28-A/481",
        "formulationNotes": (
            "Formulation contains Amoxicillin 500 mg + Clavulanic Acid 125 mg. "
            "Check packaging blister foil for intact desiccant protection."
        ),
    },
    {
        "brand": "Telma 40",
        "aliases": ["Telma-40", "Telma 40mg", "Telma"],
        "standardizedTitle": "Telmisartan Tablets IP",
        "activeIngredient": "Telmisartan",
        "strength": "40 mg",
        "strengthNumeric": 40.0,
        "strengthUnit": "mg",
        "dosageForm": "Uncoated tablet",
        "genericDosageForm": "Tablet",
        "manufacturer": "Glenmark Pharmaceuticals Ltd.",
        "manufacturerAliases": ["Glenmark", "Glenmark Pharma"],
        "route": "Oral",
        "regulatoryStatus": "Cataloged in demo SUGAM database",
        "licenseNumber": "HP/DRUG/09/84",
        "formulationNotes": "Moisture-sensitive product; package must be stored in original blister until administration.",
    },
    {
        "brand": "Thyronorm 50",
        "aliases": ["Thyronorm 50 mcg", "Thyronorm 50mcg", "Thyronorm"],
        "standardizedTitle": "Levothyroxine Sodium Tablets IP",
        "activeIngredient": "Levothyroxine Sodium",
        "strength": "50 mcg",
        "strengthNumeric": 50.0,
        "strengthUnit": "mcg",
        "dosageForm": "Uncoated tablet",
        "genericDosageForm": "Tablet",
        "manufacturer": "Abbott India Limited",
        "manufacturerAliases": ["Abbott", "Abbott India"],
        "route": "Oral",
        "regulatoryStatus": "Cataloged in demo SUGAM database",
        "licenseNumber": "G/28/142",
        "formulationNotes": "Narrow therapeutic index medication. Bottle packaging contains desiccant canister.",
    },
    {
        "brand": "Pan 40",
        "aliases": ["Pan-40", "Pan 40mg", "Pan"],
        "standardizedTitle": "Pantoprazole Gastro-resistant Tablets IP",
        "activeIngredient": "Pantoprazole",
        "strength": "40 mg",
        "strengthNumeric": 40.0,
        "strengthUnit": "mg",
        "dosageForm": "Enteric-coated / Gastro-resistant tablet",
        "genericDosageForm": "Tablet",
        "manufacturer": "Alkem Laboratories Ltd.",
        "manufacturerAliases": ["Alkem", "Alkem Labs"],
        "route": "Oral",
        "regulatoryStatus": "Cataloged in demo SUGAM database",
        "licenseNumber": "S-MNB/08/11",
        "formulationNotes": "Gastro-resistant enteric coating designed to resist stomach acid. Do not crush or chew.",
    },
]

DEMO_MEDICINE_AUTHORITY = "CDSCO/SUGAM demonstration dataset"
DEMO_SOURCE_DATE = "2025-08-06"
DEMO_MEDICINE_RETRIEVED_AT = "2025-10-20"


def _normalize(text: Optional[str]) -> str:
    """Normalizes string for robust comparison by removing non-alphanumeric chars and extra whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


def _extract_numeric_and_unit(strength_str: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    """Extracts numeric value and unit from strength string (e.g., '500 mg' -> (500.0, 'mg'))."""
    if not strength_str:
        return None, None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z/%]+)?", strength_str.strip())
    if match:
        val = float(match.group(1))
        unit = match.group(2).lower() if match.group(2) else ""
        return val, unit
    return None, None


def _find_medicine_record(
    brand: Optional[str],
    ingredient: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Searches the synthetic regulatory dataset for matching entry by brand name or active ingredient.
    Returns (record, match_method).
    """
    norm_brand = _normalize(brand)
    norm_ingredient = _normalize(ingredient)

    # 1. Primary brand match
    if norm_brand:
        for entry in SYNTHETIC_SUGAM_REGISTRY:
            entry_brand_norm = _normalize(entry["brand"])
            if norm_brand == entry_brand_norm:
                return entry, "brand_exact"
            for alias in entry.get("aliases", []):
                if norm_brand == _normalize(alias):
                    return entry, "brand_alias"
            if norm_brand in entry_brand_norm or entry_brand_norm in norm_brand:
                return entry, "brand_partial"

    # 2. Active ingredient match
    if norm_ingredient:
        for entry in SYNTHETIC_SUGAM_REGISTRY:
            entry_ing_norm = _normalize(entry["activeIngredient"])
            if norm_ingredient == entry_ing_norm or norm_ingredient in entry_ing_norm:
                return entry, "ingredient_match"

    return None, None


def verify_medicine_identity_and_composition(
    request: MedicineVerificationRequest,
    current_time: Optional[datetime.datetime] = None,
) -> MedicineVerificationResponse:
    """
    Modular medicine verification engine.

    Compares product label details against the synthetic CDSCO/SUGAM regulatory demo dataset.
    Distinguishes missing fields from confirmed mismatches.
    Never invents official approval results or makes medical/prescribing recommendations.
    """
    now = current_time or datetime.datetime.now(datetime.timezone.utc)
    timestamp_iso = now.isoformat()

    source_ref = MedicineSourceReference(
        authority=DEMO_MEDICINE_AUTHORITY,
        sourceDate=DEMO_SOURCE_DATE,
        retrievedAt=DEMO_MEDICINE_RETRIEVED_AT,
        isDemonstrationDataset=True,
        sourceNotes="Synthetic regulatory dataset modeled on Indian Pharmacopoeia / CDSCO SUGAM portal records. Never queries live portals.",
    )

    safety_disclaimer = (
        "SehatSnap does not prescribe, recommend medicines, diagnose conditions, or alter prescriptions. "
        "This service verifies product label metadata against demonstration regulatory records only. "
        "Always consult a registered medical practitioner or licensed pharmacist."
    )

    # --- Scenario 1: Source Failure Simulation ---
    if request.simulateSourceFailure:
        return MedicineVerificationResponse(
            matchConfidence=0.0,
            verdict="Regulatory Catalogue Check Unavailable",
            status="inconclusive",
            reviewBanner=None,
            product=None,
            checks=[
                MedicineCheckItem(
                    item="Source connectivity",
                    details="Connection to demonstration regulatory catalogue timed out or failed",
                    status="warning",
                ),
                MedicineCheckItem(
                    item="Verification recommendation",
                    details="Unable to query regulatory dataset at this time. Verify product label credentials directly with a licensed pharmacist.",
                    status="inconclusive",
                ),
            ],
            sourceReference=source_ref,
            evidenceLimitations="Regulatory catalogue lookup service reported a connection failure. No inference regarding product safety, approval, or authenticity is made.",
            timestamp=timestamp_iso,
            disclaimer=safety_disclaimer,
        )

    # --- Scenario 2: Insufficient Input Data ---
    raw_brand = request.brandName.strip() if request.brandName else ""
    raw_ingredient = request.activeIngredient.strip() if request.activeIngredient else ""
    raw_strength = request.strength.strip() if request.strength else ""
    raw_form = request.dosageForm.strip() if request.dosageForm else ""
    raw_mfg = request.manufacturer.strip() if request.manufacturer else ""
    raw_route = request.route.strip() if request.route else ""

    if not raw_brand and not raw_ingredient:
        return MedicineVerificationResponse(
            matchConfidence=0.0,
            verdict="Inconclusive - Insufficient Product Information",
            status="inconclusive",
            reviewBanner=None,
            product=None,
            checks=[
                MedicineCheckItem(
                    item="Product identification",
                    details="Neither brand name nor active pharmaceutical ingredient was provided",
                    status="inconclusive",
                ),
                MedicineCheckItem(
                    item="Verification recommendation",
                    details="Supply the brand name or active ingredient printed on the medicine blister packaging or box.",
                    status="review",
                ),
            ],
            sourceReference=source_ref,
            evidenceLimitations="Insufficient input data provided to initiate product comparison. Missing inputs do not imply an unapproved or counterfeit product.",
            timestamp=timestamp_iso,
            disclaimer=safety_disclaimer,
        )

    # --- Scenario 3: Regulatory Dataset Lookup ---
    record, match_method = _find_medicine_record(raw_brand, raw_ingredient)

    # Case A: Record not found in demo registry
    if not record:
        query_desc = raw_brand or raw_ingredient
        return MedicineVerificationResponse(
            matchConfidence=0.10,
            verdict="Not Verified in Demonstration Dataset",
            status="not_verified",
            reviewBanner=None,
            product=None,
            checks=[
                MedicineCheckItem(
                    item="Regulatory catalogue search",
                    details=f"No entry found matching '{query_desc}' in synthetic demonstration dataset",
                    status="review",
                ),
                MedicineCheckItem(
                    item="Missing data notice",
                    details="Absence from demonstration records must not be interpreted as lack of regulatory approval, unapproved status, or counterfeit product",
                    status="inconclusive",
                ),
            ],
            sourceReference=source_ref,
            evidenceLimitations=(
                "No matching entry found in the demonstration regulatory snapshot. Because this is a curated demo dataset, "
                "missing records do not indicate regulatory non-compliance or fraudulent activity. Always cross-check "
                "with the primary official CDSCO SUGAM directory."
            ),
            timestamp=timestamp_iso,
            disclaimer=safety_disclaimer,
        )

    # --- Case B: Record Found; Evaluate Individual Fields ---
    checks: List[MedicineCheckItem] = []
    confidence_points = 0.0
    confirmed_mismatches: List[str] = []
    missing_fields: List[str] = []
    partial_details: List[str] = []

    # 1. Active Ingredient Check
    reg_ingredient = record["activeIngredient"]
    if raw_ingredient:
        norm_query_ing = _normalize(raw_ingredient)
        norm_reg_ing = _normalize(reg_ingredient)
        if norm_query_ing == norm_reg_ing or norm_query_ing in norm_reg_ing or norm_reg_ing in norm_query_ing:
            checks.append(
                MedicineCheckItem(
                    item="Active ingredient",
                    details=f"{reg_ingredient} · match",
                    status="verified",
                )
            )
            confidence_points += 0.30
        else:
            confirmed_mismatches.append("active ingredient")
            checks.append(
                MedicineCheckItem(
                    item="Active ingredient",
                    details=f"Queried '{raw_ingredient}' differs from registered '{reg_ingredient}'",
                    status="warning",
                )
            )
    else:
        missing_fields.append("active ingredient")
        checks.append(
            MedicineCheckItem(
                item="Active ingredient",
                details=f"Not specified on query; registered as {reg_ingredient}",
                status="review",
            )
        )
        confidence_points += 0.15

    # 2. Strength Check
    reg_strength = record["strength"]
    if raw_strength:
        q_num, q_unit = _extract_numeric_and_unit(raw_strength)
        r_num, r_unit = _extract_numeric_and_unit(reg_strength)

        if q_num is not None and r_num is not None:
            if q_num == r_num and (not q_unit or not r_unit or q_unit == r_unit):
                checks.append(
                    MedicineCheckItem(
                        item="Strength",
                        details=f"{reg_strength} · match",
                        status="verified",
                    )
                )
                confidence_points += 0.25
            else:
                confirmed_mismatches.append("strength")
                checks.append(
                    MedicineCheckItem(
                        item="Strength",
                        details=f"Queried '{raw_strength}' does not match registered '{reg_strength}'",
                        status="warning",
                    )
                )
        else:
            if _normalize(raw_strength) in _normalize(reg_strength):
                checks.append(
                    MedicineCheckItem(
                        item="Strength",
                        details=f"{reg_strength} · match",
                        status="verified",
                    )
                )
                confidence_points += 0.20
            else:
                confirmed_mismatches.append("strength")
                checks.append(
                    MedicineCheckItem(
                        item="Strength",
                        details=f"Queried strength '{raw_strength}' conflicts with '{reg_strength}'",
                        status="warning",
                    )
                )
    else:
        missing_fields.append("strength")
        checks.append(
            MedicineCheckItem(
                item="Strength",
                details=f"Not specified on query; registered as {reg_strength}",
                status="review",
            )
        )
        confidence_points += 0.10

    # 3. Dosage Form / Formulation Check
    reg_form = record["dosageForm"]
    generic_form = record.get("genericDosageForm", "Tablet")
    review_banner: Optional[str] = None

    if raw_form:
        norm_query_form = _normalize(raw_form)
        norm_reg_form = _normalize(reg_form)
        norm_generic_form = _normalize(generic_form)

        if norm_query_form == norm_reg_form:
            checks.append(
                MedicineCheckItem(
                    item="Dosage form",
                    details=f"{reg_form} · match",
                    status="verified",
                )
            )
            confidence_points += 0.20
        elif norm_query_form == norm_generic_form or norm_query_form in norm_reg_form:
            # Partial detail (e.g. user entered "Tablet", while registered is "Immediate-release uncoated tablet IP")
            partial_details.append("dosage form release type")
            checks.append(
                MedicineCheckItem(
                    item="Dosage form",
                    details=f"{raw_form} · partial detail",
                    status="review",
                )
            )
            confidence_points += 0.14
            review_banner = (
                "Formulation detail requires review: The checked source lists an immediate-release tablet; "
                "the uploaded label image does not clearly show release type. Verify with a registered pharmacist or clinician."
            )

        else:
            confirmed_mismatches.append("dosage form")
            checks.append(
                MedicineCheckItem(
                    item="Dosage form",
                    details=f"Queried '{raw_form}' conflicts with registered '{reg_form}'",
                    status="warning",
                )
            )
    else:
        missing_fields.append("dosage form")
        checks.append(
            MedicineCheckItem(
                item="Dosage form",
                details=f"Not specified on query; registered as {reg_form}",
                status="review",
            )
        )
        confidence_points += 0.08

    # 4. Manufacturer Check
    reg_mfg = record["manufacturer"]
    if raw_mfg:
        norm_query_mfg = _normalize(raw_mfg)
        norm_reg_mfg = _normalize(reg_mfg)
        alias_norms = [_normalize(a) for a in record.get("manufacturerAliases", [])]

        if norm_query_mfg == norm_reg_mfg or any(norm_query_mfg in a or a in norm_query_mfg for a in [norm_reg_mfg] + alias_norms):
            checks.append(
                MedicineCheckItem(
                    item="Manufacturer",
                    details=f"{reg_mfg} · match",
                    status="verified",
                )
            )
            confidence_points += 0.20
        else:
            confirmed_mismatches.append("manufacturer")
            checks.append(
                MedicineCheckItem(
                    item="Manufacturer",
                    details=f"Queried '{raw_mfg}' does not match registered manufacturer '{reg_mfg}'",
                    status="warning",
                )
            )
    else:
        missing_fields.append("manufacturer")
        checks.append(
            MedicineCheckItem(
                item="Manufacturer",
                details=f"Not specified on query; registered as {reg_mfg}",
                status="review",
            )
        )
        confidence_points += 0.08

    # 5. Regulatory Information Check Item
    checks.append(
        MedicineCheckItem(
            item="Regulatory information",
            details="Label record available in demo",
            status="info",
        )
    )

    # --- Synthesize Overall Verdict and Status ---
    final_confidence = min(0.98, max(0.10, round(confidence_points, 2)))

    if confirmed_mismatches:
        status = "mismatch"
        mismatch_str = ", ".join(confirmed_mismatches)
        verdict = f"Product Label Mismatch Detected ({mismatch_str})"
    elif partial_details:
        status = "verified"
        verdict = "Possible Match — Human Review"
        # Match the 88% confidence from frontend reference if partial dosage form
        final_confidence = min(final_confidence, 0.88)
    elif missing_fields and not raw_brand:
        status = "inconclusive"
        verdict = "Inconclusive - Incomplete Label Details"
    else:
        status = "verified"
        verdict = "Verified Against Regulatory Dataset"

    # Assemble structured verified product information
    product = VerifiedMedicineProduct(
        brand=record["brand"],
        standardizedTitle=record["standardizedTitle"],
        activeIngredient=record["activeIngredient"],
        strength=record["strength"],
        dosageForm=record["dosageForm"],
        manufacturer=record["manufacturer"],
        route=record.get("route", "Oral"),
        regulatoryStatus=record.get("regulatoryStatus", "Cataloged in demo SUGAM database"),
        formulationNotes=record.get("formulationNotes"),
    )

    limitations = (
        f"Compared against synthetic demonstration dataset with {int(final_confidence * 100)}% match confidence. "
        "Demonstration data is simulated for workflow evaluation and does not reflect a live CDSCO/SUGAM query. "
        "Physical batch inspection, expiration dates, and package integrity must be confirmed by a licensed pharmacist."
    )

    return MedicineVerificationResponse(
        matchConfidence=final_confidence,
        verdict=verdict,
        status=status,
        reviewBanner=review_banner,
        product=product,
        checks=checks,
        sourceReference=source_ref,
        evidenceLimitations=limitations,
        timestamp=timestamp_iso,
        disclaimer=safety_disclaimer,
    )
