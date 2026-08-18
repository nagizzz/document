#!/usr/bin/env python3
"""Split stone365_user_api source OpenAPI docs into one operation per file.

The public builder later merges these files back into one document, grouping
operations with OpenAPI tags. APIPOST uses those tags as controller folders.
"""

from __future__ import annotations

import copy
import json
import re
from collections import Counter
from pathlib import Path


DOC_DIR = Path(r"D:\Code Repositories\stone365_user_api\项目资料库\前端接口文档")
METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
ENV_PREFIX = re.compile(r"^\{\{[^{}]+\}\}")
BAD_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def normalized_path(path: str) -> str:
    return ENV_PREFIX.sub("", path)


def controller_for(path: str) -> tuple[str, str]:
    """Return the APIPOST folder name and its controller source."""
    path = normalized_path(path)
    mappings = (
        ("/media/admin/video/", "媒体视频控制器", r"app\controller\media\VideoController"),
        ("/supply/admin/batch-update-fields", "供应信息控制器", r"app\controller\supply\admin\SupplyController"),
        ("/user/admin/", "后台用户控制器", r"app\controller\user\admin\IndexController"),
        ("/user/client/customerFootprint/", "客户足迹控制器", r"app\controller\user\client\FootprintController"),
        ("/operationlog/admin/shopVisits", "店铺访问记录控制器", r"app\controller\operationlog\admin\ShopVisitRecordController"),
        ("/order/virtual-pay/", "虚拟支付控制器", r"app\controller\order\client\VirtualPayController"),
        ("/notifications/client/", "通知控制器", r"app\controller\notification\member\NotificationController"),
        ("/collect/admin/import", "采集导入控制器", r"app\controller\collect\admin\IndexController"),
    )
    for prefix, title, source in mappings:
        if path.startswith(prefix):
            return title, source
    raise ValueError(f"No controller mapping for {path}")


def safe_filename(summary: str, method: str, seen: Counter[str]) -> str:
    name = BAD_FILENAME.sub("_", summary).strip(" .") or "未命名接口"
    seen[name] += 1
    if seen[name] > 1:
        name = f"{name}（{method.upper()}）"
    return f"{name}.openapi.json"


def split() -> list[dict[str, str]]:
    all_documents = sorted(DOC_DIR.glob("*.openapi.json"))
    sources: list[Path] = []
    generated: list[Path] = []
    for document_path in all_documents:
        document = json.loads(document_path.read_text(encoding="utf-8-sig"))
        if "x-source-document" in document:
            generated.append(document_path)
        else:
            sources.append(document_path)

    # A previous interrupted run leaves generated files beside the original
    # multi-operation documents. Remove only those generated interim files.
    for document_path in generated:
        document_path.unlink()
    operations: list[tuple[Path, dict, str, str, dict, dict]] = []
    for source_path in sources:
        source = json.loads(source_path.read_text(encoding="utf-8-sig"))
        for path, path_item in source.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            shared = {key: copy.deepcopy(value) for key, value in path_item.items() if key.lower() not in METHODS}
            for method, operation in path_item.items():
                if method.lower() in METHODS and isinstance(operation, dict):
                    operations.append((source_path, source, path, method.lower(), copy.deepcopy(operation), shared))

    if not operations:
        raise RuntimeError(f"No OpenAPI operations found in {DOC_DIR}")

    output_names: Counter[str] = Counter()
    written: list[dict[str, str]] = []
    for source_path, source, path, method, operation, shared in operations:
        folder, controller_source = controller_for(path)
        summary = str(operation.get("summary") or f"{method.upper()} {normalized_path(path)}")
        filename = safe_filename(summary, method, output_names)
        operation["tags"] = [folder]
        path_item = {**shared, method: operation}
        document = {
            "openapi": source.get("openapi", "3.0.3"),
            "info": {
                "title": summary,
                "version": source.get("info", {}).get("version", "1.0.0"),
                "description": operation.get("description") or source.get("info", {}).get("description", ""),
            },
            "servers": copy.deepcopy(source.get("servers", [])),
            "tags": [{"name": folder, "description": f"控制器：{controller_source}"}],
            "paths": {path: path_item},
            "components": copy.deepcopy(source.get("components", {})),
            "x-source-document": source_path.name,
            "x-controller": controller_source,
        }
        target = DOC_DIR / filename
        target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append({"file": filename, "controller": folder, "method": method.upper(), "path": path})

    written_names = {item["file"] for item in written}
    for source_path in sources:
        if source_path.name not in written_names:
            source_path.unlink()
    return written


if __name__ == "__main__":
    result = split()
    print(json.dumps({"operationCount": len(result), "documents": result}, ensure_ascii=False, indent=2))
