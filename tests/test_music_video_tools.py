import json
from pathlib import Path
import subprocess
import wave

from PIL import Image
import pytest

from app.services.music_video_tools import (
    ComfyMusicAdapter, MediaToolError, MusicRequest, ace_step_v1_graph, build_ffmpeg_command,
    ffmpeg_preflight, render_video, validate_edit_plan,
)
from scripts import music_video_tools as cli


def assets(tmp_path: Path):
    root = tmp_path / "assets"; root.mkdir()
    Image.new("RGB", (80, 50), (40, 80, 160)).save(root / "one.png")
    with wave.open(str(root / "music.wav"), "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000)
        wav.writeframes(b"\0\0" * 8000)
    return root


def plan():
    return {"clips": [{"file": "one.png", "duration_seconds": 0.5}], "audio": "music.wav",
            "output": "result.mp4", "width": 640, "height": 360, "fps": 24}


def test_music_contract_is_bounded_and_unverified_profile_cannot_execute():
    request = MusicRequest.from_dict({"prompt": "Instrumental ambient pulse", "duration_seconds": 30, "seed": 7})
    def incomplete(path):
        if path == "/queue": return {"queue_running": [], "queue_pending": []}
        if path == "/system_stats": return {"system": {"comfyui_version": "0.35.0"}}
        return {}
    adapter = ComfyMusicAdapter(incomplete)
    preflight = adapter.preflight()
    assert preflight["generation_ready"] is False and preflight["checkpoint_present"] is False
    assert "KSampler" in preflight["missing_nodes"]
    with pytest.raises(MediaToolError, match="not_verified"):
        adapter.workflow("stable-audio", request)
    for invalid in [
        None,
        {"prompt": "x", "duration_seconds": 0, "seed": 1},
        {"prompt": "x", "duration_seconds": 5, "seed": -1},
        {"prompt": "x", "duration_seconds": 5, "seed": 1, "workflow": {}},
    ]:
        with pytest.raises(MediaToolError): MusicRequest.from_dict(invalid)


def test_official_native_ace_profile_requires_all_nodes_and_checkpoint():
    def request(path):
        if path == "/queue": return {"queue_running": [], "queue_pending": []}
        if path == "/system_stats": return {"system": {"comfyui_version": "0.35.0"}}
        name = path.rsplit("/", 1)[-1]
        value = {name: {}}
        if name == "CheckpointLoaderSimple":
            value[name] = {"input": {"required": {"ckpt_name": [[ComfyMusicAdapter.CHECKPOINT]]}}}
        return value
    preflight = ComfyMusicAdapter(request).preflight()
    assert preflight["generation_ready"] is True
    assert preflight["requirements_ready"] is True and preflight["pilot_verified"] is False


def test_ace_graph_is_fixed_native_profile_with_bounded_request_only():
    request = MusicRequest.from_dict({"prompt": "Warm analog ambient, no vocals", "duration_seconds": 12, "seed": 42})
    graph = ace_step_v1_graph(request)
    assert {node["class_type"] for node in graph.values()} == set(ComfyMusicAdapter.REQUIRED_NODES)
    assert graph["1"]["inputs"]["ckpt_name"] == ComfyMusicAdapter.CHECKPOINT
    assert graph["4"]["inputs"] == {"seconds": 12.0, "batch_size": 1}
    assert graph["8"]["inputs"]["seed"] == 42
    assert graph["8"]["inputs"]["steps"] == 50 and graph["8"]["inputs"]["sampler_name"] == "euler"
    assert graph["10"]["inputs"]["filename_prefix"].startswith("AI-Company/")
    assert all("url" not in node["inputs"] and "path" not in node["inputs"] for node in graph.values())


def test_music_request_instrumental_backcompat_and_bounded_lyrics():
    instrumental=MusicRequest.from_dict({'prompt':'techno','duration_seconds':60,'seed':3})
    assert instrumental.lyrics=='[instrumental]\n'
    vocal=MusicRequest.from_dict({'prompt':'techno','duration_seconds':60,'seed':3,'lyrics':'[verse]\nRevolution'})
    assert ace_step_v1_graph(vocal)['2']['inputs']['lyrics']=='[verse]\nRevolution\n'
    for lyrics in (None,'','x'*(16*1024+1),'bad\x00text'):
        with pytest.raises(MediaToolError,match='lyrics'):
            MusicRequest.from_dict({'prompt':'techno','duration_seconds':60,'seed':3,'lyrics':lyrics})


def test_plan_rejects_escape_unknown_fields_and_unbounded_values(tmp_path):
    root = assets(tmp_path)
    assert validate_edit_plan(plan(), root)["duration"] == 0.5
    bad = plan(); bad["clips"][0]["file"] = "../one.png"
    with pytest.raises(MediaToolError, match="asset_path"): validate_edit_plan(bad, root)
    bad = plan(); bad["command"] = "anything"
    with pytest.raises(MediaToolError, match="fields"): validate_edit_plan(bad, root)
    bad = plan(); bad["clips"] *= 513
    with pytest.raises(MediaToolError, match="clips"): validate_edit_plan(bad, root)
    for malformed in (None, [], [{}]):
        with pytest.raises(MediaToolError, match="edit_plan_fields"):
            validate_edit_plan(malformed, root)


def test_command_has_fixed_codecs_filters_and_no_shell(tmp_path):
    root = assets(tmp_path); checked = validate_edit_plan(plan(), root)
    command = build_ffmpeg_command(checked, tmp_path / "out" / "result.mp4")
    assert isinstance(command, list) and command[0] == "ffmpeg"
    assert "-nostdin" in command and "libx264" in command and "aac" in command
    assert "-n" in command and "-y" not in command and command.count("file,pipe") == 2
    assert command.count("-f") >= 2 and command.count("-threads") == 3
    assert "-pattern_type" in command and command[command.index("-pattern_type") + 1] == "none"
    assert "concat=n=1:v=1:a=0" in command[command.index("-filter_complex") + 1]


def test_dry_run_validates_without_ffmpeg_or_writes(tmp_path, monkeypatch, capsys):
    root = assets(tmp_path); source = tmp_path / "plan.json"
    source.write_text(json.dumps(plan()))
    monkeypatch.setattr(cli, "render_video", lambda *a, **k: pytest.fail("dry run rendered"))
    assert cli.main(["--plan", str(source), "--assets", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "valid"
    assert not (tmp_path / "result.mp4").exists()


def test_real_cpu_ffmpeg_renders_small_verified_mp4(tmp_path):
    if not ffmpeg_preflight()["ready"]:
        pytest.skip("required FFmpeg capabilities unavailable")
    root = assets(tmp_path); output = tmp_path / "output"
    report = render_video(plan(), root, output)
    rendered = output / "result.mp4"
    assert report["status"] == "rendered" and report["published"] is False
    assert rendered.stat().st_size > 1000 and len(report["sha256"]) == 64
    assert rendered.stat().st_mode & 0o777 == 0o600
    assert output.stat().st_mode & 0o777 == 0o700
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                            "-of", "json", str(rendered)], capture_output=True, text=True, check=True)
    assert {item["codec_type"] for item in json.loads(probe.stdout)["streams"]} == {"video", "audio"}


def test_failed_render_removes_partial_output(tmp_path):
    root = assets(tmp_path); output = tmp_path / "output"
    def fake_run(command, **kwargs):
        if "-filters" in command:
            return subprocess.CompletedProcess(command, 0, "concat scale pad fps atrim", "")
        if "-encoders" in command:
            return subprocess.CompletedProcess(command, 0, "libx264 aac", "")
        if "-version" in command:
            return subprocess.CompletedProcess(command, 0, "ffmpeg test", "")
        Path(command[-1]).write_bytes(b"partial")
        return subprocess.CompletedProcess(command, 1, b"", b"private failure")
    with pytest.raises(MediaToolError, match="render_failed"):
        render_video(plan(), root, output, fake_run)
    assert not (output / "result.mp4").exists()
    assert not list(output.glob(".music-video-*"))


def test_timeout_cleans_private_partial_and_never_touches_destination(tmp_path):
    root = assets(tmp_path); output = tmp_path / "output"
    def fake_run(command, **kwargs):
        if "-filters" in command:
            return subprocess.CompletedProcess(command, 0, "concat scale pad fps atrim", "")
        if "-encoders" in command:
            return subprocess.CompletedProcess(command, 0, "libx264 aac", "")
        if "-version" in command:
            return subprocess.CompletedProcess(command, 0, "ffmpeg test", "")
        Path(command[-1]).write_bytes(b"partial")
        raise subprocess.TimeoutExpired(command, 600)
    with pytest.raises(MediaToolError, match="render_timeout"):
        render_video(plan(), root, output, fake_run)
    assert not (output / "result.mp4").exists() and not list(output.glob(".music-video-*"))


def test_atomic_publish_refuses_racing_existing_output(tmp_path, monkeypatch):
    root = assets(tmp_path); output = tmp_path / "output"; output.mkdir()
    destination = output / "result.mp4"; destination.write_bytes(b"keep")
    monkeypatch.setattr("app.services.music_video_tools.ffmpeg_preflight", lambda run: {"ready": True})
    def fake_run(command, **kwargs):
        Path(command[-1]).write_bytes(b"render")
        return subprocess.CompletedProcess(command, 0, "", "")
    monkeypatch.setattr("app.services.music_video_tools.probe_render",
                        lambda path, run: {"duration_seconds": .5, "stream_types": ["audio", "video"], "width": 640, "height": 360, "fps": 24})
    with pytest.raises(MediaToolError, match="output_exists"):
        render_video(plan(), root, output, fake_run)
    assert destination.read_bytes() == b"keep" and not list(output.glob(".music-video-*"))


def test_output_directory_symlink_is_rejected(tmp_path):
    root = assets(tmp_path); actual = tmp_path / "actual"; actual.mkdir()
    link = tmp_path / "link"; link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(MediaToolError, match="output_directory"):
        render_video(plan(), root, link)


def test_total_duration_is_bounded(tmp_path):
    root = assets(tmp_path); value = plan()
    value["clips"] = [{"file": "one.png", "duration_seconds": 60}] * 16
    with pytest.raises(MediaToolError, match="total_duration"):
        validate_edit_plan(value, root)


def test_video_dimensions_and_fps_require_real_integers(tmp_path):
    root = assets(tmp_path)
    for field in ("width", "height", "fps"):
        value = plan(); value[field] = float(value[field])
        with pytest.raises(MediaToolError, match="video_format"):
            validate_edit_plan(value, root)


@pytest.mark.parametrize('dimensions',[(640,360),(360,640)])
def test_many_segments_use_bounded_sequential_renderer_and_keep_format(tmp_path,dimensions):
    root=assets(tmp_path);value=plan()
    value.update(width=dimensions[0],height=dimensions[1],clips=[{'file':'one.png','duration_seconds':.125}]*9)
    # Longer sound prevents an accidentally short audio fixture hiding coverage.
    with wave.open(str(root/'music.wav'),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(8000);wav.writeframes(b'\0\0'*16000)
    commands=[]
    def run(command,**kwargs):
        commands.append(command)
        return subprocess.run(command,**kwargs)
    report=render_video(value,root,tmp_path/'output',run)
    assert (report['width'],report['height'],report['fps'])==(*dimensions,24)
    assert abs(report['duration_seconds']-1.125)<.1
    assert all(c.count('-i')<=2 for c in commands)
    assert report['size_bytes']>0


@pytest.mark.parametrize('dimensions',[(2560,1440),(1440,2560),(3840,2160),(2160,3840)])
def test_high_resolution_uses_sequential_decoding_even_for_short_preview(tmp_path,monkeypatch,dimensions):
    from app.services import music_video_tools as media
    root=assets(tmp_path);value=plan();value.update(width=dimensions[0],height=dimensions[1])
    selected=[]
    def sequential(plan,temporary,staged,run):
        selected.append((plan['width'],plan['height']));staged.write_bytes(b'render')
        return subprocess.CompletedProcess([],0)
    monkeypatch.setattr(media,'ffmpeg_preflight',lambda run:{'ready':True})
    monkeypatch.setattr(media,'render_sequential',sequential)
    monkeypatch.setattr(media,'probe_render',lambda *a:{'duration_seconds':.5,'stream_types':['audio','video'],'width':dimensions[0],'height':dimensions[1],'fps':24})
    receipt=render_video(value,root,tmp_path/'output')
    assert selected==[dimensions] and (receipt['width'],receipt['height'])==dimensions
