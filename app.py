import streamlit as st
from audio_recorder_streamlit import audio_recorder
import torch
from transformers import pipeline
import tempfile
import os

# Configure app
st.set_page_config(page_title="🎤 Whisper Voice Search", layout="centered")
st.title("🎤 Real-Time Transcription (Whisper)")
st.caption("Speak and see text appear instantly - 100% free")

# Initialize Whisper
@st.cache_resource
def load_whisper():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-base",
        device=device
    )
    
whisper = load_whisper()

# Audio recorder component
audio_bytes = audio_recorder(
    pause_threshold=2.0,
    sample_rate=16_000,
    text="Click to start recording",
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
)

# Process audio
if audio_bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    
    try:
        result = whisper(tmp_path)
        st.write("## Transcription")
        st.write(result["text"])
        
        st.audio(audio_bytes, format="audio/wav")
    finally:
        os.unlink(tmp_path)
