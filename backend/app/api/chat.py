from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from app.config import Settings, get_settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import LLMError, LLMService
from app.services.memory import ConversationMemory

router = APIRouter(prefix="/chat", tags=["chat"])


def get_memory(request: Request) -> ConversationMemory:
    return request.app.state.memory


def get_llm(request: Request) -> LLMService:
    return request.app.state.llm


@router.post("/messages", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    memory: ConversationMemory = Depends(get_memory),
    llm: LLMService = Depends(get_llm),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    conv_id = body.conversation_id or str(uuid4())
    history = memory.get_history(conv_id, settings.llm_max_history)
    try:
        reply = await llm.chat(history, body.message)
    except LLMError:
        raise HTTPException(status_code=502,
                            detail="Le service LLM est indisponible")
    memory.append(conv_id, "user", body.message)
    memory.append(conv_id, "assistant", reply)
    return ChatResponse(conversation_id=conv_id, reply=reply, model=llm.model)


@router.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: str,
    memory: ConversationMemory = Depends(get_memory),
    settings: Settings = Depends(get_settings),
) -> list[dict]:
    return memory.get_history(conversation_id, settings.llm_max_history)
