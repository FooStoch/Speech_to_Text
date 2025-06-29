import streamlit as st
import websocket
import json
import threading
import queue
import base64
import numpy as np
from urllib.parse import urlencode

# Streamlit UI Setup
st.set_page_config(page_title="🎙️ Voice Assistant", layout="wide")
st.title("🎙️ Real-Time Speech-to-Text")
st.caption("Speak into your microphone and see the transcription appear in real-time")

# --- Configuration ---
api_key = st.sidebar.text_input("AssemblyAI API Key", type="password")
if not api_key:
    st.warning("Please enter your AssemblyAI API key in the sidebar")
    st.stop()

CONNECTION_PARAMS = {
    "sample_rate": 16000,
    "format_turns": True,
}
API_ENDPOINT = f"wss://streaming.assemblyai.com/v3/ws?{urlencode(CONNECTION_PARAMS)}"

# --- Audio Processing ---
audio_queue = queue.Queue()
stop_event = threading.Event()

def float32_to_int16(audio_float32):
    """Convert float32 (-1 to +1) to int16 for AssemblyAI"""
    return (audio_float32 * 32767).astype(np.int16)

# --- WebSocket Handlers ---
def on_message(ws, message):
    try:
        data = json.loads(message)
        if data.get('type') == "Turn":
            transcript = data.get('transcript', '')
            if data.get('turn_is_formatted', False):
                st.session_state.transcript += f"\n{transcript}"
            else:
                # Update current line
                lines = st.session_state.transcript.split('\n')
                lines[-1] = transcript
                st.session_state.transcript = '\n'.join(lines)
            st.rerun()
    except Exception as e:
        st.error(f"Error handling message: {e}")

def on_error(ws, error):
    st.error(f"WebSocket error: {error}")
    stop_event.set()

def on_close(ws, *args):
    st.session_state.is_listening = False
    st.toast("Connection closed")
    stop_event.set()

def on_open(ws):
    st.session_state.is_listening = True
    st.toast("Connected - Speak now!", icon="🎤")
    
    def send_audio():
        while not stop_event.is_set():
            try:
                audio_data = audio_queue.get(timeout=0.1)
                ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)
            except queue.Empty:
                continue
            except Exception as e:
                st.error(f"Error sending audio: {e}")
                break
    
    threading.Thread(target=send_audio, daemon=True).start()

# --- Streamlit Components ---
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
if 'is_listening' not in st.session_state:
    st.session_state.is_listening = False

transcript_display = st.empty()
status_display = st.empty()

# Audio Capture via JavaScript
audio_js = """
<script>
const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioContext = new AudioContext({ sampleRate: 16000 });
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    
    source.connect(processor);
    processor.connect(audioContext.destination);
    
    processor.onaudioprocess = (e) => {
        const audioData = e.inputBuffer.getChannelData(0);
        window.parent.postMessage({
            type: 'audioData',
            data: Array.from(audioData)
        }, '*');
    };
}

if (!window.recordingStarted) {
    startRecording();
    window.recordingStarted = true;
}
</script>
"""

# Inject JavaScript
st.components.v1.html(audio_js, height=0)

# Handle audio data from JS
def handle_audio_data(audio_float32):
    audio_int16 = float32_to_int16(np.array(audio_float32))
    audio_bytes = audio_int16.tobytes()
    audio_queue.put(audio_bytes)

# WebSocket Management
def start_websocket():
    ws = websocket.WebSocketApp(
        API_ENDPOINT,
        header={"Authorization": api_key},
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    threading.Thread(target=ws.run_forever, daemon=True).start()

# --- UI Controls ---
col1, col2 = st.columns(2)
with col1:
    if st.button("🎤 Start Listening", disabled=st.session_state.is_listening):
        start_websocket()

with col2:
    if st.button("✋ Stop Listening", disabled=not st.session_state.is_listening):
        stop_event.set()
        st.session_state.is_listening = False
        st.rerun()

# Display transcript
transcript_display.text_area(
    "Live Transcription",
    value=st.session_state.transcript,
    height=300,
    key="transcript_box"
)

# Status indicator
if st.session_state.is_listening:
    status_display.success("✅ Listening... Speak now!")
else:
    status_display.info("🟢 Ready to start")

# Handle JavaScript messages
try:
    from streamlit.runtime.scriptrunner import RerunData, RerunException
    from streamlit.web.server.websocket_headers import _get_websocket_headers

    ctx = st.runtime.scriptrunner.get_script_run_ctx()
    if ctx and hasattr(ctx, 'request'):
        data = ctx.request._request.body
        if data:
            message = json.loads(data)
            if message.get('type') == 'audioData':
                handle_audio_data(message['data'])
except Exception:
    pass
