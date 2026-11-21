from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, health
from app.config import get_settings
from app.services.llm_service import LLMService
from app.services.memory import InMemoryConversationMemory


def create_app(llm: LLMService | None = None, memory=None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["*"], allow_headers=["*"])
    app.state.llm = llm or LLMService(settings)
    app.state.memory = memory or InMemoryConversationMemory()
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(chat.router, prefix=settings.api_prefix)
    return app


app = create_app()
