from huggingface_hub import model_info
try:
    info = model_info("Unbabel/wmt22-cometkiwi-da")
    print(f"Model private: {info.private}")
    print(f"Model gated: {info.gated}")
except Exception as e:
    print(f"Error accessing model info: {e}")
