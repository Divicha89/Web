import streamlit as st

st.set_page_config(page_title="Know who you are", page_icon="🐧", layout="wide")

# --- CSS Styling ---
st.markdown("""
<style>
.stApp {
    background-color: #d0f0ff;  /* light blue */
    color: #111111;  /* dark text for contrast */
}
.stTextInput input {
    background-color: #ffffff;
    color: #000000;
    border-radius: 6px;
}
.stButton > button {
    background-color: #00aaff;
    color: white;
    border-radius: 6px;
    padding: 6px 16px;
}
</style>
""", unsafe_allow_html=True)
st.sidebar.markdown("Dont ask stupid shit")

st.title("Give us your name, Date of birth. We will guess who you are.")

col1, col2 = st.columns(2)

with col1:
    query = st.text_input("Jathakalu cheptham", key="user_input")

with col2:
    que = st.text_input("Location")
if st.button("Ask"):
        st.session_state["last_query"] = query
        if query.strip().lower()=='vishnu':
                st.write("Little entitled bitch, If I had a dollar for every smart thing you said, I’d be broke.")
        elif query.strip().lower() =='divija':
                st.write("Great guy. deserves everything.")
        else:
               st.write("""Why is that relevant? Why are you checking everyones names😒. 
               Anyway. Thanks for being huam!!!""")
