from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import require_owner
from app.api.organization_os import get_organization_session
from app.services.workspace_exports import WorkspaceStorage, export_package, ExportConflict, ExportMissing, StorageUnavailable
from app.services.workspace_packages import PackageIntegrityError, PackageNotFound

router = APIRouter(prefix="/api", tags=["workspace-exports"], dependencies=[Depends(require_owner)])


def get_workspace_storage():
    return WorkspaceStorage()


def guarded(action, session=None):
    try:
        return action()
    except (PackageNotFound, ExportMissing) as exc:
        raise HTTPException(404, str(exc)) from exc
    except (PackageIntegrityError, ExportConflict) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (StorageUnavailable, OSError) as exc:
        raise HTTPException(503, "Magazyn niedostępny, nieprawidłowy lub przekroczono limit. Sprawdź konfigurację i wolne miejsce.") from exc
    except SQLAlchemyError as exc:
        if session is not None: session.rollback()
        raise HTTPException(503, "Nie zapisano potwierdzenia w bazie. Pliki mogą już istnieć; ponów eksport tej samej paczki.") from exc


@router.get("/workspace-storage")
def storage_status(response: Response, storage: WorkspaceStorage = Depends(get_workspace_storage)):
    response.headers["Cache-Control"] = "no-store"
    return guarded(storage.status)


@router.post("/tasks/{task_id}/workspace-packages/{package_id}/disk-export")
def store_export(task_id: int, package_id: int, response: Response,
                 session: Session = Depends(get_organization_session),
                 storage: WorkspaceStorage = Depends(get_workspace_storage)):
    response.headers["Cache-Control"] = "no-store"
    return guarded(lambda: export_package(session, storage, task_id, package_id), session)


@router.get("/tasks/{task_id}/workspace-packages/{package_id}/disk-export")
def verify_export(task_id: int, package_id: int, response: Response,
                  session: Session = Depends(get_organization_session),
                  storage: WorkspaceStorage = Depends(get_workspace_storage)):
    response.headers["Cache-Control"] = "no-store"
    return guarded(lambda: export_package(session, storage, task_id, package_id, create=False), session)
