"""Bounded contracts for music generation capability and local video assembly."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Callable
from app.services.video_formats import EXPORT_RESOLUTIONS


class MediaToolError(ValueError):
    """A stable, non-secret failure exposed by the media tooling."""


@dataclass(frozen=True)
class MusicRequest:
    prompt: str
    duration_seconds: int
    seed: int
    lyrics: str = "[instrumental]\n"

    @classmethod
    def from_dict(cls, value: dict) -> "MusicRequest":
        if not isinstance(value, dict) or set(value) not in (
                {"prompt", "duration_seconds", "seed"}, {"prompt", "duration_seconds", "seed", "lyrics"}):
            raise MediaToolError("music_request_fields_invalid")
        prompt = value.get("prompt")
        duration = value.get("duration_seconds")
        seed = value.get("seed")
        lyrics = value.get("lyrics", "[instrumental]\n")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 1200 or "\x00" in prompt:
            raise MediaToolError("music_prompt_invalid")
        if type(duration) is not int or not 1 <= duration <= 300:
            raise MediaToolError("music_duration_invalid")
        if type(seed) is not int or not 0 <= seed < 2**63:
            raise MediaToolError("music_seed_invalid")
        if not isinstance(lyrics, str) or not lyrics.strip() or len(lyrics.encode("utf-8")) > 16 * 1024 or "\x00" in lyrics:
            raise MediaToolError("music_lyrics_invalid")
        return cls(prompt.strip(), duration, seed, lyrics.strip() + "\n")


class ComfyMusicAdapter:
    """Capability adapter for one repository-owned native ComfyUI graph."""

    PROFILE = "ace-step-v1-3.5b-native.v1"
    CHECKPOINT = "ace_step_v1_3.5b.safetensors"
    REQUIRED_NODES = (
        "CheckpointLoaderSimple", "TextEncodeAceStepAudio", "ConditioningZeroOut",
        "EmptyAceStepLatentAudio", "LatentOperationTonemapReinhard", "LatentApplyOperationCFG",
        "ModelSamplingSD3", "KSampler", "VAEDecodeAudio", "SaveAudioMP3",
    )
    PROFILES = {PROFILE: {"checkpoint": CHECKPOINT, "source": "official_comfyui_ace_step_v1_template"}}
    RECOGNIZED_AUDIO_NODES = frozenset({"LoadAudio", "SaveAudio", "PreviewAudio"})

    def __init__(self, request_json: Callable[[str], dict]):
        self.request_json = request_json

    def preflight(self) -> dict:
        try:
            node_info = {name: self.request_json("/object_info/" + name) for name in self.REQUIRED_NODES}
            queue = self.request_json("/queue")
            stats = self.request_json("/system_stats")
        except Exception as exc:
            raise MediaToolError("comfyui_unavailable") from exc
        if not all(isinstance(value, dict) for value in node_info.values()):
            raise MediaToolError("comfyui_object_info_invalid")
        present_names = {name for name, value in node_info.items() if name in value}
        missing_nodes = sorted(set(self.REQUIRED_NODES).difference(present_names))
        try:
            checkpoints = node_info["CheckpointLoaderSimple"]["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        except (KeyError, TypeError, IndexError):
            checkpoints = []
        checkpoint_present = self.CHECKPOINT in checkpoints
        queue_idle = queue.get("queue_running") == [] and queue.get("queue_pending") == []
        version = stats.get("system", {}).get("comfyui_version")
        requirements_ready = not missing_nodes and checkpoint_present and version == "0.35.0"
        ready = requirements_ready and queue_idle
        return {
            "backend": "comfyui",
            "reachable": True,
            "profile": self.PROFILE,
            "requirements_ready": requirements_ready,
            "pilot_verified": False,
            "generation_ready": ready,
            "reason": None if ready else ("comfyui_busy" if requirements_ready else "ace_step_native_requirements_missing"),
            "missing_nodes": missing_nodes,
            "checkpoint_present": checkpoint_present,
            "queue_idle": queue_idle,
            "comfyui_version": version,
        }

    def workflow(self, profile: str, request: MusicRequest) -> dict:
        if profile not in self.PROFILES:
            raise MediaToolError("music_profile_not_verified")
        return ace_step_v1_graph(request)


def ace_step_v1_graph(request: MusicRequest, prefix: str = "AI-Company/music") -> dict:
    """API graph transcribed from ComfyUI's official ACE-Step V1 instrumental template."""
    if not re.fullmatch(r"AI-Company/[A-Za-z0-9_-]{1,48}", prefix):
        raise MediaToolError("music_output_prefix_invalid")
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ComfyMusicAdapter.CHECKPOINT}},
        "2": {"class_type": "TextEncodeAceStepAudio", "inputs": {
            "clip": ["1", 1], "tags": request.prompt, "lyrics": request.lyrics, "lyrics_strength": 0.99}},
        "3": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["2", 0]}},
        "4": {"class_type": "EmptyAceStepLatentAudio", "inputs": {
            "seconds": float(request.duration_seconds), "batch_size": 1}},
        "5": {"class_type": "LatentOperationTonemapReinhard", "inputs": {"multiplier": 1.0}},
        "6": {"class_type": "LatentApplyOperationCFG", "inputs": {"model": ["1", 0], "operation": ["5", 0]}},
        "7": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["6", 0], "shift": 5.0}},
        "8": {"class_type": "KSampler", "inputs": {
            "model": ["7", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0],
            "seed": request.seed, "steps": 50, "cfg": 5.0, "sampler_name": "euler",
            "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["8", 0], "vae": ["1", 2]}},
        "10": {"class_type": "SaveAudioMP3", "inputs": {
            "audio": ["9", 0], "filename_prefix": prefix, "quality": "V0"}},
    }


def ffmpeg_preflight(run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> dict:
    paths = {name: shutil.which(name) for name in ("ffmpeg", "ffprobe")}
    if not all(paths.values()):
        return {"backend": "ffmpeg", "ready": False, "reason": "binary_missing", "binaries": paths}
    checks = {}
    for name, args in {
        "filters": [paths["ffmpeg"], "-hide_banner", "-filters"],
        "encoders": [paths["ffmpeg"], "-hide_banner", "-encoders"],
    }.items():
        result = run(args, capture_output=True, text=True, timeout=10, check=False)
        checks[name] = (result.stdout or "") + (result.stderr or "")
    required_filters = ("concat", "scale", "pad", "fps", "atrim")
    required_encoders = ("libx264", "aac")
    missing = [x for x in required_filters if not re.search(rf"\b{re.escape(x)}\b", checks["filters"])]
    missing += [x for x in required_encoders if not re.search(rf"\b{re.escape(x)}\b", checks["encoders"])]
    return {
        "backend": "ffmpeg", "ready": not missing, "reason": None if not missing else "capability_missing",
        "version": _first_line(run([paths["ffmpeg"], "-version"], capture_output=True, text=True,
                                   timeout=10, check=False).stdout),
        "required": {"filters": list(required_filters), "encoders": list(required_encoders)},
        "missing": missing,
    }


def _first_line(value: str) -> str:
    return value.splitlines()[0] if value else "unknown"


def _safe_file(root: Path, relative: object, suffixes: set[str]) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise MediaToolError("asset_path_invalid")
    root = root.resolve()
    candidate = (root / relative).resolve()
    if candidate.parent != root or candidate.suffix.lower() not in suffixes or not candidate.is_file():
        raise MediaToolError("asset_path_invalid")
    return candidate


def validate_edit_plan(value: dict, asset_root: Path) -> dict:
    if not isinstance(value, dict) or set(value) != {"clips", "audio", "output", "width", "height", "fps"}:
        raise MediaToolError("edit_plan_fields_invalid")
    clips = value.get("clips")
    if not isinstance(clips, list) or not 1 <= len(clips) <= 64:
        raise MediaToolError("clips_invalid")
    normalized = []
    total_bytes = 0
    for clip in clips:
        if not isinstance(clip, dict) or set(clip) != {"file", "duration_seconds"}:
            raise MediaToolError("clip_fields_invalid")
        duration = clip["duration_seconds"]
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not .1 <= duration <= 60:
            raise MediaToolError("clip_duration_invalid")
        path = _safe_file(asset_root, clip["file"], {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".mkv"})
        size = path.stat().st_size
        if size > 256 * 1024 * 1024:
            raise MediaToolError("asset_size_invalid")
        total_bytes += size
        normalized.append({"path": path, "duration": float(duration), "image": path.suffix.lower() != ".mp4" and path.suffix.lower() not in {".mov", ".mkv"}})
    audio = _safe_file(asset_root, value["audio"], {".wav", ".mp3", ".flac", ".m4a", ".ogg"})
    audio_size = audio.stat().st_size
    if audio_size > 256 * 1024 * 1024 or total_bytes + audio_size > 512 * 1024 * 1024:
        raise MediaToolError("asset_size_invalid")
    output = value["output"]
    if not isinstance(output, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\.mp4", output):
        raise MediaToolError("output_name_invalid")
    width, height, fps = value["width"], value["height"], value["fps"]
    landscape_formats = {(640, 360), *EXPORT_RESOLUTIONS.values()}
    formats = landscape_formats | {size[::-1] for size in landscape_formats}
    if any(type(item) is not int for item in (width, height, fps)) or (width, height) not in formats or fps not in {24, 25, 30}:
        raise MediaToolError("video_format_invalid")
    duration = sum(x["duration"] for x in normalized)
    if duration > 300:
        raise MediaToolError("total_duration_invalid")
    return {"clips": normalized, "audio": audio, "output": output, "width": width, "height": height,
            "fps": fps, "duration": duration, "input_bytes": total_bytes + audio_size}


DEMUXERS = {".png": "image2", ".jpg": "image2", ".jpeg": "image2", ".webp": "image2",
            ".mp4": "mov", ".mov": "mov", ".mkv": "matroska", ".wav": "wav", ".mp3": "mp3",
            ".flac": "flac", ".m4a": "mov", ".ogg": "ogg"}


def build_ffmpeg_command(plan: dict, output_path: Path, ffmpeg: str = "ffmpeg") -> list[str]:
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
               "-filter_threads", "2", "-filter_complex_threads", "2"]
    for clip in plan["clips"]:
        if clip["image"]:
            command += ["-loop", "1", "-pattern_type", "none", "-t", str(clip["duration"])]
        command += ["-threads", "2", "-protocol_whitelist", "file,pipe", "-f", DEMUXERS[clip["path"].suffix.lower()],
                    "-i", str(clip["path"])]
    command += ["-threads", "2", "-protocol_whitelist", "file,pipe", "-f", DEMUXERS[plan["audio"].suffix.lower()],
                "-i", str(plan["audio"])]
    chains, labels = [], []
    for index, clip in enumerate(plan["clips"]):
        label = f"v{index}"
        chains.append(
            f"[{index}:v]scale={plan['width']}:{plan['height']}:force_original_aspect_ratio=decrease,"
            f"pad={plan['width']}:{plan['height']}:(ow-iw)/2:(oh-ih)/2,fps={plan['fps']},"
            f"setsar=1,format=yuv420p,trim=duration={clip['duration']},setpts=PTS-STARTPTS[{label}]"
        )
        labels.append(f"[{label}]")
    chains.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[v]")
    audio_index = len(plan["clips"])
    chains.append(f"[{audio_index}:a]atrim=duration={plan['duration']},asetpts=PTS-STARTPTS[a]")
    return command + ["-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]",
                      "-c:v", "libx264", "-threads", "2", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
                      "-movflags", "+faststart", str(output_path)]


def render_sequential(plan, temporary, staged, run):
    """One decoder at a time: the task/memory budget does not grow with shot count."""
    names = []
    deadline = time.monotonic() + 600
    def remaining():
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise subprocess.TimeoutExpired('ffmpeg', 600)
        return min(120, seconds)
    for index, clip in enumerate(plan['clips']):
        name = f'part-{index:03d}.mp4'
        part = temporary / name
        command = ['ffmpeg', '-v', 'error', '-nostdin', '-n', '-filter_threads', '1']
        if clip['image']:
            command += ['-loop', '1', '-pattern_type', 'none']
        command += ['-threads', '1', '-protocol_whitelist', 'file,pipe', '-f',
            DEMUXERS[clip['path'].suffix.lower()], '-i', str(clip['path']), '-an',
            '-vf', f"scale={plan['width']}:{plan['height']}:force_original_aspect_ratio=decrease,"
                f"pad={plan['width']}:{plan['height']}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={plan['fps']},format=yuv420p",
            '-frames:v', str(round(clip['duration'] * plan['fps'])), '-c:v', 'libx264',
            '-threads', '2', '-preset', 'medium', '-crf', '20', str(part)]
        result = run(command, capture_output=True, timeout=remaining(), check=False)
        if result.returncode or not part.is_file() or not part.stat().st_size:
            raise MediaToolError('ffmpeg_render_failed')
        names.append(f"file '{name}'\n")  # Generated filenames only; never model/user text.
    manifest = temporary / 'parts.txt'
    manifest.write_text(''.join(names))
    return run(['ffmpeg', '-v', 'error', '-nostdin', '-n', '-threads', '1',
        '-protocol_whitelist', 'file,pipe', '-f', 'concat', '-safe', '1', '-i', str(manifest),
        '-threads', '1', '-protocol_whitelist', 'file,pipe', '-f', DEMUXERS[plan['audio'].suffix.lower()],
        '-i', str(plan['audio']), '-map', '0:v:0', '-map', '1:a:0', '-t', str(plan['duration']),
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-threads', '2',
        '-movflags', '+faststart', str(staged)], capture_output=True, timeout=remaining(), check=False)


def render_video(plan_value: dict, asset_root: Path, output_root: Path,
                 run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> dict:
    plan = validate_edit_plan(plan_value, asset_root)
    if output_root.is_symlink():
        raise MediaToolError("output_directory_invalid")
    if output_root.exists() and not output_root.is_dir():
        raise MediaToolError("output_directory_invalid")
    if not output_root.exists():
        output_root.mkdir(parents=True, mode=0o700)
    output_root = output_root.resolve()
    output = output_root / plan["output"]
    preflight = ffmpeg_preflight(run)
    if not preflight["ready"]:
        raise MediaToolError("ffmpeg_not_ready")
    temporary = Path(tempfile.mkdtemp(prefix=".music-video-", dir=output_root))
    staged = temporary / "render.mp4"
    try:
        try:
            result = (render_sequential(plan, temporary, staged, run)
                      if len(plan['clips']) > 8 or plan['width'] * plan['height'] >= 2560 * 1440 else
                      run(build_ffmpeg_command(plan, staged), capture_output=True, timeout=600, check=False))
        except subprocess.TimeoutExpired as exc:
            raise MediaToolError("ffmpeg_render_timeout") from exc
        if result.returncode or not staged.is_file() or staged.stat().st_size == 0:
            raise MediaToolError("ffmpeg_render_failed")
        staged.chmod(0o600)
        measured = probe_render(staged, run)
        tolerance = max(.25, 2 / plan["fps"])
        if measured["stream_types"] != ["audio", "video"] or abs(measured["duration_seconds"] - plan["duration"]) > tolerance:
            raise MediaToolError("render_verification_failed")
        if (measured['width'], measured['height'], measured['fps']) != (plan['width'], plan['height'], plan['fps']):
            raise MediaToolError('render_format_verification_failed')
        try:
            os.link(staged, output)  # Atomic no-clobber publication on the same filesystem.
        except FileExistsError as exc:
            raise MediaToolError("output_exists") from exc
        import hashlib
        return {"schema": "music-video-render.v1", "status": "rendered", "output": output.name,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "duration_seconds": measured["duration_seconds"], "stream_types": measured["stream_types"],
                "width": measured['width'], "height": measured['height'], "fps": measured['fps'],
                "size_bytes": output.stat().st_size, "encoding": "H.264 CRF 20, AAC 192k",
                "input_bytes": plan["input_bytes"], "backend": "ffmpeg", "published": False}
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def probe_render(path: Path, run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise MediaToolError("ffprobe_missing")
    try:
        result = run([ffprobe, "-v", "error", "-protocol_whitelist", "file,pipe", "-f", "mov",
                      "-show_entries", "format=duration:stream=codec_type,width,height,avg_frame_rate", "-of", "json", str(path)],
                     capture_output=True, text=True, timeout=20, check=False)
    except subprocess.TimeoutExpired as exc:
        raise MediaToolError("ffprobe_timeout") from exc
    try:
        value = json.loads(result.stdout) if result.returncode == 0 else None
        duration = float(value["format"]["duration"])
        streams = sorted(item["codec_type"] for item in value["streams"])
        video = next(item for item in value['streams'] if item['codec_type'] == 'video')
        numerator, denominator = video['avg_frame_rate'].split('/')
        fps = float(numerator) / float(denominator)
    except (TypeError, KeyError, ValueError, StopIteration, ZeroDivisionError, json.JSONDecodeError) as exc:
        raise MediaToolError("ffprobe_invalid") from exc
    if not 0 < duration <= 301 or streams != ["audio", "video"]:
        raise MediaToolError("ffprobe_invalid")
    return {"duration_seconds": duration, "stream_types": streams,
            'width': video['width'], 'height': video['height'], 'fps': fps}
