import streamlit as st
import assemblyai as aai
import json
import time
from streamlit.components.v1 import html

# Configure AssemblyAI
aai.settings.api_key = st.secrets.get("ASSEMBLYAI_API_KEY") or st.text_input(
    "AssemblyAI API Key", 
    type="password",
    help="Get your API key from https://assemblyai.com/dashboard"
)

st.title("🎙️ Real-Time Voice Search")
st.caption("Speak and see results instantly (like Google/Siri)")

# Session state for transcript
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
    st.session_state.last_update = 0

# Audio handler component
def audio_component():
    with open("audio_handler.js") as f:
        js_code = f.read()
    
    html(f"""
    <script>
    {js_code}
    startRecording('{aai.settings.api_key}');
    </script>
    """, height=0)

# Display component
audio_component()

# Real-time transcript display
transcript_placeholder = st.empty()
status_placeholder = st.empty()

# Handle messages from JavaScript
def handle_message(msg):
    if msg.get("type") == "transcript":
        st.session_state.transcript = msg["text"]
        st.session_state.last_update = time.time()
    elif msg.get("type") == "status":
        status_placeholder.info(f"Status: {msg['message']}")
    elif msg.get("type") == "error":
        status_placeholder.error(msg["message"])

# Check for new messages
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    ctx = get_script_run_ctx()
    if ctx and hasattr(ctx, 'request'):
        msg = json.loads(ctx.request._request.body)
        handle_message(msg)
except:
    pass

# Auto-update display
if time.time() - st.session_state.last_update < 1:
    transcript_placeholder.text_area(
        "Live Transcription", 
        value=st.session_state.transcript,
        height=200,
        key="transcript_display"
    )
