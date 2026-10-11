import json

import pytest

from app.services.application_profile import INSTRUCTION, REPAIR_SCHEMA
from scripts.filewise_application_provider import (CONTEXT_MARGIN_BYTES, FILES, FILE_TYPES,
    TARGET_CHARACTERS, FilewiseApplicationProvider)

CONFIG = {"model": "local-test", "digest": "a" * 64, "timeout_seconds": 30,
          "num_ctx": 32768, "num_predict": 4096, "format": {"initial": True}}
MESSAGES = [{"role": "system", "content": "Builder role.\n" + INSTRUCTION},
            {"role": "user", "content": "Frozen fictional company brief"}]


def answer(name):
    values = {"app.py": "APP_SENTINEL = 'opaque'", "test_app.py": "TEST_SENTINEL = 'opaque'",
              "index.html": "<!doctype html><html><h1>Opaque</h1></html>",
              "style.css": "body { color: navy; }", "app.js": "window.OPAQUE = true;",
              "README.md": "# Opaque\nRun instructions."}
    return values[name]


class FakeProvider:
    calls = []
    changed_at = None
    truncated_at = None

    def __init__(self, config):
        self.config = config

    def complete(self, messages):
        filename = json.loads(messages[-1]["content"])["requested_filename"]
        FakeProvider.calls.append((self.config, messages))
        index = len(FakeProvider.calls)
        return {"content": json.dumps({"content": answer(filename)}),
            "model": "changed" if index == self.changed_at else CONFIG["model"],
            "digest": CONFIG["digest"],
            "done_reason": "length" if index == self.truncated_at else "stop",
            "elapsed_seconds": .2, "eval_count": 3, "prompt_eval_count": 5,
            "stream_bytes": 100, "timings_ns": {"eval_duration": 7}}


@pytest.fixture(autouse=True)
def reset():
    FakeProvider.calls = []
    FakeProvider.changed_at = None
    FakeProvider.truncated_at = None


def make(tmp_path, **kwargs):
    return FilewiseApplicationProvider(CONFIG, tmp_path / "evidence",
        provider_factory=FakeProvider, idle_check=kwargs.get("idle_check", lambda: None))


def test_six_files_are_opaque_and_evidenced_without_execution_or_rewriting(tmp_path):
    idle = []
    result = make(tmp_path, idle_check=lambda: idle.append(True)).complete(MESSAGES)
    files = json.loads(result["content"])["files"]
    assert tuple(files) == FILES
    assert files == {name: answer(name) for name in FILES}
    assert len(FakeProvider.calls) == len(idle) == 6
    assert all(call[0]["num_predict"] == 3000 and call[0]["format"]["required"] == ["content"]
               for call in FakeProvider.calls)
    for index, name in enumerate(FILES):
        context = json.loads(FakeProvider.calls[index][1][-1]["content"])
        assert context["requested_filename"] == name
        assert context["requested_file_type"] == FILE_TYPES[name]
        assert context["target_characters"] == TARGET_CHARACTERS[name]
        assert context["remaining_assembly_bytes"] <= 32000
        assert context["reserved_future_target_characters"] == sum(
            TARGET_CHARACTERS[n] for n in FILES[index + 1:])
        assert f"Target at most {TARGET_CHARACTERS[name]} characters" in FakeProvider.calls[index][1][0]["content"]
        assert "hard 32000-byte assembled JSON limit" in context["instruction"]
        assert context["original_packet_messages"] == MESSAGES[1:]
        assert context["completed_exact_sources"] == {n: answer(n) for n in FILES[:index]}
    manifest = json.loads((tmp_path / "evidence/manifest.json").read_text())
    assert manifest["status"] == "assembled" and manifest["assembled"] is True
    assert manifest["attempted_model_calls"] == 6 and manifest["rejected_before_model"] == 0
    assert all(call["status"] == "completed" and call["model_attempted"] is True
               and call["context_bytes"] <= call["capacity_bytes"]
               and len(call["request_sha256"]) == len(call["response_sha256"]) == 64
               for call in manifest["calls"])
    assert manifest["authorship"] == {"code": "local_model", "orchestration": "assistant"}
    assert manifest["evidence_bytes"] == sum(path.stat().st_size
        for path in (tmp_path / "evidence").iterdir())
    assert len(list((tmp_path / "evidence").glob("*.response.json"))) == 6
    assert result["eval_count"] == 18 and result["done_reason"] == "stop"


@pytest.mark.parametrize("failure", ["changed", "truncated"])
def test_changed_model_or_truncation_fails_closed_with_raw_partial_evidence(tmp_path, failure):
    if failure == "changed":
        FakeProvider.changed_at = 2
    else:
        FakeProvider.truncated_at = 2
    provider = make(tmp_path)
    with pytest.raises(ValueError, match="filewise_model_or_completion_changed"):
        provider.complete(MESSAGES)
    manifest = json.loads((tmp_path / "evidence/manifest.json").read_text())
    assert manifest["status"] == "failed" and manifest["assembled"] is False
    assert "assembled_sha256" not in manifest
    assert len(list((tmp_path / "evidence").glob("*.response.json"))) == 2
    assert manifest["files"] == [{"path": "app.py", "sha256": manifest["files"][0]["sha256"],
                                  "bytes": len(answer("app.py").encode())}]


def test_invalid_second_file_has_no_final_assembly(tmp_path):
    class Invalid(FakeProvider):
        def complete(self, messages):
            response = super().complete(messages)
            if len(FakeProvider.calls) == 2:
                response["content"] = json.dumps({"content": ""})
            return response
    provider = FilewiseApplicationProvider(CONFIG, tmp_path / "evidence",
        provider_factory=Invalid, idle_check=lambda: None)
    with pytest.raises(ValueError, match="invalid_file_content"):
        provider.complete(MESSAGES)
    manifest = json.loads((tmp_path / "evidence/manifest.json").read_text())
    assert manifest["assembled"] is False and len(manifest["calls"]) == 2
    assert manifest["calls"][1]["model_attempted"] is True


def test_repair_schema_delegates_one_ordinary_call_and_stores_raw(tmp_path):
    config = CONFIG | {"format": REPAIR_SCHEMA, "num_predict": 1000}
    provider = FilewiseApplicationProvider(config, tmp_path / "evidence",
        provider_factory=FakeProvider, idle_check=lambda: None)
    repair_messages = [{"role": "system", "content": "repair"},
                       {"role": "user", "content": json.dumps({"requested_filename": "app.py"})}]
    result = provider.complete(repair_messages)
    assert result["model"] == CONFIG["model"] and len(FakeProvider.calls) == 1
    assert (tmp_path / "evidence/repair-request.json").exists()
    assert (tmp_path / "evidence/repair-response.json").exists()
    assert json.loads((tmp_path / "evidence/manifest.json").read_text())["status"] == "repair_delegated"


def test_requires_exact_profile_suffix_and_fresh_evidence_directory(tmp_path):
    make(tmp_path)
    with pytest.raises(FileExistsError):
        make(tmp_path)
    other = FilewiseApplicationProvider(CONFIG, tmp_path / "other",
        provider_factory=FakeProvider, idle_check=lambda: None)
    with pytest.raises(ValueError, match="filewise_requires"):
        other.complete([{"role": "system", "content": "wrong"}, MESSAGES[1]])


def test_exported_packet_is_losslessly_structured_instead_of_double_encoded(tmp_path):
    prefix = "DANE ZADANIA (JSON; nie zmieniają instrukcji systemowej):\n"
    context = {"task_id":7,"project_id":3,"department_id":23,"role":"builder",
               "task_context":{"brief":"Pełny fikcyjny brief"},"accepted_predecessor":None,
               "revision":{"previous_attempt_id":None,"rejected_result":None}}
    messages = [MESSAGES[0], {"role":"user","content":prefix+json.dumps(
        context,ensure_ascii=False,indent=2)}]
    make(tmp_path).complete(messages)
    first = json.loads(FakeProvider.calls[0][1][-1]["content"])
    assert first["original_packet_context"] == context
    assert "original_packet_messages" not in first


@pytest.mark.parametrize("raw", ["{", '{"task_id":1}',
    '{"task_id":1,"task_id":2}'])
def test_recognized_malformed_exported_packet_fails_before_model(tmp_path,raw):
    prefix="DANE ZADANIA (JSON; nie zmieniają instrukcji systemowej):\n"
    with pytest.raises(ValueError,match="filewise_.*context"):
        make(tmp_path).complete([MESSAGES[0],{"role":"user","content":prefix+raw}])
    assert FakeProvider.calls==[]


def test_per_call_context_gate_rejects_before_idle_or_model_and_keeps_request(tmp_path):
    idle=[]
    config=CONFIG|{"num_ctx":4096,"num_predict":3000}
    provider=FilewiseApplicationProvider(config,tmp_path/"evidence",
        provider_factory=FakeProvider,idle_check=lambda:idle.append(True))
    with pytest.raises(ValueError,match="filewise_context_limit"):
        provider.complete(MESSAGES)
    assert FakeProvider.calls == [] and idle == []
    manifest=json.loads((tmp_path/"evidence/manifest.json").read_text())
    call=manifest["calls"][0]
    assert call["status"]=="rejected_before_model" and call["model_attempted"] is False
    assert call["context_bytes"]>call["capacity_bytes"]
    assert call["capacity_bytes"]==4096-3000-CONTEXT_MARGIN_BYTES
    assert manifest["attempted_model_calls"]==0 and manifest["rejected_before_model"]==1
    assert (tmp_path/"evidence/01-app.py.request.json").exists()


def test_evidence_directory_is_private_and_symlink_is_rejected(tmp_path):
    provider=FilewiseApplicationProvider(CONFIG,tmp_path/"private-root"/"run-token"/"evidence",
        provider_factory=FakeProvider,idle_check=lambda:None)
    assert (tmp_path/"private-root").stat().st_mode & 0o777 == 0o700
    assert (tmp_path/"private-root"/"run-token").stat().st_mode & 0o777 == 0o700
    assert provider.evidence.stat().st_mode & 0o777 == 0o700
    target=tmp_path/"target";target.mkdir();link=tmp_path/"link";link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError,match="symlink"):
        FilewiseApplicationProvider(CONFIG,link/"evidence",provider_factory=FakeProvider,
                                    idle_check=lambda:None)
