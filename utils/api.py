"""
API client for the GreenPulse backend.
All functions read the JWT token from st.session_state and raise on non-2xx responses.
"""

import os
import requests
import streamlit as st

def _base_url() -> str:
    """Read backend URL from Streamlit secrets, env var, or localhost fallback."""
    env_url = os.environ.get("BACKEND_URL", "")
    try:
        url = st.secrets.get("BACKEND_URL", env_url or "http://localhost:8000")
    except Exception:
        url = env_url or "http://localhost:8000"
    return url.rstrip("/") + "/api/v1"

BASE_URL = _base_url()


def _headers() -> dict:
    token = st.session_state.get("token", "")
    return {"Authorization": f"Bearer {token}"}


# ── Auth ───────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> dict:
    """POST /auth/login — returns {access_token, token_type}"""
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": email, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ── Users ──────────────────────────────────────────────────────────────────────

def get_users(limit: int = 100, offset: int = 0) -> dict:
    resp = requests.get(
        f"{BASE_URL}/admin/users",
        headers=_headers(),
        params={"limit": limit, "offset": offset},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def update_role(user_id: int, role: str) -> dict:
    resp = requests.patch(
        f"{BASE_URL}/admin/users/{user_id}/role",
        headers=_headers(),
        json={"role": role},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def toggle_status(user_id: int) -> dict:
    resp = requests.patch(
        f"{BASE_URL}/admin/users/{user_id}/status",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def delete_user(user_id: int) -> None:
    resp = requests.delete(
        f"{BASE_URL}/admin/users/{user_id}",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()


# ── Organisations ──────────────────────────────────────────────────────────────

def get_organizations(limit: int = 100, offset: int = 0) -> dict:
    resp = requests.get(
        f"{BASE_URL}/admin/organizations",
        headers=_headers(),
        params={"limit": limit, "offset": offset},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def delete_organization(org_id: int) -> None:
    resp = requests.delete(
        f"{BASE_URL}/admin/organizations/{org_id}",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()


# ── ML ─────────────────────────────────────────────────────────────────────────

def ml_status() -> dict:
    resp = requests.get(f"{BASE_URL}/admin/ml/status", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def ml_train() -> dict:
    resp = requests.post(f"{BASE_URL}/admin/ml/train", headers=_headers(), timeout=60)
    resp.raise_for_status()
    return resp.json()


def ml_anomalies() -> dict:
    resp = requests.get(f"{BASE_URL}/admin/ml/anomalies", headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def ml_forecast() -> dict:
    resp = requests.get(f"{BASE_URL}/admin/ml/forecast", headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── System ─────────────────────────────────────────────────────────────────────

def health_check() -> dict:
    base = _base_url().removesuffix("/api/v1")
    resp = requests.get(f"{base}/health", timeout=5)
    resp.raise_for_status()
    return resp.json()
