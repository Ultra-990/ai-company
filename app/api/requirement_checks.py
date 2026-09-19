from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.agent_packets import write
from app.api.organization_os import get_organization_session
from app.services import requirement_checks as service

router = APIRouter(prefix='/api/tasks', tags=['requirement-checks'], dependencies=[Depends(require_owner)])


class Check(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    criterion_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    source_checksum: str = Field(pattern=r'^[a-f0-9]{64}$')
    scope_checksum: str = Field(pattern=r'^[a-f0-9]{64}$')
    previous_id: int | None = Field(default=None, ge=1, strict=True)
    state: Literal['passed', 'failed', 'not_checked']
    observed_result: str = Field(min_length=10, max_length=2000)
    test_report_id: int | None = Field(default=None, ge=1, strict=True)
    confirm_observation: bool = Field(strict=True)

    @field_validator('confirm_observation')
    @classmethod
    def confirmed(cls, value):
        if value is not True:
            raise ValueError('Potwierdź zapis własnej obserwacji.')
        return value

    @field_validator('observed_result')
    @classmethod
    def valid_text(cls, value):
        value.encode('utf-8')
        if '\x00' in value:
            raise ValueError('Niedozwolony znak NUL.')
        return value


@router.get('/{task_id}/workspace-packages/{package_id}/requirements')
def get_matrix(task_id: int, package_id: int, response: Response,
               session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control'] = 'no-store'
    try:
        return service.matrix(session, task_id, package_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503, 'Nie można odczytać weryfikacji wymagań.') from exc


@router.post('/{task_id}/workspace-packages/{package_id}/requirements')
def record(task_id: int, package_id: int, payload: Check, response: Response,
           session: Session = Depends(get_organization_session)):
    return write(session, response, lambda: service.save(session, task_id, package_id,
        payload.model_dump(exclude={'confirm_observation'})))


@router.get('/{task_id}/workspace-packages/{package_id}/requirements/{criterion_id}/history')
def history(task_id: int, package_id: int, criterion_id: str, response: Response,
            before: int | None = Query(default=None, ge=1),
            session: Session = Depends(get_organization_session)):
    response.headers['Cache-Control'] = 'no-store'
    try:
        return service.history(session, task_id, package_id, criterion_id, before)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503, 'Nie można odczytać historii weryfikacji.') from exc
