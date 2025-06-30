import streamlit as st
import whisper
import streamlit.components.v1 as components
import tempfile
import numpy as np
from io import BytesIO
import os

st.title("Whisper App")

st_audiorec = components.declare_component(
    "st_audiorec", path="st_audiorec/frontend/build"
)


record_result = st_audiorec()

wav_bytes = None

if isinstance(record_result, dict) and "arr" in record_result:
    # Stefan's unpacking: record_result['arr'] is a map of {index: byte_value}
    with st.spinner("processing audio…"):
        ind, raw = zip(*record_result["arr"].items())
        ind = np.array(ind, dtype=int)
        raw = np.array(raw, dtype=int)
        sorted_bytes = raw[ind]                      # reorder by index
        # build a bytestream
        stream = BytesIO(bytearray(int(v) & 0xFF for v in sorted_bytes))
        wav_bytes = stream.read()

elif isinstance(record_result, (bytes, bytearray)):
    # in case the component ever returns raw bytes directly
    wav_bytes = bytes(record_result)

# save into session_state
st.session_state.audio_data = wav_bytes

#if wav_audio_data is not None:
    #st.audio(wav_audio_data, format="audio/wav")

model = whisper.load_model("base")
st.text("Whisper Model Loaded")

if "history" not in st.session_state:
    st.session_state.history = []

history_container = st.empty()

if st.button("Transcribe Audio"):
    if st.session_state.audio_data is None:
        st.error("No recording found!")
    else:
        # write to a temp file and pass that path to Whisper
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(st.session_state.audio_data)
        tmp.flush()
        tmp_path = tmp.name
        tmp.close()

        model = whisper.load_model("base")
        #st.success("Transcribing Audio…")
        transcription = model.transcribe(tmp_path)
        #st.success("Done!")
        st.session_state.history.append(transcription["text"])
        #st.experimental_rerun()

if st.button("Clear History"):
    st.session_state.history.clear()

for msg in st.session_state.history:
    st.chat_message("user").write(msg)





