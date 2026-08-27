import json

import pytest

from app.services.tool_calling import (
    ToolCallingError,
    execute_model_tool_call,
    parse_model_response,
    run_tool_loop,
)


def test_parse_final_response():
    assert parse_model_response('{"type":"final","content":"gotowe"}') == {
        "type": "final",
        "content": "gotowe",
    }


def test_invalid_json_is_rejected():
    with pytest.raises(ToolCallingError):
        parse_model_response("nie jest json")


def test_unknown_tool_is_rejected():
    with pytest.raises(ToolCallingError):
        execute_model_tool_call({
            "type": "tool_call",
            "name": "delete_file",
            "arguments": {},
        })


def test_invalid_arguments_are_rejected():
    with pytest.raises(ToolCallingError):
        execute_model_tool_call({
            "type": "tool_call",
            "name": "list_project_files",
            "arguments": [],
        })


def test_final_response_ends_loop():
    calls = []

    def model(context):
        calls.append(json.loads(context))
        return {"type": "final", "content": "zakończone"}

    assert run_tool_loop(
        {
            "type": "tool_call",
            "name": "list_project_files",
            "arguments": {"path": "app/tools"},
        },
        model,
    ) == "zakończone"

    assert len(calls) == 1
    assert calls[0]["type"] == "tool_result"


def test_tool_call_limit_is_enforced():
    def model(_context):
        return {
            "type": "tool_call",
            "name": "list_project_files",
            "arguments": {"path": "app/tools"},
        }

    with pytest.raises(ToolCallingError, match="limit"):
        run_tool_loop(
            {
                "type": "tool_call",
                "name": "list_project_files",
                "arguments": {"path": "app/tools"},
            },
            model,
            max_tool_calls=1,
        )


def test_final_requires_string_content():
    with pytest.raises(ToolCallingError):
        run_tool_loop(
            {"type": "final", "content": 123},
            lambda _context: {},
        )
