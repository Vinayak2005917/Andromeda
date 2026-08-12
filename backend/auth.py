from typing import Any
from fastapi import Cookie, HTTPException, status
from supabase_client import create_supabase_client

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
#the above two varibles are the names of the cookies that will be used to store the access and refresh tokens in the user's browser.
# access cookie is a short lived token that is used to authenticate the user and is valid for 15 minutes.
# refresh cookie is a long lived token that is used to refresh the access token and is valid for 7 days.



# just a helper function to get the user data from the supabase user object.
def extract_user_data(user: Any)->dict:
    metadata = getattr(user, "user_metadata", None) or {}
    return {
        "id":str(user.id),
        "name":metadata.get("name"),
        "email":user.email
    }

def get_session_value(session: Any, key: str) -> str | None:
    value = getattr(session, key, None)

    if value is None and isinstance(session, dict):
        value = session.get(key)

    return value

def verify_access_token(access_token:str)->Any:
    try:
        supabase = create_supabase_client()
        response = supabase.auth.get_user(access_token)

        user = getattr(response, "user", None)

        if user is None:
            raise ValueError("No user returned")

        return user

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc

def get_current_user(access_token: str | None = Cookie(default=None)) -> Any:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return verify_access_token(access_token)
