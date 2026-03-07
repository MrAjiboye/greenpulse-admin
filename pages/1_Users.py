import streamlit as st
import pandas as pd
from utils.api import get_users, update_role, toggle_status, delete_user
from utils.styles import inject_styles

st.set_page_config(page_title="Users · GreenPulse Admin", page_icon="👥", layout="wide")
inject_styles()

if "token" not in st.session_state:
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("User Management")

# ── Load users ─────────────────────────────────────────────────────────────────
col_refresh, col_spacer = st.columns([1, 8])
with col_refresh:
    if st.button("↻ Refresh"):
        st.rerun()

try:
    data = get_users(limit=100)
    users = data.get("items", [])
    total = data.get("total", 0)
except Exception as e:
    st.error(f"Failed to load users: {e}")
    st.stop()

st.caption(f"{total} users in the system")

# ── Table ──────────────────────────────────────────────────────────────────────
ROLE_EMOJI = {"admin": "🔴 Admin", "manager": "🔵 Manager", "viewer": "⚪ Viewer"}

rows = []
for u in users:
    rows.append({
        "ID":       u["id"],
        "Email":    u["email"],
        "Name":     f"{u.get('first_name', '')} {u.get('last_name', '')}".strip(),
        "Role":     ROLE_EMOJI.get(u.get("role", ""), u.get("role", "")),
        "Active":   "✅" if u.get("is_active") else "❌",
        "Joined":   str(u.get("created_at", ""))[:10],
    })

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# ── Actions ────────────────────────────────────────────────────────────────────
user_emails = [u["email"] for u in users]

col1, col2 = st.columns(2)

with col1:
    st.subheader("Change Role")
    sel_role_email = st.selectbox("User", user_emails, key="role_email")
    sel_role_user = next((u for u in users if u["email"] == sel_role_email), None)
    if sel_role_user:
        current_role = sel_role_user.get("role", "viewer")
        st.caption(f"Current role: **{current_role}**")
    new_role = st.selectbox("New role", ["viewer", "manager", "admin"], key="new_role")
    if st.button("Update Role", use_container_width=True):
        try:
            update_role(sel_role_user["id"], new_role)
            st.success(f"✅ {sel_role_email} → **{new_role}**")
            st.rerun()
        except Exception as e:
            st.error(str(e))

with col2:
    st.subheader("Toggle Active Status")
    sel_toggle_email = st.selectbox("User", user_emails, key="toggle_email")
    sel_toggle_user = next((u for u in users if u["email"] == sel_toggle_email), None)
    if sel_toggle_user:
        status_label = "✅ Active" if sel_toggle_user.get("is_active") else "❌ Inactive"
        st.caption(f"Current status: **{status_label}**")
    if st.button("Toggle Status", use_container_width=True):
        try:
            result = toggle_status(sel_toggle_user["id"])
            new_status = "Active" if result.get("is_active") else "Inactive"
            st.success(f"✅ {sel_toggle_email} is now **{new_status}**")
            st.rerun()
        except Exception as e:
            st.error(str(e))

st.divider()

# ── Delete ─────────────────────────────────────────────────────────────────────
st.subheader("Delete User")
st.warning("⚠️ Permanent — cannot be undone.")

del_email = st.selectbox("User to delete", user_emails, key="del_email")
del_user_obj = next((u for u in users if u["email"] == del_email), None)
confirm = st.checkbox(f'I confirm I want to permanently delete **{del_email}**')

if st.button("🗑️ Delete User", type="primary", disabled=not confirm):
    try:
        delete_user(del_user_obj["id"])
        st.success(f"Deleted {del_email}")
        st.rerun()
    except Exception as e:
        st.error(str(e))
