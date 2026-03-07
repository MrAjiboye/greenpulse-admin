import streamlit as st
import pandas as pd
from utils.api import get_organizations, delete_organization
from utils.styles import inject_styles

st.set_page_config(page_title="Organisations · GreenPulse Admin", page_icon="🏢", layout="wide")
inject_styles()

if "token" not in st.session_state:
    st.warning("Please sign in from the main page.")
    st.stop()

st.title("Organisation Management")

# ── Load orgs ─────────────────────────────────────────────────────────────────
col_refresh, _ = st.columns([1, 8])
with col_refresh:
    if st.button("↻ Refresh"):
        st.rerun()

try:
    data = get_organizations(limit=100)
    orgs  = data.get("items", [])
    total = data.get("total", 0)
except Exception as e:
    st.error(f"Failed to load organisations: {e}")
    st.stop()

st.caption(f"{total} organisations registered")

if not orgs:
    st.info("No organisations yet.")
    st.stop()

# ── Table ──────────────────────────────────────────────────────────────────────
df = pd.DataFrame([
    {
        "ID":           o["id"],
        "Name":         o["name"],
        "Users":        o["user_count"],
        "Readings":     o["reading_count"],
        "IoT Key Hint": o.get("iot_api_key_hint") or "—",
        "Created":      (o.get("created_at") or "")[:10],
    }
    for o in orgs
])

st.dataframe(df, use_container_width=True, hide_index=True)

# ── Delete org ─────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Delete Organisation")
st.warning("Deleting an organisation removes all its users. Energy/waste data is kept but becomes orphaned.")

org_options = {f"{o['name']} (id={o['id']}, {o['user_count']} users)": o["id"] for o in orgs}
selected_label = st.selectbox("Select organisation to delete", ["— select —"] + list(org_options.keys()))

if selected_label != "— select —":
    org_id = org_options[selected_label]
    if st.button(f"🗑️ Delete '{selected_label.split(' (')[0]}'", type="primary"):
        try:
            delete_organization(org_id)
            st.success("Organisation deleted.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed: {e}")
