"""API Dashboard & Indicateurs pour la Direction et les Responsables Académiques."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_staff
from ..models import (
    Application,
    ApplicationStatus,
    Conversation,
    Institution,
    InterviewAppointment,
    InterviewResult,
    InterviewStatus,
    JuryDecision,
    Message,
    Program,
    Role,
    User,
    VisitorSession,
)
from ..schemas import (
    DashboardStatsOut,
    FunnelStats,
    InstitutionStats,
    ProgramDemandItem,
)

logger = logging.getLogger("smartcampus.dashboard")

router = APIRouter(prefix="/dashboard", tags=["Tableau de bord & Statistiques"])


@router.get("/stats", response_model=DashboardStatsOut)
def get_dashboard_stats(
    institution: Optional[Institution] = Query(
        default=None,
        description="Filtre optionnel par institution (IIT / ISB) pour la Direction / Admin"
    ),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Tableau de bord décisionnel et indicateurs de performance (Direction, Responsables IIT/ISB, Responsable Entretien).
    
    Couvre :
    - Entonnoir de conversion : Visiteurs -> Conversations -> Orientations -> Préinscriptions -> Entretiens -> Inscriptions
    - Comparatif IIT vs ISB
    - Formations les plus demandées
    - Statuts des candidatures et des entretiens
    - Dossiers en attente ou abandonnés (drafts)
    """
    effective_inst = institution
    if user.role == Role.responsable_academique_iit:
        effective_inst = Institution.IIT
    elif user.role == Role.responsable_academique_isb:
        effective_inst = Institution.ISB

    # 1. Volumes globaux
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_convs = db.scalar(select(func.count(Conversation.id))) or 0
    total_msgs = db.scalar(select(func.count(Message.id))) or 0
    total_visitors = db.scalar(select(func.count(VisitorSession.id))) or 0

    # 2. Candidatures
    app_stmt = select(Application).join(Application.program)
    if effective_inst:
        app_stmt = app_stmt.where(Program.institution == effective_inst)

    all_apps = db.scalars(app_stmt).all()

    apps_by_status = {s.value: 0 for s in ApplicationStatus}
    for app in all_apps:
        apps_by_status[app.status.value] = apps_by_status.get(app.status.value, 0) + 1

    preinscriptions_submitted = sum(
        apps_by_status.get(s.value, 0)
        for s in (ApplicationStatus.submitted, ApplicationStatus.under_review, ApplicationStatus.accepted, ApplicationStatus.rejected)
    )
    inscriptions_accepted = apps_by_status.get(ApplicationStatus.accepted.value, 0)
    pending_or_abandoned = apps_by_status.get(ApplicationStatus.draft.value, 0)

    # 3. Entretiens et résultats
    interview_stmt = select(InterviewAppointment).join(InterviewAppointment.application).join(Application.program)
    if effective_inst:
        interview_stmt = interview_stmt.where(Program.institution == effective_inst)

    all_interviews = db.scalars(interview_stmt).all()
    interviews_by_status = {s.value: 0 for s in InterviewStatus}
    for it in all_interviews:
        interviews_by_status[it.status.value] = interviews_by_status.get(it.status.value, 0) + 1

    interviews_scheduled = len(all_interviews)
    interviews_completed = interviews_by_status.get(InterviewStatus.effectue.value, 0)

    results_stmt = select(InterviewResult).join(InterviewResult.application).join(Application.program)
    if effective_inst:
        results_stmt = results_stmt.where(Program.institution == effective_inst)
    all_results = db.scalars(results_stmt).all()
    decisions_by_type = {d.value: 0 for d in JuryDecision}
    for res in all_results:
        decisions_by_type[res.decision.value] = decisions_by_type.get(res.decision.value, 0) + 1

    # 4. Taux de transformation du funnel
    conv_rate_preinscr = round((preinscriptions_submitted / max(total_visitors, 1)) * 100, 2)
    conv_rate_interview = round((interviews_completed / max(preinscriptions_submitted, 1)) * 100, 2)
    conv_rate_inscr = round((inscriptions_accepted / max(preinscriptions_submitted, 1)) * 100, 2)

    funnel = FunnelStats(
        visitors_sessions=total_visitors,
        conversations=total_convs,
        orientations_advised=total_convs,
        preinscriptions_submitted=preinscriptions_submitted,
        interviews_scheduled=interviews_scheduled,
        interviews_completed=interviews_completed,
        inscriptions_accepted=inscriptions_accepted,
        conversion_rate_preinscription_pct=conv_rate_preinscr,
        conversion_rate_interview_pct=conv_rate_interview,
        conversion_rate_inscription_pct=conv_rate_inscr,
    )

    # 5. Comparatif IIT vs ISB
    comparative = {}
    for inst in (Institution.IIT, Institution.ISB):
        prog_count = db.scalar(select(func.count(Program.id)).where(Program.institution == inst, Program.is_active.is_(True))) or 0
        inst_apps_all = db.scalars(select(Application).join(Application.program).where(Program.institution == inst)).all()

        comparative[inst.value] = InstitutionStats(
            total_programs=prog_count,
            total_applications=len(inst_apps_all),
            submitted_applications=sum(1 for a in inst_apps_all if a.status != ApplicationStatus.draft),
            accepted_applications=sum(1 for a in inst_apps_all if a.status == ApplicationStatus.accepted)
        )

    # 6. Formations les plus demandées
    demand_stmt = (
        select(Program, func.count(Application.id).label("app_count"))
        .outerjoin(Application, Application.program_id == Program.id)
        .group_by(Program.id)
    )
    if effective_inst:
        demand_stmt = demand_stmt.where(Program.institution == effective_inst)
    demand_stmt = demand_stmt.order_by(func.count(Application.id).desc()).limit(10)

    demand_rows = db.execute(demand_stmt).all()
    most_demanded = [
        ProgramDemandItem(
            program_id=prog.id,
            slug=prog.slug,
            name=prog.name,
            institution=prog.institution,
            level=prog.level,
            applications_count=count
        )
        for prog, count in demand_rows
    ]

    scope_name = "global"
    if effective_inst:
        scope_name = effective_inst.value
    elif user.role == Role.responsable_entretien:
        scope_name = "entretiens"

    return DashboardStatsOut(
        scope=scope_name,
        institution_filter=effective_inst,
        total_users=total_users,
        total_conversations=total_convs,
        total_messages=total_msgs,
        funnel=funnel,
        applications_by_status=apps_by_status,
        interviews_by_status=interviews_by_status,
        decisions_by_type=decisions_by_type,
        comparative_iit_vs_isb=comparative,
        most_demanded_programs=most_demanded,
        pending_or_abandoned_dossiers_count=pending_or_abandoned
    )
