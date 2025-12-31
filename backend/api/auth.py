# backend/api/auth.py
"""OAuth 인증 API (Google, Kakao)"""
import os
from typing import Optional
from datetime import datetime, timedelta
import secrets
import hashlib

from fastapi import APIRouter, HTTPException, Response, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx

from backend.services.database import postgres_connection
from common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# 환경변수
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID", "")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "")
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:15173")

# 세션 저장소 (간단한 인메모리, 프로덕션에서는 Redis 사용)
sessions: dict[str, dict] = {}


class LoginResponse(BaseModel):
    success: bool
    user: Optional[dict] = None
    message: str = ""


def create_session(user_data: dict) -> str:
    """세션 생성"""
    session_id = secrets.token_hex(32)
    sessions[session_id] = {
        "user": user_data,
        "created_at": datetime.now().isoformat()
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """세션 조회"""
    return sessions.get(session_id)


def ensure_users_table():
    """users 테이블 생성"""
    try:
        with postgres_connection() as pg:
            pg.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT,
                    nickname TEXT,
                    password_hash TEXT,
                    provider TEXT,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # 새 컬럼 추가 (기존 테이블 호환)
            pg.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
            pg.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname TEXT")
            pg.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS xp INTEGER DEFAULT 0")
            pg.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS level INTEGER DEFAULT 1")
            pg.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE")
            # 관리자 설정
            pg.execute("UPDATE users SET is_admin = TRUE WHERE email IN ('naca11@mobigen.com', 'naca11@naver.com')")
            
            # 사용자별 문제 세트 할당 테이블
            pg.execute("""
                CREATE TABLE IF NOT EXISTS user_problem_sets (
                    user_id TEXT NOT NULL,
                    session_date DATE NOT NULL,
                    data_type VARCHAR(20) NOT NULL,
                    set_index INTEGER NOT NULL,
                    assigned_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (user_id, session_date, data_type)
                )
            """)
    except Exception as e:
        logger.error(f"Failed to create users table: {e}")


# 시작 시 테이블 생성
ensure_users_table()


# =============================================
# 이메일/비밀번호 인증
# =============================================
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


def hash_password(password: str) -> str:
    """비밀번호 해시 (SHA256 + salt)"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, password_hash: str) -> bool:
    """비밀번호 검증"""
    try:
        salt, hashed = password_hash.split(":")
        return hashlib.sha256((password + salt).encode()).hexdigest() == hashed
    except Exception:
        return False


@router.post("/register")
async def register(req: RegisterRequest, response: Response):
    """회원가입"""
    if not req.email or not req.password or not req.name:
        raise HTTPException(400, "이메일, 비밀번호, 이름을 모두 입력해주세요")
    
    if len(req.password) < 4:
        raise HTTPException(400, "비밀번호는 4자 이상이어야 합니다")
    
    try:
        with postgres_connection() as pg:
            # 이메일 중복 확인
            df = pg.fetch_df("SELECT id FROM users WHERE email = %s", [req.email])
            if len(df) > 0:
                raise HTTPException(400, "이미 등록된 이메일입니다")
            
            # 사용자 생성
            user_id = f"local_{secrets.token_hex(8)}"
            pw_hash = hash_password(req.password)
            nickname = req.name  # 초기 닉네임은 이름과 동일
            
            pg.execute("""
                INSERT INTO users (id, email, name, nickname, password_hash, provider)
                VALUES (%s, %s, %s, %s, %s, 'local')
            """, (user_id, req.email, req.name, nickname, pw_hash))
        
        # 세션 생성
        session_id = create_session({
            "id": user_id,
            "email": req.email,
            "name": req.name,
            "nickname": nickname,
            "provider": "local"
        })
        
        response.set_cookie("session_id", session_id, max_age=86400*7, httponly=True)
        return {"success": True, "user": {"id": user_id, "email": req.email, "name": req.name, "nickname": nickname}}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(500, "회원가입에 실패했습니다")


@router.post("/login")
async def login(req: LoginRequest, response: Response):
    """로그인"""
    if not req.email or not req.password:
        raise HTTPException(400, "이메일과 비밀번호를 입력해주세요")
    
    try:
        with postgres_connection() as pg:
            df = pg.fetch_df("""
                SELECT id, email, name, nickname, password_hash, provider 
                FROM users WHERE email = %s
            """, [req.email])
            
            if len(df) == 0:
                raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다")
            
            row = df.iloc[0]
            user_id = row['id']
            email = row['email']
            name = row['name']
            nickname = row.get('nickname', name)
            pw_hash = row['password_hash']
            provider = row['provider']
            
            # OAuth 사용자는 비밀번호 로그인 불가
            if provider != "local":
                raise HTTPException(400, f"{provider}로 가입한 계정입니다. {provider} 로그인을 이용해주세요")
            
            if not pw_hash or not verify_password(req.password, pw_hash):
                raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다")
        
        # 세션 생성
        session_id = create_session({
            "id": user_id,
            "email": email,
            "name": name,
            "nickname": nickname,
            "provider": "local"
        })
        
        response.set_cookie("session_id", session_id, max_age=86400*7, httponly=True)
        return {"success": True, "user": {"id": user_id, "email": email, "name": name, "nickname": nickname}}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(500, "로그인에 실패했습니다")


# =============================================
# Google OAuth
# =============================================
@router.get("/google/login")
async def google_login():
    """Google 로그인 시작"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(400, "Google OAuth not configured")
    
    redirect_uri = f"{FRONTEND_URL.replace('15173', '15174')}/auth/google/callback"
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=email%20profile"
    )
    return RedirectResponse(google_auth_url)


@router.get("/google/callback")
async def google_callback(code: str, response: Response):
    """Google OAuth 콜백"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(400, "Google OAuth not configured")
    
    redirect_uri = f"{FRONTEND_URL.replace('15173', '15174')}/auth/google/callback"
    
    # 토큰 교환
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
        )
        
        if token_res.status_code != 200:
            raise HTTPException(400, "Failed to get access token")
        
        tokens = token_res.json()
        access_token = tokens.get("access_token")
        
        # 사용자 정보 조회
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_res.status_code != 200:
            raise HTTPException(400, "Failed to get user info")
        
        user_info = user_res.json()
    
    # 사용자 저장/업데이트
    user_id = f"google_{user_info['id']}"
    save_user(user_id, user_info.get("email"), user_info.get("name"), "google")
    
    # 세션 생성
    session_id = create_session({
        "id": user_id,
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "provider": "google"
    })
    
    # 쿠키 설정 및 프론트엔드로 리다이렉트
    redirect = RedirectResponse(f"{FRONTEND_URL}?login=success")
    redirect.set_cookie("session_id", session_id, max_age=86400*7, httponly=True)
    return redirect


# =============================================
# Kakao OAuth
# =============================================
@router.get("/kakao/login")
async def kakao_login():
    """Kakao 로그인 시작"""
    if not KAKAO_CLIENT_ID:
        raise HTTPException(400, "Kakao OAuth not configured")
    
    redirect_uri = f"{FRONTEND_URL.replace('15173', '15174')}/auth/kakao/callback"
    kakao_auth_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
    )
    return RedirectResponse(kakao_auth_url)


@router.get("/kakao/callback")
async def kakao_callback(code: str, response: Response):
    """Kakao OAuth 콜백"""
    if not KAKAO_CLIENT_ID:
        raise HTTPException(400, "Kakao OAuth not configured")
    
    redirect_uri = f"{FRONTEND_URL.replace('15173', '15174')}/auth/kakao/callback"
    
    # 토큰 교환
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": KAKAO_CLIENT_ID,
                "client_secret": KAKAO_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "code": code
            }
        )
        
        if token_res.status_code != 200:
            raise HTTPException(400, "Failed to get access token")
        
        tokens = token_res.json()
        access_token = tokens.get("access_token")
        
        # 사용자 정보 조회
        user_res = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_res.status_code != 200:
            raise HTTPException(400, "Failed to get user info")
        
        user_info = user_res.json()
    
    # 사용자 저장/업데이트
    kakao_account = user_info.get("kakao_account", {})
    profile = kakao_account.get("profile", {})
    
    user_id = f"kakao_{user_info['id']}"
    email = kakao_account.get("email", f"{user_info['id']}@kakao.user")
    name = profile.get("nickname", "Kakao User")
    
    save_user(user_id, email, name, "kakao")
    
    # 세션 생성
    session_id = create_session({
        "id": user_id,
        "email": email,
        "name": name,
        "provider": "kakao"
    })
    
    # 쿠키 설정 및 프론트엔드로 리다이렉트
    redirect = RedirectResponse(f"{FRONTEND_URL}?login=success")
    redirect.set_cookie("session_id", session_id, max_age=86400*7, httponly=True)
    return redirect


# =============================================
# 공통 API
# =============================================
@router.get("/me")
async def get_me(request: Request):
    """현재 로그인 사용자 정보"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return {"logged_in": False}
    
    session = get_session(session_id)
    if not session:
        return {"logged_in": False}
    
    user = session["user"].copy()
    
    # DB에서 is_admin, xp, level 조회
    try:
        with postgres_connection() as pg:
            df = pg.fetch_df(
                "SELECT is_admin, xp, level FROM users WHERE id = %s",
                [user["id"]]
            )
            if len(df) > 0:
                user["is_admin"] = bool(df.iloc[0].get("is_admin", False))
                user["xp"] = int(df.iloc[0].get("xp", 0))
                user["level"] = int(df.iloc[0].get("level", 1))
    except Exception:
        user["is_admin"] = False
    
    return {"logged_in": True, "user": user}


@router.post("/logout")
async def logout(request: Request, response: Response):
    """로그아웃"""
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response.delete_cookie("session_id")
    return {"success": True}


@router.get("/status")
async def auth_status():
    """OAuth 설정 상태"""
    return {
        "google_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "kakao_configured": bool(KAKAO_CLIENT_ID)
    }


def save_user(user_id: str, email: str, name: str, provider: str):
    """사용자 저장/업데이트"""
    try:
        with postgres_connection() as pg:
            pg.execute("""
                INSERT INTO users (id, email, name, nickname, provider)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, nickname = EXCLUDED.nickname
            """, (user_id, email, name, name, provider))  # nickname = name 초기값
    except Exception as e:
        logger.error(f"Failed to save user: {e}")


class UpdateNicknameRequest(BaseModel):
    nickname: str


@router.patch("/nickname")
async def update_nickname(req: UpdateNicknameRequest, request: Request):
    """닉네임 변경"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401, "로그인이 필요합니다")
    
    session = get_session(session_id)
    if not session:
        raise HTTPException(401, "로그인이 필요합니다")
    
    user_id = session["user"]["id"]
    new_nickname = req.nickname.strip()
    
    if not new_nickname or len(new_nickname) < 2:
        raise HTTPException(400, "닉네임은 2자 이상이어야 합니다")
    
    try:
        with postgres_connection() as pg:
            pg.execute(
                "UPDATE users SET nickname = %s WHERE id = %s",
                (new_nickname, user_id)
            )
        
        # 세션 업데이트
        session["user"]["nickname"] = new_nickname
        
        return {"success": True, "nickname": new_nickname}
    except Exception as e:
        logger.error(f"Failed to update nickname: {e}")
        raise HTTPException(500, "닉네임 변경에 실패했습니다")



@router.delete("/account")
async def delete_account(request: Request, response: Response):
    """회원 탈퇴 - 자신의 계정 삭제"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401, "로그인이 필요합니다")
    
    session = get_session(session_id)
    if not session:
        raise HTTPException(401, "로그인이 필요합니다")
    
    user_id = session["user"]["id"]
    user_email = session["user"]["email"]
    
    try:
        with postgres_connection() as pg:
            # 관련 데이터 삭제 (submissions는 user_id 없음)
            pg.execute("DELETE FROM user_problem_sets WHERE user_id = %s", [user_id])
            pg.execute("DELETE FROM users WHERE id = %s", [user_id])
        
        # 세션 삭제
        if session_id in sessions:
            del sessions[session_id]
        
        response.delete_cookie("session_id")
        
        from backend.services.db_logger import db_log, LogCategory, LogLevel
        db_log(
            category=LogCategory.USER_ACTION,
            message=f"회원 탈퇴: {user_email}",
            level=LogLevel.WARNING,
            source="auth"
        )
        
        return {"success": True, "message": "계정이 삭제되었습니다"}
    except Exception as e:
        raise HTTPException(500, f"탈퇴 처리 실패: {str(e)}")
