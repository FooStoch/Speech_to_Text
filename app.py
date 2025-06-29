import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import websocket
import json
import queue
import numpy as np
import threading
import av
from urllib.parse import urlencode

# Debug setup
DEBUG = True  # Set to False to disable debug prints

def debug_print(*args):
    if DEBUG:
        print("[DEBUG]", *args)

# Streamlit UI
st.set_page_config(page_title="🎙️ Debug Mode", layout="centered")
st.title("🔍 Debugging Speech-to-Text")
st.warning("Debug mode enabled - check browser console and server logs")

# Configuration
api_key = st.text_input("AssemblyAI API Key", type="password")
if not api_key:
    st.stop()

CONNECTION_PARAMS = {"sample_rate": 16000, "format_turns": True}
API_ENDPOINT = f"wss://streaming.assemblyai.com/v3/ws?{urlencode(CONNECTION_PARAMS)}"

# Session State
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
    st.session_state.audio_samples = []
    st.session_state.websocket = None

# Audio Queue
audio_queue = queue.Queue()
stop_event = threading.Event()

# WebSocket Handlers
def on_message(ws, message):
    try:
        debug_print("RAW WEBSOCKET MESSAGE:", message)
        data = json.loads(message)
        
        if data.get('type') == "Turn":
            transcript = data.get('transcript', '')
            debug_print("RECEIVED TRANSCRIPT:", transcript)
            
            if data.get('turn_is_formatted', False):
                st.session_state.transcript += f"\n{transcript}"
            else:
                lines = st.session_state.transcript.split('\n')
                lines[-1] = transcript
                st.session_state.transcript = '\n'.join(lines)
            
            st.rerun()
            
        elif data.get('message'):  # Error messages
            st.error(f"AssemblyAI Error: {data['message']}")
            debug_print("ASSEMBLYAI ERROR:", data)
            
    except Exception as e:
        st.error(f"Message handling error: {str(e)}")
        debug_print("MESSAGE HANDLING ERROR:", str(e))

def on_error(ws, error):
    st.error(f"WebSocket error: {error}")
    debug_print("WEBSOCKET ERROR:", error)
    stop_event.set()

def on_close(ws, *args):
    debug_print("WEBSOCKET CLOSED:", args)
    stop_event.set()
    st.session_state.websocket = None
    st.rerun()

def on_open(ws):
    debug_print("WEBSOCKET CONNECTED")
    def send_audio():
        while not stop_event.is_set():
            try:
                audio_data = audio_queue.get(timeout=0.1)
                debug_print(f"Sending {len(audio_data)} audio bytes to AssemblyAI")
                ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)
            except queue.Empty:
                continue
            except Exception as e:
                st.error(f"Audio send error: {str(e)}")
                debug_print("AUDIO SEND ERROR:", str(e))
                break
    
    threading.Thread(target=send_audio, daemon=True).start()

# Audio Processing
def audio_frame_handler(frame: av.AudioFrame):
    try:
        audio_data = frame.to_ndarray().flatten()
        st.session_state.audio_samples.extend(audio_data.tolist())
        
        debug_print(f"Received audio frame: {len(audio_data)} samples")
        debug_print(f"Sample values (first 5): {audio_data[:5]}")
        
        audio_int16 = (audio_data * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        audio_queue.put(audio_bytes)
        
        return frame
    except Exception as e:
        debug_print("AUDIO FRAME ERROR:", str(e))
        raise

# WebRTC Component
st.write("### Microphone Access")
webrtc_ctx = webrtc_streamer(
    key="debug-audio",
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

# WebSocket Management
if webrtc_ctx.state.playing and st.session_state.websocket is None:
    debug_print("Initializing WebSocket connection...")
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
    debug_print("Stopping WebSocket connection...")
    stop_event.set()
    st.session_state.websocket.close()
    st.session_state.websocket = None

# Debug Info Panel
with st.expander("Debug Information"):
    st.write("### Audio Stats")
    st.write(f"Audio samples collected: {len(st.session_state.audio_samples)}")
    st.write(f"WebSocket state: {'Connected' if st.session_state.websocket else 'Disconnected'}")
    st.write(f"Queue size: {audio_queue.qsize()}")
    
    if st.button("Dump Session State"):
        st.write(st.session_state)

# Transcript Display
st.write("### Live Transcription")
transcript_display = st.empty()
transcript_display.text_area(
    "Transcript",
    value=st.session_state.transcript,
    height=300,
    key="transcript_box"
)

st.info("Check your browser's developer console (F12) and server logs for debug output")
