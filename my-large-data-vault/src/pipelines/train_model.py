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


def _summarize_header(header: dict) -> dict:
    """Turns a raw safetensors header into dtype/shape summary stats."""
    dtype_counts = {}
    tensor_keys = [k for k in header.keys() if k != "__metadata__"]
    for key in tensor_keys:
        entry = header.get(key, {})
        dtype = entry.get("dtype", "unknown")
        dtype_counts[dtype] = dtype_counts.get(dtype, 0) + 1
    return {
        "tensor_count": len(tensor_keys),
        "dtype_breakdown": dtype_counts,
        "metadata": header.get("__metadata__", {}),
    }


def list_model_weights() -> list:
    """Returns structured metadata for every weight asset in the vault, for the API/UI."""
    weights = list(MODEL_WEIGHTS_DIR.glob("*.safetensors")) + \
        list(MODEL_WEIGHTS_DIR.glob("*.pt")) + \
        list(MODEL_WEIGHTS_DIR.glob("*.bin"))

    results = []
    for weight in weights:
        try:
            size_bytes = weight.stat().st_size
        except OSError:
            size_bytes = 0
        entry = {
            "name": weight.name,
            "extension": weight.suffix,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "inspectable": weight.suffix == ".safetensors",
            "tensor_count": None,
            "dtype_breakdown": None,
        }
        if weight.suffix == ".safetensors":
            header = inspect_safetensors_header(weight)
            if header:
                summary = _summarize_header(header)
                entry["tensor_count"] = summary["tensor_count"]
                entry["dtype_breakdown"] = summary["dtype_breakdown"]
        results.append(entry)
    return results


def get_weight_detail(filename: str) -> dict:
    """Returns full per-tensor detail (name, dtype, shape) for a single safetensors file."""
    filepath = MODEL_WEIGHTS_DIR / filename
    if not filepath.exists() or filepath.suffix != ".safetensors":
        return {"error": "File not found or not a .safetensors file."}

    header = inspect_safetensors_header(filepath)
    if header is None:
        return {"error": "Could not parse safetensors header."}

    summary = _summarize_header(header)
    tensors = []
    for key, entry in header.items():
        if key == "__metadata__":
            continue
        tensors.append({
            "name": key,
            "dtype": entry.get("dtype"),
            "shape": entry.get("shape"),
        })

    return {
        "name": filepath.name,
        "size_mb": round(filepath.stat().st_size / (1024 * 1024), 2),
        "tensor_count": summary["tensor_count"],
        "dtype_breakdown": summary["dtype_breakdown"],
        "metadata": summary["metadata"],
        "tensors": tensors,
    }


def run_model_pipeline():
    """CLI entry point: inspects available model weight assets and prints a report."""
    print("\n--- Starting Model Training / Inference Pipeline ---")

    weights = list_model_weights()
    if not weights:
        print(f"[MODEL] No weight files found in {MODEL_WEIGHTS_DIR}.")
        return

    print(f"[MODEL] Found {len(weights)} weight asset(s):")
    for w in weights:
        print(f"  * {w['name']} ({w['size_mb']:.2f} MB)")
        if w["inspectable"] and w["tensor_count"] is not None:
            print(f"    [+] SafeTensors Header Parsed: {w['tensor_count']} tensor key(s) detected.")
