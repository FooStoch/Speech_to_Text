import streamlit as st
import streamlit.components.v1 as components
import whisper
import tempfile
import os

# Declare the local audio recorder component
_audio_recorder = components.declare_component(
    "audio_recorder", path="st_audiorec/frontend"
)

@st.cache_resource
def load_model():
    # Load Whisper "base" model, swap for "tiny", "small", etc. if desired
    return whisper.load_model("base")

model = load_model()

st.title("🎙️ Live Audio Transcription")
st.write("Speak into your mic and get live transcripts below.")

# Record audio, returns WAV bytes
audio_bytes = _audio_recorder()

if audio_bytes:
    # Playback
    st.audio(audio_bytes, format="audio/wav")

    # Save to temp file for transcription
tmp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_file.write(audio_bytes)
    tmp_file.flush()

    # Transcribe
tmp_path = tmp_file.name
    with st.spinner("Transcribing..."):
        result = model.transcribe(tmp_path)
        text = result.get("text", "")

    tmp_file.close()
    os.unlink(tmp_path)

    # Store in session history
    if "history" not in st.session_state:
        st.session_state.history = []
    st.session_state.history.append(text)

# Display transcript chat
if st.session_state.get("history"):
    st.subheader("🗨️ Transcript Chat")
    for msg in st.session_state.history:
        st.markdown(f"**You said:** {msg}")
