import streamlit as st
from utils.api import login, get_users, ml_status
from utils.styles import inject_styles

st.set_page_config(
    page_title="GreenPulse Admin",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()

# ── Auth gate ──────────────────────────────────────────────────────────────────
if "token" not in st.session_state:
    st.markdown(
        """
        <div style='text-align:center; padding: 3rem 0 1rem'>
            <span style='font-size:2.5rem'>🌿</span>
            <h1 style='margin:0.5rem 0 0.25rem'>GreenPulse Admin</h1>
            <p style='color:#6b7280'>Internal tool — authorised team members only</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col = st.columns([1, 1, 1])[1]
    with col:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@greenpulseanalytics.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Enter both email and password.")
            else:
                try:
                    result = login(email, password)
                    st.session_state.token = result["access_token"]
                    st.session_state.admin_email = email
                    st.rerun()
                except Exception as _e:
                    st.error(f"Login failed: {_e}")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌿 GreenPulse Admin")
    st.caption(f"Signed in as `{st.session_state.get('admin_email', '')}`")
    st.divider()
    if st.button("Sign Out", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ── Overview ───────────────────────────────────────────────────────────────────
st.title("Overview")

# User stats
try:
    users_data = get_users(limit=100)
    users = users_data.get("items", [])
    total = users_data.get("total", 0)
    active = sum(1 for u in users if u.get("is_active"))
    admins = sum(1 for u in users if u.get("role") == "admin")
    managers = sum(1 for u in users if u.get("role") == "manager")
    viewers = sum(1 for u in users if u.get("role") == "viewer")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Users", total)
    c2.metric("Active", active)
    c3.metric("Inactive", total - active)
    c4.metric("Admins", admins)
    c5.metric("Managers", managers)
except Exception as e:
    st.error(f"Could not load user data: {e}")

st.divider()

# ML status
st.subheader("ML Engine")
try:
    status = ml_status()
    if status.get("trained"):
        c1, c2, c3 = st.columns(3)
        c1.success("✅ Model trained and ready")
        c2.metric("Training samples", status.get("n_samples", "—"))
        trained_at = status.get("trained_at", "")[:19].replace("T", " ")
        c3.metric("Last trained", trained_at)
        st.caption(f"Features: {', '.join(status.get('features', []))}")
    else:
        st.warning("⚠️ No model trained yet — go to the **ML Engine** page to train.")
except Exception as e:
    st.error(f"Could not reach ML endpoint: {e}")
