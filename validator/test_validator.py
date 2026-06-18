"""
Test script for the validator test harness and profile-driven STIX validation.
"""

import json
from pathlib import Path

from validator.STIXTemplateValidator import STIXTemplateValidator
from validator.ProfileValidationError import ProfileValidationError

ROOT_DIR = Path(__file__).resolve().parent.parent

SCHEMA_PATH = ROOT_DIR / 'schema.json'
PROFILES_DIR = ROOT_DIR / 'examples' / 'profiles'
STIX_DIR = ROOT_DIR / 'examples' / 'stix'


def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def validate_stix_document(validator: STIXTemplateValidator, document_path: Path) -> tuple[bool, list]:
    stix_document = load_json(document_path)
    errors = validator.validate_stix_document(stix_document)
    return (len(errors) == 0, errors)


def _get_validator(profile_name: str):
    """Initialize validator with specified profile."""
    schema = load_json(SCHEMA_PATH)
    profile_path = PROFILES_DIR / profile_name
    profile_data = load_json(profile_path)
    return STIXTemplateValidator(schema, profile_data)


# Tests for basic_incident_schema.json

def test_basic_incident_schema_incident_ransom_no_report():
    """Test basic_incident_schema against incident_ransom_no_report.json - should be rejected."""
    validator = _get_validator('basic_incident_schema.json')
    document_path = STIX_DIR / 'incident_ransom_no_report.json'
    
    actual_valid, actual_errors = validate_stix_document(validator, document_path)
    
    assert actual_valid is False, (
        f'Expected incident_ransom_no_report.json to be rejected by basic_incident_schema.json '
        f'but it was accepted. Errors: {actual_errors}'
    )
    errors_dicts = [e.to_dict() for e in actual_errors]
    assert any(d['error_type'] == 'missing_type' and d['obj_type'] == 'report' for d in errors_dicts), errors_dicts


def test_basic_incident_schema_incident_ransom_report():
    """Test basic_incident_schema against incident_ransom_report.json - should be accepted."""
    validator = _get_validator('basic_incident_schema.json')
    document_path = STIX_DIR / 'incident_ransom_report.json'
    
    actual_valid, actual_errors = validate_stix_document(validator, document_path)
    
    assert ProfileValidationError.to_string_list(actual_errors) == [], (
        f'Expected incident_ransom_report.json to be accepted by basic_incident_schema.json '
        f'but got rejected. Errors: {actual_errors}'
    )


def test_basic_incident_schema_observed_data_report():
    """Test basic_incident_schema against observed_data_report.json - should be rejected."""
    validator = _get_validator('basic_incident_schema.json')
    document_path = STIX_DIR / 'observed_data_report.json'
    
    actual_valid, actual_errors = validate_stix_document(validator, document_path)
    
    assert actual_valid is False, (
        f'Expected observed_data_report.json to be rejected by basic_incident_schema.json '
        f'but it was accepted.'
    )
    errors_dicts = [e.to_dict() for e in actual_errors]
    assert any(d['error_type'] == 'missing_type' and d['obj_type'] == 'incident' for d in errors_dicts), errors_dicts
    assert any(d['error_type'] == 'missing_type' and d['obj_type'] == 'identity' for d in errors_dicts), errors_dicts
    assert any(d['error_type'] == 'missing_type' and d['obj_type'] == 'impact' for d in errors_dicts), errors_dicts


# Tests for basic_incident_schema_no_report.json

def test_basic_incident_schema_no_report_incident_ransom_no_report():
    """Test basic_incident_schema_no_report against incident_ransom_no_report.json - should be accepted."""
    validator = _get_validator('basic_incident_schema_no_report.json')
    document_path = STIX_DIR / 'incident_ransom_no_report.json'
    
    actual_valid, actual_errors = validate_stix_document(validator, document_path)
    
    assert actual_valid is True, (
        f'Expected incident_ransom_no_report.json to be accepted by basic_incident_schema_no_report.json '
        f'but got rejected. Errors: {actual_errors}'
    )


def test_basic_incident_schema_no_report_incident_ransom_report():
    """Test basic_incident_schema_no_report against incident_ransom_report.json - should be rejected."""
    validator = _get_validator('basic_incident_schema_no_report.json')
    document_path = STIX_DIR / 'incident_ransom_report.json'
    
    actual_valid, actual_errors = validate_stix_document(validator, document_path)
    
    assert actual_valid is False, (
        f'Expected incident_ransom_report.json to be rejected by basic_incident_schema_no_report.json '
        f'but got accepted. Errors: {actual_errors}'
    )
    errors_dicts = [e.to_dict() for e in actual_errors]
    assert any(d['error_type'] == 'forbidden_type' and d['obj_type'] == 'report' for d in errors_dicts), errors_dicts


def test_basic_incident_schema_no_report_observed_data_report():
    """Test basic_incident_schema_no_report against observed_data_report.json - should be rejected."""
    validator = _get_validator('basic_incident_schema_no_report.json')
    document_path = STIX_DIR / 'observed_data_report.json'
    
    actual_valid, actual_errors = validate_stix_document(validator, document_path)
    
    assert actual_valid is False, (
        f'Expected observed_data_report.json to be rejected by basic_incident_schema_no_report.json '
        f'but it was accepted.'
    )
    errors_dicts = [e.to_dict() for e in actual_errors]
    assert any(d['error_type'] == 'forbidden_type' and d['obj_type'] == 'report' for d in errors_dicts), errors_dicts
    assert any(d['error_type'] == 'missing_type' and d['obj_type'] == 'incident' for d in errors_dicts), errors_dicts

def test_sightings_vs_report():
    """Test basic_incident_schema_no_report against observed_data_report.json - should be rejected."""
    validator = _get_validator('basic_incident_schema_no_report.json')
    document_path = STIX_DIR / 'observed_data_report.json'
    
    actual_valid, actual_errors = validate_stix_document(validator, document_path)
    expected_errors = [
        "Object type 'report' has more instances than allowed by max_count (1 > 0).",
        "Missing required object type 'incident' with at least 1 instance(s); found 0.",
        "Missing required object type 'identity' with at least 1 instance(s); found 0.",
        "Missing required object type 'impact' with at least 2 instance(s); found 0."
    ]
    actual_errors = ProfileValidationError.to_string_list(actual_errors)
    
    assert(actual_errors == expected_errors), ("Errors did not match expected for test sighting vs report")

def test_sightings_vs_sighting():
    """Test sighting schema against observed_data_report.json - should be accepted."""
    validator = _get_validator('sighting.json')
    document_path = STIX_DIR / 'observed_data_report.json'
    
    actual_valid, actual_errors = validate_stix_document(validator, document_path)
    expected_errors = set([])
    actual_errors = set(ProfileValidationError.to_string_list(actual_errors))
    
    assert(actual_errors == expected_errors), (
        f'Expected errors did not match actual when testing sightings against an incident profile'
        f"Unexpected Errors: {actual_errors - expected_errors}, Missing Errors: {expected_errors - actual_errors}"
    )