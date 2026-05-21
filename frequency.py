import sys
import os
import math
import time
import numpy as np
import sounddevice as sd
import ollama

cached_pitch = 127.00
cached_energy = 0.0450

def run_live_frequency_engine():
    global cached_pitch, cached_energy
    
    print("⚡ PROJECT FREQUENCY | Persistent Hardware Audio Gateway")
    print("Initializing permanent microphone stream to prevent macOS blocking...")
    
    sample_rate = 44100
    channels = 1
    
    conversation_history = [
        {
            'role': 'system', 
            'content': "You are an acoustic alignment processor. You must strictly adjust your context to obey the [SYSTEM OVERRIDE] acoustic data tags provided with user statements."
        }
    ]
    
    # Open ONE persistent, long-lived audio stream that stays open the whole time
    with sd.InputStream(samplerate=sample_rate, channels=channels, dtype='float32') as stream:
        try:
            while True:
                print("\n" + "="*50)
                
                try:
                    duration_input = input("⏳ How many seconds do you need to speak your sentence? (e.g., 5 or 6): ")
                    if duration_input.lower() in ['exit', 'quit']:
                        break
                    secs = float(duration_input)
                except ValueError:
                    print("Please enter a valid number of seconds.")
                    continue
                
                print("\nREADY... Recording starts in 1 second.")
                time.sleep(1)
                print("🔴 [RECORDING LIVE] - SPEAK NOW! 🔴")
                
                # Securely read the raw frames directly from our open, active stream buffer
                num_frames = int(secs * sample_rate)
                audio_data, overflowed = stream.read(num_frames)
                audio_data = audio_data.flatten()
                
                print("⏹️  [RECORDING DONE] - Processing data stream...")
                
                # Calculate RMS Energy
                rms_energy = np.sqrt(np.mean(audio_data**2)) if len(audio_data) > 0 else 0.0
                
                if rms_energy < 0.006:
                    print(f"❄️  [NOISE GATE] Room quiet. Telemetry Locked -> {cached_pitch:.2f}Hz | {cached_energy:.4f} RMS")
                else:
                    # FFT Pitch Detection
                    fft_data = np.abs(np.fft.rfft(audio_data))
                    frequencies = np.fft.rfftfreq(len(audio_data), 1.0 / sample_rate)
                    peak_index = np.argmax(fft_data)
                    dominant_pitch = frequencies[peak_index]
                    
                    if 50.0 <= dominant_pitch <= 1500.0:
                        cached_pitch = dominant_pitch
                        cached_energy = rms_energy
                        print(f"📡 Telemetry Extracted -> Pitch: {cached_pitch:.2f}Hz | Energy: {cached_energy:.4f} RMS")
                    else:
                        print(f"❄️  [OUT OF BOUNDS] Telemetry Locked -> {cached_pitch:.2f}Hz | {cached_energy:.4f} RMS")
                
                user_text = input("\n✍️  Type/Verify what you said: ")
                if user_text.lower() in ['exit', 'quit']:
                    break
                
                # --- DETERMINISTIC ANTI-HALLUCINATION ROUTING LAYER ---
                sarcasm_keywords = ['wow', 'amazing', 'great', 'crazy', 'wonderful', 'cool']
                is_positive_text = any(word in user_text.lower() for word in sarcasm_keywords)
                
                if is_positive_text and cached_energy < 0.050 and (110.0 <= cached_pitch <= 150.0):
                    override_tag = "\n[SYSTEM OVERRIDE: HARDWARE SENSORS DETECT CONTRADICTION. User statement is heavily DEADPAN and SARCASTIC. Do not take literally. Respond with dry wit.]\n"
                else:
                    override_tag = f"\n[ACOUSTIC MATRIX: Pitch={cached_pitch:.2f}Hz, Energy={cached_energy:.4f}RMS]\n"
                    
                sensor_payload = f"{override_tag}[USER TEXT]: \"{user_text}\""
                
                conversation_history.append({'role': 'user', 'content': sensor_payload})
                print("\n🧠 Processing via Deterministic Truth Gateway...")
                
                response = ollama.chat(model='gemma2:2b', messages=conversation_history)
                reply = response['message']['content']
                
                print(f"\n📥 [LOCAL RESPONSE]:\n{reply}")
                conversation_history.append({'role': 'assistant', 'content': reply})
                
        except KeyboardInterrupt:
            print("\n\n⚡ Stream safely disconnected.")

if __name__ == "__main__":
    run_live_frequency_engine()
