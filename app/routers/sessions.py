from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_session, require_candidat
from ..models import User, VisitorSession
from ..schemas import LinkOut, SessionInfo, SessionOut
from ..security import new_session_token
from ..services import SessionOwnedError, link_session_to_user

router = APIRouter(prefix="/sessions", tags=["Sessions visiteurs"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(db: Session = Depends(get_db)):
    """Crée une nouvelle session anonyme. Le client conserve le jeton et le transmet via X-Session-Token."""
    token, token_hash = new_session_token()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=settings.session_ttl_hours)
    db.add(VisitorSession(token_hash=token_hash, created_at=now, last_seen_at=now, expires_at=expires))
    db.commit()
    return SessionOut(session_token=token, expires_at=expires)


@router.get("/me", response_model=SessionInfo)
def session_info(vs: VisitorSession = Depends(get_session)):
    """Retourne l'état de la session courante."""
    return SessionInfo(id=vs.id, expires_at=vs.expires_at, linked=vs.user_id is not None)


@router.post("/link", response_model=LinkOut)
def link_session(
    vs: VisitorSession = Depends(get_session),
    user: User = Depends(require_candidat),
    db: Session = Depends(get_db)
):
    """SA-29 : Rattache la session invitée courante (et ses conversations) au candidat connecté.
    L'opération est atomique et concurrente. Une session déjà rattachée à un autre compte lève 409.
    """
    try:
        count = link_session_to_user(db, vs, user)
        return LinkOut(linked_conversations=count)
    except SessionOwnedError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cette session est déjà rattachée à un autre compte"
        )
