from supabase import Client, create_client
from config import settings


#just uses the config.py to make a client instance of supabase client and returns it.
def create_supabase_client() -> Client:

    return create_client(settings.supabase_url,settings.supabase_key,)