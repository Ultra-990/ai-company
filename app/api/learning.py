"""Owner-only observation; reading status never starts models or training."""
from fastapi import APIRouter, Depends, HTTPException, Response
from app.api.auth import require_owner
from app.services.learning_status import status

router = APIRouter(prefix='/api/learning', tags=['learning'], dependencies=[Depends(require_owner)])


@router.get('/status')
def get_status(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    try: return status()
    except ValueError as exc: raise HTTPException(503, str(exc)) from exc
