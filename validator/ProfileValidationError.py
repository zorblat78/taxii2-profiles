"""Structured error model for profile validation.

ProfileValidationError is used to pass information about validation errors in a STIX input
These should be able to be used to both generate user friendly debug text and provide an automated system
with enough information to fill in potential fixes in an input GUI as a document is being drafted.
"""

from typing import Dict, Any, Tuple, List, Optional


class ProfileValidationError:
    """Represents a single profile validation error.

    Attributes:
        VALID_ERROR_TYPES: set[str] - allowed `error_type` string values.

    Instance attributes:
        error_type: str - one of the allowed error types.
        obj_type: str - the STIX object type the rule applies to.
        rule_name: str - the profile rule name that failed.
        stix_id: Optional[str] - the `id` of a STIX object this error applies to.
        path: Optional[str] - the field path within a STIX object that failed validation.
        details: Dict[str, Any] - additional structured details (counts, etc.).
    """

    VALID_ERROR_TYPES = {
        'missing_type',
        'forbidden_type',
        'no_match',
        'missing_relationship',
        'missing_embedded',
        'forbidden_embedded',
        'forbidden_relationship',
        'forbodden_relationship',
    }

    def __init__(
        self,
        error_type: str,
        obj_type: str = "",
        rule_name: str = "",
        stix_id: Optional[str] = None,
        path: Optional[str] = None,
        missing_values: List[str] = [],
        additional_values: List[str] = [],
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a `ProfileValidationError`.

        Args:
            error_type: The type of the validation error.
            obj_type: The STIX object type the rule targets (e.g. 'attack-pattern').
            rule_name: The identifier/name of the profile rule that failed.
            stix_id: Optional STIX object `id` that this error references.
            path: Optional path to the field that failed validation.
            missing_values: List of values that are missing.
            additional_values: List of values that are not allowed.
            details: Optional mapping with extra context (counts, paths, etc.).

        Raises:
            ValueError: if `error_type` is not one of `VALID_ERROR_TYPES`.
        """

        if error_type not in self.VALID_ERROR_TYPES:
            raise ValueError(f"Unsupported error_type: {error_type}")

        self.error_type = error_type
        self.obj_type = obj_type
        self.rule_name = rule_name
        self.stix_id = stix_id
        self.path = path
        self.missing_values = missing_values
        self.additional_values = additional_values
        self.details = details or {}

    @property
    def message(self) -> str:
        """Human-friendly message synthesized from structured fields.

        The returned string is derived from the `error_type`, `rule_*`
        fields and any `details` provided. Tests should prefer the
        structured fields or `to_dict()` over matching this text.
        """

        if self.error_type == 'missing_type':
            required = self.details.get('required')
            found = self.details.get('found')
            if required is not None and found is not None:
                return f"Missing required object type '{self.obj_type}' with at least {required} instance(s); found {found}."
            return f"Missing required object type '{self.obj_type}'."

        if self.error_type == 'forbidden_type':
            max_count = self.details.get('max_count')
            found = self.details.get('found')
            if max_count is not None and found is not None:
                return f"Object type '{self.obj_type}' has more instances than allowed by max_count ({found} > {max_count})."
            return f"Object type '{self.obj_type}' is forbidden by the profile."

        if self.error_type == 'no_match':
            required = self.details.get('required')
            found = self.details.get('found')
            if self.stix_id:
                return f"STIX object '{self.stix_id}' did not match profile rule '{self.rule_name}'."
            if required is not None and found is not None:
                return f"Rule '{self.rule_name}' for object type '{self.obj_type}' did not match enough instances ({found} of {required})."
            return f"Rule '{self.rule_name}' for object type '{self.obj_type}' did not match any instances."

        if self.error_type == 'missing_relationship':
            if self.stix_id:
                return f"STIX object '{self.stix_id}' is missing a required relationship for rule '{self.rule_name}'."
            return f"Missing required relationship for rule '{self.rule_name}'."

        if self.error_type == 'forbidden_relationship':
            if self.stix_id:
                return f"STIX object '{self.stix_id}' has a forbidden relationship for rule '{self.rule_name}'."
            return f"Forbidden relationship for rule '{self.rule_name}'."

        if self.error_type == 'missing_embedded':
            return f"STIX object '{self.stix_id}' ({self.obj_type}) is missing embedded field '{self.path}' for rule '{self.rule_name}'; The following values are not accounted for: {', '.join(self.missing_values)}"

        if self.error_type == 'forbidden_embedded':
            return f"STIX object '{self.stix_id}' has forbidden embedded reference(s) at '{self.path}' for rule '{self.rule_name}'; The following values are not permitted: {', '.join(self.additional_values)}"

        return "Unknown profile validation error."

    def __str__(self):
        """Return the human-friendly error message.

        This makes printing or formatting the exception convenient in
        CLIs or logs. Prefer `to_dict()` for programmatic access.
        """

        return self.message

    def __eq__(self, value):
        if isinstance(value, ProfileValidationError):
            return (
                self.error_type == value.error_type and
                self.obj_type == value.obj_type and
                self.rule_name == value.rule_name and
                self.stix_id == value.stix_id and
                self.path == value.path and
                self.details == value.details
            )
        elif isinstance(value, dict):
            return self.to_dict() == value
        elif isinstance(value, str):
            return self.message == value
        
        return False
    
    @staticmethod
    def to_string_list(errors: List['ProfileValidationError']) -> List[str]:
        """Convert a list of errors to a single string with each error on a new line."""
        return list((str(e) for e in errors))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the error to a dictionary.

        The resulting mapping contains all structured fields plus the
        derived `message` for convenience in tests and CLI output.
        """

        return {
            'error_type': self.error_type,
            'obj_type': self.obj_type,
            'rule_name': self.rule_name,
            'stix_id': self.stix_id,
            'path': self.path,
            'details': self.details,
            'message': self.message,
        }