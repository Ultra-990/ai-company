"""Validate music/video jobs, inspect capabilities, or render one bounded local edit."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.music_video_tools import ComfyMusicAdapter, ffmpeg_preflight, render_video, validate_edit_plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="Inspect local FFmpeg; does not use GPU or ComfyUI")
    parser.add_argument("--comfy-preflight", action="store_true",
                        help="Also inspect ComfyUI object metadata; never enqueue a workflow")
    parser.add_argument("--plan", type=Path, help="JSON edit plan")
    parser.add_argument("--assets", type=Path, help="Single flat input directory")
    parser.add_argument("--output-dir", type=Path, help="Local output directory")
    parser.add_argument("--run", action="store_true", help="Execute FFmpeg after validation")
    args = parser.parse_args(argv)
    if args.preflight:
        music = {"ready": False, "reason": "comfy_preflight_not_requested"}
        if args.comfy_preflight:
            from app.services.comfyui_provider import ComfyProvider
            music = ComfyMusicAdapter(ComfyProvider().request).preflight()
        print(json.dumps({"schema": "music-video-preflight.v1", "ffmpeg": ffmpeg_preflight(),
                          "music_generation": music}, indent=2))
        return 0
    if not args.plan or not args.assets:
        parser.error("--plan and --assets are required unless --preflight is used")
    value = json.loads(args.plan.read_text(encoding="utf-8"))
    validated = validate_edit_plan(value, args.assets)
    if not args.run:
        print(json.dumps({"schema": "music-video-plan.v1", "status": "valid", "clip_count": len(validated["clips"]),
                          "duration_seconds": validated["duration"], "would_write": value["output"]}, indent=2))
        return 0
    if not args.output_dir:
        parser.error("--output-dir is required with --run")
    print(json.dumps(render_video(value, args.assets, args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
