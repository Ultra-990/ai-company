"""Bounded six-call adapter for the initial python-web-v1 source generation."""
from hashlib import sha256
import json
from pathlib import Path
import time

from app.services.application_profile import INSTRUCTION, REPAIR_SCHEMA
from app.services.local_ollama import OllamaProvider, ensure_idle

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


def _save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


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


class FilewiseApplicationProvider:
    """Provider-compatible adapter. It treats all generated source as opaque text."""

    def __init__(self, config, evidence_directory, provider_factory=OllamaProvider,
                 idle_check=ensure_idle, clock=time.monotonic):
        self.config = dict(config)
        self.provider_factory = provider_factory
        self.idle_check = idle_check
        self.clock = clock
        self.evidence = Path(evidence_directory)
        self.evidence.mkdir(parents=True, exist_ok=False)
        self.manifest = {"schema": "filewise-application-provider.v1", "status": "running",
            "model": self.config.get("model"), "digest": self.config.get("digest"),
            "files": [], "calls": [], "authorship": {
                "code": "local_model", "orchestration": "assistant"},
            "max_calls": 6, "assembled": False}
        self._persist()

    def _persist(self):
        _save(self.evidence / "manifest.json", self.manifest)

    def _ordinary(self, messages):
        """Repairs retain the established single-call decoder and raw evidence."""
        self.idle_check()
        request = {"config": self.config, "messages": messages}
        _save(self.evidence / "repair-request.json", request)
        response = self.provider_factory(self.config).complete(messages)
        _save(self.evidence / "repair-response.json", response)
        self.manifest.update(status="repair_delegated", assembled=False,
            repair_response_sha256=_digest(json.dumps(response, ensure_ascii=False, sort_keys=True)))
        self._persist()
        return response

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
        prefix = messages[0]["content"][:-len(INSTRUCTION)].rstrip()
        original = messages[1:]
        started = self.clock()
        files = {}
        totals = {"elapsed_seconds": 0.0, "eval_count": 0, "prompt_eval_count": 0,
                  "stream_bytes": 0, "timings_ns": {}}
        try:
            for number, filename in enumerate(FILES, 1):
                elapsed = self.clock() - started
                remaining = 600 - elapsed
                if remaining < 1:
                    raise TimeoutError("filewise_total_deadline")
                timeout = min(self.config["timeout_seconds"], 180, int(remaining))
                call_config = self.config | {"format": SCHEMA,
                    "num_predict": min(int(self.config.get("num_predict", 3000)), 3000),
                    "timeout_seconds": timeout}
                partial_bytes = len(json.dumps({"files": files}, ensure_ascii=False).encode("utf-8"))
                remaining_bytes = 32000 - partial_bytes
                future_reserve = sum(TARGET_CHARACTERS[name] for name in FILES[number:])
                if remaining_bytes <= TARGET_CHARACTERS[filename] + future_reserve:
                    raise ValueError("filewise_insufficient_assembly_budget")
                context = {"original_packet_messages": original, "completed_exact_sources": files,
                    "requested_filename": filename,
                    "requested_file_type": FILE_TYPES[filename],
                    "file_requirements": FILE_REQUIREMENTS.get(filename, "Preserve the public brief and prior files."),
                    "target_characters": TARGET_CHARACTERS[filename],
                    "remaining_assembly_bytes": remaining_bytes,
                    "reserved_future_target_characters": future_reserve,
                    "instruction": ("Return this complete file only. Keep it compatible with prior exact sources. "
                        "The target is a soft maximum: be concise, reuse helpers, and omit redundant comments, "
                        "while preserving every requirement. Six files together have a hard 32000-byte assembled "
                        "JSON limit. Do not execute code or claim tests ran.")}
                system = prefix + "\n" + _essential_instruction() + "\n" + (
                    "OUTPUT CONTRACT FOR THIS CALL: Return ONLY JSON "
                    "{\"content\":\"complete exact source text\"}. The latest requested filename is "
                    + filename + " (" + FILE_TYPES[filename] + "). Target at most "
                    + str(TARGET_CHARACTERS[filename]) +
                    " characters. Prefer concise reused helpers and no redundant comments. "
                    "Do not return a files object, Markdown wrapper, or another filename.")
                call_messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
                request_path = self.evidence / f"{number:02d}-{filename}.request.json"
                response_path = self.evidence / f"{number:02d}-{filename}.response.json"
                _save(request_path, {"config": call_config, "messages": call_messages})
                self.idle_check()
                response = self.provider_factory(call_config).complete(call_messages)
                _save(response_path, response)
                if (response.get("model") != self.config.get("model")
                        or response.get("digest") != self.config.get("digest")
                        or response.get("done_reason") != "stop"):
                    raise ValueError("filewise_model_or_completion_changed")
                content = _parse(response.get("content"), filename)
                files[filename] = content
                self.manifest["calls"].append({"number": number, "filename": filename,
                    "request_sha256": sha256(request_path.read_bytes()).hexdigest(),
                    "response_sha256": sha256(response_path.read_bytes()).hexdigest(),
                    "source_sha256": _digest(content)})
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
            if len(combined.encode("utf-8")) > 32000:
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
