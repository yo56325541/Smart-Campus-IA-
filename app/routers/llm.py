"""Routeur API pour le service LLM local (Ollama - Modèle Gemma) et benchmark SA-32.
Gère :
- L'envoi des questions et la récupération des réponses générées
- La protection des clés d'accès via verify_llm_access
- La gestion fine des erreurs de connexion (503) et de délai de réponse (504)
- La sonde de santé et le catalogue des modèles
- L'évaluation automatisée du jeu de test SA-32 (admission, orientation, reformulations, cas ambigus)
"""
import logging
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import verify_llm_access
from ..schemas import (LLMEvalQuestionOut, LLMEvalResultItem, LLMEvalSummary,
                       LLMHealthResponse, LLMModelItem, LLMQueryRequest,
                       LLMQueryResponse)
from ..services_llm import (LLMConnectionError, LLMError, LLMModelNotFoundError,
                            LLMTimeoutError, evaluate_response_criteria,
                            llm_connector, load_sa32_questions)

logger = logging.getLogger("smartcampus.routers.llm")

router = APIRouter(prefix="/llm", tags=["LLM Service (Ollama - Gemma)"])


@router.post(
    "/chat",
    response_model=LLMQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Envoyer une question au modèle LLM local Gemma et récupérer la réponse générée",
)
def chat_with_llm(
    body: LLMQueryRequest,
    authorized: bool = Depends(verify_llm_access),
    db: Session = Depends(get_db),
):
    """Point de terminaison principal pour interroger le modèle LLM Gemma local.
    - **Protection d'accès** : vérification de la clé secrète (X-API-Key) ou authentification.
    - **Contexte académique** : injection automatisée du corpus RAG et du catalogue officiel.
    - **Résilience** : gestion des erreurs de connexion (503) et des délais dépassés (504).
    """
    try:
        conv_hist = None
        if body.conversation_history:
            conv_hist = [{"role": m.role, "content": m.content} for m in body.conversation_history]

        result = llm_connector.ask_direct(
            query=body.query,
            db=db,
            conversation_id=body.conversation_id,
            system_prompt=body.system_prompt,
            conversation_history=conv_hist,
            temperature=body.temperature,
            top_p=body.top_p,
            max_tokens=body.max_tokens,
            inject_academic_context=body.inject_academic_context,
            fallback_on_error=True,
        )

        return LLMQueryResponse(
            response=result["response"],
            model=result["model"],
            latency_ms=result["latency_ms"],
            fallback_used=result["fallback_used"],
            sources_cited=result["sources_cited"],
            status="success",
        )

    except LLMConnectionError as exc:
        logger.error(f"Erreur de connexion Ollama : {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erreur de connexion au service LLM : {exc.message}",
        )
    except LLMTimeoutError as exc:
        logger.error(f"Dépassement du délai de réponse LLM : {exc}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Délai d'attente de réponse dépassé pour le modèle : {exc.message}",
        )
    except LLMModelNotFoundError as exc:
        logger.error(f"Modèle LLM introuvable : {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        )
    except LLMError as exc:
        logger.error(f"Erreur interne du service LLM : {exc}")
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        )
    except Exception as exc:
        logger.error(f"Erreur inattendue dans l'API LLM : {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Une erreur interne est survenue lors de l'interaction avec le modèle.",
        )


@router.get(
    "/health",
    response_model=LLMHealthResponse,
    summary="Vérifier la connectivité et la disponibilité du serveur Ollama local",
)
def check_llm_health():
    """Sonde de santé dédiée au service LLM :
    - Vérifie si le serveur Ollama est en ligne
    - Contrôle la présence du modèle sélectionné (Gemma)
    - Mesure la latence d'aller-retour
    """
    health_data = llm_connector.client.check_health()
    return LLMHealthResponse(
        status=health_data.get("status", "unknown"),
        ollama_url=health_data.get("ollama_url", ""),
        configured_model=health_data.get("configured_model", ""),
        model_available=health_data.get("model_available", False),
        available_models=health_data.get("available_models", []),
        latency_ms=health_data.get("latency_ms"),
        version=health_data.get("version"),
    )


@router.get(
    "/models",
    response_model=List[LLMModelItem],
    summary="Lister les modèles LLM disponibles localement sur Ollama",
    dependencies=[Depends(verify_llm_access)],
)
def list_available_models():
    """Liste tous les modèles disponibles localement sur l'instance Ollama."""
    try:
        raw_models = llm_connector.client.list_models()
        return [
            LLMModelItem(
                name=m.get("name", ""),
                size_bytes=m.get("size"),
                modified_at=m.get("modified_at"),
            )
            for m in raw_models
        ]
    except LLMConnectionError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message)
    except LLMTimeoutError as exc:
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message)


# =====================================================================
# Endpoints du Benchmark SA-32 (Évaluation des LLM)
# =====================================================================

@router.get(
    "/evaluations/questions",
    response_model=List[LLMEvalQuestionOut],
    summary="Récupérer le jeu complet des 19 questions officielles d'évaluation SA-32",
    dependencies=[Depends(verify_llm_access)],
)
def get_evaluation_questions():
    """Retourne la liste des questions étalons pour l'évaluation du LLM (admission, orientation, reformulations, ambiguïtés)."""
    questions = load_sa32_questions()
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier de questions d'évaluation SA-32 introuvable.",
        )
    return [LLMEvalQuestionOut(**q) for q in questions]


@router.post(
    "/evaluations/run",
    response_model=LLMEvalSummary,
    summary="Exécuter la campagne d'évaluation SA-32 sur le modèle Gemma local",
    dependencies=[Depends(verify_llm_access)],
)
def run_evaluation_benchmark(
    category: Optional[str] = Query(default=None, description="Filtrer par catégorie ('admission', 'orientation', 'reformulation', 'ambiguous')"),
    limit: Optional[int] = Query(default=None, ge=1, le=50, description="Nombre maximal de questions à exécuter"),
    db: Session = Depends(get_db),
):
    """Exécute les questions du benchmark SA-32 contre le modèle local Gemma.
    Évalue en temps réel :
    - Exactitude des informations académiques
    - Utilisation des sources officielles RAG
    - Absence d'hallucinations ou de dates/frais inventés
    - Détection des ambiguïtés et formulation de questions de clarification
    - Clarté et personnalisation de l'orientation
    """
    all_questions = load_sa32_questions()
    if not all_questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier de questions d'évaluation SA-32 introuvable.",
        )

    target_questions = all_questions
    if category:
        target_questions = [q for q in target_questions if q.get("category") == category]
    if limit:
        target_questions = target_questions[:limit]

    start_bench_time = time.perf_counter()
    results: List[LLMEvalResultItem] = []
    category_stats = {}

    for q in target_questions:
        qid = q.get("id", "")
        cat = q.get("category", "")
        query_text = q.get("query", "")
        expected = q.get("expected_behavior", "")
        criteria = q.get("evaluation_criteria", [])

        # Appel LLM avec injection contexte officiel
        llm_res = llm_connector.ask_direct(
            query=query_text,
            db=db,
            inject_academic_context=True,
            fallback_on_error=True,
        )

        resp_text = llm_res["response"]
        criteria_met, feedback = evaluate_response_criteria(q, resp_text)

        results.append(
            LLMEvalResultItem(
                id=qid,
                category=cat,
                query=query_text,
                response=resp_text,
                expected_behavior=expected,
                evaluation_criteria=criteria,
                criteria_met=criteria_met,
                criteria_feedback=feedback,
                latency_ms=llm_res["latency_ms"],
                fallback_used=llm_res["fallback_used"],
            )
        )

        # Statistiques par catégorie
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0}
        category_stats[cat]["total"] += 1
        if criteria_met:
            category_stats[cat]["passed"] += 1

    total_duration = round(time.perf_counter() - start_bench_time, 2)
    passed_total = sum(1 for r in results if r.criteria_met)
    success_rate = round((passed_total / len(results) * 100), 2) if results else 0.0

    return LLMEvalSummary(
        total_questions=len(all_questions),
        evaluated_questions=len(results),
        passed_count=passed_total,
        success_rate_percent=success_rate,
        categories=category_stats,
        total_duration_seconds=total_duration,
        results=results,
    )
