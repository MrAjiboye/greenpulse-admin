import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.api import (
    ml_status, ml_train, ml_anomalies, ml_forecast,
    _headers, _base_url,
)
from utils.styles import inject_styles
import requests

st.set_page_config(page_title="ML Engine · GreenPulse Admin", page_icon="🤖", layout="wide")
inject_styles()

if "token" not in st.session_state:
    st.warning("Please sign in from the main page.")
    st.stop()

BASE_URL = _base_url()

# ── Helper for new endpoints ───────────────────────────────────────────────────
def api_get(path: str) -> dict:
    r = requests.get(f"{BASE_URL}{path}", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()

def api_post(path: str, json_body: dict | None = None) -> dict:
    r = requests.post(f"{BASE_URL}{path}", headers=_headers(), json=json_body, timeout=120)
    r.raise_for_status()
    return r.json()

# ══════════════════════════════════════════════════════════════════════════════
st.title("🤖 ML Engine")

tabs = st.tabs(["Status & Train", "Anomaly Detection", "Forecast", "Data Ingestion", "Cloud Config"])

# ── Shared organisation selector (used by Train, Anomaly, Forecast tabs) ──────
_orgs_ml = []
_orgs_ml_error = None
try:
    _orgs_ml_resp = requests.get(f"{BASE_URL}/admin/organizations?limit=200", headers=_headers(), timeout=10)
    _orgs_ml_resp.raise_for_status()
    _orgs_ml = _orgs_ml_resp.json().get("items", [])
except Exception as _e:
    _orgs_ml_error = str(_e)

_ml_org_options = ["All organisations"] + [f"{o['name']} (id={o['id']})" for o in _orgs_ml]
_ml_org_map = {f"{o['name']} (id={o['id']})": o["id"] for o in _orgs_ml}

st.markdown("### Organisation Scope")
if _orgs_ml_error:
    st.error(f"Could not load organisations: {_orgs_ml_error}")
_sel_ml_org_label = st.selectbox(
    "Run ML operations for",
    _ml_org_options,
    help="Selects which organisation's data is used for training, anomaly scanning, forecasting, and insight generation. Choose 'All organisations' to use every reading in the database.",
    key="ml_org_scope",
)
_sel_ml_org_id = _ml_org_map.get(_sel_ml_org_label)  # None when "All organisations"

if _sel_ml_org_id is not None:
    st.info(f"Scope: **{_sel_ml_org_label}** — only this organisation's data will be used and insights directed to them.")
else:
    st.warning("Scope: **All organisations** — model trains on all data and insights have no organisation tag.")

st.divider()


# ── Tab 1: Status & Train ─────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("Model Status")
    col_r, _ = st.columns([1, 6])
    with col_r:
        refresh = st.button("↻ Refresh")

    try:
        status_data = api_get("/admin/ml/status")
        if status_data.get("trained"):
            c1, c2, c3, c4 = st.columns(4)
            c1.success("✅ Trained")
            c2.metric("Samples", status_data.get("n_samples", "—"))
            c3.metric("Version", status_data.get("version", 1))
            trained_at = str(status_data.get("trained_at", ""))[:19].replace("T", " ")
            c4.metric("Last trained", trained_at)

            # Metrics
            metrics = status_data.get("metrics", {})
            if metrics:
                st.divider()
                st.caption("Cross-validation metrics (lower is better)")
                mc1, mc2, mc3, mc4, mc5 = st.columns(5)
                mc1.metric("GBR MAE",  metrics.get("gbr_mae", "—"))
                mc2.metric("GBR RMSE", metrics.get("gbr_rmse", "—"))
                mc3.metric("LR MAE",   metrics.get("lr_mae", "—"))
                mc4.metric("LR RMSE",  metrics.get("lr_rmse", "—"))
                mc5.metric("CV Folds", metrics.get("cv_splits", "—"))

            # Ensemble weights
            weights = status_data.get("ensemble_weights", {})
            if weights:
                st.caption(
                    f"Ensemble weights — GBR: **{weights.get('gbr', '?')}** | "
                    f"LR: **{weights.get('lr', '?')}**  _(auto-calculated from CV performance)_"
                )

            # Cloud status
            cloud = status_data.get("cloud", {})
            st.divider()
            st.caption(f"Cloud provider: **{cloud.get('provider', 'local')}** — "
                       f"{'✅ Available' if cloud.get('available') else '⚪ Local mode'}")
        else:
            st.warning("No model trained yet. Train below.")
    except Exception as e:
        st.error(f"Cannot load status: {e}")

    st.divider()
    st.subheader("Train")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Train only**")
        st.caption(
            "Trains IsolationForest (anomalies) + GradientBoosting + LinearRegression (forecast) "
            "with TimeSeriesSplit cross-validation."
        )
        if st.button("🚀 Train Models", type="primary", use_container_width=True):
            with st.spinner("Training — this may take a moment..."):
                try:
                    _qs = f"?organization_id={_sel_ml_org_id}" if _sel_ml_org_id else ""
                    r = api_post(f"/admin/ml/train{_qs}")
                    st.success(
                        f"✅ Trained on {r.get('n_samples')} samples "
                        f"| GBR MAE: {r.get('metrics', {}).get('gbr_mae', '—')}"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Training failed: {e}")

    with col_b:
        st.markdown("**Train + Auto-generate Insights**")
        st.caption(
            "Trains models then analyses patterns and writes Insight + Notification "
            "records that appear on the user dashboard automatically."
        )
        if st.button("🚀 Train + Generate Insights", use_container_width=True):
            with st.spinner("Training and analysing..."):
                try:
                    _qs = f"?organization_id={_sel_ml_org_id}" if _sel_ml_org_id else ""
                    r = api_post(f"/admin/ml/train-and-insights{_qs}")
                    insights_r = r.get("insights", {})
                    st.success(
                        f"✅ Trained on {r.get('n_samples')} samples | "
                        f"Insights created: {insights_r.get('created', 0)}"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")

    st.divider()
    st.subheader("Generate Insights Only")
    st.caption("Skips training — runs pattern analysis and writes Insights using the current model.")
    if st.button("💡 Generate Insights", use_container_width=True):
        with st.spinner("Analysing..."):
            try:
                _qs = f"?organization_id={_sel_ml_org_id}" if _sel_ml_org_id else ""
                r = api_post(f"/admin/ml/generate-insights{_qs}")
                st.success(f"Insights created: {r.get('created', 0)}")
            except Exception as e:
                st.error(str(e))


# ── Tab 2: Anomaly Detection ──────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Anomaly Detection")

    days = st.slider("Scan last N days", min_value=1, max_value=90, value=7)

    if st.button("🔍 Run Scan", type="primary"):
        with st.spinner(f"Scanning last {days} days..."):
            try:
                _org_qs = f"&organization_id={_sel_ml_org_id}" if _sel_ml_org_id else ""
                data = api_get(f"/admin/ml/anomalies?days={days}{_org_qs}")
                total  = data.get("total_checked", 0)
                count  = data.get("anomaly_count", 0)
                rate   = data.get("anomaly_rate_pct", 0)
                anomalies = data.get("anomalies", [])

                c1, c2, c3 = st.columns(3)
                c1.metric("Readings checked", total)
                c2.metric("Anomalies found",  count)
                c3.metric("Anomaly rate",     f"{rate}%")

                if anomalies:
                    SEV = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                    rows = [{
                        "Timestamp":   a["timestamp"][:16].replace("T", " "),
                        "Zone":        a["zone"],
                        "kWh":         a["consumption_kwh"],
                        "Score":       a["anomaly_score"],
                        "Severity":    f"{SEV.get(a['severity'], '')} {a['severity'].upper()}",
                    } for a in anomalies]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    # Chart: anomaly scores
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=[a["timestamp"][:16].replace("T", " ") for a in anomalies],
                        y=[a["anomaly_score"] for a in anomalies],
                        marker_color=[
                            "#ef4444" if a["severity"] == "high"
                            else "#f59e0b" if a["severity"] == "medium"
                            else "#10b981"
                            for a in anomalies
                        ],
                    ))
                    fig.update_layout(
                        title="Anomaly Scores (more negative = more anomalous)",
                        xaxis_title="Timestamp",
                        yaxis_title="Score",
                        height=350,
                        margin=dict(l=0, r=0, t=40, b=0),
                        plot_bgcolor="white", paper_bgcolor="white",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("✅ No anomalies detected.")

            except Exception as e:
                st.error(f"Scan failed: {e}")


# ── Tab 3: Forecast ───────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("Energy Forecast")

    col1, col2 = st.columns([1, 2])
    with col1:
        hours = st.selectbox("Horizon", [24, 48, 72, 168, 336, 720],
                             format_func=lambda h: f"{h} h ({h//24} days)")

    if st.button("📈 Generate Forecast", type="primary"):
        with st.spinner("Generating..."):
            try:
                _org_qs = f"&organization_id={_sel_ml_org_id}" if _sel_ml_org_id else ""
                data = api_get(f"/admin/ml/forecast?hours={hours}{_org_qs}")
                pts  = data.get("forecast", [])
                df   = pd.DataFrame(pts)
                df["timestamp"] = pd.to_datetime(df["timestamp"])

                fig = go.Figure()
                # Confidence band
                fig.add_trace(go.Scatter(
                    x=list(df["timestamp"]) + list(df["timestamp"][::-1]),
                    y=list(df["upper_kwh"]) + list(df["lower_kwh"][::-1]),
                    fill="toself",
                    fillcolor="rgba(16,185,129,0.10)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="±15% band",
                    showlegend=True,
                ))
                # Main prediction
                fig.add_trace(go.Scatter(
                    x=df["timestamp"],
                    y=df["predicted_kwh"],
                    mode="lines",
                    name="Predicted kWh",
                    line=dict(color="#10b981", width=2),
                    hovertemplate="%{x|%a %d %b %H:%M}<br>%{y:.2f} kWh<extra></extra>",
                ))
                fig.update_layout(
                    xaxis_title="Time",
                    yaxis_title="kWh",
                    height=450,
                    margin=dict(l=0, r=0, t=10, b=0),
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                )
                st.plotly_chart(fig, use_container_width=True)

                # Stats
                c1, c2, c3, c4 = st.columns(4)
                peak_row = df.loc[df["predicted_kwh"].idxmax()]
                low_row  = df.loc[df["predicted_kwh"].idxmin()]
                c1.metric("Peak",         f"{peak_row['predicted_kwh']} kWh",
                          peak_row["timestamp"].strftime("%a %d %b %H:%M"))
                c2.metric("Lowest",       f"{low_row['predicted_kwh']} kWh",
                          low_row["timestamp"].strftime("%a %d %b %H:%M"))
                c3.metric("Avg per hour", f"{round(df['predicted_kwh'].mean(), 2)} kWh")
                c4.metric("Total",        f"{round(df['predicted_kwh'].sum(), 1)} kWh")

                # Download
                csv = df.to_csv(index=False).encode()
                st.download_button("⬇ Download CSV", csv, "forecast.csv", "text/csv")

            except Exception as e:
                st.error(f"Forecast failed: {e}")


# ── Tab 4: Data Ingestion ─────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("Data Ingestion")

    # ── Organisation selector (admin assigns data to correct org) ────────────────
    try:
        _orgs_resp = requests.get(f"{BASE_URL}/admin/organizations?limit=200", headers=_headers(), timeout=10)
        _orgs_resp.raise_for_status()
        _orgs = _orgs_resp.json().get("items", [])
    except Exception:
        _orgs = []

    if _orgs:
        _org_map = {f"{o['name']} (id={o['id']})": o["id"] for o in _orgs}
        _sel_org_label = st.selectbox(
            "Target Organisation",
            list(_org_map.keys()),
            help="All data submitted below will be assigned to this organisation.",
            key="ingest_org",
        )
        _sel_org_id = _org_map[_sel_org_label]
    else:
        st.warning("No organisations found — data will be stored without an org.")
        _sel_org_id = None

    ingest_tabs = st.tabs(["Manual Reading", "Batch JSON", "IoT Webhook Info", "Data Sources", "Waste Log", "Waste CSV", "Energy Provider API"])

    with ingest_tabs[0]:
        st.caption("Push a single energy reading manually.")
        with st.form("manual_reading"):
            c1, c2 = st.columns(2)
            ts  = c1.date_input("Date")
            hr  = c2.selectbox("Hour", list(range(24)))
            kwh = st.number_input("Consumption (kWh)", min_value=0.0, step=0.1)
            zone = st.text_input("Zone", value="main")
            submitted = st.form_submit_button("Submit Reading", use_container_width=True)

        if submitted:
            from datetime import datetime, timezone
            timestamp_str = datetime.combine(ts, __import__('datetime').time(hr, 0)).isoformat()
            payload = {
                "timestamp": timestamp_str,
                "consumption_kwh": kwh,
                "zone": zone,
                "facility_id": 1,
                "organization_id": _sel_org_id,
            }
            try:
                r = requests.post(
                    f"{BASE_URL}/ingest/reading",
                    headers=_headers(),
                    json=payload,
                    timeout=10,
                )
                r.raise_for_status()
                st.success(f"✅ Reading submitted — ID {r.json().get('id')}")
            except Exception as e:
                st.error(str(e))

    with ingest_tabs[1]:
        st.caption(
            "Paste a JSON array of readings. "
            "Each object must have: `timestamp`, `consumption_kwh`, `zone`."
        )
        sample = json.dumps([
            {"timestamp": "2025-11-01T08:00:00", "consumption_kwh": 12.4, "zone": "kitchen"},
            {"timestamp": "2025-11-01T09:00:00", "consumption_kwh": 14.1, "zone": "kitchen"},
        ], indent=2)
        raw = st.text_area("JSON array", value=sample, height=200)

        if st.button("Submit Batch", type="primary"):
            try:
                records = json.loads(raw)
                if not isinstance(records, list):
                    st.error("Must be a JSON array.")
                else:
                    for rec in records:
                        rec.setdefault("organization_id", _sel_org_id)
                    r = requests.post(
                        f"{BASE_URL}/ingest/batch",
                        headers=_headers(),
                        json={"readings": records},
                        timeout=30,
                    )
                    r.raise_for_status()
                    st.success(f"✅ {r.json().get('ingested')} readings ingested.")
            except json.JSONDecodeError:
                st.error("Invalid JSON.")
            except Exception as e:
                st.error(str(e))

    with ingest_tabs[2]:
        st.markdown("### Restaurant / Device Setup")
        st.caption(
            "Generate a unique webhook URL for each restaurant or meter device. "
            "Share the URL and API key with their IT team or meter provider."
        )

        import re
        from utils.api import BASE_URL as _BACKEND_BASE

        # Strip /api/v1 to get the root URL for display
        _backend_root = _BACKEND_BASE.replace("/api/v1", "")

        st.divider()

        col_name, col_zone = st.columns(2)
        with col_name:
            restaurant_name = st.text_input(
                "Restaurant name",
                placeholder="e.g. The Ivy London",
                help="Used to generate a unique device ID for this location."
            )
        with col_zone:
            default_zone = st.text_input(
                "Default zone",
                value="main",
                help="Zone label sent with readings (e.g. kitchen, dining, all)."
            )

        # Auto-generate device_id slug from name
        if restaurant_name.strip():
            device_id = re.sub(r"[^a-z0-9]+", "-", restaurant_name.strip().lower()).strip("-")
        else:
            device_id = "restaurant-name"

        webhook_url = f"{_backend_root}/api/v1/ingest/webhook/{device_id}"

        st.divider()
        st.markdown("#### Generated webhook URL")
        st.code(webhook_url, language="text")

        st.markdown("#### Required header")
        st.code("X-API-Key: <your IOT_API_KEY from backend .env>", language="text")

        st.markdown("#### Example payload")
        example_payload = json.dumps({
            "consumption_kwh": 14.2,
            "zone": default_zone or "main",
            "device_id": device_id,
            "unit": "kWh",
            # timestamp is optional — defaults to current time if omitted
        }, indent=2)
        st.code(example_payload, language="json")

        st.markdown("#### Test with curl")
        curl_cmd = (
            f'curl -X POST "{webhook_url}" \\\n'
            f'  -H "Content-Type: application/json" \\\n'
            f'  -H "X-API-Key: YOUR_IOT_API_KEY" \\\n'
            f'  -d \'{{"consumption_kwh": 14.2, "zone": "{default_zone or "main"}"}}\''
        )
        st.code(curl_cmd, language="bash")

        st.divider()
        st.markdown("#### Share with their IT team")
        share_text = f"""GreenPulse Meter Integration — {restaurant_name or 'Your Restaurant'}
=================================================
Webhook URL : {webhook_url}
Method      : POST
Header      : X-API-Key: <ask GreenPulse for your API key>
Content-Type: application/json

Minimum payload:
  {{"consumption_kwh": <float>, "zone": "{default_zone or 'main'}"}}

Optional fields:
  "timestamp"  — ISO-8601 string (defaults to current UTC time if omitted)
  "device_id"  — your meter serial / identifier string
  "unit"       — "kWh" (informational only)

Supported sources: smart meters, Raspberry Pi, Google Cloud IoT Core,
AWS IoT Core, Azure IoT Hub, or any device that can POST JSON over HTTPS.
"""
        st.text_area("Copy and send this to the restaurant", value=share_text, height=260)

        st.info(
            "Make sure `IOT_API_KEY` is set in your backend `.env` before sharing. "
            "Use a different device ID for each restaurant so you can tell their data apart."
        )

    with ingest_tabs[3]:
        st.caption("Data sources that have pushed readings, grouped by zone.")
        if st.button("↻ Load Sources"):
            try:
                r = requests.get(f"{BASE_URL}/ingest/sources", headers=_headers(), timeout=10)
                r.raise_for_status()
                sources = r.json().get("sources", [])
                if sources:
                    st.dataframe(pd.DataFrame(sources), use_container_width=True, hide_index=True)
                else:
                    st.info("No readings ingested yet.")
            except Exception as e:
                st.error(str(e))

    # ── Waste Log (manual) ──────────────────────────────────────────────────────
    with ingest_tabs[4]:
        st.caption("Manually log a single waste entry for any organisation.")

        WASTE_STREAMS = ["food_waste", "recycling", "landfill", "compost", "packaging", "glass", "cardboard", "general"]

        with st.form("manual_waste"):
            c1, c2 = st.columns(2)
            w_date   = c1.date_input("Date")
            w_time   = c2.selectbox("Hour", list(range(24)), index=8, format_func=lambda h: f"{h:02d}:00")
            w_stream = st.selectbox("Waste stream", WASTE_STREAMS)
            w_weight = st.number_input("Weight (kg)", min_value=0.0, step=0.5)
            w_loc    = st.text_input("Location / zone", placeholder="e.g. kitchen, bar, dining")
            w_contam = st.checkbox("Contamination detected")
            w_submit = st.form_submit_button("Submit Waste Log", use_container_width=True)

        if w_submit:
            from datetime import datetime as _dt, time as _time
            ts = _dt.combine(w_date, _time(w_time, 0)).isoformat()
            payload = {
                "timestamp": ts,
                "stream": w_stream,
                "weight_kg": w_weight,
                "location": w_loc or "unknown",
                "contamination_detected": w_contam,
                "organization_id": _sel_org_id,
            }
            try:
                r = requests.post(f"{BASE_URL}/waste/logs", headers=_headers(), json=payload, timeout=10)
                r.raise_for_status()
                st.success(f"✅ Waste log submitted — ID {r.json().get('id')}")
            except Exception as e:
                st.error(str(e))

    # ── Waste CSV Upload ────────────────────────────────────────────────────────
    with ingest_tabs[5]:
        st.caption("Upload a CSV file of waste logs. Each row becomes one waste entry.")

        st.markdown("#### Required columns")
        st.code("date,time,stream,weight_kg,location,contamination_detected", language="text")

        sample_csv = (
            "date,time,stream,weight_kg,location,contamination_detected\n"
            "2026-03-01,08:00,food_waste,12.5,kitchen,false\n"
            "2026-03-01,14:00,recycling,8.0,bar,false\n"
            "2026-03-02,09:00,landfill,5.5,dining,true\n"
        )
        st.download_button("⬇ Download template CSV", sample_csv, "waste_template.csv", "text/csv")

        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded:
            try:
                df_waste = pd.read_csv(uploaded)
                st.dataframe(df_waste.head(10), use_container_width=True, hide_index=True)
                st.caption(f"{len(df_waste)} rows loaded. Preview shows first 10.")

                if st.button("📤 Submit All Rows", type="primary"):
                    ok, fail = 0, 0
                    for _, row in df_waste.iterrows():
                        try:
                            ts = f"{row['date']}T{row['time']}"
                            payload = {
                                "timestamp": ts,
                                "stream": str(row["stream"]),
                                "weight_kg": float(row["weight_kg"]),
                                "location": str(row.get("location", "unknown")),
                                "contamination_detected": str(row.get("contamination_detected", "false")).lower() == "true",
                                "organization_id": _sel_org_id,
                            }
                            r = requests.post(f"{BASE_URL}/waste/logs", headers=_headers(), json=payload, timeout=10)
                            r.raise_for_status()
                            ok += 1
                        except Exception:
                            fail += 1
                    st.success(f"✅ {ok} rows submitted.")
                    if fail:
                        st.warning(f"⚠️ {fail} rows failed — check date/stream format.")
            except Exception as e:
                st.error(f"Could not read CSV: {e}")

    # ── Energy Provider API ─────────────────────────────────────────────────────
    with ingest_tabs[6]:
        st.markdown("### Energy Provider API Integration")
        st.caption(
            "Connect to your energy supplier's API to pull smart meter data directly into GreenPulse. "
            "Once configured, run the sync script on a schedule (cron/Task Scheduler) to keep data current."
        )

        provider_tabs = st.tabs(["Octopus Energy", "n3rgy (BG / EDF / SSE)", "Manual CSV from Supplier"])

        with provider_tabs[0]:
            st.markdown("#### Octopus Energy API")
            st.markdown("""
Octopus Energy provides a free REST API for all customers with a smart meter (SMETS2).

**Step 1 — Get your API key**
1. Log in at [octopus.energy/dashboard](https://octopus.energy/dashboard)
2. Go to **API access** at the bottom of the account page
3. Your API key is shown there (starts with `sk_live_...`)

**Step 2 — Find your MPAN and serial number**
- MPAN = your electricity meter point reference (on your bill)
- Serial = meter serial number (on the physical meter or in your account)

**Step 3 — Fetch half-hourly consumption**
            """)
            st.code("""
import requests, os
from datetime import datetime, timedelta

API_KEY = "sk_live_YOUR_KEY"
MPAN    = "YOUR_MPAN"
SERIAL  = "YOUR_SERIAL"

url = (
    f"https://api.octopus.energy/v1/electricity-meter-points/{MPAN}"
    f"/meters/{SERIAL}/consumption/"
    f"?period_from={(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    f"&order_by=period"
)
resp = requests.get(url, auth=(API_KEY, ""))
data = resp.json()["results"]  # list of {interval_start, interval_end, consumption}

# Push each interval to GreenPulse
for reading in data:
    requests.post(
        "https://greenpulse-backend-production.up.railway.app/api/v1/ingest/reading",
        headers={"Authorization": "Bearer YOUR_ADMIN_JWT"},
        json={
            "timestamp": reading["interval_start"],
            "consumption_kwh": reading["consumption"],
            "zone": "main",
        }
    )
""", language="python")
            st.info("Octopus provides data in 30-minute intervals. Run this script daily via cron or Task Scheduler.")

        with provider_tabs[1]:
            st.markdown("#### n3rgy API (British Gas, EDF, SSE, E.ON, ScottishPower)")
            st.markdown("""
n3rgy provides smart meter data for most UK suppliers via a single API.

**Step 1 — Register at [data.n3rgy.com](https://data.n3rgy.com)**
- Create an account and accept the data sharing agreement

**Step 2 — Authorise your meter**
- Go to [consumer.n3rgy.com](https://consumer.n3rgy.com) and enter your IHD MAC address
  (found on the back of your In-Home Display device)

**Step 3 — Fetch consumption**
            """)
            st.code("""
import requests
from datetime import datetime, timedelta

API_KEY = "YOUR_N3RGY_API_KEY"
MPXN    = "YOUR_MPAN_OR_MPRN"

start = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d%H%M")
end   = datetime.now().strftime("%Y%m%d%H%M")

url  = f"https://consumer-api.data.n3rgy.com/electricity/{MPXN}/consumption/1?start={start}&end={end}"
resp = requests.get(url, headers={"Authorization": API_KEY})
values = resp.json()["values"]

for v in values:
    requests.post(
        "https://greenpulse-backend-production.up.railway.app/api/v1/ingest/reading",
        headers={"Authorization": "Bearer YOUR_ADMIN_JWT"},
        json={
            "timestamp": v["timestamp"],
            "consumption_kwh": v["value"],
            "zone": "main",
        }
    )
""", language="python")
            st.info("n3rgy data is typically available 24–48 hours after consumption.")

        with provider_tabs[2]:
            st.markdown("#### Manual CSV from your supplier")
            st.markdown("""
Most UK suppliers let you download your smart meter history as CSV from their online portal.

| Supplier | Where to find it |
|---|---|
| British Gas | My Account → Energy Use → Export Data |
| EDF | My Account → Usage → Download |
| Octopus | Dashboard → Usage → Export |
| E.ON | My E.ON → Energy Usage → Download CSV |
| SSE | Online Account → Usage History |

**Once downloaded**, reformat the CSV to match GreenPulse's batch format:
```
timestamp,consumption_kwh,zone
2026-03-01T00:00:00,1.42,main
2026-03-01T00:30:00,1.18,main
```
Then use the **Batch JSON** tab to push the data, or convert the CSV to JSON and submit.
            """)
            st.download_button(
                "⬇ Download GreenPulse energy CSV template",
                "timestamp,consumption_kwh,zone\n2026-03-01T00:00:00,1.42,main\n2026-03-01T00:30:00,1.18,main\n",
                "energy_template.csv",
                "text/csv",
            )


# ── Tab 5: Cloud Config ───────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("Cloud ML Configuration")

    try:
        cloud = api_get("/admin/ml/cloud")
        provider = cloud.get("provider", "local")
        available = cloud.get("available", False)

        if provider == "local":
            st.info("☁️ Running in **local mode** — no cloud ML provider configured.")
        elif available:
            st.success(f"✅ Connected to **{provider}**")
        else:
            st.error(f"❌ **{provider}** configured but not reachable.")

        st.json(cloud)
    except Exception as e:
        st.error(str(e))

    st.divider()
    st.markdown("### How to connect a cloud provider")

    with st.expander("Google Vertex AI"):
        st.markdown("""
1. Create a GCP project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable the **Vertex AI API** and **IAM API**
3. Create a **service account** with `Vertex AI User` role
4. Download the service account JSON key
5. Add to your backend `.env`:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=europe-west2
GOOGLE_CLOUD_CREDENTIALS_JSON={"type":"service_account",...}  # paste JSON as one line
VERTEX_AI_ENDPOINT_ID=projects/.../locations/.../endpoints/...
```
6. Deploy a model to a Vertex AI endpoint (online prediction)
7. Restart the backend — it will auto-detect and use Vertex AI for predictions
        """)

    with st.expander("Google BigQuery ML"):
        st.markdown("""
1. Enable the **BigQuery API** in your GCP project
2. Create a BigQuery dataset
3. Add to `.env`:
```
GOOGLE_CLOUD_PROJECT=your-project-id
BIGQUERY_DATASET=greenpulse_ml
GOOGLE_CLOUD_CREDENTIALS_JSON={"type":"service_account",...}
```
4. Use the System page → Raw API Tester to run SQL via `/api/v1/admin/ml/cloud`
5. Or run `CREATE MODEL` statements directly in BigQuery console
        """)

    with st.expander("AWS SageMaker"):
        st.markdown("""
1. Deploy a SageMaker real-time endpoint (from SageMaker Studio or CLI)
2. Create an IAM user with `sagemaker:InvokeEndpoint` permission
3. Add to `.env`:
```
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=AKIAxxx
AWS_SECRET_ACCESS_KEY=xxxxx
SAGEMAKER_ENDPOINT_NAME=greenpulse-energy-forecast
```
4. Restart the backend
        """)
