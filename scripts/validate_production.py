#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a voice drama production YAML.")
    parser.add_argument("production", type=Path)
    return parser.parse_args()


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path}: failed to parse YAML: {exc}"]

    if not isinstance(data, dict):
        return [f"{path}: root must be a mapping"]

    for key in ("project", "cast", "segments"):
        if key not in data:
            errors.append(f"{path}: missing top-level key `{key}`")

    project = data.get("project")
    if not isinstance(project, dict):
        errors.append(f"{path}: `project` must be a mapping")
    else:
        if not str(project.get("title") or "").strip():
            errors.append(f"{path}: `project.title` is required")

    cast = data.get("cast")
    cast_ids: set[str] = set()
    alias_map: set[str] = set()
    if not isinstance(cast, list) or not cast:
        errors.append(f"{path}: `cast` must be a non-empty list")
    else:
        for index, role in enumerate(cast, start=1):
            prefix = f"{path}: cast[{index}]"
            if not isinstance(role, dict):
                errors.append(f"{prefix} must be a mapping")
                continue
            role_id = str(role.get("id") or "").strip()
            mode = str(role.get("mode") or "").strip()
            if not role_id:
                errors.append(f"{prefix}.id is required")
            elif role_id in cast_ids:
                errors.append(f"{prefix}.id `{role_id}` is duplicated")
            else:
                cast_ids.add(role_id)
                alias_map.add(role_id)
            if not str(role.get("name") or "").strip():
                errors.append(f"{prefix}.name is required")
            if mode not in {"clone", "voicedesign"}:
                errors.append(f"{prefix}.mode must be `clone` or `voicedesign`")
            if not str(role.get("server_url") or "").strip():
                errors.append(f"{prefix}.server_url is required")
            if mode == "clone" and not str(role.get("ref_wav") or "").strip():
                errors.append(f"{prefix}.ref_wav is required for clone mode")
            if mode == "voicedesign" and not str(role.get("caption") or "").strip():
                errors.append(f"{prefix}.caption is required for voicedesign mode")
            aliases = _as_list(role.get("aliases"))
            for alias in aliases:
                alias_text = str(alias).strip()
                if alias_text:
                    alias_map.add(alias_text)

    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append(f"{path}: `segments` must be a non-empty list")
    else:
        for index, segment in enumerate(segments, start=1):
            prefix = f"{path}: segments[{index}]"
            if not isinstance(segment, dict):
                errors.append(f"{prefix} must be a mapping")
                continue
            speaker = str(segment.get("speaker") or "").strip()
            if not speaker:
                errors.append(f"{prefix}.speaker is required")
            elif alias_map and speaker not in alias_map:
                errors.append(f"{prefix}.speaker `{speaker}` does not match any cast id or alias")
            text = str(segment.get("text") or "").strip()
            tts_text = str(segment.get("tts_text") or "").strip()
            chunks = segment.get("chunks")
            if not text and not tts_text and not (isinstance(chunks, list) and chunks):
                errors.append(f"{prefix} needs `text`, `tts_text`, or non-empty `chunks`")
            if chunks is not None:
                if not isinstance(chunks, list) or not chunks:
                    errors.append(f"{prefix}.chunks must be a non-empty list when present")
                elif not all(str(item).strip() for item in chunks):
                    errors.append(f"{prefix}.chunks cannot contain empty items")

    return errors


def main() -> int:
    args = parse_args()
    errors = validate(args.production)
    if errors:
        for error in errors:
            print(error)
        print(f"\nValidation failed: {len(errors)} issue(s)")
        return 1
    print(f"Validated production YAML: {args.production}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
