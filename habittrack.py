import numpy as np
from scipy.stats import norm
import streamlit as st
import pandas as pd
import sqlite3
import datetime
import altair as alt
import google.generativeai as genai

# --- Setup ---
st.set_page_config(page_title="Habit Logger", layout="wide")
st.title("📅 Habit & Time Tracker")

# --- Database Setup ---
DB_FILE = "habits.db"
@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    # Drop existing table to ensure new schema
    conn.execute("DROP TABLE IF EXISTS habit_log")
    conn.execute('''CREATE TABLE IF NOT EXISTS habit_log (
        habit TEXT,
        start_time TEXT,
        end_time TEXT,
        date TEXT
    )''')
    return conn

conn = get_connection()
cursor = conn.cursor()

# --- Data Retrieval ---
df = pd.read_sql_query("SELECT * FROM habit_log", conn)
df["date"] = pd.to_datetime(df["date"]).dt.date  # Convert to date only

# Convert time strings to datetime for duration calculation
df["start_time"] = pd.to_datetime(df["start_time"], format='%H:%M').dt.time
df["end_time"] = pd.to_datetime(df["end_time"], format='%H:%M').dt.time
df["duration_hours"] = (pd.to_datetime(df["end_time"].astype(str)) - pd.to_datetime(df["start_time"].astype(str))).dt.total_seconds() / 3600

# --- Tabs for Sections ---
tab1, tab2 = st.tabs(["➕ Log Habit", "📊 Visualize & Analyze"])

with tab1:
    st.subheader("Log New Entry")
    with st.form("log_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            habit = st.text_input("Habit / Task", placeholder="e.g. reading")
        with col2:
            start_time = st.time_input("Start Time", value=datetime.time(14, 0))  # Default 2:00 PM
        with col3:
            end_time = st.time_input("End Time", value=datetime.time(14, 45))    # Default 2:45 PM
        with col4:
            date = st.date_input("Date", value=datetime.date.today())

        submitted = st.form_submit_button("Log Activity")
        if submitted and habit:
            habit_clean = habit.strip().lower()
            cursor.execute("INSERT INTO habit_log VALUES (?, ?, ?, ?)", 
                          (habit_clean, start_time.strftime('%H:%M'), end_time.strftime('%H:%M'), date.isoformat()))
            conn.commit()
            st.success(f"✅ Logged '{habit_clean}' from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')} on {date}.")

with tab2:
    st.subheader("Filter & Analyze")
    colf1, colf2 = st.columns(2)
    with colf1:
        unique_habits = sorted(df["habit"].unique().tolist())
        selected_habit = st.selectbox("Filter by Habit", ["All"] + unique_habits)
    with colf2:
        time_range = st.selectbox("Time Range", ["This Week", "Fortnight", "This Month"])
        if time_range == "This Week":
            days_back = 7
        elif time_range == "Fortnight":
            days_back = 14
        else:  # This Month
            days_back = 30
        min_date = (datetime.datetime.today() - datetime.timedelta(days=days_back)).date()  # Convert to date

    filtered_df = df[df["date"] >= min_date]  # Now compatible comparison
    if selected_habit != "All":
        filtered_df = filtered_df[filtered_df["habit"] == selected_habit]

        # --- Visualization ---
    if not filtered_df.empty:
        st.write("### 📈 Summary Table")
        summary = filtered_df.groupby("habit")["duration_hours"].sum().reset_index()
        summary = summary.rename(columns={"duration_hours": "Total Hours"})
        st.dataframe(summary, use_container_width=False, width=300)

        st.write("### 📊 Visualizations")
        col_viz1, col_viz2 = st.columns(2)

        with col_viz1:
            st.write("#### 📅 Activity Over Time")
            chart_data = filtered_df.groupby(["date", "habit"])["duration_hours"].sum().reset_index()
            bar_chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X("date:T", title="Date", timeUnit="yearmonthdate"),
                y="duration_hours:Q",
                color="habit:N",
                tooltip=["habit", "duration_hours", "date"]
            ).properties(height=300)
            st.altair_chart(bar_chart, use_container_width=True)

        

    else:
        st.info("No data to display for selected filters.")
# --- Sidebar for Gemini ---
with st.sidebar:
    if st.button("💬 Show AI Feedback"):
        if not filtered_df.empty:
            prompt_context = "\n".join([f"{row['habit']}: {row['start_time']} to {row['end_time']} on {row['date']} ({row['duration_hours']:.2f} hours)" for _, row in filtered_df.iterrows()])
            prompt = f"""
            You are a friendly productivity coach.
            Here's the user's activity log for the past {days_back} days:

            {prompt_context}

            Please provide a motivational summary, highlight their most consistent habit, and gently suggest any improvement.
            """
            st.write("### 🤖 AI Feedback")
            try:
                gemini_api_key = st.secrets["gemini"]["api_key"]
                genai.configure(api_key=gemini_api_key)
                model = genai.GenerativeModel("gemini-2.5-flash")
                stream = model.generate_content(prompt, stream=True)
                response_text = ""
                response_box = st.empty()
                for chunk in stream:
                    if chunk.text:
                        response_text += chunk.text
                        response_box.markdown(response_text)
            except Exception as e:
                st.error(f"Error with AI: {e}")
        else:
            st.warning("No data available for feedback.")

# --- Clear DB Option ---
with st.expander("⚙️ Reset / Clear Database"):
    if st.button("Delete All Entries"):
        cursor.execute("DELETE FROM habit_log")
        conn.commit()
        st.warning("All entries deleted.")
        st.rerun()
