import sys
import time
import numpy as np
from frequency import AudioPipelineEngine  # Assuming the refactored engine lives here

def main():
    print("[Initialization] Booting Project Frequency Core App...")
    
    # 1. Initialize the Hardware Audio Pipeline Engine
    # We maintain the 30-element FIFO ring buffer (~1.92s of buffer safety)
    engine = AudioPipelineEngine(max_buffer_len=30, sigma_boundary=4.0)
    
    # Pre-allocate a list to accumulate our 1D NumPy token stream
    token_accumulator = []
    required_batch_size = 3072
    block_sample_size = 1024
    
    # Mock Model Instance Placeholder
    # Replace this with your actual model initialization down the wire
    model = lambda x: print(f"[Model Inference] Successfully processed 1D tensor shape: {x.shape}")

    try:
        # 2. Spin up the out-of-band hardware background daemon thread
        print("[Lifecycle] Launching out-of-band hardware daemon...")
        engine.start_daemon()
        print("[System Status] Pipeline online. Awaiting data stream... (Press Ctrl+C to exit)")
        
        # 3. Main Application Consumption Loop
        while True:
            # Pull the next normalized, ±4σ clamped block from the FIFO ring
            # This call blocks cleanly, utilizing condition variables to eliminate CPU spinning
            clamped_block = engine.process_next_token_payload()
            
            # Guard rail: If the engine returns empty data, the daemon is tearing down
            if clamped_block.size == 0:
                continue
                
            # Flatten the 1024-sample block to ensure a clean 1D array stream
            flattened_block = clamped_block.ravel()
            token_accumulator.append(flattened_block)
            
            # Check if we have accumulated exactly 3 blocks (1024 * 3 = 3072 tokens)
            if len(token_accumulator) * block_sample_size >= required_batch_size:
                # Concatenate the accumulated blocks into a continuous 1D NumPy array stream
                continuous_stream = np.concatenate(token_accumulator)
                
                # Slice precisely to match token batch constraints if array math shifts
                inference_payload = continuous_stream[:required_batch_size]
                
                # Execute Downstream Inference Token Injection
                model(inference_payload)
                
                # Clear accumulator or keep trailing remainder samples if block sizes ever become dynamic
                token_accumulator = []
                
            # Small yield step to keep the main OS thread balanced
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n[User Intercept] Shutdown signal received via keyboard interrupt.")
        
    except Exception as e:
        print(f"\n[Runtime Crash] System error encountered: {e}", file=sys.stderr)
        
    finally:
        # 4. Strict, Graceful Lifecycle Teardown
        # The finally block guarantees this execution path runs even if the app panics or errors.
        print("[Teardown] Gracefully severing hardware connections...")
        engine.stop_daemon()
        print("[System Status] Safe termination complete. Hardware locks released cleanly.")

if __name__ == "__main__":
    main()
