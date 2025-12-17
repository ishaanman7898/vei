import os
from typing import Any, Dict, Optional, Tuple

import streamlit as st
from supabase import Client, create_client

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _clean_env_value(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = str(v).strip()
    if v.startswith("\"") and v.endswith("\""):
        v = v[1:-1]
    if v.startswith("'") and v.endswith("'"):
        v = v[1:-1]
    return v.strip() or None


def _get_supabase_url_key() -> Tuple[str, str]:
    url = None
    key = None

    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_ANON_KEY")
    except Exception:
        pass

    url = url or _clean_env_value(os.getenv("SUPABASE_URL"))
    key = key or _clean_env_value(os.getenv("SUPABASE_ANON_KEY"))

    if not url or not key:
        raise RuntimeError("Missing Supabase config. Set SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit secrets or environment variables.")

    return url, key


def get_supabase() -> Client:
    url, key = _get_supabase_url_key()
    return create_client(url, key)


def supabase_sign_in(email: str, password: str) -> Dict[str, Any]:
    supabase = get_supabase()
    res = supabase.auth.sign_in_with_password({"email": email, "password": password})

    session = getattr(res, "session", None)
    if not session:
        raise RuntimeError("Supabase sign-in did not return a session.")

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
    }


def get_authed_supabase() -> Client:
    supabase = get_supabase()
    session = st.session_state.get("supabase_session")
    if not session:
        raise RuntimeError("Supabase session not found. Please log in again.")

    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    if not access_token or not refresh_token:
        raise RuntimeError("Supabase session is missing tokens. Please log in again.")

    supabase.auth.set_session(access_token, refresh_token)
    return supabase


def get_current_supabase_user_id() -> Optional[str]:
    try:
        supabase = get_authed_supabase()
        user = supabase.auth.get_user()
        u = getattr(user, "user", None)
        return getattr(u, "id", None)
    except Exception:
        return None
