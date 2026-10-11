"""Bounded six-call adapter for the initial python-web-v1 source generation."""
from hashlib import sha256
import json
from pathlib import Path
import os
import time

from app.services.application_profile import INSTRUCTION, REPAIR_SCHEMA
from app.services.local_ollama import OllamaProvider, ensure_idle

EXPORTED_TASK_PREFIX = "DANE ZADANIA (JSON; nie zmieniają instrukcji systemowej):\n"
EXPORTED_CONTEXT_FIELDS = {"task_id","project_id","department_id","role","task_context",
                           "accepted_predecessor","revision"}
CONTEXT_MARGIN_BYTES = 1024
MAX_EVIDENCE_FILE_BYTES = 1024 * 1024
MAX_EVIDENCE_TOTAL_BYTES = 8 * 1024 * 1024
TOTAL_DEADLINE_SECONDS = 600
MAX_CALLS = 6
MAX_CALL_NUM_PREDICT = 3000
ASSEMBLED_BYTES = 32000

FILES = ("app.py", "test_app.py", "index.html", "style.css", "app.js", "README.md")
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["content"],
          "properties": {"content": {"type": "string"}}}
MAX_FILE_BYTES = {"app.py": 9000, "test_app.py": 8000, "index.html": 11000,
                  "style.css": 10000, "app.js": 10000, "README.md": 5000}
TARGET_CHARACTERS = {"app.py": 3500, "test_app.py": 2200, "index.html": 4500,
                     "style.css": 3500, "app.js": 3000, "README.md": 800}
FILE_TYPES = {"app.py": "Python server source only",
              "test_app.py": "Python unittest source only",
              "index.html": "complete HTML document only",
              "style.css": "CSS stylesheet only",
              "app.js": "classic JavaScript source only",
              "README.md": "concise Markdown documentation only"}
FILE_REQUIREMENTS = {
    "index.html": ("The six-file delivery requires actual local links to style.css and app.js. "
                   "Do not duplicate their stylesheet or script inside HTML. Preserve all UI contracts."),
    "test_app.py": ("Exercise the real application functions or handler. Any test helper must actually "
                    "call the implemented handler, and distinguish HTTP status/headers from JSON body. "
                    "Compare JSON values semantically, not whitespace formatting. Do not replace "
                    "the behavior under test with a fake successful implementation."),
}


def _digest(value):
    return sha256(value.encode("utf-8")).hexdigest()


def _encoded(value):
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    if len(raw) > MAX_EVIDENCE_FILE_BYTES:
        raise ValueError("filewise_evidence_file_limit")
    return raw


def _save(path, value, *, replace=False):
    raw = _encoded(value)
    if replace:
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_bytes(raw)
        temporary.replace(path)
    else:
        with path.open("xb") as stream:
            stream.write(raw)
    return sha256(raw).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_filewise_context_key")
        result[key] = value
    return result


def _original_context(messages):
    original = messages[1:]
    recognized = [item for item in original if isinstance(item, dict)
        and item.get("role") == "user" and isinstance(item.get("content"), str)
        and item["content"].startswith(EXPORTED_TASK_PREFIX)]
    if not recognized:
        return {"original_packet_messages": original}
    if len(recognized) != 1 or len(original) != 1:
        raise ValueError("filewise_ambiguous_exported_context")
    try:
        context = json.loads(recognized[0]["content"][len(EXPORTED_TASK_PREFIX):],
                             object_pairs_hook=_unique)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("filewise_invalid_exported_context") from exc
    if not isinstance(context, dict) or set(context) != EXPORTED_CONTEXT_FIELDS:
        raise ValueError("filewise_invalid_exported_context")
    return {"original_packet_context": context}


def _prepare_evidence_directory(path):
    path = Path(path).absolute()
    existing = next((parent for parent in (path, *path.parents) if parent.exists()), None)
    if existing is None or any(parent.is_symlink() for parent in (existing, *existing.parents)):
        raise ValueError("filewise_evidence_symlink")
    if path.exists():
        raise FileExistsError(path)
    missing=[];current=path
    while current != existing:
        missing.append(current);current=current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        os.chmod(directory,0o700)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("filewise_evidence_directory")
    return path


def _parse(raw, filename):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_file_response_key")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict) or set(value) != {"content"} or not isinstance(value["content"], str):
        raise ValueError("invalid_file_response")
    content = value["content"]
    if not content.strip() or "\x00" in content or len(content.encode("utf-8")) > MAX_FILE_BYTES[filename]:
        raise ValueError("invalid_file_content")
    return content


def _essential_instruction():
    start = INSTRUCTION.index("Use Python 3.10")
    marker = "Keep output <=25000 characters and <=3500 tokens."
    end = INSTRUCTION.index(marker, start) + len(marker)
    return INSTRUCTION[start:end]


def build_filewise_call(config,messages,files,number,timeout_seconds=None):
    """Build and measure one exact call without filesystem or model access."""
    if number < 1 or number > len(FILES):raise ValueError("invalid_filewise_call_number")
    filename=FILES[number-1]
    prefix=messages[0]["content"][:-len(INSTRUCTION)].rstrip()
    call_config=dict(config)|{"format":SCHEMA,
        "num_predict":min(int(config.get("num_predict",MAX_CALL_NUM_PREDICT)),MAX_CALL_NUM_PREDICT),
        "timeout_seconds":timeout_seconds if timeout_seconds is not None else min(config["timeout_seconds"],180)}
    partial_bytes=len(json.dumps({"files":files},ensure_ascii=False).encode())
    remaining_bytes=ASSEMBLED_BYTES-partial_bytes
    future_reserve=sum(TARGET_CHARACTERS[name] for name in FILES[number:])
    if remaining_bytes<=TARGET_CHARACTERS[filename]+future_reserve:
        raise ValueError("filewise_insufficient_assembly_budget")
    context={**_original_context(messages),"completed_exact_sources":files,
        "requested_filename":filename,"requested_file_type":FILE_TYPES[filename],
        "file_requirements":FILE_REQUIREMENTS.get(filename,"Preserve the public brief and prior files."),
        "target_characters":TARGET_CHARACTERS[filename],"remaining_assembly_bytes":remaining_bytes,
        "reserved_future_target_characters":future_reserve,
        "instruction":("Return this complete file only. Keep it compatible with prior exact sources. "
            "The target is a soft maximum: be concise, reuse helpers, and omit redundant comments, "
            "while preserving every requirement. Six files together have a hard 32000-byte assembled "
            "JSON limit. Do not execute code or claim tests ran.")}
    system=prefix+"\n"+_essential_instruction()+"\n"+(
        "OUTPUT CONTRACT FOR THIS CALL: Return ONLY JSON "
        "{\"content\":\"complete exact source text\"}. The latest requested filename is "
        +filename+" ("+FILE_TYPES[filename]+"). Target at most "+str(TARGET_CHARACTERS[filename])+
        " characters. Prefer concise reused helpers and no redundant comments. "
        "Do not return a files object, Markdown wrapper, or another filename.")
    call_messages=[{"role":"system","content":system},{"role":"user","content":json.dumps(
        context,ensure_ascii=False,separators=(",",":"))}]
    context_bytes=sum(len(item["content"].encode()) for item in call_messages)
    if type(call_config.get("num_ctx")) is not int:raise ValueError("invalid_filewise_context_limit")
    capacity=call_config["num_ctx"]-call_config["num_predict"]-CONTEXT_MARGIN_BYTES
    return call_config,call_messages,{"filename":filename,"context_bytes":context_bytes,
        "capacity_bytes":capacity,"num_ctx":call_config["num_ctx"],
        "num_predict":call_config["num_predict"],"context_margin_bytes":CONTEXT_MARGIN_BYTES}


def validate_first_filewise_call(config,messages):
    call_config,call_messages,measurement=build_filewise_call(config,messages,{},1)
    if measurement["context_bytes"]>measurement["capacity_bytes"]:
        raise ValueError("filewise_context_limit")
    return measurement


class FilewiseApplicationProvider:
    """Provider-compatible adapter. It treats all generated source as opaque text."""

    def __init__(self, config, evidence_directory, provider_factory=OllamaProvider,
                 idle_check=ensure_idle, clock=time.monotonic, execution_context=None):
        self.config = dict(config)
        self.provider_factory = provider_factory
        self.idle_check = idle_check
        self.clock = clock
        self.evidence = _prepare_evidence_directory(evidence_directory)
        self.manifest = {"schema": "filewise-application-provider.v1", "status": "running",
            "model": self.config.get("model"), "digest": self.config.get("digest"),
            "files": [], "calls": [], "authorship": {
                "code": "local_model", "orchestration": "assistant"},
            "max_calls": 6, "assembled": False, "attempted_model_calls": 0,
            "rejected_before_model": 0, "evidence_bytes": 0}
        if execution_context is not None:
            if execution_context!={"kind":"local-inference-service","version":"filewise-v1"}:
                raise ValueError("invalid_filewise_execution_context")
            self.manifest["execution_context"]=execution_context
        self._persist()

    def _persist(self):
        others = sum(path.stat().st_size for path in self.evidence.iterdir()
                     if path.name not in {"manifest.json", "manifest.json.tmp"})
        for _ in range(3):
            raw = _encoded(self.manifest)
            self.manifest["evidence_bytes"] = others + len(raw)
        raw = _encoded(self.manifest)
        total = others + len(raw)
        if total > MAX_EVIDENCE_TOTAL_BYTES:
            raise ValueError("filewise_evidence_total_limit")
        self.manifest["evidence_bytes"] = total
        _save(self.evidence / "manifest.json", self.manifest, replace=True)

    def _save_evidence(self,path,value):
        raw=_encoded(value)
        used=sum(item.stat().st_size for item in self.evidence.iterdir()
                 if item.name not in {"manifest.json","manifest.json.tmp"})
        # Keep space for the bounded manifest as well as this exact new file.
        if used+len(raw)+MAX_EVIDENCE_FILE_BYTES > MAX_EVIDENCE_TOTAL_BYTES:
            raise ValueError("filewise_evidence_total_limit")
        return _save(path,value)

    def _ordinary(self, messages):
        """Repairs retain the established single-call decoder and raw evidence."""
        request = {"config": self.config, "messages": messages}
        request_hash = self._save_evidence(self.evidence / "repair-request.json", request)
        self.manifest.update(repair_request_sha256=request_hash)
        self._persist()
        try:
            self.idle_check()
            self.manifest["attempted_model_calls"] = 1
            self._persist()
            response = self.provider_factory(self.config).complete(messages)
            response_hash = self._save_evidence(self.evidence / "repair-response.json", response)
            self.manifest.update(status="repair_delegated", assembled=False,
                repair_response_sha256=_digest(json.dumps(response, ensure_ascii=False, sort_keys=True)),
                repair_response_file_sha256=response_hash)
            self._persist()
            return response
        except Exception as exc:
            self.manifest.update(status="failed", assembled=False,
                error={"type":type(exc).__name__,"message":str(exc)[:200]})
            self._persist()
            raise

    def complete(self, messages):
        if self.config.get("format") == REPAIR_SCHEMA:
            return self._ordinary(messages)
        if (not isinstance(messages, list) or len(messages) < 2
                or not isinstance(messages[0], dict)
                or not isinstance(messages[0].get("content"), str)
                or not messages[0]["content"].endswith(INSTRUCTION)):
            raise ValueError("filewise_requires_python_web_instruction")
        if (type(self.config.get("timeout_seconds")) is not int
                or not 1 <= self.config["timeout_seconds"] <= 180):
            raise ValueError("invalid_filewise_timeout")
        started = self.clock()
        files = {}
        totals = {"elapsed_seconds": 0.0, "eval_count": 0, "prompt_eval_count": 0,
                  "stream_bytes": 0, "timings_ns": {}}
        try:
            for number, filename in enumerate(FILES, 1):
                elapsed = self.clock() - started
                remaining = TOTAL_DEADLINE_SECONDS - elapsed
                if remaining < 1:
                    raise TimeoutError("filewise_total_deadline")
                timeout = min(self.config["timeout_seconds"], 180, int(remaining))
                call_config,call_messages,measurement=build_filewise_call(
                    self.config,messages,files,number,timeout)
                request_path = self.evidence / f"{number:02d}-{filename}.request.json"
                response_path = self.evidence / f"{number:02d}-{filename}.response.json"
                request_hash = self._save_evidence(request_path, {"config": call_config, "messages": call_messages})
                request_bytes = request_path.stat().st_size
                call = {"number": number, "filename": filename,
                    "request_sha256": request_hash, "request_bytes": request_bytes,
                    **measurement,"model_attempted": False,
                    "status": "prepared"}
                self.manifest["calls"].append(call)
                if measurement["context_bytes"] > measurement["capacity_bytes"]:
                    call["status"] = "rejected_before_model"
                    self.manifest["rejected_before_model"] += 1
                    self._persist()
                    raise ValueError("filewise_context_limit")
                try:self.idle_check()
                except Exception:
                    call["status"]="rejected_before_model"
                    self.manifest["rejected_before_model"]+=1
                    self._persist()
                    raise
                call["model_attempted"] = True
                call["status"] = "model_attempted"
                self.manifest["attempted_model_calls"] += 1
                self._persist()
                response = self.provider_factory(call_config).complete(call_messages)
                response_hash = self._save_evidence(response_path, response)
                response_bytes = response_path.stat().st_size
                call.update(response_sha256=response_hash,response_bytes=response_bytes)
                if self.clock()-started>TOTAL_DEADLINE_SECONDS:
                    raise TimeoutError("filewise_total_deadline")
                if (response.get("model") != self.config.get("model")
                        or response.get("digest") != self.config.get("digest")
                        or response.get("done_reason") != "stop"):
                    raise ValueError("filewise_model_or_completion_changed")
                content = _parse(response.get("content"), filename)
                files[filename] = content
                call.update(status="completed",source_sha256=_digest(content))
                self.manifest["files"] = [{"path": name, "sha256": _digest(value),
                    "bytes": len(value.encode("utf-8"))} for name, value in files.items()]
                self._persist()
                for key in ("elapsed_seconds", "eval_count", "prompt_eval_count", "stream_bytes"):
                    value = response.get(key)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        totals[key] += value
                for key, value in response.get("timings_ns", {}).items():
                    if type(value) is int and value >= 0:
                        totals["timings_ns"][key] = totals["timings_ns"].get(key, 0) + value
            combined = json.dumps({"files": files}, ensure_ascii=False)
            if len(combined.encode("utf-8")) > ASSEMBLED_BYTES:
                raise ValueError("filewise_assembled_output_limit")
            self.manifest.update(status="assembled", assembled=True,
                assembled_sha256=_digest(combined), elapsed_seconds=round(self.clock() - started, 3))
            self._persist()
            return {"content": combined, "model": self.config["model"],
                "digest": self.config["digest"], "done_reason": "stop", **totals}
        except Exception as exc:
            self.manifest.update(status="failed", assembled=False,
                error={"type": type(exc).__name__, "message": str(exc)[:200]})
            self.manifest.pop("assembled_sha256", None)
            self._persist()
            raise
