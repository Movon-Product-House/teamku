from fastapi import APIRouter

from movon_hr.core.auth import CurrentUser
from movon_hr.core.db import DB
from movon_hr.modules.dashboard import service
from movon_hr.modules.dashboard.schemas import DashboardOut

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard(db: DB, user: CurrentUser) -> DashboardOut:
    return await service.dashboard(db, user)
