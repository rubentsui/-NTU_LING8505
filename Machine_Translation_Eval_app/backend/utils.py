import torch

def get_hardware_info():
    if torch.cuda.is_available():
        return {"device": "cuda", "name": torch.cuda.get_device_name(0)}
    elif torch.backends.mps.is_available():
        return {"device": "mps", "name": "Apple Silicon GPU"}
    else:
        return {"device": "cpu", "name": "CPU"}

def estimate_time(rows: int, num_models: int, hardware_info: dict):
    # Heuristic: 
    # CPU: ~1 row per second per model (very rough)
    # GPU: ~10-50 rows per second per model
    
    device = hardware_info.get("device")
    
    if device == "cpu":
        rows_per_sec = 1.0
    else:
        rows_per_sec = 20.0 # Conservative GPU estimate
        
    total_seconds = (rows * num_models) / rows_per_sec
    return total_seconds
