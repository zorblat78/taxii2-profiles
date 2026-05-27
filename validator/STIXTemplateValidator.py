"""
STIX Template Validator Library

This library provides functionality to validate:
1. Template schema files against the TAXII Template Schema
2. STIX JSON documents against a supplied template schema
"""

import copy
import json
import os
from pathlib import Path
from typing import Dict, Any, Set, Tuple, List, Optional
from jsonschema import Draft202012Validator, ValidationError
from stix2validator import validate_parsed_json

try:
    from validator.ProfileValidationError import ProfileValidationError
except ImportError:
    from ProfileValidationError import ProfileValidationError

class STIXTemplateValidator:
    """Validator for TAXII template schemas and STIX documents."""

    def __init__(self, schema: Any, template: Dict[str, Any]):
        """
        Initialize the validator with the TAXII Template Schema.

        Args:
            schema: Either a path to the schema JSON file or a loaded schema dictionary.
            template: The template schema dictionary to validate against.

        Raises:
            FileNotFoundError: If schema file does not exist when a path is provided
            json.JSONDecodeError: If schema file is not valid JSON when a path is provided
            TypeError: If schema is not a dict or valid path
        """
        if isinstance(schema, (str, Path)):
            schema_path = str(schema)
            if not os.path.exists(schema_path):
                raise FileNotFoundError(f"Schema file not found: {schema_path}")
            with open(schema_path, 'r', encoding='utf-8') as f:
                self.template_schema = json.load(f)
        elif isinstance(schema, dict):
            self.template_schema = schema
        else:
            raise TypeError("schema must be a dict or path to a JSON schema file")

        self.resolve_external = False
        self.allow_additional = True
        self.object_limits = {}
        self.object_property_map = {}
        self.embedded_references = []
        self.relationship_map = {}

        self._load_template(template)

    def _load_template(self, template: Dict[str, Any]) -> None:
        """
        Validates and loads the template

        Args:
            template: Loaded template schema dictionary
        """

        if not isinstance(template, dict):
            raise TypeError("Template must be a dictionary")

        errors = []
        validator = Draft202012Validator(self.template_schema)
        for error in sorted(validator.iter_errors(template), key=str):
            errors.append(error.message)

        if len(errors) > 0:
            raise ValidationError("Template schema validation failed:\n" + "\n".join(errors))
        
        self.resolve_external = template.get('resolve_external', False)
        self.allow_additional = template.get('allow_additional', True)
        self.object_limits = template.get('object_limits', {})
        self.relationship_rules = template.get('relationship_rules', [])
        self.embedded_references = template.get('embedded_references', [])

        for obj_type, rule in self.object_limits.items():
            min_count = rule.get('min_count', 0)
            required_min = 0
            max_count = rule.get('max_count', None)
            if "id_map" in rule:
                self.object_property_map[obj_type] = rule["id_map"]

                for id_rule in rule["id_map"]:
                    required_min += id_rule.get("min_count", 0)

                if max_count is not None and id_rule.get("max_count", 0) > max_count:
                    raise ValidationError(f"Object type '{obj_type}' has a max_count for rule {id_rule.get('name', '')} that is not null and exceeds the limit for the type.")

            if min_count < required_min:
                raise ValidationError(f"Object type '{obj_type}' has a min_count of {min_count} that is less than the sum of the min_counts for its rules which is {required_min}.")

    def validate_stix_document(self, stix_objects: List[Dict[str, Any]] | Dict[str, Any]) -> List[ProfileValidationError]:
        """
        Validate a STIX payload against a template schema dictionary.

        Args:
            stix_objects: Loaded STIX payload (bundle dict or list of objects)

        Returns:
            List of ProfileValidationError objects. An empty list means the document is valid.
        """

        if type(stix_objects) == dict and 'objects' in stix_objects:
            stix_objects = stix_objects['objects']

        errors: List[ProfileValidationError] = []
        objects_by_id: Dict[str, List[Dict[str, Any]]] = {}

        # Initial load of objects by type which will include relationships
        # This will add errors if forbidden types are discovered
        objects_by_type = self._load_objects_by_type(stix_objects, errors)
        
        # pull out all relationships and store them separately for relationship based rules
        relationships_by_type = {}
        for relationship in objects_by_type.pop("relationship", []):
            relationships_by_type.setdefault(relationship["relationship_type"], []).append(relationship)

        # if there were no errors based on the type load the objects are then processed by ID and errors are added if discovered
        if len(errors) == 0:
            for obj_type in self.object_property_map.keys():
                object_list = objects_by_type.get(obj_type, [])
                self._load_objects_by_id(objects_by_id, obj_type, object_list, errors)

        # We now load relationships which will update the objects_by_id dictionary so that embedded rules can reference relationship object
        # TODO: Add call to _validate_relationships

        # As the final step check embedded relationships
        if len(errors) == 0:
            errors.extend(self._validate_embedded_references(stix_objects, objects_by_id))

        return errors

    def _load_objects_by_type(self, objects: List[Dict[str, Any]], errors: List[ProfileValidationError]) -> Dict[str, List[Dict[str, Any]]]:
        objects_by_type: Dict[str, List[Dict[str, Any]]] = {}
        
        for obj in objects:
            obj_type = obj.get('type')

            if not self.allow_additional and obj_type != "relationship" and obj_type not in self.object_limits:
                errors.append(ProfileValidationError(
                    error_type='forbidden_type',
                    obj_type=obj_type,
                    rule_name='allow_additional',
                    stix_id=obj.get('id', None),
                    details={'found': 1}
                ))
                continue

            objects_by_type.setdefault(obj_type, []).append(obj)

            # check max_count as we go
            type_max = self.object_limits.get(obj_type, {}).get('max_count', None)
            if type_max is not None and len(objects_by_type[obj_type]) > type_max and obj_type != "relationship":
                errors.append(ProfileValidationError(
                    error_type='forbidden_type',
                    obj_type=obj_type,
                    rule_name='max_count',
                    stix_id=obj.get('id', None),
                    details={'max_count': type_max, 'found': len(objects_by_type[obj_type])}
                ))
                continue
        
        # once we have everything validate we meet the min_count
        for obj_type, limits in self.object_limits.items():
            obj_count = len(objects_by_type.get(obj_type, []))
            if limits.get('min_count', 0) > obj_count:
                errors.append(ProfileValidationError(
                    error_type='missing_type',
                    obj_type=obj_type,
                    rule_name='min_count',
                    stix_id=None,
                    details={'required': limits.get('min_count', 0), 'found': obj_count}
                ))
                continue

        return objects_by_type

    def _load_objects_by_id(self, objects_by_id: Dict[str, List[Dict[str, Any]]], obj_type: str, object_list: List[Dict[str, Any]], errors: List[ProfileValidationError]) -> None:
        for rule in self.object_property_map.get(obj_type, []):
            id_rules = rule["ids"] # per the schema this must be a list of at least length 1
            min_count = rule.get("min_count", 0)
            max_count = rule.get("max_count", None)
            required_extensions = rule.get("required_extensions", [])
            matches = 0

            # we want to use a loop here so we can pop off elements as we go so that only one rule will ever match an object
            idx = 0
            while idx < len(object_list):
                obj = object_list[idx]
                # objects that are missing an extension can't be a match
                if (not all(ext in obj.get('extensions', {}) for ext in required_extensions)):
                    idx += 1
                    continue

                invalid_property = False
                for key, property_rule in rule.get("property_rules", {}).items():
                    if not self._validate_property_rule(obj, key, property_rule):
                        invalid_property = True
                        break

                if invalid_property:
                    idx += 1
                    continue

                # if we get here we know it matches all rules
                for id in id_rules:
                    objects_by_id.setdefault(id, []).append(obj)
                
                # finally we remove the object from the list so it can't match another rule
                matches += 1
                object_list.pop(idx)

            rule_name = rule.get("name", "<unnamed>")
            if matches < min_count:
                errors.append(ProfileValidationError(
                    error_type='no_match',
                    obj_type=obj_type,
                    rule_name=rule_name,
                    stix_id=None,
                    details={'required': min_count, 'found': matches}
                ))
            elif max_count is not None and matches > max_count:
                errors.append(ProfileValidationError(
                    error_type='forbidden_type',
                    obj_type=obj_type,
                    rule_name=rule_name,
                    stix_id=None,
                    details={'max_count': max_count, 'found': matches}
                ))
            
        return objects_by_id
    
    def validate_template_schema(self, template: Any) -> Tuple[bool, List[str]]:
        """
        Validate a template schema against the TAXII template schema.

        Args:
            template: Path to a template JSON file or loaded template dictionary.

        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        if isinstance(template, (str, Path)):
            template_path = str(template)
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Template file not found: {template_path}")
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)

        if not isinstance(template, dict):
            raise TypeError("Template must be a dictionary")

        errors = []
        validator = Draft202012Validator(self.template_schema)
        for error in sorted(validator.iter_errors(template), key=str):
            errors.append(error.message)

        if len(errors) > 0:
            return False, errors

        self._load_template(template)
        return True, []

    def _validate_property_rule(self, obj: Dict[str, Any], key: str, property_rule: Dict[str, Any]) -> bool:
        result = True

        if property_rule.get("rule_type") == "enum":
            result = obj.get(key, "") in property_rule.get("values", [])
        elif property_rule.get("rule_type") == "string_array":
            result = all(isinstance(val, str) for val in obj.get(key, []))
        elif property_rule.get("rule_type") == "referenced_type":
            ref_id = obj.get(key, "").split("--")[0]
            result = ref_id in property_rule.get("value", "")
        elif property_rule.get("rule_type") == "reference_list":
            for ref_id in obj.get(key, []):
                ref_type = ref_id.split("--")[0]
                
                if ref_type not in property_rule.get("values", []):
                    result = False
                    break
        elif property_rule.get("rule_type") == "object_array":
            for sub_obj in obj.get(key, []):
                if type(sub_obj) != dict:
                    result = False
                    break

                for sub_key, sub_rule in property_rule.get("property_rules", {}).items():
                    if not self._validate_property_rule(sub_obj, sub_key, sub_rule):
                        result = False
                        break
        
        return result
    
    def _validate_relationships(self, stix_objects: List[Dict[str, Any]], objects_by_id: Dict[str, List[Dict[str, Any]]]) -> List[ProfileValidationError]:
        errors: List[ProfileValidationError] = []
        for rule in self.relationship_rules:
            pass

        return errors

    def _validate_embedded_references(self, stix_objects: List[Dict[str, Any]], objects_by_id: Dict[str, List[Dict[str, Any]]]) -> List[ProfileValidationError]:
        errors: List[ProfileValidationError] = []
        obj = {}
        count = 0
        for ref_rule in self.embedded_references:
            count += 1
            id = ref_rule["id"] # force an error if this is not present
            coverage = ref_rule["coverage"] # force an error if this is not present
            property_path = ref_rule["property_path"] # force an error if this is not present
            rule_type = ref_rule["rule_type"] # force an error if this is not present

            full_set = set()
            for target_id in ref_rule.get('target_ids', []):
                full_set.update([obj.get('id') for obj in objects_by_id.get(target_id, [])])
            
            remaining_set = copy.copy(full_set)

            for obj in objects_by_id.get(id, []):
                field_value = self._get_referenced_field(obj, property_path)
                if field_value is None:
                    if ref_rule.get("optional", False):
                        continue
                    else:
                        errors.append(ProfileValidationError(
                            error_type='missing_embedded',
                            obj_type=obj.get('type', ''),
                            rule_name=coverage,
                            stix_id=obj.get('id', ''),
                            path=property_path,
                        ))
                        break

                if self._process_embedded_references(field_value, rule_type, coverage, ref_rule.get("allow_additional", False), full_set, remaining_set) is False:
                    # tell which values aren't allowed
                    extra_values = set()
                    for item in field_value:
                        if item not in full_set:
                            extra_values.add(item)

                    errors.append(ProfileValidationError(
                        error_type='forbidden_embedded',
                        obj_type=obj.get('type', ''),
                        rule_name=coverage,
                        stix_id=obj.get('id', ''),
                        path=property_path,
                        additional_values=sorted(list(extra_values))
                    ))
                    continue

            if coverage == "covered" and len(remaining_set) > 0:
                print(obj)
                errors.append(ProfileValidationError(
                    error_type='missing_embedded',
                    obj_type=obj.get('type', ''),
                    path=property_path,
                    rule_name=f"Embedded reference coverage rule {count} ({id})",
                    missing_values=sorted(list(remaining_set))
                ))

        return errors
    
    def _process_embedded_references(self, field: Any, rule_type: str, coverage: str, allow_additional: bool, full_set: Set[str], remaining_set: Set[str]) -> bool:
        added = set()

        if rule_type == "list":
            if type(field) != list:
                return False
            for item in field:
                if item not in full_set and not allow_additional:
                    return False
                else:
                    remaining_set.discard(item)

                    if coverage == "full":
                        added.add(item)
        elif rule_type == "single":
            if field not in full_set and not allow_additional:
                return False
            
            remaining_set.discard(field)
            if coverage == "full":
                added.add(item)
        
        # if there are any items left when we need a full set then it is an error
        if coverage == "full" and len(full_set - added) > 0:
            return False
                    
        return True

    def _get_referenced_field(self, obj: Dict[str, Any], path_str: str) -> Any:
        current_level = obj
        for path_part in path_str.split('.'):
            if path_part not in current_level:
                return None
            current_level = current_level[path_part]
        return current_level