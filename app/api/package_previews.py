"""Owner-authenticated JSON only: never host source HTML under the owner's origin."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.services.package_previews import PreviewUnavailable, read_preview
from app.services.workspace_packages import PackageIntegrityError, PackageNotFound

router = APIRouter(prefix="/api/tasks", tags=["package-previews"], dependencies=[Depends(require_owner)])


@router.get("/{task_id}/workspace-packages/{package_id}/preview")
def get_preview(task_id: int, package_id: int, response: Response,
                session: Session = Depends(get_organization_session)):
    response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
    try:
        return read_preview(session, task_id, package_id)
    except PackageNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except PackageIntegrityError as exc:
        raise HTTPException(409, str(exc)) from exc
    except PreviewUnavailable as exc:
        raise HTTPException(422, str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Podgląd jest chwilowo niedostępny.") from exc
