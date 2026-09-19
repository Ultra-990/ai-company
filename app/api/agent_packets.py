"""Owner-only handoff preparation and external-result intake. No executor endpoint."""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.services.agent_packets import prepare_packet, read_packet, import_result, export_prompt

router = APIRouter(prefix="/api/tasks", tags=["agent-handoff"], dependencies=[Depends(require_owner)])


class ExternalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    packet_id: int = Field(ge=1)
    packet_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_content: str = Field(min_length=1, max_length=32000)
    source_note: str = Field(min_length=1, max_length=1000)

    @field_validator("result_content", "source_note")
    @classmethod
    def valid_text(cls, value):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("Nieprawidłowy tekst UTF-8.") from exc
        if "\x00" in value:
            raise ValueError("Tekst nie może zawierać NUL.")
        return value


def write(session, response, operation):
    response.headers["Cache-Control"] = "no-store"
    try:
        session.execute(text("BEGIN IMMEDIATE"))
        result = operation()
        session.commit()
        return result
    except LookupError as exc:
        session.rollback()
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, "Niepewny wynik zapisu. Odśwież; identyczne ponowienie nie tworzy duplikatu.") from exc


@router.post("/{task_id}/agent-packet")
def prepare(task_id: int, response: Response, session: Session = Depends(get_organization_session)):
    return write(session, response, lambda: read_packet(session, task_id, prepare_packet(session, task_id).id))


@router.get("/{task_id}/agent-packets/{packet_id}")
def get_packet(task_id: int, packet_id: int, response: Response, session: Session = Depends(get_organization_session)):
    response.headers["Cache-Control"] = "no-store"
    try:
        return read_packet(session, task_id, packet_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{task_id}/agent-results")
def submit(task_id: int, payload: ExternalResult, response: Response, session: Session = Depends(get_organization_session)):
    return write(session, response, lambda: import_result(session, task_id, **payload.model_dump()))


@router.get("/{task_id}/agent-packets/{packet_id}/prompt")
def get_prompt(task_id: int, packet_id: int, response: Response, session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control'] = 'no-store'
    try:
        return export_prompt(session, task_id, packet_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
