import streamlit as st
from streamlit.components.v1 import html
import json

st.title("🎤 Real-Time Voice Search")
st.write("Speak and see text appear instantly")

# Get API key
api_key = st.text_input("AssemblyAI API Key", type="password")

# Load JavaScript
with open("audio.js") as f:
    js_code = f.read().replace("YOUR_API_KEY", api_key)

# Inject JavaScript
html(f"""
<script>
{js_code}
</script>
<div id="status">Waiting for microphone access...</div>
<div id="transcript" style="margin:20px; padding:10px; border:1px solid #ccc;"></div>
""", height=300)

# Handle messages from JavaScript
def handle_message(msg):
    if msg.get("type") == "transcript":
        st.write(f"**You said:** {msg['text']}")
    elif msg.get("type") == "error":
        st.error(msg["message"])

# Check for messages
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    ctx = get_script_run_ctx()
    if ctx and hasattr(ctx, 'request'):
        msg = json.loads(ctx.request._request.body)
        handle_message(msg)
except:
    pass
