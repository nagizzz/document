#!/usr/bin/env python3
"""Rebuild stone365_user_api path schemas for APIPOST field rendering.

Components remain as source references, while every request and response schema
under paths becomes self-contained. This avoids APIPOST's unreliable expansion
of deep references and oneOf combinations in imported aggregate documents.
"""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path


DOC_DIR = Path(r"D:\Code Repositories\stone365_user_api\项目资料库\前端接口文档")
METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def resolve_ref(ref: str, document: dict) -> object | None:
    if not ref.startswith("#/components/"):
        return None
    current: object = document
    for part in ref[2:].split("/"):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def expand_schema(value: object, document: dict, stack: tuple[str, ...] = ()) -> object:
    if isinstance(value, list):
        return [expand_schema(item, document, stack) for item in value]
    if not isinstance(value, dict):
        return copy.deepcopy(value)

    if "$ref" in value:
        ref = str(value["$ref"])
        target = resolve_ref(ref, document)
        if target is not None and ref not in stack:
            expanded = expand_schema(target, document, stack + (ref,))
            if isinstance(expanded, dict):
                # OpenAPI permits sibling fields alongside a reference in 3.1;
                # retaining them keeps local descriptions while output stays 3.0.
                siblings = {key: item for key, item in value.items() if key != "$ref"}
                expanded.update({key: expand_schema(item, document, stack) for key, item in siblings.items()})
            return expanded

    expanded = {key: expand_schema(item, document, stack) for key, item in value.items()}
    if "oneOf" in expanded:
        options = expanded.pop("oneOf")
        if isinstance(options, list) and options:
            # APIPOST cannot reliably render oneOf. Prefer the array/object form
            # that callers use most often, then document other forms as compatibility.
            primary = next((item for item in options if isinstance(item, dict) and item.get("type") in {"array", "object"}), options[0])
            if isinstance(primary, dict):
                original_description = str(expanded.get("description", "")).strip()
                alternate = [item for item in options if item is not primary]
                compatibility = "兼容说明：后端仍兼容其他历史传参形式；前端联调请优先按当前展示的结构传参。"
                expanded = copy.deepcopy(primary)
                if original_description:
                    expanded["description"] = f"{original_description}\n\n{compatibility}"
                else:
                    expanded["description"] = compatibility
    return expanded


def schema_from_example(value: object) -> dict:
    if isinstance(value, dict):
        return {"type": "object", "properties": {str(key): schema_from_example(item) for key, item in value.items()}}
    if isinstance(value, list):
        items = schema_from_example(value[0]) if value else {}
        return {"type": "array", "items": items}
    if isinstance(value, bool):
        return {"type": "boolean", "example": value}
    if isinstance(value, int):
        return {"type": "integer", "example": value}
    if isinstance(value, float):
        return {"type": "number", "example": value}
    if value is None:
        return {"type": "string", "nullable": True, "example": None}
    return {"type": "string", "example": str(value)}


def example_value(media: dict) -> object | None:
    if "example" in media:
        return media["example"]
    examples = media.get("examples", {})
    if isinstance(examples, dict):
        for item in examples.values():
            if isinstance(item, dict) and "value" in item:
                return item["value"]
    return None


def normalize_compatibility_text(value: object, property_name: str = "") -> None:
    """Make the flattened oneOf compatibility text accurate for each field."""
    if isinstance(value, dict):
        description = value.get("description")
        if isinstance(description, str) and "后端仍兼容其他历史传参形式" in description:
            if property_name == "ProductList":
                value["description"] = description.replace("其他历史传参形式", "JSON 字符串等旧调用形式")
            elif value.get("type") in {"integer", "number"}:
                value["description"] = description.replace("其他历史传参形式", "字符串等旧调用形式")
        for key, item in value.items():
            normalize_compatibility_text(item, str(key))
    elif isinstance(value, list):
        for item in value:
            normalize_compatibility_text(item, property_name)


def notification_count_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "Msg": {"type": "string", "description": "业务提示文案。"},
            "Code": {"type": "integer", "description": "业务状态码，200 表示成功。", "example": 200},
            "Data": {
                "type": "object",
                "properties": {"Unread": {"type": "integer", "description": "未读通知数。", "example": 12}},
            },
        },
    }


def rebuild_document(path: Path) -> dict[str, int]:
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    changed = 0
    generated = 0
    for path_item in document.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in METHODS or not isinstance(operation, dict):
                continue
            request_body = operation.get("requestBody", {})
            if isinstance(request_body, dict):
                for media in request_body.get("content", {}).values():
                    if isinstance(media, dict):
                        schema = media.get("schema")
                        if isinstance(schema, dict):
                            media["schema"] = expand_schema(schema, document)
                            changed += 1
                        elif (value := example_value(media)) is not None:
                            media["schema"] = schema_from_example(value)
                            generated += 1
            for response in operation.get("responses", {}).values():
                if not isinstance(response, dict):
                    continue
                for media in response.get("content", {}).values():
                    if isinstance(media, dict):
                        schema = media.get("schema")
                        if isinstance(schema, dict):
                            media["schema"] = expand_schema(schema, document)
                            changed += 1
                        elif (value := example_value(media)) is not None:
                            media["schema"] = schema_from_example(value)
                            generated += 1
            # The historical GET compatibility doc omitted its response body,
            # while the controller returns the same envelope as POST counts.
            if method.lower() == "get" and "notifications/client/counts" in str(next(iter(document.get("paths", {})), "")):
                response = operation.get("responses", {}).get("200")
                if isinstance(response, dict) and "content" not in response:
                    response["content"] = {"application/json": {"schema": notification_count_schema(), "examples": {"success": {"value": {"Msg": "成功", "Code": 200, "Data": {"Unread": 12}}}}}}
                    generated += 1
            normalize_compatibility_text(operation)
    document.setdefault("info", {})["version"] = date.today().isoformat()
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"expanded": changed, "generated": generated}


if __name__ == "__main__":
    totals = {"documents": 0, "expanded": 0, "generated": 0}
    for document_path in sorted(DOC_DIR.rglob("*.openapi.json")):
        result = rebuild_document(document_path)
        totals["documents"] += 1
        totals["expanded"] += result["expanded"]
        totals["generated"] += result["generated"]
    print(json.dumps(totals, ensure_ascii=False, indent=2))
