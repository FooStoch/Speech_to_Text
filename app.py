import streamlit as st
import pyaudio
import websocket
import json
import threading
import time
from urllib.parse import urlencode
from datetime import datetime

# Streamlit app configuration
st.set_page_config(page_title="Voice Assistant", page_icon="🎙️")
st.title("🎙️ Real-Time Voice Assistant")
st.caption("Speak and see your words appear in real-time (like Siri/Alexa)")

# --- Configuration ---
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("AssemblyAI API Key", type="password")
if not api_key:
    st.warning("Please enter your AssemblyAI API key in the sidebar")
    st.stop()

CONNECTION_PARAMS = {
    "sample_rate": 16000,
    "format_turns": True,
}
API_ENDPOINT_BASE_URL = "wss://streaming.assemblyai.com/v3/ws"
API_ENDPOINT = f"{API_ENDPOINT_BASE_URL}?{urlencode(CONNECTION_PARAMS)}"

# Audio Configuration
FRAMES_PER_BUFFER = 800  # 50ms of audio (0.05s * 16000Hz)
SAMPLE_RATE = CONNECTION_PARAMS["sample_rate"]
CHANNELS = 1
FORMAT = pyaudio.paInt16

# Global variables for audio stream and websocket
audio = None
stream = None
ws_app = None
audio_thread = None
stop_event = threading.Event()

# Initialize session state for transcript
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
if 'is_listening' not in st.session_state:
    st.session_state.is_listening = False

# --- WebSocket Event Handlers ---
def on_open(ws):
    st.session_state.is_listening = True
    st.toast("Listening... Speak now!", icon="🎤")

def on_message(ws, message):
    try:
        data = json.loads(message)
        msg_type = data.get('type')
        
        if msg_type == "Turn":
            transcript = data.get('transcript', '')
            formatted = data.get('turn_is_formatted', False)
            
            if formatted:
                st.session_state.transcript += f"\n{transcript}"
            else:
                # Update the last line for partial results
                lines = st.session_state.transcript.split('\n')
                if lines:
                    lines[-1] = transcript
                    st.session_state.transcript = '\n'.join(lines)
            
            # Rerun to update the display
            st.rerun()
            
    except Exception as e:
        st.error(f"Error handling message: {e}")

def on_error(ws, error):
    st.error(f"WebSocket Error: {error}")
    stop_event.set()

def on_close(ws, close_status_code, close_msg):
    st.session_state.is_listening = False
    st.toast("Stopped listening", icon="✋")
    cleanup_resources()
    st.rerun()

def cleanup_resources():
    global stream, audio
    stop_event.set()
    
    if stream:
        if stream.is_active():
            stream.stop_stream()
        stream.close()
        stream = None
    
    if audio:
        audio.terminate()
        audio = None
    
    if audio_thread and audio_thread.is_alive():
        audio_thread.join(timeout=1.0)

# --- Audio Streaming Function ---
def stream_audio():
    global stream
    while not stop_event.is_set() and st.session_state.is_listening:
        try:
            audio_data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
            ws_app.send(audio_data, websocket.ABNF.OPCODE_BINARY)
        except Exception as e:
            st.error(f"Error streaming audio: {e}")
            break

# --- Start/Stop Functions ---
def start_listening():
    global audio, stream, ws_app, audio_thread
    
    try:
        # Initialize PyAudio
        audio = pyaudio.PyAudio()
        
        # Open microphone stream
        stream = audio.open(
            input=True,
            frames_per_buffer=FRAMES_PER_BUFFER,
            channels=CHANNELS,
            format=FORMAT,
            rate=SAMPLE_RATE,
        )
        
        # Create WebSocketApp
        ws_app = websocket.WebSocketApp(
            API_ENDPOINT,
            header={"Authorization": api_key},
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        
        # Run WebSocket in a thread
        ws_thread = threading.Thread(target=ws_app.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Start audio streaming in another thread
        stop_event.clear()
        audio_thread = threading.Thread(target=stream_audio)
        audio_thread.daemon = True
        audio_thread.start()
        
    except Exception as e:
        st.error(f"Error starting listening: {e}")
        cleanup_resources()

def stop_listening():
    stop_event.set()
    if ws_app and ws_app.sock and ws_app.sock.connected:
        try:
            terminate_message = {"type": "Terminate"}
            ws_app.send(json.dumps(terminate_message))
            time.sleep(1)  # Give time for message to process
        except Exception as e:
            st.error(f"Error sending termination message: {e}")
    
    if ws_app:
        ws_app.close()
    
    cleanup_resources()
    st.session_state.is_listening = False
    st.rerun()

# --- UI Components ---
col1, col2 = st.columns(2)
with col1:
    if st.button("🎤 Start Listening", disabled=st.session_state.is_listening):
        start_listening()

with col2:
    if st.button("✋ Stop Listening", disabled=not st.session_state.is_listening):
        stop_listening()

# Display transcript
st.subheader("Transcript")
transcript_display = st.empty()
transcript_display.text_area("Your speech will appear here:", 
                            value=st.session_state.transcript, 
                            height=300,
                            label_visibility="collapsed")

# Status indicator
status_placeholder = st.empty()
if st.session_state.is_listening:
    status_placeholder.success("Status: Listening... Speak now!")
else:
    status_placeholder.info("Status: Ready to listen")

# Instructions
st.markdown("""
### How to use:
1. Enter your AssemblyAI API key in the sidebar
2. Click "Start Listening" and grant microphone permissions
3. Speak naturally - your words will appear in real-time
4. Click "Stop Listening" when finished
""")

# Cleanup when app closes
def on_app_close():
    stop_listening()

import atexit
atexit.register(on_app_close)
