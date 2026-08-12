from fastapi import APIRouter, Cookie, HTTPException, Response, status


from supabase_client import create_supabase_client
from auth import ACCESS_COOKIE, REFRESH_COOKIE, extract_user_data, get_session_value
from config import settings
from schemas import AuthResponse, LoginRequest, SignupRequest

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    cookie_options = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }

    # 15 minutes for the access token
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=60 * 60, 
        **cookie_options,
    )

    # 30 days for the refresh token, so the user has to login again after 30 days
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=60 * 60 * 24 * 30,
        **cookie_options,
    )

def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")

@router.post("/signup",response_model=AuthResponse,status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, response: Response):
    try:
        supabase = create_supabase_client()
        auth_response = supabase.auth.sign_up({
                "email": str(payload.email),
                "password": payload.password,
                "options": {"data": {"name": payload.name.strip(),}},
            }
        )

        user = getattr(auth_response, "user", None)
        session = getattr(auth_response, "session", None)

        if user is None or session is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=("Account created, but no active session was returned. \nCheck Supabase email confirmation settings."),
            )

        access_token = get_session_value(session, "access_token")
        refresh_token = get_session_value(session, "refresh_token")

        if not access_token or not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supabase did not return authentication tokens",
            )

        set_auth_cookies(response, access_token, refresh_token)
        return {"user": extract_user_data(user),}

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create account",
        ) from exc


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response):
    try:
        supabase = create_supabase_client()
        auth_response = supabase.auth.sign_in_with_password({
                "email": str(payload.email),
                "password": payload.password,
            }
        )

        user = getattr(auth_response, "user", None)
        session = getattr(auth_response, "session", None)

        if user is None or session is None:
            raise ValueError("Missing user or session")

        access_token = get_session_value(session, "access_token")
        refresh_token = get_session_value(session, "refresh_token")

        if not access_token or not refresh_token:
            raise ValueError("Missing authentication tokens")

        set_auth_cookies(response, access_token, refresh_token)

        return {"user": extract_user_data(user),}

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc


@router.post("/refresh", response_model=AuthResponse)
def refresh_session(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
):
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        supabase = create_supabase_client()

        auth_response = supabase.auth.refresh_session(refresh_token)

        session = getattr(auth_response, "session", None)
        user = getattr(auth_response, "user", None)

        if session is None or user is None:
            raise ValueError("Missing refreshed session")

        access_token = get_session_value(session, "access_token")
        new_refresh_token = get_session_value(session, "refresh_token")

        if not access_token or not new_refresh_token:
            raise ValueError("Missing refreshed tokens")

        set_auth_cookies(response, access_token, new_refresh_token)

        return {"user": extract_user_data(user),}

    except Exception as exc:
        clear_auth_cookies(response)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to refresh session",
        ) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    clear_auth_cookies(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


