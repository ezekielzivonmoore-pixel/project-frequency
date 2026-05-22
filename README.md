# 🚀 Project FREQUENCY: Low-Overhead Acoustic State Validation for Edge LLMs

### Project Concept
Modern edge language models (like Gemma) suffer from severe semantic bias—they rely entirely on the statistical probability of text tokens. When a user delivers a prompt with heavy contradiction (like deadpan sarcasm), text-only decoders take the words literally and hallucinate an incorrect contextual response.

Project FREQUENCY introduces a deterministic, out-of-model verification layer. Instead of routing heavy native audio streams through computationally expensive transformer layers—which drains device battery and wastes token context—this framework handles feature extraction at the hardware buffer level.

### How It Works
1. **Hardware-Isolated Physics Layer:** Implements a long-lived, persistent background input stream using `sounddevice` to completely bypass macOS privacy/blocking cycles.
2. **Zero-Cost Feature Extraction:** Uses programmatic Fast Fourier Transforms (FFT) and Root Mean Square (RMS) algorithms to instantly capture real-world voice pitch (Hz) and volume amplitude.
3. **Deterministic Truth Gateway:** A programmatic Python validation layer compares the literal text tokens against the physical acoustic metrics. If a structural mismatch is detected (e.g., highly enthusiastic text paired with low-amplitude, monotone pitch), the script intercepts the data packet.
4. **Context Injection:** Injects an explicit state constraint payload into a local model (Gemma 2 via Ollama) using only a few words worth of token overhead, successfully shattering the model's text bias and forcing an aligned, grounded response without wasting local VRAM.
## 🗺️ System Architecture Diagram

Below is the blueprint of how Project FREQUENCY processes physical bimodal inputs locally without transformer token overhead:

```mermaid
graph TD
    A[1. Built-in Microphone Array] -->|Raw PCM Audio Buffer| B(2. Python Static DSP Layer)
    B -->|Extracts Pitch via FFT / Energy via RMS| C{3. Bimodal Truth Gateway}
    C -->|Mismatched Tone: Inject SYSTEM OVERRIDE Tag| D[4. Local LLM Runtime: Gemma 2]
    C -->|Normal Tone: Pass Baseline Transcript| D
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#fdd,stroke:#333,stroke-width:2px
    style D fill:#bfb,stroke:#333,stroke-width:2px
