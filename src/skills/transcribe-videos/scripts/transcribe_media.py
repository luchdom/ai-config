#!/usr/bin/env python3
"""Transcribe public, direct, or local media into temporary JSON segments."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class Job:
    slug: str
    title: str
    input_value: str
    direct_media: bool


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "video"


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _job_from_mapping(item: dict[str, Any], index: int) -> Job:
    input_value = str(item.get("input", "")).strip()
    if not input_value:
        raise ValueError(f"Manifest item {index} is missing 'input'")
    title = str(item.get("title", "")).strip() or f"Video {index:02d}"
    slug = slugify(str(item.get("slug", "")).strip() or title)
    return Job(
        slug=slug,
        title=title,
        input_value=input_value,
        direct_media=bool(item.get("direct_media", False)),
    )


def load_manifest(path: Path) -> list[Job]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list) or not items:
        raise ValueError("Manifest must be a non-empty list or an object with an 'items' list")
    jobs: list[Job] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Manifest item {index} must be an object")
        jobs.append(_job_from_mapping(item, index))
    slugs = [job.slug for job in jobs]
    if len(slugs) != len(set(slugs)):
        raise ValueError("Manifest contains duplicate slugs")
    return jobs


def check_dependencies() -> dict[str, bool]:
    return {
        "yt_dlp": shutil.which("yt-dlp") is not None,
        "faster_whisper": importlib.util.find_spec("faster_whisper") is not None,
    }


def require_yt_dlp() -> str:
    executable = shutil.which("yt-dlp")
    if executable is None:
        raise RuntimeError("yt-dlp is required for public page URLs; install it from the official project")
    return executable


def download_audio(url: str, directory: Path) -> Path:
    executable = require_yt_dlp()
    template = str(directory / "source.%(ext)s")
    completed = subprocess.run(
        [
            executable,
            "--no-playlist",
            "--no-progress",
            "--no-warnings",
            "-f",
            "bestaudio/best",
            "-o",
            template,
            url,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError("yt-dlp could not acquire the public media")
    candidates = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix not in {".part", ".ytdl", ".json"}
    ]
    if not candidates:
        raise RuntimeError("yt-dlp completed without producing an audio file")
    return max(candidates, key=lambda path: path.stat().st_size)


def load_model(args: argparse.Namespace) -> Any:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is missing; install it in an isolated Python environment"
        ) from exc
    kwargs: dict[str, Any] = {
        "device": args.device,
        "compute_type": args.compute_type,
    }
    if args.model_cache:
        kwargs["download_root"] = str(Path(args.model_cache).resolve())
    return WhisperModel(args.model, **kwargs)


def transcribe_job(job: Job, model: Any, args: argparse.Namespace) -> dict[str, Any]:
    source_kind = "direct-media" if job.direct_media else "local-file"
    try:
        with tempfile.TemporaryDirectory(prefix="codex-video-media-") as temp_name:
            temp_dir = Path(temp_name)
            if is_http_url(job.input_value):
                if job.direct_media:
                    media: str | Path = job.input_value
                else:
                    source_kind = "public-url"
                    media = download_audio(job.input_value, temp_dir)
            else:
                input_path = Path(job.input_value)
                if not input_path.is_file():
                    raise RuntimeError("input is neither an existing file nor an HTTP(S) URL")
                source_kind = "local-file"
                media = input_path

            language = None if args.language == "auto" else args.language
            segments_iter, info = model.transcribe(
                str(media),
                language=language,
                beam_size=args.beam_size,
                vad_filter=True,
            )
            segments = [
                {
                    "start": round(float(segment.start), 3),
                    "end": round(float(segment.end), 3),
                    "text": segment.text.strip(),
                }
                for segment in segments_iter
                if segment.text.strip()
            ]
    except Exception as exc:
        raise RuntimeError(f"Could not decode or transcribe '{job.slug}'") from exc

    return {
        "slug": job.slug,
        "title": job.title,
        "source_kind": source_kind,
        "duration": round(float(getattr(info, "duration", 0.0)), 3),
        "language": getattr(info, "language", args.language),
        "language_probability": round(float(getattr(info, "language_probability", 0.0)), 4),
        "segments": segments,
    }


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe media into timestamped JSON without retaining temporary downloads."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", help="Public URL, direct media URL, or local media file")
    source.add_argument("--manifest", type=Path, help="JSON batch manifest")
    parser.add_argument("--output", type=Path, help="Output JSON for one input")
    parser.add_argument("--output-dir", type=Path, help="Output directory for a batch")
    parser.add_argument("--title", default="Video", help="Title for one input")
    parser.add_argument("--slug", help="Slug for one input")
    parser.add_argument("--direct-media", action="store_true", help="Stream input directly")
    parser.add_argument("--language", default="auto", help="Language code or 'auto'")
    parser.add_argument("--model", default="small", help="faster-whisper model name")
    parser.add_argument("--device", default="cpu", help="CTranslate2 device")
    parser.add_argument("--compute-type", default="int8", help="CTranslate2 compute type")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--model-cache", help="Optional model cache directory")
    parser.add_argument("--check", action="store_true", help="Report dependency availability")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without transcription")
    return parser.parse_args()


def resolve_jobs(args: argparse.Namespace) -> list[Job]:
    if args.manifest:
        if args.output or not args.output_dir:
            raise ValueError("Batch mode requires --output-dir and does not accept --output")
        return load_manifest(args.manifest)
    if args.input:
        if args.output_dir or not args.output:
            raise ValueError("Single mode requires --output and does not accept --output-dir")
        return [
            Job(
                slug=slugify(args.slug or args.title),
                title=args.title,
                input_value=args.input,
                direct_media=args.direct_media,
            )
        ]
    raise ValueError("Provide --input or --manifest")


def main() -> int:
    args = parse_args()
    if args.check:
        status = check_dependencies()
        print(json.dumps(status, indent=2))
        return 0 if all(status.values()) else 1
    try:
        jobs = resolve_jobs(args)
        if args.dry_run:
            print(json.dumps({"jobs": [job.slug for job in jobs]}, indent=2))
            return 0
        model = load_model(args)
        for index, job in enumerate(jobs, start=1):
            print(f"[{index}/{len(jobs)}] Transcribing {job.slug}", flush=True)
            result = transcribe_job(job, model, args)
            output = args.output if args.output else args.output_dir / f"{job.slug}.json"
            write_result(output, result)
            print(
                f"[{index}/{len(jobs)}] Wrote {output} ({len(result['segments'])} segments)",
                flush=True,
            )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
