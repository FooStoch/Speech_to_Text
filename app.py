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
st.set_page_config(page_title="🎙️ Speech-to-Text", layout="centered")
st.title("🎙️ Live Speech-to-Text")

api_key = st.text_input("AssemblyAI API Key", type="password", key="api_key")
if not api_key:
    st.stop()

# Session State
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
    st.session_state.ws_connected = False

# Audio Queue
audio_queue = queue.Queue()
stop_event = threading.Event()

# WebSocket Setup
def start_websocket():
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
        st.session_state.ws_connected = False
        st.rerun()

    def on_open(ws):
        st.session_state.ws_connected = True
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

    ws = websocket.WebSocketApp(
        f"wss://streaming.assemblyai.com/v3/ws?{urlencode({'sample_rate': 16000, 'format_turns': True})}",
        header={"Authorization": api_key},
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    
    threading.Thread(target=ws.run_forever, daemon=True).start()
    return ws

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
            "echoCancellation": True,
            "noiseSuppression": True,
        },
        "video": False
    },
    async_processing=True,
)

# Connection Management
if webrtc_ctx.state.playing and not st.session_state.ws_connected:
    start_websocket()
elif not webrtc_ctx.state.playing and st.session_state.ws_connected:
    stop_event.set()
    st.session_state.ws_connected = False

# UI Display
st.text_area("Transcript", value=st.session_state.transcript, height=300)

if st.session_state.ws_connected:
    st.success("✅ Connected and listening")
else:
    st.info("🔴 Not connected - Allow microphone access")
