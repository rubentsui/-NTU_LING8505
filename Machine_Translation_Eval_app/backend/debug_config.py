from config import get_models
import json

try:
    models = get_models()
    print(json.dumps(models, indent=2))
except Exception as e:
    print(f"Error: {e}")
