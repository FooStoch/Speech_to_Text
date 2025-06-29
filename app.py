import streamlit as st
from st_audiorec import st_audiorec
import whisper
import tempfile
import os

# Load Whisper model (change "base" to "small" or "tiny" for faster but less accurate transcription)
@st.cache_resource
def load_model():
    return whisper.load_model("base")

model = load_model()

st.title("🎙️ Live Audio Transcription")
st.write("Record your voice and get an instant transcript below!")

# Record audio (returns WAV bytes)
audio_bytes = st_audiorec()  # returns WAV bytes arrayBuffer format

if audio_bytes:
    # Play back the recording
    st.audio(audio_bytes, format="audio/wav")

    # Save to temporary file for Whisper
    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_wav.write(audio_bytes)
    tmp_wav.flush()

    # Transcribe
    with st.spinner("Transcribing..."):
        result = model.transcribe(tmp_wav.name)
        transcript = result.get("text", "")

    # Clean up temp file
    tmp_wav.close()
    os.unlink(tmp_wav.name)

    # Initialize chat history
    if "history" not in st.session_state:
        st.session_state.history = []
    # Append new transcript
    st.session_state.history.append(transcript)

# Display chat history
if "history" in st.session_state and st.session_state.history:
    st.subheader("🗨️ Transcript Chat")
    chat_content = "".join([
        f"**You said:** {line}" for line in st.session_state.history
    ])
    st.markdown(chat_content)
