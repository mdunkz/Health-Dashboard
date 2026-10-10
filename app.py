import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
import gspread
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. OLED HIGH-CONTRAST GLASSMORPHISM STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="PRO Health OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background-color: #06080C; color: #E6EDF3; }
    h1, h2, h3, h4, h5, p, span, label { color: #FFFFFF !important; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    .stCaption { color: #9198A1 !important; font-size: 14px !important; }

    div[data-testid="stMetric"] {
        background: #111620;
        border: 1px solid #262C36;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
    }
    div[data-testid="stMetricValue"] { font-size: 30px !important; font-weight: 800 !important; color: #00FF87 !important; }
    div[data-testid="stMetricLabel"] { font-size: 12px !important; font-weight: 700 !important; color: #A3B1C2 !important; text-transform: uppercase; }

    .stTabs [data-baseweb="tab-list"] { gap: 10px; border-bottom: 1px solid #262C36; }
    .stTabs [data-baseweb="tab"] {
        background-color: #111620;
        border: 1px solid #262C36;
        border-radius: 8px 8px 0px 0px;
        padding: 12px 24px;
        color: #FFFFFF !important;
        font-size: 15px !important;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00FF87 !important;
        color: #06080C !important;
        border-color: #00FF87 !important;
        font-weight: 800 !important;
    }
    section[data-testid="stSidebar"] { background-color: #0B0E14; border-right: 1px solid #1F242D; }

    /* Active Date Picker Glowing Style */
    .date-active-label {
        color: #00FF87 !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

# Standard Plotly Legend Style for High Contrast
HIGH_CONTRAST_LEGEND = dict(
    orientation="h",
    y=1.15,
    x=0,
    font=dict(color="#FFFFFF", size=13, family="-apple-system, sans-serif"),
    bgcolor="rgba(17, 22, 32, 0.85)",
    bordercolor="#30363D",
    borderwidth=1
)


# ---------------------------------------------------------
# 2. FRACTIONAL COMPOUND MUSCLE SPLITTING ENGINE
# ---------------------------------------------------------
COMPOUND_SPLITS = {
    "leg press": [("Quads", 0.60), ("Hamstrings & Glutes", 0.40)],
    "hack squat": [("Quads", 0.65), ("Hamstrings & Glutes", 0.35)],
    "squat": [("Quads", 0.55), ("Hamstrings & Glutes", 0.45)],
    "lunge": [("Quads", 0.50), ("Hamstrings & Glutes", 0.50)],
    "split squat": [("Quads", 0.60), ("Hamstrings & Glutes", 0.40)],
    "deadlift": [("Back", 0.50), ("Hamstrings & Glutes", 0.50)],
    "bench press": [("Chest", 0.70), ("Arms", 0.30)],
    "dip": [("Chest", 0.50), ("Arms", 0.50)],
    "overhead press": [("Shoulders", 0.75), ("Arms", 0.25)],
}

SINGLE_MUSCLE_MAP = {
    "Core": ["crunch", "ab crunch", "ab wheel", "situp", "plank", "hanging leg", "knee raise", "abs"],
    "Chest": ["chest", "fly", "pec", "pushup", "incline press", "decline press", "cable crossover"],
    "Back": ["row", "lat", "pulldown", "pullup", "chinup", "back extension", "shrug", "trap", "t-bar"],
    "Quads": ["quad", "leg extension", "sissy squat", "goblet squat"],
    "Hamstrings & Glutes": ["rdl", "stiff", "leg curl", "hip thrust", "glute", "nordic", "hamstring", "abductor", "adductor"],
    "Calves": ["calf", "calves", "gastrocnemius", "soleus", "heel raise"],
    "Shoulders": ["lateral raise", "deltoid", "delt", "upright row", "rear delt", "reverse fly"],
    "Arms": ["bicep", "tricep", "curl", "extension", "skull", "hammer", "preacher", "pushdown"]
}

def split_workout_volume(row):
    ex_name = str(row.get("Exercise", "")).lower().strip()
    vol = row.get("Volume", 0)
    
    for compound_key, splits in COMPOUND_SPLITS.items():
        if compound_key in ex_name:
            return [(muscle, vol * ratio, ratio) for muscle, ratio in splits]
            
    for muscle, keywords in SINGLE_MUSCLE_MAP.items():
        if any(kw in ex_name for kw in keywords):
            return [(muscle, vol, 1.0)]
            
    return [("Chest", vol, 1.0)]


# ---------------------------------------------------------
# 3. PASSWORD GATE & CONDITIONAL DATA LOADER
# ---------------------------------------------------------
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.sidebar.markdown("### 🔒 Owner Login")
        password_input = st.sidebar.text_input("Enter Password for Real Data", type="password")
        if st.sidebar.button("Login"):
            try:
                if password_input == st.secrets["password"]["pin"]:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.sidebar.error("Incorrect password")
            except Exception:
                st.sidebar.error("Password secret not configured.")
        return False
    return True

is_authenticated = check_password()

@st.cache_data(ttl=60)
def load_sheet(tab_name, authenticated):
    # If not authenticated, return clean demo data so public viewers see a working preview
    if not authenticated:
        if tab_name == "Weight":
            return pd.DataFrame({"Date": pd.date_range(end=datetime.today(), periods=30), "Weight": [175 - i*0.1 for i in range(30)]})
        elif tab_name == "Steps":
            return pd.DataFrame({"Date": pd.date_range(end=datetime.today(), periods=30), "Step Count": [10000 + (i*120)%3000 for i in range(30)]})
        elif tab_name == "Sleep":
            return pd.DataFrame({"Date": pd.date_range(end=datetime.today(), periods=30), "Hours Slept": [7.5 for _ in range(30)]})
        elif tab_name == "Workouts":
            return pd.DataFrame({
                "Date": pd.date_range(end=datetime.today(), periods=10),
                "Exercise": ["Bench Press", "Squat", "Deadlift"] * 3 + ["Bench Press"],
                "Weight": [225, 315, 405] * 3 + [225],
                "Reps": [5, 5, 3] * 3 + [5],
                "Muscle": ["Chest", "Quads", "Back"] * 3 + ["Chest"]
            })
        return pd.DataFrame()

    # If authenticated, pull real Google Sheet data securely
    try:
        if "gspread" in st.secrets:
            creds_dict = dict(st.secrets["gspread"])
            gc = gspread.service_account_from_dict(creds_dict)
        else:
            gc = gspread.service_account(filename="credentials.json")
            
        sh = gc.open("Health Dashboard")
        worksheet = sh.worksheet(tab_name)
        data = worksheet.get_all_records()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
        if "Date" in df.columns and not df.empty:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"]).sort_values("Date")
        return df
    except Exception:
        return pd.DataFrame()

raw_weight_df = load_sheet("Weight", is_authenticated)
raw_steps_df = load_sheet("Steps", is_authenticated)
raw_sleep_df = load_sheet("Sleep", is_authenticated)
raw_workouts_df = load_sheet("Workouts", is_authenticated)

if not raw_steps_df.empty and "Step Count" in raw_steps_df.columns:
    raw_steps_df["Step Count"] = raw_steps_df["Step Count"].astype(str).str.replace(",", "").astype(float)

if not raw_workouts_df.empty and {"Exercise", "Weight", "Reps"}.issubset(raw_workouts_df.columns):
    raw_workouts_df["Weight"] = pd.to_numeric(raw_workouts_df["Weight"], errors="coerce").fillna(0)
    raw_workouts_df["Reps"] = pd.to_numeric(raw_workouts_df["Reps"], errors="coerce").fillna(0)
    raw_workouts_df["Set"] = pd.to_numeric(raw_workouts_df.get("Set", 1), errors="coerce").fillna(1)
    raw_workouts_df["Volume"] = raw_workouts_df["Weight"] * raw_workouts_df["Reps"]
    raw_workouts_df["Epley_1RM"] = np.where(raw_workouts_df["Reps"] > 0, raw_workouts_df["Weight"] * (1 + raw_workouts_df["Reps"] / 30.0), 0)

weight_df = raw_weight_df.copy()
steps_df = raw_steps_df.copy()
sleep_df = raw_sleep_df.copy()
workouts_df = raw_workouts_df.copy()


# ---------------------------------------------------------
# 4. SIDEBAR CONTROLS & DYNAMIC DATE COLORING
# ---------------------------------------------------------
st.sidebar.title("⚡ CONTROL CENTER")
if is_authenticated:
    if st.sidebar.button("🔄 Sync Sheet Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.divider()

all_dates = []
for df in [raw_weight_df, raw_steps_df, raw_sleep_df, raw_workouts_df]:
    if not df.empty and "Date" in df.columns:
        all_dates.extend(df["Date"].tolist())

is_filtered = False
if all_dates:
    min_d, max_d = min(all_dates).date(), max(all_dates).date()
    
    if "date_picker" in st.session_state and isinstance(st.session_state["date_picker"], tuple) and len(st.session_state["date_picker"]) == 2:
        p_start, p_end = st.session_state["date_picker"][0], st.session_state["date_picker"][1]
        if p_start > min_d or p_end < max_d:
            is_filtered = True

    if is_filtered:
        st.sidebar.markdown("<p class='date-active-label'>⚡ DATE RANGE FILTER ACTIVE</p>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<p style='color: #A3B1C2; font-size: 13px;'>Filter Date Range</p>", unsafe_allow_html=True)
        
    selected_range = st.sidebar.date_input("", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="date_picker")
    
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = pd.to_datetime(selected_range[0]), pd.to_datetime(selected_range[1])
        if start_date.date() > min_d or end_date.date() < max_d:
            is_filtered = True
            
        if not weight_df.empty: weight_df = weight_df[(weight_df["Date"] >= start_date) & (weight_df["Date"] <= end_date)]
        if not steps_df.empty: steps_df = steps_df[(steps_df["Date"] >= start_date) & (steps_df["Date"] <= end_date)]
        if not sleep_df.empty: sleep_df = sleep_df[(sleep_df["Date"] >= start_date) & (sleep_df["Date"] <= end_date)]
        if not workouts_df.empty: workouts_df = workouts_df[(workouts_df["Date"] >= start_date) & (workouts_df["Date"] <= end_date)]


# ---------------------------------------------------------
# 5. RESTRUCTURED 2-ROW KPI CARDS
# ---------------------------------------------------------
st.title("⚡ PRO HEALTH OPERATING SYSTEM")
mode_banner = "🔓 Live Owner Mode" if is_authenticated else "👁️ Public Demo Preview Mode"
st.caption(f"Live Biometric Telemetry & Compound Loading Engine — *{mode_banner}*")
st.divider()

# ROW 1: 7-DAY MOVING AVERAGES + RANGE TONNAGE
st.subheader("📈 7-Day Averages & Volume")
r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)

with r1_col1:
    if not weight_df.empty and "Weight" in weight_df.columns:
        w_7d_avg = round(weight_df["Weight"].tail(7).mean(), 1)
        st.metric("7D Avg Weight", f"{w_7d_avg} lbs")
    else: st.metric("7D Avg Weight", "--")

with r1_col2:
    if not steps_df.empty and "Step Count" in steps_df.columns:
        s_7d_avg = int(steps_df["Step Count"].tail(7).mean())
        st.metric("7D Avg Steps", f"{s_7d_avg:,}")
    else: st.metric("7D Avg Steps", "--")

with r1_col3:
    if not sleep_df.empty and "Hours Slept" in sleep_df.columns:
        sl_7d_avg = round(sleep_df["Hours Slept"].tail(7).mean(), 1)
        st.metric("7D Avg Sleep", f"{sl_7d_avg} hrs")
    else: st.metric("7D Avg Sleep", "--")

with r1_col4:
    if not workouts_df.empty and "Volume" in workouts_df.columns:
        total_vol = int(workouts_df["Volume"].sum())
        metric_label = "Range Volume" if is_filtered else "Lifetime Volume"
        st.metric(metric_label, f"{total_vol:,} lbs")
    else: st.metric("Range Volume", "--")

# ROW 2: MOST RECENT SINGLE-DAY STATS
st.subheader("📍 Most Recent Stats")
r2_col1, r2_col2, r2_col3 = st.columns(3)

with r2_col1:
    if not weight_df.empty and "Weight" in weight_df.columns:
        latest_w = weight_df["Weight"].iloc[-1]
        prev_w = weight_df["Weight"].iloc[-2] if len(weight_df) > 1 else latest_w
        delta_w = round(latest_w - prev_w, 1)
        st.metric("Latest Weight", f"{latest_w} lbs", delta=f"{delta_w} lbs", delta_color="inverse")
    else: st.metric("Latest Weight", "--")

with r2_col2:
    if not steps_df.empty and "Step Count" in steps_df.columns:
        latest_s = int(steps_df["Step Count"].iloc[-1])
        st.metric("Latest Daily Steps", f"{latest_s:,}")
    else: st.metric("Latest Daily Steps", "--")

with r2_col3:
    if not sleep_df.empty and "Hours Slept" in sleep_df.columns:
        latest_sl = sleep_df["Hours Slept"].iloc[-1]
        st.metric("Latest Sleep Duration", f"{latest_sl} hrs")
    else: st.metric("Latest Sleep Duration", "--")

st.divider()


# ---------------------------------------------------------
# 6. DASHBOARD MODULES
# ---------------------------------------------------------
tab_overview, tab_forecast, tab_workouts, tab_heatmap, tab_history = st.tabs([
    "📊 Executive Overview", "🎯 Target Weight Forecast", "🏋️ Strength & Working Weight", "🦵 Realistic Body Map", "🏛️ All-Time Historical"
])

# EXECUTIVE OVERVIEW
with tab_overview:
    st.subheader("Weight Trend vs Step Activity")
    if not weight_df.empty and not steps_df.empty:
        weight_df["Weight_EMA14"] = weight_df["Weight"].ewm(span=14, adjust=False).mean()
        merged = pd.merge(weight_df, steps_df, on="Date", how="inner")
        
        fig_ov = go.Figure()
        fig_ov.add_trace(go.Bar(x=merged["Date"], y=merged["Step Count"], name="Steps", marker_color="rgba(0, 255, 135, 0.25)", yaxis="y2"))
        fig_ov.add_trace(go.Scatter(x=merged["Date"], y=merged["Weight"], mode="markers", name="Daily Weight", marker=dict(color="#FF4949", size=6)))
        fig_ov.add_trace(go.Scatter(x=merged["Date"], y=merged["Weight_EMA14"], mode="lines", name="14D Weight EMA", line=dict(color="#00FF87", width=3)))
        
        fig_ov.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#FFFFFF", size=13), yaxis=dict(title="Weight (lbs)", showgrid=False),
            yaxis2=dict(title="Steps", overlaying="y", side="right", showgrid=False),
            hovermode="x unified", legend=HIGH_CONTRAST_LEGEND
        )
        st.plotly_chart(fig_ov, use_container_width=True)

# TARGET WEIGHT FORECAST MODULE
with tab_forecast:
    st.subheader("🎯 Goal Weight Timeline Predictor")
    if not weight_df.empty and "Weight" in weight_df.columns:
        curr_weight = weight_df["Weight"].iloc[-1]
        
        c_target, c_calc = st.columns([1, 2])
        with c_target:
            target_wt = st.number_input("Enter Target Weight (lbs)", value=float(curr_weight - 10.0), step=0.5)
            
            weight_df["EMA_14"] = weight_df["Weight"].ewm(span=14, adjust=False).mean()
            recent_ema14 = weight_df["EMA_14"].tail(14)
            daily_rate_14 = (recent_ema14.iloc[-1] - recent_ema14.iloc[0]) / 14.0 if len(recent_ema14) > 1 else 0.0
            weekly_rate_14 = round(daily_rate_14 * 7.0, 2)
            
            weight_df["EMA_30"] = weight_df["Weight"].ewm(span=30, adjust=False).mean()
            recent_ema30 = weight_df["EMA_30"].tail(30)
            daily_rate_30 = (recent_ema30.iloc[-1] - recent_ema30.iloc[0]) / 30.0 if len(recent_ema30) > 1 else 0.0
            weekly_rate_30 = round(daily_rate_30 * 7.0, 2)
            
            st.write(f"**Current Weight:** {curr_weight} lbs")
            st.divider()
            
            st.markdown("##### ⚡ 14-Day EMA Trend (Short-Term Momentum)")
            st.write(f"**Velocity:** {weekly_rate_14} lbs/week")
            if daily_rate_14 != 0:
                wt_diff = target_wt - curr_weight
                days_14 = int(wt_diff / daily_rate_14)
                if days_14 > 0:
                    date_14 = datetime.now() + timedelta(days=days_14)
                    st.success(f"**Proj. Date:** {date_14.strftime('%b %d, %Y')} ({days_14} days)")
                else: st.info("Trend moving away from target.")
            
            st.divider()
            st.markdown("##### 🐢 30-Day EMA Trend (Long-Term Pace)")
            st.write(f"**Velocity:** {weekly_rate_30} lbs/week")
            if daily_rate_30 != 0:
                days_30 = int(wt_diff / daily_rate_30)
                if days_30 > 0:
                    date_30 = datetime.now() + timedelta(days=days_30)
                    st.info(f"**Proj. Date:** {date_30.strftime('%b %d, %Y')} ({days_30} days)")
                else: st.info("Trend moving away from target.")

        with c_calc:
            max_days = min(max(days_14 if 'days_14' in locals() and days_14 > 0 else 30, days_30 if 'days_30' in locals() and days_30 > 0 else 30), 365)
            future_dates = [datetime.now() + timedelta(days=i) for i in range(0, max_days)]
            future_weights_14 = [curr_weight + (daily_rate_14 * i) for i in range(0, max_days)]
            future_weights_30 = [curr_weight + (daily_rate_30 * i) for i in range(0, max_days)]
            
            fig_f = go.Figure()
            fig_f.add_trace(go.Scatter(x=weight_df["Date"], y=weight_df["EMA_14"], mode="lines", name="Historical 14D EMA", line=dict(color="#00FF87", width=2.5)))
            fig_f.add_trace(go.Scatter(x=weight_df["Date"], y=weight_df["EMA_30"], mode="lines", name="Historical 30D EMA", line=dict(color="#FFD600", width=2.5)))
            fig_f.add_trace(go.Scatter(x=future_dates, y=future_weights_14, mode="lines", name="14D Momentum Proj.", line=dict(color="#00FF87", width=3, dash="dash")))
            fig_f.add_trace(go.Scatter(x=future_dates, y=future_weights_30, mode="lines", name="30D Steady Pace Proj.", line=dict(color="#00B0FF", width=3, dash="dot")))
            fig_f.add_hline(y=target_wt, line_dash="solid", line_color="#FF4949", annotation_text=f"Target: {target_wt} lbs", annotation_font_color="#FF4949")
            
            fig_f.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis=dict(showgrid=False), legend=HIGH_CONTRAST_LEGEND)
            st.plotly_chart(fig_f, use_container_width=True)

# STRENGTH & WORKING WEIGHT ENGINE
with tab_workouts:
    st.subheader("🏋️ Working Weight Trajectory & Performance History")
    if not workouts_df.empty:
        exercise_list = sorted(workouts_df["Exercise"].dropna().unique().tolist())
        selected_ex = st.selectbox("Select Exercise Movement", exercise_list)
        ex_df = workouts_df[workouts_df["Exercise"] == selected_ex].sort_values("Date")
        
        st.markdown(f"#### 📍 Previous Lift Performance: **{selected_ex}**")
        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        
        last_session_date = ex_df["Date"].iloc[-1].strftime("%b %d, %Y")
        latest_sets = ex_df[ex_df["Date"] == ex_df["Date"].iloc[-1]]
        max_recent_wt = latest_sets["Weight"].max()
        all_time_max = ex_df["Weight"].max()
        total_ex_vol = int(ex_df["Volume"].sum())
        
        with p_col1: st.metric("Last Trained Date", last_session_date)
        with p_col2: st.metric("Most Recent Max Weight", f"{max_recent_wt} lbs")
        with p_col3: st.metric("All-Time Max Weight", f"{all_time_max} lbs")
        with p_col4: st.metric("Total Volume Lifted", f"{total_ex_vol:,} lbs")
            
        st.divider()
        fig_weight_history = px.scatter(
            ex_df, x="Date", y="Weight", size="Reps", color="Reps",
            title=f"Working Weight History: {selected_ex} (Bubble size = Reps)",
            color_continuous_scale="Viridis"
        )
        fig_weight_history.add_trace(go.Scatter(x=ex_df["Date"], y=ex_df["Weight"], mode="lines", name="Max Weight Trend", line=dict(color="#00FF87", width=2)))
        fig_weight_history.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis=dict(showgrid=False), legend=HIGH_CONTRAST_LEGEND)
        st.plotly_chart(fig_weight_history, use_container_width=True)
        
        st.markdown("##### 📋 Recent Set Logs")
        st.dataframe(ex_df[["Date", "Set", "Weight", "Reps", "Volume"]].tail(15), use_container_width=True)
        
        st.divider()
        st.markdown(f"#### 📈 Calculated 1-Rep Max (1RM) Trajectory: **{selected_ex}**")
        st.caption("Scroll down analysis for calculated max strength potential based on Epley formula.")
        
        fig_1rm = go.Figure()
        fig_1rm.add_trace(go.Scatter(x=ex_df["Date"], y=ex_df["Epley_1RM"], mode="lines+markers", name="Calculated Epley 1RM", line=dict(color="#00B0FF", width=3)))
        fig_1rm.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#FFFFFF", size=13), yaxis=dict(showgrid=False, title="Projected 1RM (lbs)"), legend=HIGH_CONTRAST_LEGEND)
        st.plotly_chart(fig_1rm, use_container_width=True)

# ANATOMICAL MUSCLE MAP
with tab_heatmap:
    st.subheader("Anatomical Muscle Volume Heatmap (Compound Split Attribution)")
    vol_summary, sets_summary = {}, {}
    if not workouts_df.empty:
        for idx, row in workouts_df.iterrows():
            splits = split_workout_volume(row)
            for muscle, split_vol, ratio in splits:
                vol_summary[muscle] = vol_summary.get(muscle, 0) + split_vol
                sets_summary[muscle] = sets_summary.get(muscle, 0) + ratio

    def get_stat(muscle):
        v = vol_summary.get(muscle, 0)
        s = round(sets_summary.get(muscle, 0), 1)
        return f"{int(v):,} lbs ({s} effective sets)"

    chest_stat = get_stat("Chest")
    back_stat = get_stat("Back")
    quads_stat = get_stat("Quads")
    ham_stat = get_stat("Hamstrings & Glutes")
    calves_stat = get_stat("Calves")
    delts_stat = get_stat("Shoulders")
    arms_stat = get_stat("Arms")
    core_stat = get_stat("Core")

    svg_body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ background-color: #06080C; color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; flex-direction: column; margin: 0; padding: 10px; }}
        .body-container {{ display: flex; gap: 60px; align-items: center; }}
        .muscle-group {{ fill: #161D2A; stroke: #00FF87; stroke-width: 1.2; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; }}
        .muscle-group:hover {{ fill: #00FF87 !important; filter: drop-shadow(0px 0px 12px #00FF87); }}
        .body-silhouette {{ fill: #0B0E14; stroke: #262C36; stroke-width: 1.5; }}
        .tooltip {{ position: absolute; background: rgba(17, 22, 32, 0.95); border: 1px solid #00FF87; color: #FFFFFF; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: bold; pointer-events: none; display: none; box-shadow: 0 4px 16px rgba(0,0,0,0.85); z-index: 1000; }}
        .title-label {{ font-weight: 800; font-size: 13px; fill: #A3B1C2; text-anchor: middle; letter-spacing: 1px; }}
    </style>
    </head>
    <body>
    <div class="tooltip" id="tooltip"></div>
    <div class="body-container">
        <!-- ANTERIOR -->
        <svg width="220" height="460" viewBox="0 0 200 400">
            <text x="100" y="20" class="title-label">ANTERIOR (FRONT)</text>
            <path class="body-silhouette" d="M 90 35 C 90 22 110 22 110 35 C 110 52 90 52 90 35 Z M 93 54 L 84 68 L 116 68 L 107 54 Z"/>
            <path class="muscle-group" data-name="Shoulders" data-stat="{delts_stat}" d="M 64 70 C 52 74 48 88 56 102 C 62 100 66 88 68 76 Z M 136 70 C 148 74 152 88 144 102 C 138 100 134 88 132 76 Z"/>
            <path class="muscle-group" data-name="Chest" data-stat="{chest_stat}" d="M 84 72 C 72 74 68 86 68 98 C 82 108 98 108 100 110 C 102 108 118 108 132 98 C 132 86 128 74 116 72 C 100 70 100 70 84 72 Z"/>
            <path class="muscle-group" data-name="Arms" data-stat="{arms_stat}" d="M 54 104 C 46 112 44 130 52 142 C 60 132 60 118 58 104 Z M 146 104 C 154 112 156 130 148 142 C 140 132 140 118 142 104 Z M 50 146 C 42 160 40 178 48 190 C 54 182 56 166 54 146 Z M 150 146 C 158 160 160 178 152 190 C 146 182 144 166 146 146 Z"/>
            <path class="muscle-group" data-name="Core" data-stat="{core_stat}" d="M 82 112 C 78 130 80 160 84 182 C 92 186 108 186 116 182 C 120 160 122 130 118 112 C 108 110 92 110 82 112 Z"/>
            <path class="muscle-group" data-name="Quads" data-stat="{quads_stat}" d="M 82 188 C 70 200 68 250 82 282 C 94 280 96 230 98 188 Z M 118 188 C 130 200 132 250 118 282 C 106 280 104 230 102 188 Z"/>
            <path class="muscle-group" data-name="Calves" data-stat="{calves_stat}" d="M 80 292 C 68 310 70 348 82 368 C 88 360 90 328 88 292 Z M 120 292 C 104 288 108 360 Q 122 350 120 288 Z"/>
        </svg>
        <!-- POSTERIOR -->
        <svg width="220" height="460" viewBox="0 0 200 400">
            <text x="100" y="20" class="title-label">POSTERIOR (BACK)</text>
            <path class="body-silhouette" d="M 90 35 C 90 22 110 22 110 35 C 110 52 90 52 90 35 Z M 93 54 L 84 68 L 116 68 L 107 54 Z"/>
            <path class="muscle-group" data-name="Back" data-stat="{back_stat}" d="M 84 70 L 116 70 L 132 90 C 130 120 118 148 100 160 C 82 148 70 120 68 90 Z"/>
            <path class="muscle-group" data-name="Arms" data-stat="{arms_stat}" d="M 58 92 C 50 102 48 122 54 138 C 62 128 62 110 62 92 Z M 142 92 C 150 102 152 122 146 138 C 138 128 138 110 138 92 Z"/>
            <path class="muscle-group" data-name="Hamstrings & Glutes" data-stat="{ham_stat}" d="M 76 166 C 68 180 66 240 82 280 C 94 278 98 220 98 166 Z M 124 166 C 132 180 134 240 118 280 C 106 278 102 220 102 166 Z"/>
            <path class="muscle-group" data-name="Calves" data-stat="{calves_stat}" d="M 78 288 C 66 310 68 348 82 368 C 88 360 90 328 88 288 Z M 122 288 C 134 310 132 348 118 368 C 112 360 110 328 112 288 Z"/>
        </svg>
    </div>
    <script>
        const tooltip = document.getElementById('tooltip');
        const muscles = document.querySelectorAll('.muscle-group');
        muscles.forEach(m => {{
            m.addEventListener('mousemove', (e) => {{
                tooltip.style.display = 'block';
                tooltip.style.left = (e.pageX + 15) + 'px';
                tooltip.style.top = (e.pageY - 10) + 'px';
                tooltip.innerHTML = '<strong>' + m.getAttribute('data-name') + '</strong><br/>' + m.getAttribute('data-stat');
            }});
            m.addEventListener('mouseleave', () => {{ tooltip.style.display = 'none'; }});
        }});
    </script>
    </body>
    </html>
    """
    components.html(svg_body_html, height=480)

    st.divider()
    if not workouts_df.empty:
        chart_data = pd.DataFrame(list(vol_summary.items()), columns=["Primary Muscle", "Volume"])
        fig_bar = px.bar(chart_data, x="Primary Muscle", y="Volume", title="Fractional Volume Share (lbs Lifted in Range)", color="Primary Muscle", color_discrete_sequence=px.colors.qualitative.Vivid)
        fig_bar.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#FFFFFF"), yaxis=dict(showgrid=False), legend=HIGH_CONTRAST_LEGEND)
        st.plotly_chart(fig_bar, use_container_width=True)

# ALL-TIME HISTORICAL HALL OF FAME MODULE
with tab_history:
    st.subheader("🏛️ Lifetime Health & Performance Records (All-Time Unfiltered)")
    
    if not raw_weight_df.empty and "Weight" in raw_weight_df.columns:
        first_weight = raw_weight_df["Weight"].iloc[0]
        latest_weight = raw_weight_df["Weight"].iloc[-1]
        weight_delta = round(latest_weight - first_weight, 1)
        peak_weight = raw_weight_df["Weight"].max()
        lowest_weight = raw_weight_df["Weight"].min()
        
        st.markdown("#### ⚖️ Body Weight Journey")
        w_h1, w_h2, w_h3, w_h4 = st.columns(4)
        with w_h1: st.metric("Net Scale Change", f"{weight_delta} lbs", delta=f"{weight_delta} lbs", delta_color="inverse")
        with w_h2: st.metric("First Recorded Weight", f"{first_weight} lbs")
        with w_h3: st.metric("All-Time Peak Weight", f"{peak_weight} lbs")
        with w_h4: st.metric("All-Time Lowest Weight", f"{lowest_weight} lbs")
        st.divider()

    if not raw_steps_df.empty and "Step Count" in raw_steps_df.columns:
        total_lifetime_steps = int(raw_steps_df["Step Count"].sum())
        all_time_avg_steps = int(raw_steps_df["Step Count"].mean())
        single_day_step_record = int(raw_steps_df["Step Count"].max())
        total_step_days = len(raw_steps_df)
        
        st.markdown("#### 👟 Lifetime Movement Telemetry")
        s_h1, s_h2, s_h3, s_h4 = st.columns(4)
        with s_h1: st.metric("Total Steps Ever Taken", f"{total_lifetime_steps:,}")
        with s_h2: st.metric("Lifetime Daily Step Avg", f"{all_time_avg_steps:,}")
        with s_h3: st.metric("Single-Day Step Record", f"{single_day_step_record:,}")
        with s_h4: st.metric("Total Tracking Days Logged", f"{total_step_days:,} days")
        st.divider()

    if not raw_workouts_df.empty and "Volume" in raw_workouts_df.columns:
        raw_workouts_df["Week_Year"] = raw_workouts_df["Date"].dt.to_period("W")
        weekly_volume_df = raw_workouts_df.groupby("Week_Year")["Volume"].sum()
        
        avg_weekly_volume = int(weekly_volume_df.mean())
        peak_weekly_volume = int(weekly_volume_df.max())
        total_lifetime_volume = int(raw_workouts_df["Volume"].sum())
        total_sets_logged = len(raw_workouts_df)
        
        st.markdown("#### 🏋️ Lifetime Strength & Weekly Tonnage")
        v_h1, v_h2, v_h3, v_h4 = st.columns(4)
        with v_h1: st.metric("Average Weight Lifted / Week", f"{avg_weekly_volume:,} lbs")
        with v_h2: st.metric("Peak Volume Week", f"{peak_weekly_volume:,} lbs")
        with v_h3: st.metric("Lifetime Tonnage", f"{total_lifetime_volume:,} lbs")
        with v_h4: st.metric("Total Hard Sets Logged", f"{total_sets_logged:,} sets")
        st.divider()

        weekly_vol_chart = weekly_volume_df.reset_index()
        weekly_vol_chart["Week_Start"] = weekly_vol_chart["Week_Year"].dt.start_time
        fig_weekly_vol = px.bar(
            weekly_vol_chart, x="Week_Start", y="Volume",
            title="Lifetime Weekly Tonnage Trajectory (lbs / week)",
            color_discrete_sequence=["#00FF87"]
        )
        fig_weekly_vol.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis=dict(showgrid=False), legend=HIGH_CONTRAST_LEGEND)
        st.plotly_chart(fig_weekly_vol, use_container_width=True)
