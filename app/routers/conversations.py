import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_optional_session, get_optional_user, get_session
from ..models import Conversation, Message, MessageRole, Role, User, VisitorSession
from ..schemas import (ChatResponse, ConversationIn, ConversationOut,
                       MessageIn, MessageOut)
from ..services import link_session_to_user
from ..services_llm import LLMConnectionError, LLMTimeoutError, llm_connector

router = APIRouter(prefix="/conversations", tags=["Conversations"])


def _check_consistent(vs: VisitorSession | None, user: User | None) -> None:
    """Un JWT et un jeton de session appartenant à deux comptes différents sont strictement refusés."""
    if vs and user and vs.user_id is not None and vs.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cette session appartient à un autre compte")


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: ConversationIn,
    vs: VisitorSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Création d'une conversation.
    - Visiteur anonyme : conversation anonyme (user_id = None).
    - Candidat connecté : la session est liée atomiquement si elle était anonyme,
      et la conversation est rattachée au compte candidat.
    - Violation d'invariance : une session d'un tiers est rejetée (403).
    """
    _check_consistent(vs, user)

    if user:
        if user.role != Role.candidat:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Seuls les candidats et visiteurs peuvent créer des conversations")
        # Invariant de possession : si la session n'était pas liée, on la lie atomiquement au candidat
        if vs.user_id is None:
            link_session_to_user(db, vs, user)
        target_user_id = user.id
    else:
        # Visiteur anonyme : refus si la session a déjà été revendiquée par un candidat
        if vs.user_id is not None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Cette session a été rattachée à un compte. Veuillez vous connecter."
            )
        target_user_id = None

    conv = Conversation(
        session_id=vs.id,
        user_id=target_user_id,
        title=body.title
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    limit: int = Query(50, ge=1, le=200, description="Nombre maximal de résultats"),
    offset: int = Query(0, ge=0, description="Décalage pour pagination"),
    vs: VisitorSession | None = Depends(get_optional_session),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Liste les conversations de manière paginée.
    - Candidat connecté : toutes ses conversations rattachées (toutes sessions confondues).
    - Visiteur anonyme : uniquement les conversations anonymes de sa session courante.
    """
    _check_consistent(vs, user)

    if user:
        # Le candidat connecté voit uniquement les conversations lui appartenant
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return db.scalars(stmt).all()

    if vs:
        # Si la session a été liée à un compte, une requête anonyme ne doit plus lister les conversations
        if vs.user_id is not None:
            return []
        stmt = (
            select(Conversation)
            .where(Conversation.session_id == vs.id, Conversation.user_id.is_(None))
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return db.scalars(stmt).all()

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session ou authentification requise")


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: uuid.UUID,
    vs: VisitorSession | None = Depends(get_optional_session),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Récupère une conversation spécifique avec contrôle d'accès strict.
    Retourne 404 si non trouvée ou si l'appelant n'en est pas le propriétaire légitime.
    """
    _check_consistent(vs, user)
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")

    is_owner = False
    if user and conv.user_id == user.id:
        is_owner = True
    elif not user and vs and conv.session_id == vs.id and conv.user_id is None and vs.user_id is None:
        is_owner = True

    if not is_owner:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")

    return conv


# =====================================================================
# SA-26 & SA-36 : Dialogue LLM et Mémoire Conversationnelle
# =====================================================================

@router.post("/{conversation_id}/messages", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: uuid.UUID,
    body: MessageIn,
    vs: VisitorSession | None = Depends(get_optional_session),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Envoie un message utilisateur dans la conversation et génère la réponse du LLM (SA-36).
    Enregistre les messages dans la mémoire conversationnelle (SA-26).
    """
    _check_consistent(vs, user)
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")

    # Vérification des droits d'accès
    is_owner = False
    if user and conv.user_id == user.id:
        is_owner = True
    elif not user and vs and conv.session_id == vs.id and conv.user_id is None and vs.user_id is None:
        is_owner = True

    if not is_owner:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")

    # 1. Enregistrer le message de l'utilisateur
    user_msg = Message(
        conversation_id=conv.id,
        role=MessageRole.user,
        content=body.content
    )
    db.add(user_msg)

    # Si la conversation n'a pas de titre, lui donner les 50 premiers caractères du message
    if not conv.title or conv.title.strip() == "":
        conv.title = body.content[:50].strip()

    db.commit()
    db.refresh(user_msg)

    # 2. Générer la réponse du LLM en injectant le contexte et la mémoire (SA-36)
    try:
        assistant_reply_text = llm_connector.generate_reply(db, conv, body.content)
    except LLMConnectionError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message)
    except LLMTimeoutError as exc:
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message)

    # 3. Enregistrer la réponse de l'assistant dans la mémoire
    assistant_msg = Message(
        conversation_id=conv.id,
        role=MessageRole.assistant,
        content=assistant_reply_text
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatResponse(user_message=user_msg, assistant_message=assistant_msg)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: uuid.UUID,
    vs: VisitorSession | None = Depends(get_optional_session),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Consulte l'historique complet des messages de la conversation (mémoire conversationnelle)."""
    _check_consistent(vs, user)
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")

    is_owner = False
    if user and conv.user_id == user.id:
        is_owner = True
    elif not user and vs and conv.session_id == vs.id and conv.user_id is None and vs.user_id is None:
        is_owner = True

    if not is_owner:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")

    stmt = select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.asc())
    return db.scalars(stmt).all()
