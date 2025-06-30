The app.py is for local Streamlit runs. Adapt for cloud-only version.

This Streamlit app converts speech to text.

The following are important points for running locally.
1. For Stefan Rummer's streamlit-audio-recorder, make sure app.py is in the same folder with "st_audiorec". Inside "st_audiorec" is "frontend", and inside "frontend" is "build."
2. For ffmpeg, after it's downloaded and extracted, make sure to add "C:\Users\...\ffmpeg\bin" into Windows Environment Variables "Path." 
