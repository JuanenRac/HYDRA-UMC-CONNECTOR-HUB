# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - a small evaluator for the subset of JSON Schema the published schema uses
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Just enough JSON Schema (type, required, properties, items, enum, pattern, minLength,
minItems, minProperties, exclusiveMinimum, if/then, local $ref) to run the published
schema against the fixtures without adding a dependency. A keyword it does not know raises,
so a schema that grows past this subset cannot pass unchecked."""

from __future__ import annotations

import re

KNOWN = {
    "$schema", "$id", "title", "description", "type", "required", "properties", "items", "enum", "pattern",
    "minLength", "minItems", "minProperties", "exclusiveMinimum", "if", "then", "$ref", "$defs",
}
TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}


def _resolve(root: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"only local references are supported: {ref}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def errors(instance, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    root = root if root is not None else schema
    unknown = set(schema) - KNOWN
    if unknown:
        raise ValueError(f"unsupported schema keyword(s) {sorted(unknown)} at {path}")
    if "$ref" in schema:
        return errors(instance, _resolve(root, schema["$ref"]), root, path)
    found: list[str] = []
    wanted = schema.get("type")
    if wanted is not None and not TYPES[wanted](instance):
        return [f"{path}: expected {wanted}"]
    if "enum" in schema and instance not in schema["enum"]:
        found.append(f"{path}: not one of {schema['enum']}")
    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            found.append(f"{path}: does not match {schema['pattern']}")
        if len(instance) < schema.get("minLength", 0):
            found.append(f"{path}: too short")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "exclusiveMinimum" in schema and not instance > schema["exclusiveMinimum"]:
            found.append(f"{path}: must be greater than {schema['exclusiveMinimum']}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                found.append(f"{path}: missing {key}")
        if len(instance) < schema.get("minProperties", 0):
            found.append(f"{path}: needs at least {schema['minProperties']} properties")
        for key, sub in schema.get("properties", {}).items():
            if key in instance:
                found += errors(instance[key], sub, root, f"{path}.{key}")
        if "if" in schema and not errors(instance, schema["if"], root, path):
            found += errors(instance, schema.get("then", {}), root, path)
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            found.append(f"{path}: needs at least {schema['minItems']} items")
        if "items" in schema:
            for index, item in enumerate(instance):
                found += errors(item, schema["items"], root, f"{path}[{index}]")
    return found
