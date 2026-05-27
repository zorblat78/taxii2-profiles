#!/usr/bin/env python3
"""STIX Template Validator CLI.

This CLI is a thin wrapper around STIXTemplateValidator.
Can be run directly: python validator/helpers/validate.py
Or imported as a module.
"""

import argparse
import sys
import json
from pathlib import Path

# Setup path for imports
SCRIPT_DIR = Path(__file__).resolve().parent  # validator/helpers/
VALIDATOR_DIR = SCRIPT_DIR.parent  # validator/
PROJECT_ROOT = VALIDATOR_DIR.parent  # project root

# Ensure project root is in path for package imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Also ensure validator dir is available for direct imports
if str(VALIDATOR_DIR) not in sys.path:
    sys.path.insert(0, str(VALIDATOR_DIR))

from validator.STIXTemplateValidator import STIXTemplateValidator


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Validate TAXII template schemas and STIX documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python validate.py -s schema.json -t ../examples/basic_incident/basic_incident_schema.json
  python validate.py -s schema.json -t ../examples/basic_incident/basic_incident_schema.json -d stix_document.json
        '''
    )

    parser.add_argument(
        '-s', '--schema',
        required=True,
        help='Path to the TAXII Template Schema JSON file'
    )
    parser.add_argument(
        '-t', '--template',
        required=True,
        help='Path to the template schema JSON file to validate'
    )
    parser.add_argument(
        '-d', '--document',
        help='Path to the STIX document JSON file to validate'
    )
    args = parser.parse_args()

    try:
        with open(args.schema, 'rt', encoding='utf-8') as fh:
            schema_data = json.load(fh)
    except Exception as exc:
        print(f"ERROR: Failed to load schema file: {exc}", file=sys.stderr)
        return 1

    try:
        with open(args.template, 'rt', encoding='utf-8') as fh:
            template_data = json.load(fh)
    except Exception as exc:
        print(f"ERROR: Failed to load template file: {exc}", file=sys.stderr)
        return 1

    try:
        validator = STIXTemplateValidator(schema_data, template_data)
    except Exception as exc:
        print(f"ERROR: Failed to initialize validator: {exc}", file=sys.stderr)
        return 1

    print("=" * 70)
    print("VALIDATING TEMPLATE SCHEMA")
    print(f"Template Schema: {args.template}")
    print("=" * 70)
    

    print("Template schema is VALID\n")

    if args.document:
        print("=" * 70)
        print("VALIDATING STIX DOCUMENT")
        print("=" * 70)
        print(f"STIX Document: {args.document}")

        try:
            with open(args.document, 'r', encoding='utf-8') as fh:
                document_data = json.load(fh)
        except Exception as exc:
            print(f"ERROR: Failed to load STIX document file: {exc}", file=sys.stderr)
            return 1

        errors = validator.validate_stix_document(document_data)
        if errors:
            print("STIX document is INVALID\n")
            _print_errors(errors)
            return 1

        print("STIX document is VALID\n")

    print("=" * 70)
    print("All validations passed!")
    print("=" * 70)
    return 0

def _print_errors(errors: list) -> None:
    print("Errors:")
    for idx, error in enumerate(errors, 1):
        print(f"  {idx}. {error}")
    print()


if __name__ == '__main__':
    sys.exit(main())
