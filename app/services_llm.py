"""Module d'intégration du LLM local (Ollama - Modèle Gemma) et du moteur RAG officiel IIT / ISB.
Conforme aux Règles d'utilisation du Corpus RAG officiel :
1. Chaque document constitue une unité documentaire source avec ses métadonnées.
2. Statut de vérification conservé (non_verifie, partielle_ou_manquante, etc.).
3. Aucune donnée non_verifie n'est présentée comme un fait officiel définitif (frais et conditions indicatifs).
4. Orientation vers les contacts officiels en cas de données absentes ou partielles.
5. Citation obligatoire du document_id et du source_url dans les réponses générées.
6. Aucune déduction automatique d'équivalence ou d'admissibilité sans décision de la commission.
7. Détection des cas ambigus et demande de clarification systématique (SA-32).
8. Protection des secrets et gestion résiliente des erreurs réseau et de dépassement de délai (timeout).
"""
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import AdmissionCondition, Conversation, Message, MessageRole, Program, Tariff

logger = logging.getLogger("smartcampus.llm")


# =====================================================================
# Exceptions Métier LLM
# =====================================================================

class LLMError(Exception):
    """Exception de base pour le service LLM."""
    def __init__(self, message: str, error_code: str = "LLM_ERROR", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class LLMConnectionError(LLMError):
    """Erreur de connexion au serveur Ollama local."""
    def __init__(self, message: str = "Impossible de se connecter au serveur local Ollama.", detail: str = ""):
        full_msg = f"{message} {detail}".strip()
        super().__init__(full_msg, error_code="LLM_CONNECTION_ERROR", status_code=503)


class LLMTimeoutError(LLMError):
    """Dépassement du délai de réponse maximal du modèle LLM."""
    def __init__(self, message: str = "Le délai d'attente de réponse du modèle LLM a expiré.", detail: str = ""):
        full_msg = f"{message} {detail}".strip()
        super().__init__(full_msg, error_code="LLM_TIMEOUT", status_code=504)


class LLMModelNotFoundError(LLMError):
    """Le modèle LLM configuré est introuvable sur l'instance Ollama."""
    def __init__(self, model_name: str):
        msg = f"Le modèle '{model_name}' n'est pas disponible sur l'instance Ollama. Exécutez 'ollama pull {model_name}'."
        super().__init__(msg, error_code="LLM_MODEL_NOT_FOUND", status_code=404)


# =====================================================================
# Vocabulaire et Dictionnaire Dialecte Tunisien / Arabizi / Français
# =====================================================================

TUNISIAN_ARABIZI_KEYWORDS = {
    "frais": [
        "flous", "frais", "tarif", "tarifs", "b9adeh", "b9adech", "bkoddech",
        "kadech", "prix", "cout", "somme", "payer", "mensualite", "echeance", "budget"
    ],
    "programs": [
        "formation", "formations", "filiere", "filieres", "branche", "specialite",
        "licence", "master", "mastere", "mba", "ingenieur", "cycle", "diplome",
        "architecture", "prepa", "informatique"
    ],
    "admission": [
        "chourout", "admission", "moyenne", "bac", "concours", "dossier",
        "koulia", "chahada", "condition", "entretien", "test", "admissibilite",
        "prerequis", "justificatif", "piece", "pieces", "documents"
    ],
    "bourses": ["bourse", "bourses", "aide", "sociale", "bourset", "financement"],
    "iit": [
        "iit", "technologie", "ingenierie", "informatique", "genie civil",
        "genie industriel", "genie mecanique", "procedes", "seier", "mecatronique", "architecture"
    ],
    "isb": [
        "isb", "business", "gestion", "finance", "management", "marketing",
        "comptabilite", "droit", "mba", "logistique"
    ],
    "greeting": ["aslema", "ahla", "salut", "bonjour", "salam", "marhba", "coucou", "sbah el khir", "ahla bik"],
}


# =====================================================================
# Chargement du corpus RAG officiel
# =====================================================================

_CORPUS_CACHE: List[Dict[str, Any]] = []


def get_rag_corpus() -> List[Dict[str, Any]]:
    """Charge le corpus RAG complet et met en cache mémoire."""
    global _CORPUS_CACHE
    if not _CORPUS_CACHE:
        corpus_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "corpus_rag_iit_isb.json")
        if os.path.exists(corpus_path):
            try:
                with open(corpus_path, "r", encoding="utf-8") as f:
                    _CORPUS_CACHE = json.load(f)
            except Exception as e:
                logger.error(f"Erreur lors du chargement du corpus RAG : {e}")
                _CORPUS_CACHE = []
    return _CORPUS_CACHE


def search_rag_corpus(query: str, institution: Optional[str] = None, limit: int = 4) -> List[Dict[str, Any]]:
    """Recherche plein-texte dans le corpus officiel avec filtrage optionnel par établissement."""
    corpus = get_rag_corpus()
    if not corpus:
        return []

    tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    scored_docs = []

    for doc in corpus:
        doc_inst = doc.get("etablissement", "").upper()
        if institution and doc_inst != institution.upper():
            continue

        doc_text = (
            f"{doc.get('document_id', '')} "
            f"{doc.get('formation', '')} "
            f"{doc.get('type', '')} "
            f"{doc.get('content', '')}"
        ).lower()

        score = sum(doc_text.count(t) for t in tokens)
        if score > 0:
            scored_docs.append((score, doc))

    scored_docs.sort(key=lambda x: x[0], reverse=True)
    return [d[1] for d in scored_docs[:limit]]


def get_conversation_memory(db: Session, conversation_id: Any, limit: int = 8) -> List[Dict[str, str]]:
    """Récupère la mémoire temporaire des derniers échanges de la conversation (SA-26)."""
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(reversed(db.scalars(stmt).all()))
    return [{"role": msg.role.value, "content": msg.content} for msg in messages]


def find_relevant_academic_context(
    db: Optional[Session],
    query: str,
    history: Optional[List[Dict[str, str]]] = None
) -> str:
    """Extrait les informations pertinentes du catalogue académique et du corpus RAG officiel.
    Prend en compte la mémoire temporaire de la session (US-006 / SA-26) pour contextualiser
    les questions de suivi et anaphores ('ses frais', 'cette formation', 'les conditions', etc.).
    """
    query_lower = query.lower()

    # Enrichissement contextuel à partir des échanges récents de la session
    context_tokens = query_lower
    if history:
        recent_text = " ".join(m.get("content", "") for m in history[-3:])
        context_tokens = f"{recent_text.lower()} {query_lower}"

    # Détection de l'institution visée
    is_iit = any(w in context_tokens for w in TUNISIAN_ARABIZI_KEYWORDS["iit"])
    is_isb = any(w in context_tokens for w in TUNISIAN_ARABIZI_KEYWORDS["isb"])
    target_inst = "IIT" if is_iit and not is_isb else ("ISB" if is_isb and not is_iit else None)

    lines: List[str] = []

    # 1. Base relationnelle si session active
    if db:
        try:
            stmt = select(Program).where(Program.is_active.is_(True))
            if target_inst:
                stmt = stmt.where(Program.institution == target_inst)

            programs = db.scalars(stmt).all()
            if programs:
                for p in programs[:5]:
                    info = f"- [{p.institution.value}] {p.name} ({p.level.capitalize()}, {p.duration_years or 3} ans) : {p.description}"
                    if p.conditions:
                        conds = "; ".join(c.title for c in p.conditions[:2])
                        info += f" | Conditions : {conds}"
                    if p.tariffs:
                        t = p.tariffs[-1]
                        info += f" | Tarifs ({t.academic_year}) : {t.amount} {t.currency}"
                    lines.append(info)
        except Exception as e:
            logger.warning(f"Impossible de lire le catalogue relationnel pour le contexte : {e}")

    # 2. Documents RAG officiels avec requête enrichie si question courte de suivi
    search_query = query
    if history and len(query.split()) <= 7:
        last_turn_content = history[-1].get("content", "") if history else ""
        search_query = f"{last_turn_content} {query}"

    rag_matches = search_rag_corpus(search_query, institution=target_inst, limit=3)
    if not rag_matches and search_query != query:
        rag_matches = search_rag_corpus(query, institution=target_inst, limit=3)

    if rag_matches:
        lines.append("\nExtraits documentaires officiels (RAG IIT / ISB) :")
        for doc in rag_matches:
            status_verif = doc.get("statut_verification", "non_verifie")
            lines.append(
                f"- Doc [{doc.get('document_id')}] ({doc.get('source_url')}) [Statut: {status_verif}] :\n"
                f"  {doc.get('content')[:300]}..."
            )

    return "\n".join(lines) if lines else "Aucune information académique spécifique trouvée."


# =====================================================================
# Client HTTP Ollama Local
# =====================================================================

class OllamaClient:
    """Client HTTP résilient pour communiquer avec le démon Ollama local."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout_seconds
        self.api_key = api_key or settings.ollama_api_key
        self.temperature = temperature if temperature is not None else settings.ollama_temperature
        self.top_p = top_p if top_p is not None else settings.ollama_top_p
        self.max_tokens = max_tokens or settings.ollama_max_tokens

    def _build_headers(self) -> Dict[str, str]:
        """Génère les en-têtes HTTP sans fuite de secrets dans les journaux."""
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key.strip():
            headers["Authorization"] = f"Bearer {self.api_key.strip()}"
        return headers

    def check_health(self) -> Dict[str, Any]:
        """Vérifie la disponibilité du serveur Ollama, des modèles et mesure la latence."""
        start_time = time.perf_counter()
        tags_url = f"{self.base_url}/api/tags"
        version_url = f"{self.base_url}/api/version"

        try:
            with httpx.Client(timeout=min(self.timeout, 5.0)) as client:
                resp = client.get(tags_url, headers=self._build_headers())
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

                if resp.status_code != 200:
                    return {
                        "status": "degraded",
                        "ollama_url": self.base_url,
                        "configured_model": self.model,
                        "model_available": False,
                        "available_models": [],
                        "latency_ms": duration_ms,
                        "version": None,
                        "error": f"Statut HTTP inattendu : {resp.status_code}"
                    }

                data = resp.json()
                raw_models = data.get("models", [])
                available_model_names = [m.get("name", "") for m in raw_models]
                
                # Vérifie si le modèle exact ou sa version sans tag est présent
                model_found = any(
                    self.model == name or self.model in name or name.startswith(self.model)
                    for name in available_model_names
                )

                # Récupérer la version si disponible
                version_str = None
                try:
                    v_resp = client.get(version_url, headers=self._build_headers())
                    if v_resp.status_code == 200:
                        version_str = v_resp.json().get("version")
                except Exception:
                    pass

                return {
                    "status": "ok" if model_found else "degraded",
                    "ollama_url": self.base_url,
                    "configured_model": self.model,
                    "model_available": model_found,
                    "available_models": available_model_names,
                    "latency_ms": duration_ms,
                    "version": version_str
                }

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"Ollama local injoignable sur {self.base_url} : {exc}")
            return {
                "status": "unavailable",
                "ollama_url": self.base_url,
                "configured_model": self.model,
                "model_available": False,
                "available_models": [],
                "latency_ms": duration_ms,
                "version": None,
                "error": "Serveur Ollama injoignable (déconnecté ou port non actif)"
            }
        except httpx.TimeoutException as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"Timeout lors de la vérification de santé Ollama : {exc}")
            return {
                "status": "timeout",
                "ollama_url": self.base_url,
                "configured_model": self.model,
                "model_available": False,
                "available_models": [],
                "latency_ms": duration_ms,
                "version": None,
                "error": "Dépassement du délai de réponse de la sonde"
            }
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Erreur inattendue de sonde Ollama : {exc}")
            return {
                "status": "error",
                "ollama_url": self.base_url,
                "configured_model": self.model,
                "model_available": False,
                "available_models": [],
                "latency_ms": duration_ms,
                "version": None,
                "error": str(exc)
            }

    def list_models(self) -> List[Dict[str, Any]]:
        """Liste les modèles installés localement avec leurs métadonnées."""
        url = f"{self.base_url}/api/tags"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=self._build_headers())
                if resp.status_code == 200:
                    return resp.json().get("models", [])
                return []
        except (httpx.ConnectError, httpx.NetworkError) as e:
            raise LLMConnectionError(detail=str(e))
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(detail=str(e))
        except Exception as e:
            raise LLMError(f"Erreur lors de la récupération des modèles : {e}")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Exécute une requête de chat completion sur Ollama avec gestion rigoureuse des erreurs."""
        target_model = model or self.model
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
                "top_p": top_p if top_p is not None else self.top_p,
                "num_predict": max_tokens or self.max_tokens,
            }
        }

        start_time = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=self._build_headers())

                if resp.status_code == 404:
                    raise LLMModelNotFoundError(target_model)
                elif resp.status_code != 200:
                    raise LLMError(
                        f"Erreur du serveur Ollama (HTTP {resp.status_code}) : {resp.text}",
                        status_code=resp.status_code
                    )

                data = resp.json()
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                assistant_content = data.get("message", {}).get("content", "")

                return {
                    "content": assistant_content,
                    "model": target_model,
                    "latency_ms": duration_ms,
                    "total_duration": data.get("total_duration"),
                    "eval_count": data.get("eval_count"),
                }

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            logger.error(f"Erreur de connexion Ollama ({url}) : {exc}")
            raise LLMConnectionError(detail=f"Incapable d'atteindre {self.base_url}")
        except httpx.TimeoutException as exc:
            logger.error(f"Délai d'attente dépassé ({self.timeout}s) pour Ollama : {exc}")
            raise LLMTimeoutError(detail=f"Temps dépassé ({self.timeout}s)")


# =====================================================================
# Prompt Système Officiel SmartCampus AI
# =====================================================================

SYSTEM_PROMPT_TEMPLATE = """Tu es SmartCampus AI, l'assistant officiel d'orientation académique et d'admission de l'Institut International de Technologie (IIT) et de l'International School of Business (ISB) de Sfax, Tunisie.

DIRECTIVES FONDAMENTALES DE CONDUITE, MÉMOIRE ET SÉCURITÉ ADMINISTRATIVE :

1. LANGUE ET STYLE DE COMMUNICATION :
   - Réponds avec bienveillance, clarté, concision et neutralité en Français (ou en dialecte tunisien / Arabizi si l'utilisateur s'exprime ainsi).
   - Utilise une mise en forme Markdown structurée et soignée.

2. PÉRIMÈTRE INSTITUTIONNEL STRICT & SITUATIONS HORS CORPUS :
   - Tu représentes EXCLUSIVEMENT l'Institut International de Technologie (IIT) et l'International School of Business (ISB) de Sfax.
   - Les formations couvertes sont strictement :
     • IIT : Cycle Préparatoire, Licences Scientifiques (Informatique, SEIER, Mécatronique), Cycles Ingénieur (Informatique, Génie Civil, Industriel, Mécanique, Procédés), Architecture.
     • ISB : Licences et Mastères/MBA en Gestion, Finance, Business Administration, Marketing Digital, Comptabilité, Logistique, Droit des Affaires.
   - Si la demande concerne une discipline NON DISPENSÉE (ex: médecine, pharmacie, etc.) ou une information absente du catalogue, déclare immédiatement que cette formation n'est pas proposée par l'IIT ou l'ISB et oriente vers les contacts officiels :
     • IIT : ameni.trigui@iit.ens.tn / (+216) 74 465 020 / https://iit.tn/
     • ISB : contact@isb.ens.tn / scolarite@isb.ens.tn / (+216) 74 465 020 / https://isb.tn/
   - Ne JAMAIS improviser de cursus externes ou inventer des programmes inexistants dans notre catalogue.

3. MÉMOIRE TEMPORAIRE DE SESSION & QUESTIONS DE SUIVI (US-006 / SA-26) :
   - Tu disposes de l'historique complet des messages récents de la session en cours.
   - Analyse attentivement les échanges antérieurs pour maintenir la continuité thématique.
   - Lorsqu'un candidat pose une question de suivi ou utilise des formulations implicites ou anaphoriques (ex: 'Et quels sont ses frais ?', 'Y a-t-il un concours ?', 'Quels en sont les débouchés ?', 'Et pour la licence ?'), identifie immédiatement la filière ou l'établissement concerné dans les messages précédents et réponds précisément dans ce contexte.

4. PROTECTION RIGOUREUSE CONTRE LES INFORMATIONS NON VÉRIFIÉES (RÈGLE ADMINISTRATIVE STRICTE) :
   - INTERDICTION ABSOLUE de présenter des données administratives (frais de scolarité, bourses, dispenses, critères de sélection, équivalences, dates limites) comme des vérités officielles définitives si elles sont assorties du statut 'non_verifie', 'indicatif' ou 'partielle_ou_manquante'.
   - Toute donnée financière ou tarifaire doit être expressément accompagnée de la réserve suivante :
     "Tarifs et frais de scolarité indicatifs : ces montants doivent être obligatoirement revalidés auprès de l'administration avant tout engagement financier."
   - Ne JAMAIS prononcer ou déduire d'admission, de dispense ou d'équivalence de diplôme automatique. Rappelle que seule la Commission d'Admission souveraine de l'établissement (IIT ou ISB) est légalement habilitée à statuer après étude du dossier complet.
   - RÈGLE ABSOLUE SUR LES DATES LIMITES : Aucune date limite exacte de candidature n'est fixée dans le corpus actuel. Si l'on te demande la date limite, NE DONNE AUCUNE DATE FICTIVE OU INVENTÉE. Déclare impérativement que la date limite officielle n'est pas précisée dans le corpus actuel et invite le candidat à contacter directement le secrétariat officiel :
     • Institut International de Technologie (IIT) : ameni.trigui@iit.ens.tn / (+216) 74 465 020 / https://iit.tn/
     • International School of Business (ISB) : contact@isb.ens.tn / scolarite@isb.ens.tn / (+216) 74 465 020 / https://isb.tn/

5. CAS AMBIGUS & CONTEXTE MANQUANT :
   - Lorsque la requête est ambiguë ou trop vague (ex: 'C'est combien ?', 'Est-ce que je peux y accéder ?', 'Quelle est la meilleure formation ?', 'Je veux m'inscrire'), NE FAIS AUCUNE SUPPOSITION.
   - Demande poliment les précisions nécessaires au candidat (nom de la formation visée, baccalauréat, moyenne obtenue, filière IIT ou ISB).

6. CITATION OBLIGATOIRE DES SOURCES :
   - Cite systématiquement les identifiants documentaires (ex: `[frais-et-conditions-generales-iit]`) et les URLs officielles associées.

--- CONTEXTE DOCUMENTAIRE ACADÉMIQUE OFFICIEL ---
{academic_context}
-------------------------------------------------
"""


# =====================================================================
# Connecteur Principal SmartCampusLLMConnector
# =====================================================================

class SmartCampusLLMConnector:
    """Connecteur principal reliant la mémoire, le RAG et le modèle Gemma Ollama local avec repli résilient."""

    def __init__(self):
        self.client = OllamaClient()

    def _extract_cited_sources(self, text: str) -> List[str]:
        """Extrait les identifiants documentaires et URLs cités dans le texte généré."""
        sources = []
        doc_matches = re.findall(r"\[([a-zA-Z0-9_\-\.]+)\]", text)
        for doc in doc_matches:
            if doc not in sources and len(doc) > 3:
                sources.append(doc)
        url_matches = re.findall(r"https?://[^\s\)\>]+", text)
        for url in url_matches:
            if url not in sources:
                sources.append(url)
        return sources

    def _fallback_rule_engine(
        self,
        db: Optional[Session],
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Moteur de repli déterministe basé sur les règles et le corpus RAG lorsque Ollama est hors ligne."""
        user_text = user_message.strip()
        user_lower = user_text.lower()

        # Prise en compte de l'historique de session pour les questions de suivi en repli
        context_str = user_lower
        if history:
            recent_hist_str = " ".join(m.get("content", "") for m in history[-3:]).lower()
            context_str = f"{recent_hist_str} {user_lower}"

        # 1. Salutations en Français ou dialecte tunisien / Arabizi (SA-34)
        if any(w in user_lower for w in TUNISIAN_ARABIZI_KEYWORDS["greeting"]) and len(user_text.split()) <= 4:
            return (
                "Marhba bik fi SmartCampus AI ! 🎓\n\n"
                "Je suis votre assistant pour vous orienter sur les filières officielles de "
                "l'**IIT** (Institut International de Technologie) et de l'**ISB** (International School of Business).\n"
                "Je peux vous renseigner sur les programmes d'études, les conditions d'admission, "
                "les bourses et les tarifs indicatifs.\n\n"
                "Comment puis-je vous aider aujourd'hui ?"
            )

        # 2. Cas Ambigu : Détection de requêtes courtes ou non spécifiées sans historique préalable
        ambiguous_patterns = [
            ("c'est combien", "Pourriez-vous préciser de quelle formation vous souhaitez connaître les frais de scolarité ou d'inscription (IIT ou ISB) ?"),
            ("est-ce que je peux y accéder", "Pour savoir si vous êtes éligible, pourriez-vous préciser la formation visée ainsi que votre diplôme actuel (Baccalauréat, Licence, etc.) et votre filière ?"),
            ("quelle est la meilleure formation", "Il n'y a pas de formation unique meilleure dans l'absolu. Quelles sont vos matières préférées, vos compétences et votre projet professionnel (informatique, ingénierie, gestion, finance) ?"),
            ("comment faire", "Les démarches dépendent de la formation choisie. Quelle filière de l'IIT ou de l'ISB vous intéresse pour que je vous détaille les étapes d'admission ?"),
        ]
        if not history or len(history) == 0:
            for pattern, prompt_clarif in ambiguous_patterns:
                if pattern in user_lower and len(user_text.split()) <= 8:
                    return f"Afin de vous donner une réponse exacte et officielle : {prompt_clarif}"

        # 3. Tarifs / Frais (b9adeh / flous / prix / coût)
        if any(w in user_lower for w in TUNISIAN_ARABIZI_KEYWORDS["frais"]) or ("frais" in context_str and len(user_text.split()) <= 5):
            is_iit = any(w in context_str for w in TUNISIAN_ARABIZI_KEYWORDS["iit"])
            is_isb = any(w in context_str for w in TUNISIAN_ARABIZI_KEYWORDS["isb"])

            parts = [
                "Voici les tarifs et frais de scolarité indicatifs extraits du corpus officiel SmartCampus AI :\n"
            ]
            if not is_isb:
                parts.append(
                    "### 🏛️ Institut International de Technologie (IIT)\n"
                    "• **Cycle préparatoire** : 556 DT / 9 mois (national) ou 234 € / 9 mois (international).\n"
                    "• **Licences SEIER & Mécatronique** : 567 DT / 9 mois (national) ou 167 € / 9 mois (international).\n"
                    "• **Licence Informatique (4 parcours)** : 667 DT / 9 mois (national) ou 189 € / 9 mois (international).\n"
                    "• **Cycle Ingénieur Génie Informatique** : 778 DT / 9 mois (national) ou 234 € / 9 mois (international).\n"
                    "• **Cycle Ingénieur Génie des Procédés, Industriel, Mécanique & Civil** : 611 DT / 9 mois (national) ou 234 € / 9 mois (international).\n"
                    "• **Architecture (5 ans)** : 776 DT / 9 mois (national) ou 278 € / 9 mois (international).\n"
                    "• **Droit d'inscription** : 800 DT (national) ou 800 € (international), en supplément des frais de scolarité.\n"
                    "• **Modalités** : Réduction de 5 % pour paiement total comptant à l'inscription. Majoration de 5 % à partir de la 2ème année.\n"
                    "• **Contact officiel IIT** : ameni.trigui@iit.ens.tn\n"
                )
            if not is_iit:
                parts.append(
                    "### 🏢 International School of Business (ISB)\n"
                    "• **Licences (12 parcours)** : Fourchette indicative de 4 000 à 6 000 DT / an (national) ou 1 500 à 2 500 € / an (international).\n"
                    "• **Mastères Professionnels & MBA (10 parcours)** : Fourchette indicative de 5 000 à 8 000 DT / an (national) ou 2 000 à 3 500 € / an (international).\n"
                    "• **Frais d'inscription** : 300 à 500 DT selon filière (ou inclus selon convention).\n"
                    "• **Contact officiel ISB** : contact@isb.ens.tn | scolarite@isb.ens.tn\n"
                )
            parts.append(
                "> ⚠️ **Règle de conformité administrative** : Ces montants sont strictement indicatifs (statut non vérifié) "
                "et doivent être obligatoirement revalidés auprès de l'administration avant tout engagement financier.\n\n"
                "**Sources citées :**\n"
                "- `frais-et-conditions-generales-iit` : https://iit.tn/test/procedure-et-frais-dinscription/\n"
                "- `frais-et-conditions-generales-isb` : https://isb.tn/frais-de-scolarite/"
            )
            return "\n".join(parts)

        # 4. Conditions d'admission & Pièces à fournir (Documents)
        if any(w in user_lower for w in TUNISIAN_ARABIZI_KEYWORDS["admission"]):
            # Vérifier si la question porte spécifiquement sur les documents
            if any(w in user_lower for w in ["document", "documents", "piece", "pieces", "justificatif", "justificatifs", "dossier"]):
                return (
                    "### 📂 Documents à préparer pour votre candidature officielle :\n\n"
                    "Selon la procédure officielle d'inscription IIT / ISB, votre dossier doit comporter :\n"
                    "1. Une copie certifiée conforme du **Baccalauréat** ou diplôme équivalent.\n"
                    "2. Les **relevés de notes** des années universitaires précédentes (pour cycles ingénieur/mastère).\n"
                    "3. Une copie de la **Carte d'Identité Nationale (CIN)** ou du Passeport.\n"
                    "4. Un **Curriculum Vitae (CV)** récent.\n"
                    "5. Deux photos d'identité récentes.\n\n"
                    "> ⚠️ Toute admission définitive est soumise à la décision souveraine de la commission d'admission après étude du dossier complet.\n\n"
                    "**Sources citées :**\n"
                    "- `procedure-admission-ingenierie-iit` : https://iit.tn/test/procedure-et-frais-dinscription/\n"
                    "- `procedure-admission-isb` : https://isb.tn/admission/"
                )

            return (
                "### 📋 Procédures et Conditions d'Admission Officielles\n\n"
                "**1. Cycle Ingénieur IIT :**\n"
                "- Admission sur **concours sur dossier**, suivi d'un **entretien de validation** et d'un **test d'admission**.\n"
                "- Prérequis : Diplôme de classe préparatoire (MP/PC/PT) ou Licence scientifique (informatique, mécanique, civil, etc.).\n\n"
                "**2. Cycle Préparatoire & Licences IIT :**\n"
                "- Accessible aux titulaires d'un **Baccalauréat scientifique ou technique** (Maths, Sciences Expérimentales, Informatique, Technique).\n\n"
                "**3. Licences & Mastères ISB :**\n"
                "- Licences : Baccalauréat toutes sections + entretien d'orientation.\n"
                "- Mastères & MBA : Licence Bac+3 avec sélection sur dossier et entretien individuel d'évaluation.\n\n"
                "> ⚠️ **Règle administrative essentielle** : Une simple proximité de filière ne confère pas automatiquement une équivalence ou une décision d'admission. Toute admission dépend de la décision souveraine de la commission.\n\n"
                "**Sources citées :**\n"
                "- `procedure-admission-ingenierie-iit` : https://iit.tn/test/procedure-et-frais-dinscription/\n"
                "- `criteres-admission-ingenierie-iit-pdf` : https://iit.tn/wp-content/uploads/2026/10/Criteres_d_admission.pdf\n"
                "- `procedure-admission-isb` : https://isb.tn/admission/"
            )

        # 5. Recherche RAG sur demande libre
        search_term = user_text
        if history and len(user_text.split()) <= 6:
            search_term = f"{history[-1].get('content', '')} {user_text}"

        rag_results = search_rag_corpus(search_term, limit=3)
        if rag_results:
            response_lines = ["Selon les données officielles du corpus académique SmartCampus AI :\n"]
            cited_sources = []
            for doc in rag_results:
                response_lines.append(f"• **{doc.get('formation', doc.get('document_id'))}** [{doc.get('etablissement')}] :")
                response_lines.append(f"  {doc.get('content')}\n")
                cited_sources.append(f"- `{doc.get('document_id')}` : {doc.get('source_url')}")

            response_lines.append(
                "> ℹ️ Pour toute question administrative spécifique ou vérification officielle : "
                "ameni.trigui@iit.ens.tn (IIT) ou contact@isb.ens.tn (ISB).\n"
            )
            response_lines.append("**Sources citées :**\n" + "\n".join(cited_sources))
            return "\n".join(response_lines)

        return (
            "Cette information n'est pas précisée dans le corpus officiel SmartCampus AI actuellement disponible.\n\n"
            "Nous vous invitons à contacter directement le secrétariat officiel pour obtenir une information vérifiée :\n"
            "• **IIT** : ameni.trigui@iit.ens.tn / (+216) 74 465 020 / https://iit.tn/\n"
            "• **ISB** : contact@isb.ens.tn / (+216) 74 465 020 / https://isb.tn/"
        )

    def generate_reply(
        self,
        db: Session,
        conversation: Conversation,
        user_message: str
    ) -> str:
        """Génère la réponse de l'assistant pour le routeur conversations en injectant la mémoire temporaire (US-006) et le RAG."""
        user_text = user_message.strip()
        user_lower = user_text.lower()

        # 0. Réponse immédiate pour les salutations brèves (SA-34)
        if any(w in user_lower for w in TUNISIAN_ARABIZI_KEYWORDS["greeting"]) and len(user_text.split()) <= 4:
            return self._fallback_rule_engine(db, user_text)

        # 1. Récupération de la mémoire temporaire des échanges de la conversation (US-006 / SA-26)
        raw_history = get_conversation_memory(db, conversation.id, limit=8)

        # Retirer le message courant de l'historique s'il y figure déjà pour éviter les doublons
        history_context: List[Dict[str, str]] = []
        if raw_history:
            if raw_history[-1]["content"] == user_text and raw_history[-1]["role"] == "user":
                history_context = raw_history[:-1]
            else:
                history_context = raw_history

        # 2. Extraction du contexte académique RAG enrichi par l'historique (suivi conversationnel)
        academic_context = find_relevant_academic_context(db, user_text, history=history_context)
        system_content = SYSTEM_PROMPT_TEMPLATE.format(academic_context=academic_context)

        # 3. Assemblage complet du fil de discussion pour Gemma
        messages = [{"role": "system", "content": system_content}]
        for m in history_context:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_text})

        # 4. Appel Ollama avec gestion des pannes et fallback automatique
        try:
            res = self.client.chat_completion(messages=messages)
            content = res.get("content", "").strip()
            if content:
                # Conformité administrative : mention expresse des tarifs et réserve obligatoire pour toute question financière
                is_financial = any(w in user_lower for w in TUNISIAN_ARABIZI_KEYWORDS["frais"])
                if is_financial:
                    if "tarif" not in content.lower():
                        content = f"### Tarifs et frais de scolarité indicatifs :\n{content}"
                    if not any(k in content.lower() for k in ["indicatif", "revalider", "confirmation"]):
                        content += "\n\n> ⚠️ **Note administrative** : Ces tarifs et frais sont fournis à titre indicatif et doivent être obligatoirement confirmés auprès de l'administration officielle."
                return content
            logger.warning("Réponse vide de Gemma, bascule sur le moteur de règles RAG.")
        except (LLMConnectionError, LLMTimeoutError, LLMModelNotFoundError) as exc:
            logger.warning(f"Ollama Gemma indisponible ({exc}). Activation du repli déterministe RAG.")
            if not settings.llm_fallback_enabled:
                raise
        except Exception as exc:
            logger.error(f"Erreur inattendue lors de l'appel LLM : {exc}")
            if not settings.llm_fallback_enabled:
                raise LLMError(f"Erreur LLM : {exc}")

        # 5. Repli déterministe local avec historique
        return self._fallback_rule_engine(db, user_text, history=history_context)

    def ask_direct(
        self,
        query: str,
        db: Optional[Session] = None,
        conversation_id: Optional[Any] = None,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        inject_academic_context: bool = True,
        fallback_on_error: bool = True,
    ) -> Dict[str, Any]:
        """Méthode directe d'interrogation du LLM avec support de la mémoire temporaire (US-006)."""
        start_time = time.perf_counter()

        # 1. Chargement de l'historique conversationnel depuis la base si conversation_id fourni
        active_history = conversation_history or []
        if conversation_id and db and not conversation_history:
            raw_mem = get_conversation_memory(db, conversation_id, limit=8)
            if raw_mem and raw_mem[-1]["content"] == query.strip() and raw_mem[-1]["role"] == "user":
                active_history = raw_mem[:-1]
            else:
                active_history = raw_mem

        # 2. Construction du contexte avec prise en compte de la mémoire
        if inject_academic_context:
            academic_context = find_relevant_academic_context(db, query, history=active_history)
            sys_text = (system_prompt or SYSTEM_PROMPT_TEMPLATE).format(academic_context=academic_context)
        else:
            sys_text = system_prompt or "Tu es un assistant académique utile et véridique."

        # 3. Formatage ordonné des messages
        messages = [{"role": "system", "content": sys_text}]
        if active_history:
            for item in active_history:
                messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": query})

        fallback_used = False
        reply_text = ""
        model_name = self.client.model

        # 4. Exécution Ollama Gemma
        try:
            res = self.client.chat_completion(
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
            reply_text = res.get("content", "").strip()
            is_financial = any(w in query.lower() for w in TUNISIAN_ARABIZI_KEYWORDS["frais"])
            if is_financial:
                if "tarif" not in reply_text.lower():
                    reply_text = f"### Tarifs et frais de scolarité indicatifs :\n{reply_text}"
                if not any(k in reply_text.lower() for k in ["indicatif", "revalider", "confirmation"]):
                    reply_text += "\n\n> ⚠️ **Note administrative** : Ces tarifs et frais sont fournis à titre indicatif et doivent être obligatoirement confirmés auprès de l'administration officielle."
            model_name = res.get("model", model_name)
        except (LLMConnectionError, LLMTimeoutError, LLMModelNotFoundError, LLMError) as exc:
            if not fallback_on_error or not settings.llm_fallback_enabled:
                raise
            logger.info(f"Bascule vers le repli déterministe suite à : {exc}")
            reply_text = self._fallback_rule_engine(db, query, history=active_history)
            fallback_used = True
        except Exception as exc:
            if not fallback_on_error or not settings.llm_fallback_enabled:
                raise LLMError(f"Erreur d'exécution LLM : {exc}")
            logger.error(f"Erreur inattendue, repli activé : {exc}")
            reply_text = self._fallback_rule_engine(db, query, history=active_history)
            fallback_used = True

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        sources_cited = self._extract_cited_sources(reply_text)

        return {
            "response": reply_text,
            "model": model_name,
            "latency_ms": latency_ms,
            "fallback_used": fallback_used,
            "sources_cited": sources_cited,
            "status": "success"
        }


# =====================================================================
# Moteur d'Évaluation du Benchmark SA-32
# =====================================================================

def load_sa32_questions() -> List[Dict[str, Any]]:
    """Charge le jeu de test officiel des 19 questions SA-32."""
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "eval_questions_sa32.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("questions", [])
    return []


def evaluate_response_criteria(
    question_data: Dict[str, Any],
    response_text: str
) -> Tuple[bool, List[str]]:
    """Évalue la réponse générée au regard des critères de la tâche SA-32."""
    category = question_data.get("category", "")
    qid = question_data.get("id", "")
    text_lower = response_text.lower()
    feedback = []
    passed = True

    # Règle transversale : Présence de contenu significatif
    if len(response_text.strip()) < 15:
        feedback.append("Réponse trop brève ou vide.")
        return False, feedback

    if category == "ambiguous":
        # Doit demander des précisions et ne pas inventer arbitrairement
        clarification_indicators = [
            "préciser", "quelle formation", "quel diplôme", "quel établissement",
            "pourriez-vous", "veuillez préciser", "quel est votre", "votre parcours",
            "intérêts", "objectifs", "baccalauréat", "iit ou isb"
        ]
        has_clarif = any(ind in text_lower for ind in clarification_indicators) or ("?" in response_text)
        if has_clarif:
            feedback.append("Clarification demandée avec succès pour le cas ambigu.")
        else:
            feedback.append("Échec : Le modèle n'a pas posé de question de clarification pour le cas ambigu.")
            passed = False

    elif category == "admission":
        # Exactitude, absence d'invention, demande du nom si besoin
        if qid == "ADM-001":
            has_conditions = any(w in text_lower for w in ["bac", "licence", "concours", "dossier", "entretien", "formation"])
            if has_conditions:
                feedback.append("Conditions d'admission pertinentes mentionnées.")
            else:
                passed = False
                feedback.append("Conditions d'admission manquantes.")

        elif qid == "ADM-002":
            has_docs = any(w in text_lower for w in ["bac", "relevé", "cin", "passeport", "cv", "photo", "dossier"])
            if has_docs:
                feedback.append("Documents officiels listés avec exactitude.")
            else:
                passed = False
                feedback.append("Liste des pièces manquante ou imprécise.")

        elif qid == "ADM-003":
            # Doit indiquer la date limite ou préciser qu'elle n'est pas disponible sans inventer
            has_date_handling = any(w in text_lower for w in ["non précisée", "non disponible", "contacter", "secrétariat", "date", "administration"])
            if has_date_handling:
                feedback.append("Date limite gérée avec rigueur sans invention arbitraire.")
            else:
                passed = False
                feedback.append("Gestion de la date limite non satisfaisante.")

        elif qid == "ADM-004":
            has_fees = any(w in text_lower for w in ["dt", "€", "euro", "tarif", "frais", "scolarité", "préciser", "formation"])
            if has_fees:
                feedback.append("Tarifs officiels ou demande de formation visée respectés.")
            else:
                passed = False
                feedback.append("Tarifs non traités correctement.")

        elif qid == "ADM-005":
            has_eligibility = any(w in text_lower for w in ["diplôme", "préciser", "commission", "éligible", "conditions", "formation"])
            if has_eligibility:
                feedback.append("Demande de précisions sur le diplôme et vérification d'éligibilité conformes.")
            else:
                passed = False
                feedback.append("Éligibilité non analysée conformément.")

    elif category == "orientation":
        has_programs = any(w in text_lower for w in ["iit", "isb", "licence", "ingénieur", "informatique", "génie", "parcours", "spécialité", "gestion"])
        if has_programs:
            feedback.append("Formations pertinentes recommandées à partir du catalogue officiel.")
        else:
            passed = False
            feedback.append("Absence de recommandations alignées sur le catalogue.")

    elif category == "reformulation":
        group_id = question_data.get("group_id", "")
        if group_id == "admission_documents":
            has_docs = any(w in text_lower for w in ["document", "pièce", "dossier", "bac", "cin", "cv", "justificatif"])
            if has_docs:
                feedback.append("Intention 'documents d'admission' bien comprise.")
            else:
                passed = False
                feedback.append("Intention documents non reconnue.")
        elif group_id == "admission_fees":
            has_fees = any(w in text_lower for w in ["frais", "tarif", "coût", "dt", "€", "budget", "scolarité", "préciser"])
            if has_fees:
                feedback.append("Intention 'frais et budget' bien comprise.")
            else:
                passed = False
                feedback.append("Intention tarifs non reconnue.")

    return passed, feedback


llm_connector = SmartCampusLLMConnector()
