#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import unicodedata
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx
import yaml
from gradio_client import Client, file


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_OUTPUT_ROOT = Path("generated_voice_drama")
DEFAULT_CLONE_CHECKPOINT = "Aratako/Irodori-TTS-500M-v2"
DEFAULT_VOICEDESIGN_CHECKPOINT = "Aratako/Irodori-TTS-500M-v2-VoiceDesign"


class IrodoriClient(Client):
    """Support Gradio apps mounted under /gradio_api."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._skip_components = True
        api_prefix = str(self.config.get("api_prefix") or "/gradio_api").rstrip("/")
        base = self.src.rstrip("/")
        for attr in ("api_url", "sse_url", "sse_data_url", "reset_url", "upload_url"):
            value = getattr(self, attr, None)
            if isinstance(value, str) and value.startswith(base) and api_prefix not in value:
                setattr(self, attr, value.replace(base, f"{base}{api_prefix}", 1))

    def _get_api_info(self):
        url = self.src.rstrip("/") + "/gradio_api/info"
        response = httpx.get(url, headers=self.headers, cookies=self.cookies, verify=self.ssl_verify, timeout=30.0)
        if response.is_success:
            return response.json()
        raise ValueError(f"Could not fetch api info for {self.src}: {response.text}")


@dataclass
class Role:
    id: str
    name: str
    aliases: list[str]
    mode: str
    server_url: str
    ref_wav: Path | None
    upload_wav: Path | None
    uploaded_ref_path: str | None
    caption: str | None
    checkpoint: str


@dataclass
class Segment:
    id: str
    speaker_key: str
    display_text: str
    tts_text: str
    pause_ms: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a split voice drama from a production YAML.")
    parser.add_argument("production", type=Path)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--num-candidates", type=int, default=1)
    parser.add_argument("--model-device", default="cuda")
    parser.add_argument("--codec-device", default="cuda")
    parser.add_argument("--model-precision", default="bf16")
    parser.add_argument("--codec-precision", default="bf16")
    parser.add_argument("--cfg-guidance-mode", default="independent")
    parser.add_argument("--cfg-scale-text", type=float, default=2.5)
    parser.add_argument("--cfg-scale-speaker", type=float, default=4.5)
    parser.add_argument("--cfg-scale-caption", type=float, default=4.0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def sanitize_filename(text: str, max_len: int = 120) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip()
    normalized = re.sub(r"[<>:\"/\\\\|?*\r\n\t]+", "-", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized)
    normalized = normalized.strip(" .-")
    if not normalized:
        normalized = "sample"
    if len(normalized) > max_len:
        normalized = normalized[:max_len].rstrip(" .-")
    return normalized


def parse_seed(log_text: str) -> int | None:
    match = re.search(r"seed_used:\s*(\d+)", log_text)
    return int(match.group(1)) if match else None


def split_text_for_tts(text: str, max_chars: int) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sentence_like = re.findall(r"[^。！？!?…]+[。！？!?…]*|[。！？!?…]+", text)
    if not sentence_like:
        sentence_like = [text]

    chunks: list[str] = []
    current = ""

    def flush_current() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    def split_hard(fragment: str) -> list[str]:
        fragment = fragment.strip()
        if len(fragment) <= max_chars:
            return [fragment]
        parts = re.findall(r"[^、，,]+[、，,]*|[、，,]+", fragment)
        out: list[str] = []
        buf = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(buf) + len(part) <= max_chars:
                buf += part
            else:
                if buf:
                    out.append(buf.strip())
                buf = part
        if buf:
            out.append(buf.strip())
        final: list[str] = []
        for item in out:
            if len(item) <= max_chars:
                final.append(item)
                continue
            for start in range(0, len(item), max_chars):
                final.append(item[start : start + max_chars].strip())
        return [item for item in final if item]

    for piece in sentence_like:
        piece = piece.strip()
        if not piece:
            continue
        if len(piece) > max_chars:
            flush_current()
            chunks.extend(split_hard(piece))
            continue
        if len(current) + len(piece) <= max_chars:
            current += piece
        else:
            flush_current()
            current = piece
    flush_current()
    return chunks


def resolve_path(base_dir: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def load_production(path: Path) -> tuple[dict[str, Role], list[Segment], dict[str, object]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("Production YAML root must be a mapping.")

    base_dir = path.parent
    project = data["project"]
    default_pause_ms = int(project.get("default_pause_ms", 500))
    chunk_pause_ms = int(project.get("chunk_pause_ms", 150))
    max_chars_per_chunk = int(project.get("max_chars_per_chunk", 70))

    alias_map: dict[str, Role] = {}
    for role_data in data["cast"]:
        mode = str(role_data["mode"]).strip()
        role = Role(
            id=str(role_data["id"]).strip(),
            name=str(role_data["name"]).strip(),
            aliases=[str(item).strip() for item in role_data.get("aliases", []) if str(item).strip()],
            mode=mode,
            server_url=str(role_data["server_url"]).strip(),
            ref_wav=resolve_path(base_dir, role_data.get("ref_wav")),
            upload_wav=None,
            uploaded_ref_path=None,
            caption=str(role_data.get("caption") or "").strip() or None,
            checkpoint=str(
                role_data.get("checkpoint")
                or (DEFAULT_CLONE_CHECKPOINT if mode == "clone" else DEFAULT_VOICEDESIGN_CHECKPOINT)
            ).strip(),
        )
        alias_map[role.id] = role
        alias_map[role.name] = role
        for alias in role.aliases:
            alias_map[alias] = role

    segments: list[Segment] = []
    for index, seg_data in enumerate(data["segments"], start=1):
        speaker_key = str(seg_data["speaker"]).strip()
        role = alias_map.get(speaker_key)
        if role is None:
            raise SystemExit(f"Unknown speaker in segment {index}: {speaker_key}")
        display_text = str(seg_data.get("text") or "").strip()
        tts_text = str(seg_data.get("tts_text") or display_text).strip()
        chunk_values = seg_data.get("chunks")
        if isinstance(chunk_values, list) and chunk_values:
            chunks = [str(item).strip() for item in chunk_values if str(item).strip()]
        else:
            chunks = split_text_for_tts(tts_text, max_chars_per_chunk)
        if not chunks:
            raise SystemExit(f"Segment {index} has no usable text.")
        pause_ms = int(seg_data.get("pause_ms", default_pause_ms))
        for chunk_index, chunk in enumerate(chunks, start=1):
            segments.append(
                Segment(
                    id=f"{str(seg_data.get('id') or f's{index:03d}')}-c{chunk_index:02d}",
                    speaker_key=role.id,
                    display_text=display_text or tts_text,
                    tts_text=chunk,
                    pause_ms=chunk_pause_ms if chunk_index < len(chunks) else pause_ms,
                )
            )

    meta = {
        "title": str(project["title"]).strip(),
        "manuscript": str(project.get("manuscript") or "").strip(),
        "output_group": str(project.get("output_group") or "").strip(),
    }
    unique_roles = {role.id: role for role in alias_map.values()}
    return unique_roles, segments, meta


def get_client(cache: dict[str, IrodoriClient], server_url: str) -> IrodoriClient:
    client = cache.get(server_url)
    if client is None:
        client = IrodoriClient(server_url, download_files=False)
        cache[server_url] = client
    return client


def extract_audio_path(result: object) -> Path:
    if isinstance(result, (list, tuple)) and result:
        first = result[0]
        if isinstance(first, dict):
            if "path" in first:
                return Path(first["path"])
            value = first.get("value")
            if isinstance(value, dict) and "path" in value:
                return Path(value["path"])
        if isinstance(first, str):
            return Path(first)
    raise ValueError(f"Unexpected result payload: {type(result)!r}")


def run_generation(
    client: IrodoriClient,
    role: Role,
    segment_text: str,
    args: argparse.Namespace,
) -> tuple[Path, str, int | None]:
    if role.mode == "clone":
        uploaded_ref = upload_file_to_gradio(client, role)
        result = client.predict(
            role.checkpoint,
            args.model_device,
            args.model_precision,
            args.codec_device,
            args.codec_precision,
            segment_text,
            uploaded_ref,
            args.steps,
            args.num_candidates,
            "",
            args.cfg_guidance_mode,
            args.cfg_scale_text,
            args.cfg_scale_speaker,
            "",
            0.5,
            1.0,
            True,
            "",
            "",
            "",
            "",
            "0.9",
            "",
            api_name="/_run_generation",
        )
    else:
        result = client.predict(
            role.checkpoint,
            args.model_device,
            args.model_precision,
            args.codec_device,
            args.codec_precision,
            segment_text,
            role.caption or "",
            args.steps,
            args.num_candidates,
            "",
            args.cfg_guidance_mode,
            args.cfg_scale_text,
            args.cfg_scale_caption,
            "",
            0.5,
            1.0,
            True,
            "",
            "",
            "",
            "",
            "",
            api_name="/_run_generation",
        )
    audio_path = extract_audio_path(result)
    log_text = str(result[-2]) if isinstance(result, list) and len(result) >= 2 else ""
    return audio_path, log_text, parse_seed(log_text)


def append_wave_files(rows: list[dict[str, object]], combined_path: Path) -> None:
    if not rows:
        raise SystemExit("No generated rows to combine.")

    first_audio = Path(rows[0]["output_path"])
    with wave.open(str(first_audio), "rb") as first_wav:
        nchannels = first_wav.getnchannels()
        sampwidth = first_wav.getsampwidth()
        framerate = first_wav.getframerate()
        comptype = first_wav.getcomptype()
        compname = first_wav.getcompname()

    silence_frame = b"\x00" * sampwidth * nchannels
    with wave.open(str(combined_path), "wb") as out_wav:
        out_wav.setnchannels(nchannels)
        out_wav.setsampwidth(sampwidth)
        out_wav.setframerate(framerate)
        out_wav.setcomptype(comptype, compname)
        for row in rows:
            with wave.open(str(row["output_path"]), "rb") as in_wav:
                if (
                    in_wav.getnchannels() != nchannels
                    or in_wav.getsampwidth() != sampwidth
                    or in_wav.getframerate() != framerate
                ):
                    raise ValueError(f"Wave format mismatch for {row['output_path']}")
                out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
            pause_ms = int(row["pause_after_ms"])
            silence_frames = int(framerate * (pause_ms / 1000.0))
            if silence_frames > 0:
                out_wav.writeframes(silence_frame * silence_frames)


def prepare_reference_audio(role: Role, cache_dir: Path) -> None:
    if role.mode != "clone" or role.ref_wav is None:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / f"{sanitize_filename(role.id, max_len=40)}{role.ref_wav.suffix.lower() or '.wav'}"
    if not destination.exists():
        shutil.copy2(role.ref_wav, destination)
    role.upload_wav = destination


def upload_file_to_gradio(client: IrodoriClient, role: Role) -> dict[str, object]:
    if role.uploaded_ref_path:
        return {
            "path": role.uploaded_ref_path,
            "orig_name": Path(role.uploaded_ref_path).name,
            "meta": {"_type": "gradio.FileData"},
        }
    source = role.upload_wav or role.ref_wav
    if source is None:
        raise ValueError(f"Role {role.id} has no reference wav.")
    with open(source, "rb") as fp:
        files = [("files", (Path(source).name, fp))]
        response = httpx.post(
            client.upload_url,
            headers=client.headers,
            cookies=client.cookies,
            verify=client.ssl_verify,
            files=files,
            timeout=120.0,
        )
    response.raise_for_status()
    uploaded = response.json()
    role.uploaded_ref_path = str(uploaded[0])
    return {
        "path": role.uploaded_ref_path,
        "orig_name": Path(source).name,
        "meta": {"_type": "gradio.FileData"},
    }


def main() -> int:
    args = parse_args()
    roles, segments, meta = load_production(args.production)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    group = sanitize_filename(str(meta["output_group"] or meta["title"]), max_len=80)
    out_root = args.output_root / stamp / group
    segments_dir = out_root / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    ref_cache_dir = out_root / "_ref_cache"

    for role in roles.values():
        prepare_reference_audio(role, ref_cache_dir)

    clients: dict[str, IrodoriClient] = {}
    manifest_jsonl = out_root / "manifest.jsonl"
    manifest_csv = out_root / "manifest.csv"
    combined_wav = out_root / f"{sanitize_filename(str(meta['title']), max_len=100)}__full.wav"

    rows: list[dict[str, object]] = []
    generated = 0

    for segment in segments:
        role = roles[segment.speaker_key]
        speaker_dir = segments_dir / sanitize_filename(role.name, max_len=60)
        speaker_dir.mkdir(parents=True, exist_ok=True)
        destination = speaker_dir / f"{sanitize_filename(segment.id, max_len=40)}.wav"
        if destination.exists() and not args.overwrite:
            continue
        client = get_client(clients, role.server_url)
        print(f"[generate] {segment.id} {role.name}: {segment.tts_text}")
        audio_path, log_text, seed = run_generation(client, role, segment.tts_text, args)
        shutil.copy2(audio_path, destination)
        row = {
            "segment_id": segment.id,
            "speaker_id": role.id,
            "speaker_name": role.name,
            "display_text": segment.display_text,
            "tts_text": segment.tts_text,
            "pause_after_ms": segment.pause_ms,
            "seed": seed,
            "output_path": str(destination.resolve()),
        }
        rows.append(row)
        with manifest_jsonl.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")
        generated += 1
        if log_text:
            print(log_text.splitlines()[0])
        if args.limit and generated >= args.limit:
            break

    with manifest_csv.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=["segment_id", "speaker_id", "speaker_name", "display_text", "tts_text", "pause_after_ms", "seed", "output_path"],
        )
        writer.writeheader()
        writer.writerows(rows)

    append_wave_files(rows, combined_wav)

    print(
        json.dumps(
            {
                "generated_segments": len(rows),
                "output_dir": str(out_root.resolve()),
                "combined_wav": str(combined_wav.resolve()),
                "manifest_jsonl": str(manifest_jsonl.resolve()),
                "manifest_csv": str(manifest_csv.resolve()),
                "manuscript": meta["manuscript"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
