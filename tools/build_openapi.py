#!/usr/bin/env python3
"""Serve one APIPOST-ready OpenAPI document per repository on localhost.

The source documents are never modified. Before every HTTP request, this
program checks for changed source files and rebuilds only when necessary.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote


SOURCE_ROOT = Path(r"D:\Code Repositories")
OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "openapi"
COMPONENT_REF = re.compile(r"^#/components/([^/]+)/(.+)$")
PRIVATE_IP = re.compile(r"\b(?:10(?:\.\d{1,3}){3}|127(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})\b")
APIPOST_PATH_PREFIX = re.compile(r"^\{\{[^{}]+\}\}")
LOCK = threading.Lock()
LAST_FINGERPRINT: tuple[tuple[str, int, int], ...] | None = None


def source_files() -> list[tuple[str, Path]]:
    if not SOURCE_ROOT.is_dir():
        return []
    files: list[tuple[str, Path]] = []
    for directory in SOURCE_ROOT.rglob("前端接口文档"):
        if not directory.is_dir() or directory.parent.name != "项目资料库":
            continue
        repository = directory.parent.parent.name
        # Source documents may be organized in controller subdirectories.
        for document in directory.rglob("*.openapi.json"):
            files.append((repository, document))
    return sorted(files, key=lambda item: (item[0].lower(), str(item[1]).lower()))


def fingerprint(files: list[tuple[str, Path]]) -> tuple[tuple[str, int, int], ...]:
    return tuple((str(path), path.stat().st_mtime_ns, path.stat().st_size) for _, path in files)


def deep_rewrite_refs(value: object, reference_map: dict[str, str]) -> object:
    if isinstance(value, dict):
        return {key: deep_rewrite_refs(item, reference_map) for key, item in value.items()}
    if isinstance(value, list):
        return [deep_rewrite_refs(item, reference_map) for item in value]
    if isinstance(value, str) and value in reference_map:
        return reference_map[value]
    return value


def redact_public_values(value: object) -> object:
    """Remove private-network addresses from the public documentation copy."""
    if isinstance(value, dict):
        return {key: redact_public_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_public_values(item) for item in value]
    if isinstance(value, str):
        return PRIVATE_IP.sub("<private-ip>", value)
    return value


def normalize_openapi_path(path_name: str) -> str:
    """Turn APIPOST-style {{environment}}/path keys into standard OpenAPI paths."""
    normalized = APIPOST_PATH_PREFIX.sub("", path_name)
    return normalized if normalized.startswith("/") else f"/{normalized.lstrip('/')}"


def clean_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def merge_repository(repository: str, documents: list[Path]) -> tuple[dict, list[str]]:
    merged_paths: dict[str, object] = {}
    merged_components: dict[str, dict[str, object]] = {}
    servers: list[object] = []
    server_signatures: set[str] = set()
    tags: list[object] = []
    tag_names: set[str] = set()
    warnings: list[str] = []

    for document_number, document_path in enumerate(documents, start=1):
        try:
            source = json.loads(document_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            warnings.append(f"Skipped unreadable JSON: {document_path.name} ({error})")
            continue

        prefix = f"doc{document_number:02d}_{clean_name(document_path.stem)[:36]}"
        reference_map: dict[str, str] = {}
        components = source.get("components", {})
        if isinstance(components, dict):
            for section, definitions in components.items():
                if not isinstance(definitions, dict):
                    continue
                for name in definitions:
                    old_ref = f"#/components/{section}/{name}"
                    new_name = f"{prefix}__{name}"
                    reference_map[old_ref] = f"#/components/{section}/{new_name}"

        rewritten = redact_public_values(deep_rewrite_refs(copy.deepcopy(source), reference_map))
        for server in rewritten.get("servers", []):
            if isinstance(server, dict) and "{{" in str(server.get("url", "")):
                # Keep environment variables in the source document, but omit them from
                # the public strict-OpenAPI export. APIPOST can configure its own env.
                continue
            signature = json.dumps(server, ensure_ascii=False, sort_keys=True)
            if signature not in server_signatures:
                servers.append(server)
                server_signatures.add(signature)

        for tag in rewritten.get("tags", []):
            if not isinstance(tag, dict):
                continue
            name = str(tag.get("name", json.dumps(tag, ensure_ascii=False, sort_keys=True)))
            if name not in tag_names:
                tags.append(tag)
                tag_names.add(name)

        rewritten_components = rewritten.get("components", {})
        if isinstance(rewritten_components, dict):
            for section, definitions in rewritten_components.items():
                if not isinstance(definitions, dict):
                    continue
                target_section = merged_components.setdefault(section, {})
                for name, definition in definitions.items():
                    old_ref = f"#/components/{section}/{name}"
                    new_ref = reference_map.get(old_ref, old_ref)
                    new_name = new_ref.rsplit("/", 1)[-1]
                    target_section[new_name] = definition

        paths = rewritten.get("paths", {})
        if not isinstance(paths, dict):
            warnings.append(f"Skipped invalid paths object: {document_path.name}")
            continue
        for path_name, path_item in paths.items():
            path_name = normalize_openapi_path(path_name)
            if path_name not in merged_paths:
                merged_paths[path_name] = path_item
                continue
            if not isinstance(merged_paths[path_name], dict) or not isinstance(path_item, dict):
                warnings.append(f"Skipped duplicate path: {path_name} in {document_path.name}")
                continue
            target_item = merged_paths[path_name]
            for method, operation in path_item.items():
                if method in target_item:
                    warnings.append(
                        f"Skipped duplicate operation: {method.upper()} {path_name} in {document_path.name}"
                    )
                else:
                    target_item[method] = operation

    merged: dict[str, object] = {
        "openapi": "3.0.3",
        "info": {
            "title": f"{repository} - APIPOST 聚合接口文档",
            "version": datetime.now().strftime("%Y.%m.%d"),
            "description": "由本机 OpenAPI 聚合服务自动生成。请勿手工编辑此文件。",
        },
        "paths": merged_paths,
    }
    if servers:
        merged["servers"] = servers
    if tags:
        merged["tags"] = tags
    if merged_components:
        merged["components"] = merged_components
    return merged, warnings


def build(force: bool = False) -> dict:
    global LAST_FINGERPRINT
    files = source_files()
    current_fingerprint = fingerprint(files)
    if not force and current_fingerprint == LAST_FINGERPRINT and OUTPUT_ROOT.is_dir():
        return json.loads((OUTPUT_ROOT / "index.json").read_text(encoding="utf-8"))

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[Path]] = {}
    for repository, path in files:
        grouped.setdefault(repository, []).append(path)

    index: dict[str, object] = {
        "generatedAt": datetime.now(timezone.utc).astimezone().isoformat(),
        "sourceRoot": str(SOURCE_ROOT),
        "repositories": [],
        "warnings": [],
    }
    expected_outputs: set[Path] = {OUTPUT_ROOT / "index.json"}
    for repository, documents in grouped.items():
        merged, warnings = merge_repository(repository, documents)
        output_name = f"{repository}.openapi.json"
        output_path = OUTPUT_ROOT / output_name
        output_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        expected_outputs.add(output_path)
        index["repositories"].append(
            {
                "repository": repository,
                "file": output_name,
                "sourceFileCount": len(documents),
                "pathCount": len(merged["paths"]),
                "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
            }
        )
        index["warnings"].extend(f"{repository}: {warning}" for warning in warnings)

    for old_output in OUTPUT_ROOT.glob("*.openapi.json"):
        if old_output not in expected_outputs:
            old_output.unlink()
    (OUTPUT_ROOT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LAST_FINGERPRINT = current_fingerprint
    return index


class AggregateHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUTPUT_ROOT), **kwargs)

    def do_GET(self):
        with LOCK:
            build()
        super().do_GET()

    def do_HEAD(self):
        with LOCK:
            build()
        super().do_HEAD()

    def log_message(self, format: str, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()

    with LOCK:
        index = build(force=True)
    if args.build_only:
        print(json.dumps(index, ensure_ascii=False, indent=2))
        return 0

    print(f"Serving {len(index['repositories'])} aggregated OpenAPI files on http://127.0.0.1:{args.port}/")
    print("Use one of these URLs in APIPOST:")
    for item in index["repositories"]:
        print(f"  http://127.0.0.1:{args.port}/{item['file']}")
    print("Keep this window open. Press Ctrl+C to stop.")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), AggregateHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
