import sys
import time
import threading
import queue
import numpy as np
import sounddevice as sd

# ==========================================
# 🎛️ CORE HARDWARE CONFIGURATION
# ==========================================
FS = 44100          # Sample rate (Hz)
BLOCK_SIZE = 1024   # Block size expected by app.py

def get_clean_pitch(audio_data, fs):
    """Extracts fundamental pitch via Autocorrelation filtered to human speech (60Hz-300Hz)."""
    corr = np.correlate(audio_data, audio_data, mode='full')
    corr = corr[len(corr)//2:]
    d = np.diff(corr)
    start = np.where(d > 0)[0]
    if len(start) == 0: return 150.0  # Default fallback if no pitch detected
    peak = start[0] + np.argmax(corr[start[0]:])
    frequency = fs / peak
    return round(frequency, 2) if 60 <= frequency <= 300 else 150.0

class AudioPipelineEngine:
    def __init__(self, max_buffer_len=30, sigma_boundary=4.0):
        self.max_buffer_len = max_buffer_len
        self.sigma_boundary = sigma_boundary
        
        # Thread-safe FIFO queue to hold our 1024-sample audio blocks
        self.buffer_queue = queue.Queue(maxsize=self.max_buffer_len)
        
        # Thread control flags
        self.is_running = False
        self.daemon_thread = None
        self.stream = None
        
        # Baselines (Set default fallback values; we can calibrate these)
        self.vocal_baseline = 150.0
        self.volume_baseline = 0.02

    def calibrate(self):
        """Builds a dynamic baseline for Volume Energy (RMS)."""
        print("\n" + "="*50)
        print("🎙️ ENGINE PROFILE CALIBRATION")
        print("="*50)
        print("Please speak in your NORMAL, GENUINE voice for 3 seconds...")
        print("Starting in 3... 2... 1...")
        time.sleep(1)
        
        print("\n🔴 LISTENING FOR BASELINE...")
        recording = sd.rec(int(3 * FS), samplerate=FS, channels=1, dtype='float32')
        sd.wait()
        print("🟢 BASELINE CAPTURED.")
        
        audio_stream = recording.flatten()
        self.volume_baseline = np.sqrt(np.mean(audio_stream**2))
        
        # Ensure our baseline isn't mathematically zero to avoid DivisionByZero errors later
        if self.volume_baseline < 0.001:
            self.volume_baseline = 0.001
            
        print(f"📊 Calibrated Volume Baseline RMS: {round(self.volume_baseline, 4)}")
        print("="*50 + "\n")

    def _audio_callback(self, indata, frames, time_info, status):
        """Asynchronous callback that handles continuous incoming mic data."""
        if status:
            print(f"[Hardware Warning] {status}", file=sys.stderr)
            
        # Flatten input block to 1D
        block = indata.flatten()
        
        # Apply mathematical constraint: Clamping volume spikes to our sigma boundary
        local_rms = np.sqrt(np.mean(block**2)) if block.size > 0 else 0
        
        # Calculate dynamic threshold based on our calibrated baseline and sigma parameter
        max_allowed_energy = self.volume_baseline * self.sigma_boundary
        
        if local_rms > max_allowed_energy and local_rms > 0:
            # Scale down the entire block mathematically to suppress the spike
            reduction_factor = max_allowed_energy / local_rms
            block = block * reduction_factor

        # Push the processed, clamped block into the queue
        try:
            self.buffer_queue.put_nowait(block)
        except queue.Full:
            # Drop oldest frame to maintain low-latency, real-time audio consistency
            try:
                self.buffer_queue.get_nowait()
                self.buffer_queue.put_nowait(block)
            except queue.Empty:
                pass

    def start_daemon(self):
        """Launches the non-blocking background recording stream."""
        if self.is_running:
            return
            
        self.calibrate()  # Run a quick calibration before starting the stream
        self.is_running = True
        
        # Initialize and start the sounddevice InputStream
        self.stream = sd.InputStream(
            samplerate=FS,
            channels=1,
            blocksize=BLOCK_SIZE,
            dtype='float32',
            callback=self._audio_callback
        )
        self.stream.start()

    def process_next_token_payload(self):
        """Blocks cleanly until a block is available, then returns it to app.py."""
        if not self.is_running:
            return np.array([])
            
        try:
            # Clean blocking call using internal queue condition variables
            return self.buffer_queue.get(timeout=1.0)
        except queue.Empty:
            return np.array([])

    def stop_daemon(self):
        """Gracefully closes the streams and shuts down background processing."""
        self.is_running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        print("[Engine] Background audio stream terminated cleanly.")
