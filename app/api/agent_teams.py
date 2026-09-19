"""Owner-controlled configuration, never execution authorization."""
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.services.agent_teams import initialize_teams, roster, department_work

router = APIRouter(prefix="/api/agent-teams", tags=["agent-teams"], dependencies=[Depends(require_owner)])


@router.get("")
def get_teams(response: Response, session: Session = Depends(get_organization_session)):
    response.headers["Cache-Control"] = "no-store"
    return roster(session)


@router.post("/initialize")
def prepare_teams(response: Response, session: Session = Depends(get_organization_session)):
    response.headers["Cache-Control"] = "no-store"
    try:
        session.execute(text("BEGIN IMMEDIATE"))
        created = initialize_teams(session)
        session.commit()
        return {**roster(session), "created": created}
    except ValueError as exc:
        session.rollback()
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, "Niepewny wynik konfiguracji. Odśwież zespoły; ponowienie jest idempotentne.") from exc


@router.get('/{department_id}/work')
def get_department_work(department_id:int,response:Response,before:int|None=Query(default=None,ge=1),
                        session:Session=Depends(get_organization_session)):
    response.headers['Cache-Control']='no-store'
    try:return department_work(session,department_id,before)
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
