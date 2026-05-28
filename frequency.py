import threading
import time
from collections import deque
import numpy as np

class WelfordVarianceTracker:
    """Implements numerically stable online variance calculation.
    Prevents catastrophic cancellation under high-volume streaming.
    """
    def __init__(self):
        self.count = 0
        self.mean = 0.0
        self.M2 = 0.0  # Sum of squares of differences from the current mean

    def update(self, block: np.ndarray):
        block_size = block.size
        if block_size == 0:
            return

        block_mean = np.mean(block)
        block_var = np.var(block)

        # Calculate new aggregates using Chan's parallel batch adaptation
        new_count = self.count + block_size
        delta = block_mean - self.mean

        self.mean += delta * block_size / new_count
        self.M2 += (block_var * block_size + (delta**2) * self.count * block_size / new_count)
        self.count = new_count

    @property
    def variance(self) -> float:
        return self.M2 / self.count if self.count > 1 else 1e-8

    @property
    def std_dev(self) -> float:
        return np.sqrt(max(self.variance, 1e-8))

class AudioPipelineEngine:
    def __init__(self, max_buffer_len: int = 30, sigma_boundary: float = 4.0):
        self.max_len = max_buffer_len
        self.sigma_boundary = sigma_boundary
        self.buffer = deque(maxlen=max_buffer_len)
        self.buffer_lock = threading.Lock()
        self.data_available_cv = threading.Condition(self.buffer_lock)
        self.tracker = WelfordVarianceTracker()
        self.shutdown_event = threading.Event()
        self.daemon_thread = None

    def start_daemon(self):
        self.shutdown_event.clear()
        self.daemon_thread = threading.Thread(
            target=self._daemon_loop, name="OOB_Acoustic_Daemon", daemon=True
        )
        self.daemon_thread.start()

    def stop_daemon(self):
        print("[Lifecycle] Initiating daemon teardown sequence...")
        self.shutdown_event.set()
        with self.buffer_lock:
            self.data_available_cv.notify_all()
        if self.daemon_thread and self.daemon_thread.is_alive():
            self.daemon_thread.join(timeout=3.0)
            print("[Lifecycle] Daemon thread terminated cleanly.")

    def _daemon_loop(self):
        try:
            while not self.shutdown_event.is_set():
                time.sleep(0.064)  # ~64ms ticks for 1024 chunks at 16kHz
                raw_voltage_block = np.random.normal(0, 1.0, 1024)
                self._ingest_block(raw_voltage_block)
        except Exception as e:
            print(f"[Daemon Panic] Unhandled exception: {e}")

    def _ingest_block(self, block: np.ndarray):
        with self.buffer_lock:
            self.buffer.append(block)
            self.data_available_cv.notify()

    def process_next_token_payload(self) -> np.ndarray:
        with self.data_available_cv:
            while len(self.buffer) == 0 and not self.shutdown_event.is_set():
                if not self.data_available_cv.wait(timeout=1.0):
                    if self.shutdown_event.is_set():
                        return np.array([])
            if self.shutdown_event.is_set() and len(self.buffer) == 0:
                return np.array([])
            block = self.buffer.popleft()

        # Update running variance metrics OUTSIDE of lock block to maximize concurrency
        self.tracker.update(block)
        
        normalized_block = (block - self.tracker.mean) / self.tracker.std_dev
        return np.clip(normalized_block, -self.sigma_boundary, self.sigma_boundary)
