from __future__ import annotations

import streamlit as st

from .config import settings
from .database import connect, init_db
from .seed import seed
from .services import get_user, list_users, reset_candidate_attempt


def require_user():
    cfg = settings()
    conn = connect()
    init_db(conn)
    if cfg.development_auth:
        seed()
        users = list_users(conn)
        email = st.sidebar.selectbox("Development user", [u["email"] for u in users])
        db_user = get_user(conn, email)
        if db_user and db_user["role"] == "candidate":
            if st.sidebar.button("Reset selected candidate"):
                reset_candidate_attempt(conn, db_user["id"])
                st.sidebar.success("Candidate reset")
                st.rerun()
        return conn, db_user

    user = getattr(st, "user", None)
    logged_in = bool(getattr(user, "is_logged_in", False))
    if not logged_in:
        if hasattr(st, "login"):
            st.button("Log in", on_click=st.login)
        else:
            st.error("OIDC login requires a Streamlit version with st.login().")
        st.stop()

    email = getattr(user, "email", None) or user.get("email")
    db_user = get_user(conn, email)
    if not db_user:
        st.error("Your account is not allowlisted for this assessment system.")
        st.stop()
    return conn, db_user


def require_interviewer(user) -> None:
    if user["role"] not in {"interviewer", "admin"}:
        st.error("This page is only available to interviewers.")
        st.stop()
