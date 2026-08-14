import json
import struct
from pathlib import Path

MODEL_WEIGHTS_DIR = Path("00_raw_data/model_weights")

def inspect_safetensors_header(filepath: Path):
    """Reads the JSON header from a .safetensors file without loading heavy weights into RAM."""
    try:
        with open(filepath, "rb") as f:
            header_size_bytes = f.read(8)
            if len(header_size_bytes) < 8:
                return None
            header_size = struct.unpack("<Q", header_size_bytes)[0]
            header_json_bytes = f.read(header_size)
            header = json.loads(header_json_bytes.decode("utf-8"))
            return header
    except Exception:
        return None

def run_model_pipeline():
    """Inspects available model weight assets."""
    print("\n--- Starting Model Training / Inference Pipeline ---")
    
    weights = list(MODEL_WEIGHTS_DIR.glob("*.safetensors")) + \
              list(MODEL_WEIGHTS_DIR.glob("*.pt")) + \
              list(MODEL_WEIGHTS_DIR.glob("*.bin"))

    if not weights:
        print(f"[MODEL] No weight files found in {MODEL_WEIGHTS_DIR}.")
        return

    print(f"[MODEL] Found {len(weights)} weight asset(s):")
    for weight in weights:
        file_size_mb = weight.stat().st_size / (1024 * 1024)
        print(f"  * {weight.name} ({file_size_mb:.2f} MB)")
        
        if weight.suffix == ".safetensors":
            header = inspect_safetensors_header(weight)
            if header:
                tensor_count = len([k for k in header.keys() if k != "__metadata__"])
                print(f"    [+] SafeTensors Header Parsed: {tensor_count} tensor key(s) detected.")
