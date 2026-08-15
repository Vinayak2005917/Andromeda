from supabase import Client, create_client
from fastapi import HTTPException, status
from config import settings


#just uses the config.py to make a client instance of supabase client and returns it.
def create_supabase_client() -> Client:

    return create_client(settings.supabase_url,settings.supabase_key,)


def create_server_supabase_client() -> Client:
    """Client for backend operations after explicit ownership validation."""
    if not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPABASE_SERVICE_ROLE_KEY must be configured for server data operations",
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
