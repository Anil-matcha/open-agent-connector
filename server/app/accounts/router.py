from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts import mailer, service
from app.accounts.cookies import cookie_name, cookie_secure, csrf_ok, read_session_cookie
from app.accounts.models import AccountSession, User
from app.core.config import settings
from app.db.session import get_db

router = APIRouter(prefix="/accounts", tags=["Accounts"])


def _error(err: service.AccountError) -> HTTPException:
    return HTTPException(status_code=err.status, detail={"error": {"code": err.code, "message": err.message}})


async def require_csrf_header(request: Request) -> None:
    if not csrf_ok(request):
        raise HTTPException(status_code=403, detail={"error": {"code": "CSRF", "message": "Missing request header."}})


class SignupInput(BaseModel):
    email: str
    password: str
    inviteCode: Optional[str] = None


class LoginInput(BaseModel):
    email: str
    password: str
    remember: bool = True


class VerifyInput(BaseModel):
    email: str
    code: str
    remember: bool = True


class ForgotInput(BaseModel):
    email: str


class ResetInput(BaseModel):
    email: str
    code: str
    password: str


class ChangePasswordInput(BaseModel):
    currentPassword: str
    newPassword: str


class DeleteInput(BaseModel):
    password: str


def _login_response(user: User, token: str, max_age: int, body: Optional[dict] = None) -> JSONResponse:
    response = JSONResponse(content=body or {"user": _user_dict(user)})
    response.set_cookie(
        key=cookie_name(), value=token, max_age=max_age, path="/",
        httponly=True, secure=cookie_secure(), samesite="lax",
    )
    return response


def _clear_cookie(response: JSONResponse) -> JSONResponse:
    response.delete_cookie(key=cookie_name(), path="/", httponly=True, secure=cookie_secure(), samesite="lax")
    return response


def _user_dict(user: User) -> dict:
    return {"email": user.email, "tenantId": user.tenant_id, "createdAt": user.created_at}


async def current_session(request: Request, db: AsyncSession = Depends(get_db)):
    token = read_session_cookie(request)
    found = await service.get_session_user(db, token)
    if not found:
        raise HTTPException(status_code=401, detail={"error": {"code": "NOT_AUTHENTICATED", "message": "Please sign in."}})
    session, user = found
    return token, session, user


@router.get("/config")
async def accounts_config():
    mode = service.effective_signup_mode()
    return {"signupMode": mode, "emailVerification": mailer.email_enabled(),
            "passwordMinLength": service.MIN_PASSWORD}


@router.post("/signup", dependencies=[Depends(require_csrf_header)])
async def signup(data: SignupInput, request: Request, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        status, pending = await service.signup(db, data.email, data.password, data.inviteCode, service.client_ip(request))
    except service.AccountError as err:
        raise _error(err)
    if pending:
        user, code = pending
        background.add_task(service.queue_email, user, code, "verify_email")
    return JSONResponse(status_code=201 if status == "created" else 202, content={"status": status})


@router.post("/verify-email", dependencies=[Depends(require_csrf_header)])
async def verify_email(data: VerifyInput, request: Request, db: AsyncSession = Depends(get_db)):
    ip = service.client_ip(request)
    try:
        user = await service.verify_email(db, data.email, data.code, ip)
    except service.AccountError as err:
        raise _error(err)
    token, max_age = await service.create_session(db, user, ip, request.headers.get("user-agent"), data.remember)
    return _login_response(user, token, max_age)


@router.post("/login", dependencies=[Depends(require_csrf_header)])
async def login(data: LoginInput, request: Request, db: AsyncSession = Depends(get_db)):
    ip = service.client_ip(request)
    try:
        user = await service.login(db, data.email, data.password, ip)
    except service.AccountError as err:
        raise _error(err)
    token, max_age = await service.create_session(db, user, ip, request.headers.get("user-agent"), data.remember)
    return _login_response(user, token, max_age)


@router.post("/logout", dependencies=[Depends(require_csrf_header)])
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    await service.revoke_session(db, read_session_cookie(request))
    return _clear_cookie(JSONResponse(content={"status": "signed_out"}))


@router.get("/me")
async def me(ctx=Depends(current_session)):
    _, _, user = ctx
    return {"user": _user_dict(user)}


@router.post("/forgot-password", dependencies=[Depends(require_csrf_header)])
async def forgot_password(data: ForgotInput, request: Request, background: BackgroundTasks,
                          db: AsyncSession = Depends(get_db)):
    try:
        pending = await service.forgot_password(db, data.email, service.client_ip(request))
    except service.AccountError as err:
        raise _error(err)
    if pending:
        user, code = pending
        background.add_task(service.queue_email, user, code, "reset_password")
    # Same answer whether or not the account exists
    return JSONResponse(status_code=202, content={"status": "if_account_exists_code_sent"})


@router.post("/resend-verification", dependencies=[Depends(require_csrf_header)])
async def resend_verification(data: ForgotInput, request: Request, background: BackgroundTasks,
                              db: AsyncSession = Depends(get_db)):
    try:
        pending = await service.resend_verification(db, data.email, service.client_ip(request))
    except service.AccountError as err:
        raise _error(err)
    if pending:
        user, code = pending
        background.add_task(service.queue_email, user, code, "verify_email")
    return JSONResponse(status_code=202, content={"status": "if_unverified_code_sent"})


@router.post("/reset-password", dependencies=[Depends(require_csrf_header)])
async def reset_password(data: ResetInput, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        await service.reset_password(db, data.email, data.code, data.password, service.client_ip(request))
    except service.AccountError as err:
        raise _error(err)
    return {"status": "password_reset"}


@router.post("/change-password", dependencies=[Depends(require_csrf_header)])
async def change_password(data: ChangePasswordInput, ctx=Depends(current_session), db: AsyncSession = Depends(get_db)):
    token, _, user = ctx
    try:
        await service.change_password(db, user, data.currentPassword, data.newPassword, keep_token=token)
    except service.AccountError as err:
        raise _error(err)
    return {"status": "password_changed"}


@router.post("/delete", dependencies=[Depends(require_csrf_header)])
async def delete_account(data: DeleteInput, ctx=Depends(current_session), db: AsyncSession = Depends(get_db)):
    _, _, user = ctx
    try:
        await service.delete_account(db, user, data.password)
    except service.AccountError as err:
        raise _error(err)
    return _clear_cookie(JSONResponse(content={"status": "deleted"}))
