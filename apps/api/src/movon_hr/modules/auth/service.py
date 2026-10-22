import re
import uuid
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from fastapi import BackgroundTasks, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from movon_hr.core.identity import AuthSession, Employee, Tenant
from movon_hr.core.mailer import send_email
from movon_hr.core.security import (
    hash_password_async,
    needs_rehash,
    password_policy_error,
    verify_password_async,
)
from movon_hr.core.settings import settings
from movon_hr.modules.audit.service import audit
from movon_hr.modules.auth.models import LoginAttempt, PasswordReset
from movon_hr.modules.auth.schemas import (
    AcceptInviteIn,
    ChangePasswordIn,
    InviteIn,
    InviteOut,
    InvitePreviewOut,
    LoginIn,
    MeOut,
    ResetPasswordIn,
    ResetPreviewOut,
    SignupIn,
    TenantOut,
)
from movon_hr.modules.employees import service as employees_service
from movon_hr.modules.employees.models import Invitation
from movon_hr.modules.notifications.service import notify
from movon_hr.modules.settings import service as settings_service
from movon_hr.modules.settings.models import CalendarSettings, WorkLocation

# Sessions expire after this absolute lifetime (no idle timeout).
SESSION_TTL = timedelta(hours=12)
# Login throttling: block an email after too many failures inside the window.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW = timedelta(minutes=15)
INVITE_TTL = timedelta(days=7)
RESET_TTL = timedelta(hours=1)
# Signup's primary location: the old OfficeLocation defaults, renamed.
DEFAULT_OFFICE = {"latitude": -6.2, "longitude": 106.8166, "radius_meters": 300}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# Before the tenant is known (login, tokens) every lookup is explicitly cross-tenant.
CROSS_TENANT = {"cross_tenant": True}

INVALID_LOGIN = "Email atau kata sandi salah"
EMAIL_TAKEN = "Email kerja sudah digunakan"
INVITE_NOT_FOUND = "Undangan tidak ditemukan"
INVITE_EXPIRED = "Undangan sudah kedaluwarsa. Minta HR mengirim undangan baru."
INVITE_USED = "Undangan sudah dipakai. Masuk dengan email dan kata sandi Anda."
RESET_NOT_FOUND = "Tautan atur ulang tidak valid"
RESET_GONE = "Tautan atur ulang sudah tidak berlaku"

_dummy_hash: str | None = None


async def dummy_hash() -> str:
    """A real hash to verify against for unknown emails, so timing does not reveal them."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = await hash_password_async(token_urlsafe(16))
    return _dummy_hash


def app_url(path: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}{path}"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure or settings.environment == "production",
        max_age=int(SESSION_TTL.total_seconds()),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")


def check_password_policy(password: str) -> None:
    error = password_policy_error(password)
    if error:
        raise HTTPException(422, error)


async def employee_by_email(db: AsyncSession, email: str) -> Employee | None:
    return await db.scalar(
        select(Employee)
        .where(func.lower(Employee.email) == email)
        .execution_options(**CROSS_TENANT)
    )


def bind_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    db.info["tenant_id"] = tenant_id


def create_session(db: AsyncSession, employee: Employee) -> str:
    token = token_urlsafe(32)
    db.add(
        AuthSession(
            token=token, employee_id=employee.id, expires_at=datetime.now(UTC) + SESSION_TTL
        )
    )
    return token


async def me(db: AsyncSession, user: Employee) -> MeOut:
    tenant = await db.get_one(Tenant, user.tenant_id)
    user_out = (await employees_service.to_out(db, [user]))[0]
    return MeOut(user=user_out, tenant=TenantOut.model_validate(tenant))


# --- Signup and login ---


def slugify_company(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:40] or f"perusahaan-{uuid.uuid4().hex[:8]}"


async def signup(db: AsyncSession, payload: SignupIn) -> tuple[MeOut, str]:
    """New company: tenant, primary location, calendar settings and its HR admin."""
    email = payload.email.strip().lower()
    check_password_policy(payload.password)
    if await employees_service.email_taken(db, email):
        raise HTTPException(409, EMAIL_TAKEN)
    slug = payload.slug.strip().lower() if payload.slug else slugify_company(payload.company_name)
    if not SLUG.fullmatch(slug):
        raise HTTPException(422, "Slug perusahaan hanya boleh huruf, angka, dan tanda hubung")
    taken = await db.scalar(
        select(Tenant.id).where(Tenant.slug == slug).execution_options(**CROSS_TENANT)
    )
    if taken is not None:
        raise HTTPException(409, "Slug perusahaan sudah digunakan")
    tenant = Tenant(name=payload.company_name.strip(), slug=slug)
    db.add(tenant)
    await db.flush()
    bind_tenant(db, tenant.id)
    office = WorkLocation(name="Kantor Pusat", is_primary=True, **DEFAULT_OFFICE)
    db.add_all([office, CalendarSettings()])
    await db.flush()
    admin = Employee(
        name=payload.admin_name.strip(),
        email=email,
        role="hr_admin",
        department="Human Resources",
        title="HR Admin",
        status="active",
        salary=0,
        password_hash=await hash_password_async(payload.password),
        work_location_id=office.id,
    )
    db.add(admin)
    await db.flush()
    token = create_session(db, admin)
    await audit(db, "auth.signup", admin, str(tenant.id))
    return await me(db, admin), token


async def raise_if_locked_out(db: AsyncSession, email: str, message: str) -> None:
    """Password guesses per email, shared by login and change-password."""
    failures = await db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.email == email,
            LoginAttempt.attempted_at > datetime.now(UTC) - LOGIN_ATTEMPT_WINDOW,
        )
        .execution_options(**CROSS_TENANT)
    )
    if (failures or 0) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, message)


async def record_failed_attempt(db: AsyncSession, email: str) -> None:
    db.add(LoginAttempt(email=email))
    await db.commit()  # keep the failure: get_db rolls back on the error the caller raises


async def clear_failed_attempts(db: AsyncSession, email: str) -> None:
    await db.execute(
        delete(LoginAttempt).where(LoginAttempt.email == email).execution_options(**CROSS_TENANT)
    )


async def login(db: AsyncSession, payload: LoginIn) -> tuple[MeOut, str]:
    email = payload.email.strip().lower()
    await raise_if_locked_out(
        db, email, "Terlalu banyak percobaan masuk. Coba lagi dalam beberapa menit."
    )
    user = await employee_by_email(db, email)
    # Always verify against a real hash, then give every failure the same error.
    reference_hash = user.password_hash if user else await dummy_hash()
    password_ok = await verify_password_async(payload.password, reference_hash)
    if user is None or not password_ok or user.status != "active":
        await record_failed_attempt(db, email)
        raise HTTPException(401, INVALID_LOGIN)
    bind_tenant(db, user.tenant_id)
    await clear_failed_attempts(db, email)
    # Transparently upgrade legacy/weak hashes on successful login.
    if needs_rehash(user.password_hash):
        user.password_hash = await hash_password_async(payload.password)
    token = create_session(db, user)
    await audit(db, "auth.login", user, str(user.id))
    return await me(db, user), token


async def logout(db: AsyncSession, user: Employee, token: str) -> None:
    await db.execute(delete(AuthSession).where(AuthSession.token == token))
    await audit(db, "auth.logout", user, str(user.id))


# --- Invitations ---


async def create_invite(db: AsyncSession, user: Employee, payload: InviteIn) -> InviteOut:
    """Commits before sending: the invitation stays even when the email fails (plan R4)."""
    email = payload.email.strip().lower()
    if await employees_service.email_taken(db, email):
        raise HTTPException(409, EMAIL_TAKEN)
    # Not validated (bug kept, see the plan); an id the FK cannot hold is dropped.
    location_id = employees_service.parse_id(payload.work_location_id)
    if location_id not in await settings_service.locations_by_id(db):
        location_id = None
    invitation = Invitation(
        token=token_urlsafe(24),
        email=email,
        name=payload.name.strip(),
        role=payload.role,
        department=payload.department.strip(),
        title=payload.title.strip(),
        salary=payload.salary,
        invited_by=user.id,
        expires_at=datetime.now(UTC) + INVITE_TTL,
        is_remote=payload.is_remote,
        work_location_id=location_id,
    )
    db.add(invitation)
    await audit(db, "invite.created", user, email)
    company = (await db.get_one(Tenant, user.tenant_id)).name
    await db.commit()
    invite_url = app_url(f"/invite?token={invitation.token}")
    ok = await send_email(
        email,
        f"Undangan Teamku — {company}",
        (
            f"Halo {invitation.name},\n\n"
            f"{user.name} mengundang Anda bergabung di {company}.\n"
            f"Aktifkan akun: {invite_url}\n"
            "Undangan berlaku 7 hari.\n"
        ),
        kind="invite",
    )
    if not ok:
        await audit(db, "invite.email_failed", user, email)
    return InviteOut(
        email=email,
        expires_at=invitation.expires_at,
        invite_url=invite_url,
        email_status="sent" if ok else "failed",
    )


async def open_invitation(db: AsyncSession, token: str) -> tuple[Invitation, str]:
    """The invitation behind ``token`` and its company name; 404 unknown, 410 used or expired."""
    row = (
        await db.execute(
            select(Invitation, Tenant.name)
            .join(Tenant, Tenant.id == Invitation.tenant_id)
            .where(Invitation.token == token)
            .execution_options(**CROSS_TENANT)
        )
    ).first()
    if row is None:
        raise HTTPException(404, INVITE_NOT_FOUND)
    invitation, company = row
    if invitation.accepted_at:
        raise HTTPException(410, INVITE_USED)
    if invitation.expires_at <= datetime.now(UTC):
        raise HTTPException(410, INVITE_EXPIRED)
    return invitation, company


async def preview_invite(db: AsyncSession, token: str) -> InvitePreviewOut:
    invitation, company = await open_invitation(db, token)
    bind_tenant(db, invitation.tenant_id)
    inviter = await db.get(Employee, invitation.invited_by)
    return InvitePreviewOut(
        email=invitation.email,
        name=invitation.name,
        company=company,
        role=invitation.role,
        department=invitation.department,
        title=invitation.title,
        invited_by=inviter.name if inviter else None,
        expires_at=invitation.expires_at,
    )


async def accept_invite(db: AsyncSession, payload: AcceptInviteIn) -> tuple[MeOut, str]:
    invitation, _ = await open_invitation(db, payload.token)
    check_password_policy(payload.password)
    if await employee_by_email(db, invitation.email):
        raise HTTPException(409, EMAIL_TAKEN)
    bind_tenant(db, invitation.tenant_id)
    employee = Employee(
        name=(payload.name or invitation.name).strip(),
        email=invitation.email,
        role=invitation.role,
        department=invitation.department,
        title=invitation.title,
        status="active",
        salary=invitation.salary,
        password_hash=await hash_password_async(payload.password),
        is_remote=invitation.is_remote,
        work_location_id=invitation.work_location_id,
    )
    db.add(employee)
    await db.flush()
    invitation.accepted_at = datetime.now(UTC)
    token = create_session(db, employee)
    await notify(
        db,
        employee.id,
        "Akun Anda aktif",
        "Undangan sudah diterima. Selamat datang.",
        "/app/overview",
    )
    await audit(db, "invite.accepted", employee, invitation.email)
    return await me(db, employee), token


# --- Passwords ---


async def forgot_password(db: AsyncSession, email: str, background_tasks: BackgroundTasks) -> None:
    """Same answer whether or not the account exists; the email goes out after the commit."""
    email = email.strip().lower()
    user = await employee_by_email(db, email)
    if user is None or user.status != "active":
        return
    bind_tenant(db, user.tenant_id)
    reset = PasswordReset(
        token=token_urlsafe(24), employee_id=user.id, expires_at=datetime.now(UTC) + RESET_TTL
    )
    db.add(reset)
    reset_url = app_url(f"/reset-password?token={reset.token}")
    background_tasks.add_task(
        send_email,
        email,
        "Atur ulang kata sandi Teamku",
        (
            f"Halo {user.name},\n\n"
            f"Gunakan tautan ini untuk mengatur ulang kata sandi: {reset_url}\n"
            "Tautan berlaku 1 jam. Abaikan email ini jika Anda tidak memintanya.\n"
        ),
        kind="password_reset",
    )
    await audit(db, "auth.password_reset_requested", user, str(user.id))


async def open_reset(db: AsyncSession, token: str) -> tuple[PasswordReset, Employee]:
    """The usable reset behind ``token`` and its employee; 404 unknown, 410 used or expired."""
    reset = await db.scalar(
        select(PasswordReset).where(PasswordReset.token == token).execution_options(**CROSS_TENANT)
    )
    if reset is None:
        raise HTTPException(404, RESET_NOT_FOUND)
    if reset.used_at or reset.expires_at <= datetime.now(UTC):
        raise HTTPException(410, RESET_GONE)
    bind_tenant(db, reset.tenant_id)
    user = await db.get(Employee, reset.employee_id)
    if user is None or user.status != "active":
        raise HTTPException(404, RESET_NOT_FOUND)
    return reset, user


async def preview_reset(db: AsyncSession, token: str) -> ResetPreviewOut:
    _, user = await open_reset(db, token)
    return ResetPreviewOut(email=user.email)


async def reset_password(db: AsyncSession, payload: ResetPasswordIn) -> tuple[MeOut, str]:
    reset, user = await open_reset(db, payload.token)
    check_password_policy(payload.password)
    user.password_hash = await hash_password_async(payload.password)
    reset.used_at = datetime.now(UTC)
    # The lockout copy offers a reset as the way out, so it must lift the lock.
    await clear_failed_attempts(db, user.email.strip().lower())
    await employees_service.revoke_sessions(db, user.id)
    token = create_session(db, user)
    await audit(db, "auth.password_reset", user, str(user.id))
    return await me(db, user), token


async def change_password(
    db: AsyncSession, user: Employee, token: str, payload: ChangePasswordIn
) -> None:
    email = user.email.strip().lower()
    await raise_if_locked_out(
        db, email, "Terlalu banyak percobaan. Coba lagi dalam beberapa menit."
    )
    if not await verify_password_async(payload.current_password, user.password_hash):
        await record_failed_attempt(db, email)
        # 422, not 401: the session is valid; 401 makes the web client log the user out.
        raise HTTPException(422, "Kata sandi saat ini salah")
    await clear_failed_attempts(db, email)
    if payload.new_password == payload.current_password:
        raise HTTPException(422, "Kata sandi baru harus berbeda dari kata sandi lama")
    check_password_policy(payload.new_password)
    user.password_hash = await hash_password_async(payload.new_password)
    # Force re-login on other devices; keep the current session active.
    await employees_service.revoke_sessions(db, user.id, keep_token=token)
    await audit(db, "auth.password_changed", user, str(user.id))
