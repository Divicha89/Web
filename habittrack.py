import streamlit as st
import pandas as pd
import datetime
import altair as alt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai

# --- Setup ---
st.set_page_config(page_title="Habit Logger", layout="wide")
st.title("📅 Habit & Time Tracker")

# --- Google Sheets Setup ---
@st.cache_resource
def connect_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("habit_log").sheet1
    return sheet

sheet = connect_gsheet()

# --- Read Data ---
data = sheet.get_all_records()
df = pd.DataFrame(data)
if not df.empty:
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["duration_hours"] = pd.to_numeric(df["duration_hours"], errors="coerce")

# --- Tabs ---
tab1, tab2 = st.tabs(["➕ Log Habit", "📊 Visualize & Analyze"])

with tab1:
    st.subheader("Log New Entry")
    with st.form("log_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            habit = st.text_input("Habit / Task", placeholder="e.g. reading")
        with col2:
            start_time = st.time_input("Start Time", value=datetime.time(14, 0))
        with col3:
            end_time = st.time_input("End Time", value=datetime.time(14, 45))
        with col4:
            date = st.date_input("Date", value=datetime.date.today())

        submitted = st.form_submit_button("Log Activity")
        if submitted and habit:
            habit_clean = habit.strip().lower()
            duration = (datetime.datetime.combine(date, end_time) - datetime.datetime.combine(date, start_time)).total_seconds() / 3600
            sheet.append_row([
                habit_clean,
                start_time.strftime('%H:%M'),
                end_time.strftime('%H:%M'),
                date.isoformat(),
                round(duration, 2)
            ])
            st.success(f"✅ Logged '{habit_clean}' from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')} on {date}.")

with tab2:
    st.subheader("Filter & Analyze")

    if df.empty:
        st.info("No records found in sheet.")
    else:
        colf1, colf2 = st.columns(2)
        with colf1:
            unique_habits = sorted(df["habit"].unique().tolist())
            selected_habit = st.selectbox("Filter by Habit", ["All"] + unique_habits)
        with colf2:
            time_range = st.selectbox("Time Range", ["This Week", "Fortnight", "This Month"])
            days_back = {"This Week": 7, "Fortnight": 14, "This Month": 30}[time_range]
            min_date = (datetime.datetime.today() - datetime.timedelta(days=days_back)).date()

        filtered_df = df[df["date"] >= min_date]
        if selected_habit != "All":
            filtered_df = filtered_df[filtered_df["habit"] == selected_habit]

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

# --- Sidebar for Gemini AI ---
with st.sidebar:
    if st.button("💬 Show AI Feedback"):
        if not filtered_df.empty:
            prompt_context = "\n".join([
                f"{row['habit']}: {row['start_time']} to {row['end_time']} on {row['date']} ({row['duration_hours']:.2f} hours)"
                for _, row in filtered_df.iterrows()
            ])
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
