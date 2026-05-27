# STIX Template Validator

A Python tool for validating TAXII template schemas and STIX documents.  This validator does not support the `resolve_external` option, but will work fully otherwise.  The following logic is used to handle validating TAXII envelopes:

1. Validation is performed against the template
2. The `object_limits` settings are read in from the template and `allow_additional` is checked within it.
3. The TAXII envelope is read in and objects are sorted by type.
    a. `allow_additional` is false and any objects are found that are not within it then processing ends and the envelope is rejected
    b. If during processing any object types have a `max_count` set and this is exceeded the envelope is rejected
    c. Upon all objects being read and sorted if any object types had a `min_count` set which was not reached the envelope is rejected
4. After loading the objects by type the rules in the `template` section are processed in order.
    a. Any object that matches a rule is assigned to the listed IDs and removed from the by type list.  An object will only match the first rule it hits.
    b. If during processing a rule has a `max_count` set which is exceeded the envelope is rejected
    c. If after a rule is processed if the number of matches do not reach `min_count` the envelope is rejected
    d. After all rules are processed if any objects remain sorted by a type that has `id_required` set as true in `object_limits` the envelope is rejected
5. Relationship objects are processed
6. After all objects the rules in `referenced_objects` are processed in order.

## Features

- **Template Schema Validation**: Validate template schema files against the TAXII Template Schema
- **STIX Document Validation**: Validate STIX JSON documents against a template schema
- **Clear Error Reporting**: Detailed error messages for validation failures
- **Library and CLI**: Both programmatic library interface and command-line tool

## Installation

### Prerequisites

- Python 3.7+
- jsonschema library

### Setup

Install the required dependency:

```bash
pip install jsonschema
```

## Usage

### Command Line

```bash
python validate.py -s schema.json -t template_schema.json [-d stix_document.json] [-v]
```

#### Options

- `-s, --schema` (required): Path to the TAXII Template Schema JSON file
- `-t, --template` (required): Path to the template schema JSON file to validate
- `-d, --document` (optional): Path to the STIX document JSON file to validate
- `-v, --verbose` (optional): Enable verbose output

#### Examples

Validate a template schema:
```bash
python validate.py -s ../schema.json -t ../examples/basic_incident/basic_incident_schema.json
```

Validate both template schema and STIX document:
```bash
python validate.py -s ../schema.json -t ../examples/basic_incident/basic_incident_schema.json -d stix_data.json
```

### Python Library

Use the `STIXTemplateValidator` class in your own Python code:

```python
from stix_validator import STIXTemplateValidator

# Initialize the validator with the TAXII Template Schema
validator = STIXTemplateValidator('schema.json')

# Validate a template schema
is_valid, errors = validator.validate_template_schema('template_schema.json')
if is_valid:
    print("Template schema is valid!")
else:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")

# Validate a STIX document against a template
is_valid, errors = validator.validate_stix_document('template_schema.json', 'stix_document.json')
if is_valid:
    print("STIX document is valid!")
else:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

## Output

The validator provides:
- Success messages (✓) when validation passes
- Error messages (✗) with details about what failed
- Error paths showing where in the JSON structure the problem occurred
- Expected values when applicable

## Exit Codes

- `0`: All validations passed
- `1`: One or more validations failed
