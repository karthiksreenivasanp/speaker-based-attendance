import streamlit as st
import requests
import pandas as pd
import os
import time

# Styling
# Styling
st.set_page_config(page_title="Voice Attendance", layout="wide", initial_sidebar_state="collapsed")

# --- MOBILE APP STYLING (Glassmorphism + Dark Mode) ---
st.markdown("""
    <style>
    /* 1. Global Reset & Dark Theme */
    .stApp {
        background-color: #0e1117;
        font-family: 'Inter', sans-serif;
    }
    
    /* 2. Hide Streamlit Bloat */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;} /* Hides the top colored bar */
    
    /* 3. Mobile Card Style (Glassmorphism) */
    .css-1r6slb0, .css-12oz5g7 {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
    }
    
    /* 4. Large Touch-Friendly Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        height: 50px;
        font-size: 18px;
        border-radius: 12px;
        background-color: #1c1f26;
        color: white;
        border: 1px solid #333;
    }
    
    /* 5. Gradient Action Buttons (Full Width) */
    .stButton button {
        width: 100%;
        height: 55px;
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        color: white;
        font-size: 20px;
        font-weight: bold;
        border: none;
        border-radius: 12px;
        transition: transform 0.1s;
    }
    .stButton button:active {
        transform: scale(0.98);
    }
    
    /* 6. Success/Error Messages */
    .stSuccess, .stError, .stInfo, .stWarning {
        border-radius: 12px;
        font-size: 1.1rem;
    }
    
    /* 7. Typography */
    h1 {
        font-size: 2.2rem;
        font-weight: 800;
        background: -webkit-linear-gradient(eee, #999);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding-bottom: 20px;
    }
    h2, h3 {
        color: #ddd;
    }
    
    /* 8. Audio Input Fixes for Mobile */
    .stAudio {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎙️ Voice Access")

# Sidebar for navigation
with st.sidebar.expander("⚙️ Server Settings"):
    # Allow user to paste Ngrok URL. Default to localhost.
    default_url = "http://127.0.0.1:8000/api/v1"
    API_URL = st.text_input("Backend API URL", value=default_url)

menu = st.sidebar.selectbox("Menu", ["Register Student", "Enroll Voice", "Identify Speaker", "Admin Dashboard"])

def record_audio(key):
    """Simple audio recorder using webrtc"""
    # Note: Streamlit execution model makes saving files tricky with webrtc direct to disk.
    # For this demo, we will use a simpler file uploader or assume webrtc saves to a temp file.
    # To keep it robust without complex webrtc handling code block which is huge:
    # We will use st.file_uploader for high reliability in this version, 
    # as webrtc requires STUN/TURN servers for real deployment often.
    # But user asked for Android/App feel. Reverting to simple file upload for maximum stability.
    return st.file_uploader("Upload Audio Sample (WAV)", type=["wav"], key=key, accept_multiple_files=False)

if menu == "Register Student":
    st.header("Register New Student")
    with st.form("register_form"):
        name = st.text_input("Full Name")
        roll_no = st.text_input("Roll Number")
        course = st.text_input("Course")
        submit = st.form_submit_button("Register")
        
        if submit:
             resp = requests.post(f"{API_URL}/students/", json={
                 "name": name, "roll_number": roll_no, "course": course
             })
             if resp.status_code == 200:
                 new_id = resp.json()['id']
                 st.session_state['last_id'] = new_id
                 st.success(f"Student Registered! ID: {new_id} (Copied to clipboard)")
             else:
                 st.error(f"Error: {resp.text}")

elif menu == "Enroll Voice":
    st.header("Enroll Voice Specs")
    
    default_id = st.session_state.get('last_id', 1)
    student_id = st.number_input("Enter Student ID", min_value=1, value=default_id)
    
    # Check if student exists and show name
    if student_id:
        chk = requests.get(f"{API_URL}/students/{student_id}")
        if chk.status_code == 200:
            st.success(f"👤 Selected: **{chk.json()['name']}**")
        else:
            st.error("❌ Student not found! Please Register first.")
    
    st.info("Record (or Upload) 3 voice samples (e.g., 'My voice is my password')")
    
    enroll_mode = st.radio("Input Source", ["Microphone", "Upload Files"], horizontal=True, key="enroll_mode")
    
    f1, f2, f3 = None, None, None
    
    if enroll_mode == "Microphone":
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Sample 1")
            f1 = st.audio_input("Record Sample 1", key="s1")
        with col2:
            st.subheader("Sample 2")
            f2 = st.audio_input("Record Sample 2", key="s2")
        with col3:
            st.subheader("Sample 3")
            f3 = st.audio_input("Record Sample 3", key="s3")
    else:
        # Upload Mode
        f1 = st.file_uploader("Upload Sample 1 (WAV)", type=["wav"], key="u1")
        f2 = st.file_uploader("Upload Sample 2 (WAV)", type=["wav"], key="u2")
        f3 = st.file_uploader("Upload Sample 3 (WAV)", type=["wav"], key="u3")
        
    if st.button("Enroll Voice"):
        if f1 and f2 and f3:
            # st.audio_input returns a file-like object (BytesIO)
            files = [
                ('files', ("s1.wav", f1, "audio/wav")),
                ('files', ("s2.wav", f2, "audio/wav")),
                ('files', ("s3.wav", f3, "audio/wav"))
            ]
            with st.spinner("Processing Voice Templates..."):
                resp = requests.post(f"{API_URL}/enroll/{student_id}", files=files)
            
            if resp.status_code == 200:
                st.balloons()
                st.success("✅ Enrollment Successful!")
            else:
                st.error(f"Enrollment Failed: {resp.json().get('detail')}")
        else:
            st.warning("Please record all 3 samples.")


elif menu == "Identify Speaker":
    st.header("🕵️ Identify Who is Speaking")
    st.info("The system will guess who you are from the database.")
    
    # Selection Mode
    mode = st.radio("Input Source", ["Microphone", "Upload File"], horizontal=True)
    
    audio_file = None
    if mode == "Microphone":
        audio_file = st.audio_input("Record Voice", key="ident_mic")
    else:
        audio_file = st.file_uploader("Upload Audio (WAV)", type=["wav"], key="ident_upload")
    
    if st.button("Identify Me"):
        if audio_file:
            files = {'file': ("identify.wav", audio_file, "audio/wav")}
            with st.spinner("Analyzing Voice Database..."):
                resp = requests.post(f"{API_URL}/verify/identify", files=files)
            
            if resp.status_code == 200:
                res = resp.json()
                if res['identified']:
                    st.balloons()
                    st.success(f"✅ You are: **{res['name']}** (ID: {res['student_id']})")
                    st.caption(f"Confidence Score: {res['score']:.3f}")
                else:
                    st.error("❌ Unknown Speaker")
                        
                    if 'best_score' in res:
                        st.warning(f"Best Guess: {res.get('message', '')} (Score: {res['best_score']:.3f})")
            else:
                st.error(f"Error: {resp.text}")

elif menu == "Admin Dashboard":
    st.header("📊 Admin Dashboard")
    
    st.subheader("📋 Class Roster Status")
    
    if st.button("Refresh Roster"):
        # 1. Fetch Students
        s_resp = requests.get(f"{API_URL}/students/")
        students = s_resp.json() if s_resp.status_code == 200 else []
        
        # 2. Fetch Attendance Logs
        a_resp = requests.get(f"{API_URL}/admin/attendance")
        logs = a_resp.json() if a_resp.status_code == 200 else []
        
        if students:
            # Create Base DataFrame
            df = pd.DataFrame(students)[['id', 'name', 'roll_number']]
            df['Status'] = 'Absent' # Default
            
            # Find Present IDs
            present_ids = set([log['student_id'] for log in logs if log['status'] == 'PRESENT'])
            
            # Update Status
            df.loc[df['id'].isin(present_ids), 'Status'] = 'Present'
            
            # Styling Function
            def color_status(val):
                color = '#28a745' if val == 'Present' else '#dc3545' # Green vs Red
                return f'color: {color}; font-weight: bold'

            # Display Styled Table
            st.dataframe(df.style.map(color_status, subset=['Status']), use_container_width=True)
            
            # Counts
            total = len(df)
            present = len(present_ids)
            st.metric("Attendance Count", f"{present}/{total}", delta=f"{present} Present")
            
        else:
            st.info("No students registered.")
            
    st.divider()
    with st.expander("View Raw Logs"):
        # Optional: Show raw history if needed
        l_resp = requests.get(f"{API_URL}/admin/attendance")
        if l_resp.status_code == 200 and l_resp.json():
             st.dataframe(pd.DataFrame(l_resp.json()))
