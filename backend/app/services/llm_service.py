import httpx
from app.config import Settings

SYSTEM_PROMPT = (
    "Tu es l'assistant d'orientation SmartCampus AI de l'IIT et de l'ISB. "
    "Aide les futurs etudiants a choisir un parcours (Licence, Preparatoire, "
    "Ingenierie, formations ISB) a partir des seules informations officielles "
    "fournies. Comprends le francais, le dialecte tunisien et l'Arabizi "
    "(ex: 'chnowa el conditions mta3 el inscription ?') et reponds dans la "
    "langue du candidat. Propose plusieurs options sans imposer de choix. "
    "Les decisions officielles (admission, inscription) sont validees par un "
    "humain. Si tu ne sais pas, dis-le clairement."
)


class LLMError(Exception):
    """Erreur de communication ou reponse invalide du fournisseur LLM."""


class LLMService:
    def __init__(self, settings: Settings,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._s = settings
        self._transport = transport

    @property
    def model(self) -> str:
        return self._s.llm_model

    async def chat(self, history: list[dict], user_message: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": user_message},
        ]
        payload = {"model": self._s.llm_model, "messages": messages,
                   "temperature": 0.3}
        headers = {"Authorization": f"Bearer {self._s.llm_api_key}"}
        try:
            async with httpx.AsyncClient(
                base_url=self._s.llm_base_url,
                timeout=self._s.llm_timeout_s,
                transport=self._transport,
            ) as client:
                resp = await client.post("/chat/completions",
                                         json=payload, headers=headers)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Appel LLM en echec : {exc}") from exc
        try:
            return resp.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError, AttributeError) as exc:
            raise LLMError("Reponse LLM invalide") from exc
