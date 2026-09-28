from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.docs.dashboard import get_dashboard_docs
from app.core.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse, StageResultCountItem, WeaknessKeywordItem
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse, **get_dashboard_docs)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    (
        application_count,
        completed_retrospect_count,
        self_blame_count,
        most_failed_stage,
        weakness_keywords,
        stage_results,
    ) = dashboard_service.get_dashboard(db, current_user.user_id)
    return DashboardResponse(
        application_count=application_count,
        completed_retrospect_count=completed_retrospect_count,
        self_blame_count=self_blame_count,
        most_failed_stage=most_failed_stage,
        weakness_keywords=[
            WeaknessKeywordItem(keyword=keyword, count=count) for keyword, count in weakness_keywords
        ],
        stage_results=[
            StageResultCountItem(
                stage=result.stage,
                pass_count=result.pass_count,
                fail_count=result.fail_count,
                total_count=result.total_count,
            )
            for result in stage_results
        ],
    )
