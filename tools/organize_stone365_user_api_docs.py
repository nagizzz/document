#!/usr/bin/env python3
"""Organize one-operation stone365_user_api OpenAPI docs by controller."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path


DOC_DIR = Path(r"D:\Code Repositories\stone365_user_api\项目资料库\前端接口文档")
METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
ENV_PREFIX = re.compile(r"^\{\{[^{}]+\}\}")
BAD_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def get_operation(document: dict) -> tuple[str, str]:
    operations = [
        (path, method.lower())
        for path, path_item in document.get("paths", {}).items()
        if isinstance(path_item, dict)
        for method, operation in path_item.items()
        if method.lower() in METHODS and isinstance(operation, dict)
    ]
    if len(operations) != 1:
        raise ValueError(f"Expected exactly one operation, got {len(operations)}")
    return operations[0]


def filename_for(path: str, method: str, used: Counter[str]) -> str:
    # {{stone365_user_api}}/media/admin/video/token -> media-admin-video-token
    name = ENV_PREFIX.sub("", path).strip("/").replace("/", "-").replace("{", "").replace("}", "")
    name = BAD_FILENAME.sub("-", name).strip(" .-")
    if not name:
        raise ValueError(f"Cannot create filename for path {path}")
    used[name.lower()] += 1
    if used[name.lower()] > 1:
        # GET and POST /notifications/client/counts are distinct operations.
        name = f"{name}-{method.lower()}"
    return f"{name}.openapi.json"


def controller_directory(document: dict, source: Path) -> Path:
    """Mirror the controller's directory below app/controller.

    app\\controller\\user\\admin\\IndexController becomes user\\admin.
    """
    controller = str(document.get("x-controller", "")).replace("\\", "/").strip("/")
    prefix = "app/controller/"
    if not controller.startswith(prefix):
        raise ValueError(f"Missing usable x-controller metadata: {source}")
    relative = Path(controller[len(prefix):])
    if relative.parent == Path("."):
        raise ValueError(f"Controller has no directory: {source}")
    return relative.parent


def organize() -> list[dict[str, str]]:
    source_files = sorted(DOC_DIR.rglob("*.openapi.json"))
    records: list[tuple[Path, dict, Path, str, str]] = []
    for source in source_files:
        document = json.loads(source.read_text(encoding="utf-8-sig"))
        path, method = get_operation(document)
        records.append((source, document, controller_directory(document, source), path, method))

    # Keep POST as the unsuffixed document when a URL supports more than one
    # method. This also makes repeated runs idempotent.
    records.sort(key=lambda item: (item[3], 0 if item[4] == "post" else 1, item[4], str(item[0])))
    planned: list[tuple[Path, Path, str, str]] = []
    used: Counter[str] = Counter()
    for source, _, controller_directory_path, path, method in records:
        target = DOC_DIR / controller_directory_path / filename_for(path, method, used)
        planned.append((source, target, str(controller_directory_path), path))

    targets = [target for _, target, _, _ in planned]
    if len(set(targets)) != len(targets):
        raise ValueError("Duplicate target filename")

    for source, target, _, _ in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            shutil.move(str(source), str(target))

    # Remove only empty legacy custom-name folders left by a previous layout.
    for directory in sorted((item for item in DOC_DIR.rglob("*") if item.is_dir()), key=lambda item: len(item.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass

    return [
        {"controller": controller, "file": str(target.relative_to(DOC_DIR)), "path": path}
        for _, target, controller, path in planned
    ]


if __name__ == "__main__":
    result = organize()
    print(json.dumps({"documentCount": len(result), "documents": result}, ensure_ascii=False, indent=2))
