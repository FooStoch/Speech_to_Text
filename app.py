import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import websocket
import json
import queue
import numpy as np
import threading
import av
from urllib.parse import urlencode

# Streamlit UI
st.set_page_config(page_title="🎙️ Live Speech-to-Text", layout="centered")
st.title("🎙️ Live Speech-to-Text")
st.caption("Speak into your microphone and see real-time transcription")

# Configuration
api_key = st.sidebar.text_input("AssemblyAI API Key", type="password")
if not api_key:
    st.warning("Please enter your AssemblyAI API key")
    st.stop()

CONNECTION_PARAMS = {
    "sample_rate": 16000,
    "format_turns": True,
}
API_ENDPOINT = f"wss://streaming.assemblyai.com/v3/ws?{urlencode(CONNECTION_PARAMS)}"

# Session State
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
if 'websocket' not in st.session_state:
    st.session_state.websocket = None

# Audio Queue
audio_queue = queue.Queue()
stop_event = threading.Event()

# WebSocket Handlers
def on_message(ws, message):
    try:
        data = json.loads(message)
        if data.get('type') == "Turn":
            transcript = data.get('transcript', '')
            if data.get('turn_is_formatted', False):
                st.session_state.transcript += f"\n{transcript}"
            else:
                lines = st.session_state.transcript.split('\n')
                lines[-1] = transcript
                st.session_state.transcript = '\n'.join(lines)
            st.rerun()
    except Exception as e:
        st.error(f"Error: {str(e)}")

def on_error(ws, error):
    st.error(f"WebSocket error: {error}")
    stop_event.set()

def on_close(ws, *args):
    stop_event.set()
    st.session_state.websocket = None
    st.rerun()

def on_open(ws):
    def send_audio():
        while not stop_event.is_set():
            try:
                audio_data = audio_queue.get(timeout=0.1)
                ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)
            except queue.Empty:
                continue
            except Exception as e:
                st.error(f"Audio send error: {str(e)}")
                break
    
    threading.Thread(target=send_audio, daemon=True).start()

# Audio Processing
def audio_frame_handler(frame: av.AudioFrame):
    audio_data = frame.to_ndarray().flatten()
    audio_int16 = (audio_data * 32767).astype(np.int16)
    audio_bytes = audio_int16.tobytes()
    audio_queue.put(audio_bytes)
    return frame

# WebRTC Component
webrtc_ctx = webrtc_streamer(
    key="speech-to-text",
    mode=WebRtcMode.SENDONLY,
    audio_frame_callback=audio_frame_handler,
    media_stream_constraints={
        "audio": {
            "sampleRate": 16000,
            "channelCount": 1,
        },
        "video": False
    },
    async_processing=True,
)

# WebSocket Management
if webrtc_ctx.state.playing and st.session_state.websocket is None:
    st.session_state.websocket = websocket.WebSocketApp(
        API_ENDPOINT,
        header={"Authorization": api_key},
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    threading.Thread(
        target=st.session_state.websocket.run_forever,
        daemon=True
    ).start()
elif not webrtc_ctx.state.playing and st.session_state.websocket:
    stop_event.set()
    st.session_state.websocket.close()
    st.session_state.websocket = None

# Transcript Display
st.text_area(
    "Live Transcription",
    value=st.session_state.transcript,
    height=300,
    key="transcript_display"
)

# Status
if webrtc_ctx.state.playing:
    st.success("🎤 Listening... Speak now!")
else:
    st.info("🟢 Ready to start - Allow microphone access when prompted")
