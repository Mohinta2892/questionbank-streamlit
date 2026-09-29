from __future__ import annotations

import streamlit as st

from .admin_seed import seed_configured_users
from .config import settings
from .database import connect, init_db
from .passwords import verify_password
from .seed import seed
from .services import get_user, list_users, reset_candidate_attempt


def password_login(conn):
    if st.session_state.get("auth_email"):
        db_user = get_user(conn, st.session_state["auth_email"])
        if db_user:
            if st.sidebar.button("Log out"):
                del st.session_state["auth_email"]
                st.rerun()
            return db_user

    st.title("Assessment Login")
    with st.form("login"):
        email = st.text_input("Email").strip().lower()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        db_user = get_user(conn, email)
        if db_user and verify_password(password, db_user["password_hash"]):
            st.session_state["auth_email"] = db_user["email"]
            st.rerun()
        st.error("Invalid email or password.")
    st.stop()


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

    seed_configured_users(conn)
    if not cfg.oidc_auth:
        return conn, password_login(conn)

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
