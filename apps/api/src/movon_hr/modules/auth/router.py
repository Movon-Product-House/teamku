from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from movon_hr.core.auth import CurrentUser, require_role
from movon_hr.core.db import DB
from movon_hr.core.identity import Employee
from movon_hr.core.settings import settings
from movon_hr.modules.auth import service
from movon_hr.modules.auth.schemas import (
    AcceptInvite,
    ChangePassword,
    ForgotPassword,
    InviteInput,
    InviteOut,
    InvitePreview,
    Login,
    MeOut,
    ResetPassword,
    ResetPreview,
    ResetPreviewInput,
    Signup,
)
from movon_hr.modules.notifications.schemas import Ok

router = APIRouter()
HrAdmin = Annotated[Employee, Depends(require_role("hr_admin"))]


async def session_token(request: Request) -> str:
    """The caller's token, read the same way as ``current_user`` (which already checked it)."""
    return request.cookies.get(settings.session_cookie_name) or ""


SessionToken = Annotated[str, Depends(session_token)]


@router.post("/auth/signup")
async def signup(db: DB, payload: Signup, response: Response) -> MeOut:
    out, token = await service.signup(db, payload)
    service.set_session_cookie(response, token)
    return out


@router.post("/auth/login")
async def login(db: DB, payload: Login, response: Response) -> MeOut:
    out, token = await service.login(db, payload)
    service.set_session_cookie(response, token)
    return out


@router.post("/auth/logout")
async def logout(db: DB, user: CurrentUser, token: SessionToken, response: Response) -> Ok:
    await service.logout(db, user, token)
    service.clear_session_cookie(response)
    return Ok(ok=True)


@router.post("/invites")
async def create_invite(db: DB, user: HrAdmin, payload: InviteInput) -> InviteOut:
    return await service.create_invite(db, user, payload)


@router.get("/invites/{token}")
async def preview_invite(db: DB, token: str) -> InvitePreview:
    return await service.preview_invite(db, token)


@router.post("/auth/accept-invite")
async def accept_invite(db: DB, payload: AcceptInvite, response: Response) -> MeOut:
    out, token = await service.accept_invite(db, payload)
    service.set_session_cookie(response, token)
    return out


@router.post("/auth/forgot-password")
async def forgot_password(db: DB, payload: ForgotPassword, background_tasks: BackgroundTasks) -> Ok:
    await service.forgot_password(db, payload.email, background_tasks)
    return Ok(ok=True)


@router.post("/auth/reset-password/preview")
async def preview_reset(db: DB, payload: ResetPreviewInput) -> ResetPreview:
    # POST so the token stays out of the URL (and the access logs).
    return await service.preview_reset(db, payload.token)


@router.post("/auth/reset-password")
async def reset_password(db: DB, payload: ResetPassword, response: Response) -> MeOut:
    out, token = await service.reset_password(db, payload)
    service.set_session_cookie(response, token)
    return out


@router.post("/auth/change-password")
async def change_password(
    db: DB, user: CurrentUser, token: SessionToken, payload: ChangePassword
) -> Ok:
    await service.change_password(db, user, token, payload)
    return Ok(ok=True)


@router.get("/me")
async def me(db: DB, user: CurrentUser) -> MeOut:
    return await service.me(db, user)
