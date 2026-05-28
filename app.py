import streamlit as st
import pyaudio
import numpy as np
import pandas as pd
import altair as alt
import threading
import time
import random
from datetime import datetime

st.set_page_config(
    page_title="Project Frequency: Production Panel",
    page_icon="🎤",
    layout="wide"
)

st.title("🎤 PROJECT FREQUENCY: UNIFIED REAL-TIME TELEMETRY")
st.markdown("---")

# 1. SIDEBAR TELEMETRY CONTROLS
st.sidebar.header("🎛️ Telemetry Configuration")
mode = st.sidebar.radio(
    "Select Telemetry Source Data:",
    ["Live Hardware Stream (Microphone)", "Synthetic Telemetry Simulation"],
    index=1  # Default to simulation so it instantly works for anyone clicking the cloud link!
)

# Initialize global shared tracking structures
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Timestamp", "Pitch Z", "Volume Z"])
if "live_metrics" not in st.session_state:
    st.session_state.live_metrics = {"pitch_z": 0.0, "vol_z": 0.0}

RATE = 16000
CHUNK = 1024

@st.cache_resource
def start_isolated_audio_thread():
    """Dynamically scans your Mac's hardware to find and bind to the physical microphone."""
    def audio_loop():
        p = pyaudio.PyAudio()
        target_index = None
        
        # --- THE SMART HARDWARE SCANNER ---
        try:
            device_count = p.get_device_count()
            for i in range(device_count):
                dev_info = p.get_device_info_by_index(i)
                dev_name = dev_info.get("name", "").lower()
                
                # Dynamic Check: Look for real built-in microphone hardware strings
                if dev_info.get("maxInputChannels", 0) > 0 and ("built-in" in dev_name or "microphone" in dev_name):
                    target_index = i
                    break
            
            # Fallback to system default if string matches fail
            if target_index is None:
                target_index = p.get_default_input_device_info().get("index", 0)
        except Exception:
            target_index = 0

        try:
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=RATE,
                input=True,
                input_device_index=target_index,  # Locks onto the physical channel!
                frames_per_buffer=CHUNK
            )
        except Exception:
            return

        while True:
            if mode == "Live Hardware Stream (Microphone)":
                try:
                    raw_data = stream.read(CHUNK, exception_on_overflow=False)
                    audio_data = np.frombuffer(raw_data, dtype=np.float32)
                    
                    if len(audio_data) > 0:
                        rms_volume = np.sqrt(np.mean(audio_data**2))
                        vol_z = max(-4.0, min(4.0, (rms_volume * 12) - 1.0))
                        
                        zero_crosses = np.nonzero(np.diff(audio_data > 0))[0]
                        pitch_z = (len(zero_crosses) / CHUNK * 4) - 2.0 if rms_volume > 0.01 else 0.0
                        
                        st.session_state.live_metrics["pitch_z"] = pitch_z
                        st.session_state.live_metrics["vol_z"] = vol_z
                except Exception:
                    pass
            time.sleep(0.01)

    t = threading.Thread(target=audio_loop, daemon=True)
    t.start()

start_isolated_audio_thread()

# --- SIMULATION SIGNAL GENERATION ---
def generate_simulation_frames():
    """Generates synthetic math vectors if local hardware is busy or unavailable."""
    t_val = time.time()
    st.session_state.live_metrics["pitch_z"] = np.sin(t_val * 3) * 1.5 + np.cos(t_val * 7) * 0.5
    st.session_state.live_metrics["vol_z"] = abs(np.sin(t_val * 2)) * 2.0 - 1.0 + random.uniform(-0.2, 0.2)

# --- THE STABLE VISUAL RENDERING LOOP ---
@st.fragment(run_every=0.05)
def render_graphics_panel():
    current_time = datetime.now().strftime("%H:%M:%S.%f")[:-4]
    
    if mode == "Synthetic Telemetry Simulation":
        generate_simulation_frames()
        
    pitch_z = st.session_state.live_metrics["pitch_z"]
    vol_z = st.session_state.live_metrics["vol_z"]

    new_point = pd.DataFrame([{"Timestamp": current_time, "Pitch Z": pitch_z, "Volume Z": vol_z}])
    st.session_state.history = pd.concat([st.session_state.history, new_point], ignore_index=True)
    
    if len(st.session_state.history) > 30:
        st.session_state.history = st.session_state.history.iloc[1:]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎵 Voice Pitch Modulation (Z-Score)")
        st.metric(label="Live Pitch Deviation", value=f"{pitch_z:+.2f} σ")
        chart_p = alt.Chart(st.session_state.history).mark_line(color="#1f77b4", strokeWidth=3).encode(
            x=alt.X("Timestamp:N", axis=alt.Axis(title="Timeline Stream")),
            y=alt.Y("Pitch Z:Q", scale=alt.Scale(domain=[-4, 4]))
        ).properties(height=350)
        st.altair_chart(chart_p, use_container_width=True)

    with col2:
        st.subheader("🔊 Acoustic Volume Intensity (Z-Score)")
        st.metric(label="Live Amplitude Energy", value=f"{vol_z:+.2f} σ")
        chart_v = alt.Chart(st.session_state.history).mark_line(color="#ff7f0e", strokeWidth=3).encode(
            x=alt.X("Timestamp:N", axis=alt.Axis(title="Timeline Stream")),
            y=alt.Y("Volume Z:Q", scale=alt.Scale(domain=[-4, 4]))
        ).properties(height=350)
        st.altair_chart(chart_v, use_container_width=True)

print("Starting render engine...")
render_graphics_panel()