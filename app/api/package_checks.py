"""Static analysis only; owner-authorized, never a shell/runner endpoint."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.services.package_checks import create_check, read_check
from app.services.workspace_packages import PackageIntegrityError, PackageNotFound

router = APIRouter(prefix="/api/tasks", tags=["package-checks"], dependencies=[Depends(require_owner)])


def checked(action, session):
    try:
        return action()
    except PackageNotFound as exc:
        session.rollback()
        raise HTTPException(404, str(exc)) from exc
    except PackageIntegrityError as exc:
        session.rollback()
        raise HTTPException(409, str(exc)) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(503, "Raport niedostępny. Przed ponowieniem zapisu sprawdź artefakty zadania.") from exc


@router.post("/{task_id}/workspace-packages/{package_id}/static-check", status_code=201)
def inspect_package(task_id: int, package_id: int, response: Response,
                    session: Session = Depends(get_organization_session)):
    response.headers["Cache-Control"] = "no-store"
    def run():
        artifact = create_check(session, task_id, package_id)
        return read_check(session, task_id, artifact.id)
    return checked(run, session)


@router.get("/{task_id}/static-checks/{report_id}")
def get_check(task_id: int, report_id: int, response: Response,
              session: Session = Depends(get_organization_session)):
    response.headers["Cache-Control"] = "no-store"
    return checked(lambda: read_check(session, task_id, report_id), session)
