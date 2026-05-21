# 🚀 Project FREQUENCY: Low-Overhead Acoustic State Validation for Edge LLMs

### Project Concept
Modern edge language models (like Gemma) suffer from severe semantic bias—they rely entirely on the statistical probability of text tokens. When a user delivers a prompt with heavy contradiction (like deadpan sarcasm), text-only decoders take the words literally and hallucinate an incorrect contextual response.

Project FREQUENCY introduces a deterministic, out-of-model verification layer. Instead of routing heavy native audio streams through computationally expensive transformer layers—which drains device battery and wastes token context—this framework handles feature extraction at the hardware buffer level.

### How It Works
1. **Hardware-Isolated Physics Layer:** Implements a long-lived, persistent background input stream using `sounddevice` to completely bypass macOS privacy/blocking cycles.
2. **Zero-Cost Feature Extraction:** Uses programmatic Fast Fourier Transforms (FFT) and Root Mean Square (RMS) algorithms to instantly capture real-world voice pitch (Hz) and volume amplitude.
3. **Deterministic Truth Gateway:** A programmatic Python validation layer compares the literal text tokens against the physical acoustic metrics. If a structural mismatch is detected (e.g., highly enthusiastic text paired with low-amplitude, monotone pitch), the script intercepts the data packet.
4. **Context Injection:** Injects an explicit state constraint payload into a local model (Gemma 2 via Ollama) using only a few words worth of token overhead, successfully shattering the model's text bias and forcing an aligned, grounded response without wasting local VRAM.
