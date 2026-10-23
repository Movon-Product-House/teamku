from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from movon_hr.core.auth import CurrentUser, require_role
from movon_hr.core.db import DB
from movon_hr.core.identity import Employee
from movon_hr.core.settings import settings
from movon_hr.modules.auth import service
from movon_hr.modules.auth.schemas import (
    AcceptInviteIn,
    ChangePasswordIn,
    ForgotPasswordIn,
    InviteIn,
    InviteOut,
    InvitePreviewOut,
    LoginIn,
    MeOut,
    ResetPasswordIn,
    ResetPreviewIn,
    ResetPreviewOut,
    SignupIn,
)
from movon_hr.modules.notifications.schemas import OkOut

router = APIRouter(tags=["auth"])
HrAdmin = Annotated[Employee, Depends(require_role("hr_admin"))]


async def session_token(request: Request) -> str:
    """The caller's token, read the same way as ``current_user`` (which already checked it)."""
    return request.cookies.get(settings.session_cookie_name) or ""


SessionToken = Annotated[str, Depends(session_token)]


@router.post("/auth/signup")
async def signup(db: DB, payload: SignupIn, response: Response) -> MeOut:
    out, token = await service.signup(db, payload)
    service.set_session_cookie(response, token)
    return out


@router.post("/auth/login")
async def login(db: DB, payload: LoginIn, response: Response) -> MeOut:
    out, token = await service.login(db, payload)
    service.set_session_cookie(response, token)
    return out


@router.post("/auth/logout")
async def logout(db: DB, user: CurrentUser, token: SessionToken, response: Response) -> OkOut:
    await service.logout(db, user, token)
    service.clear_session_cookie(response)
    return OkOut(ok=True)


@router.post("/invites")
async def create_invite(db: DB, user: HrAdmin, payload: InviteIn) -> InviteOut:
    return await service.create_invite(db, user, payload)


@router.get("/invites/{token}")
async def get_invite(db: DB, token: str) -> InvitePreviewOut:
    return await service.preview_invite(db, token)


@router.post("/auth/accept-invite")
async def accept_invite(db: DB, payload: AcceptInviteIn, response: Response) -> MeOut:
    out, token = await service.accept_invite(db, payload)
    service.set_session_cookie(response, token)
    return out


@router.post("/auth/forgot-password")
async def forgot_password(
    db: DB, payload: ForgotPasswordIn, background_tasks: BackgroundTasks
) -> OkOut:
    await service.forgot_password(db, payload.email, background_tasks)
    return OkOut(ok=True)


@router.post("/auth/reset-password/preview")
async def preview_reset_password(db: DB, payload: ResetPreviewIn) -> ResetPreviewOut:
    # POST so the token stays out of the URL (and the access logs).
    return await service.preview_reset(db, payload.token)


@router.post("/auth/reset-password")
async def reset_password(db: DB, payload: ResetPasswordIn, response: Response) -> MeOut:
    out, token = await service.reset_password(db, payload)
    service.set_session_cookie(response, token)
    return out


@router.post("/auth/change-password")
async def change_password(
    db: DB, user: CurrentUser, token: SessionToken, payload: ChangePasswordIn
) -> OkOut:
    await service.change_password(db, user, token, payload)
    return OkOut(ok=True)


@router.get("/me")
async def get_me(db: DB, user: CurrentUser) -> MeOut:
    return await service.me(db, user)
