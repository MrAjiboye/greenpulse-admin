import json
import streamlit as st
import requests
from utils.api import _base_url
from utils.styles import inject_styles

st.set_page_config(page_title="System · GreenPulse Admin", page_icon="⚙️", layout="wide")
inject_styles()

if "token" not in st.session_state:
    st.warning("Please sign in from the main page.")
    st.stop()

# Strip /api/v1 suffix to get the root backend URL
BACKEND = _base_url().removesuffix("/api/v1")

st.title("System")

# ── Health check ───────────────────────────────────────────────────────────────
st.subheader("Backend Health")
if st.button("Check Health"):
    try:
        resp = requests.get(f"{BACKEND}/health", timeout=5)
        if resp.ok:
            st.success(f"✅ Backend is up")
            st.json(resp.json())
        else:
            st.error(f"Backend returned HTTP {resp.status_code}")
            st.code(resp.text)
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach backend — is it running on port 8000?")
    except Exception as e:
        st.error(str(e))

# ── API docs link ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("API Documentation")
st.markdown(
    "FastAPI auto-generates interactive docs. Open these in your browser while the backend is running:"
)
col1, col2 = st.columns(2)
col1.markdown(f"**Swagger UI** — [{BACKEND}/docs]({BACKEND}/docs)")
col2.markdown(f"**ReDoc** — [{BACKEND}/redoc]({BACKEND}/redoc)")

# ── Raw API tester ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("Raw API Tester")
st.caption(
    "Send any authenticated request to the backend. "
    "Useful for testing new endpoints or diagnosing issues without leaving this tool."
)

col1, col2 = st.columns([1, 3])
with col1:
    method = st.selectbox("Method", ["GET", "POST", "PATCH", "DELETE", "PUT"])
with col2:
    path = st.text_input("Path", value="/api/v1/admin/users", placeholder="/api/v1/...")

body_raw = st.text_area(
    "Request body (JSON)",
    placeholder='{"role": "manager"}',
    height=120,
)

if st.button("▶ Send", type="primary"):
    headers = {
        "Authorization": f"Bearer {st.session_state.get('token', '')}",
        "Content-Type": "application/json",
    }
    url = f"{BACKEND}{path}"
    try:
        payload = json.loads(body_raw) if body_raw.strip() else None
        resp = requests.request(method, url, headers=headers, json=payload, timeout=15)

        color = "green" if resp.ok else "red"
        st.markdown(f"**Status:** :{color}[{resp.status_code}]")

        try:
            st.json(resp.json())
        except Exception:
            st.code(resp.text or "(empty response)")

    except json.JSONDecodeError:
        st.error("Invalid JSON in request body.")
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach backend.")
    except Exception as e:
        st.error(str(e))

# ── Notes ──────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Integration Notes")
st.markdown("""
**Adding a new external API:**
1. Create a new router in `greenpulse-backend/app/routers/`
2. Add `require_role(UserRole.ADMIN)` dependency to protect it
3. Register the router in `main.py`
4. Add the API call to `utils/api.py` in this admin tool
5. Build the UI in a new page under `pages/`

**Adding a new ML model:**
- Place training logic in `app/routers/ml.py` or a separate `app/ml/` module
- Pickle models to `app/ml_models.pkl` (or add a new path)
- Expose `/admin/ml/<new-endpoint>` and wire it up here

**Cloudflare Access (team-only access):**
- Add this app's URL to a Cloudflare Access application
- Set policy to allow only `@greenpulseanalytics.com` emails
- Zero-trust — no VPN needed
""")
