import os
import getpass
from huggingface_hub import login

def text_eval_login():
    token = os.getenv("HF_TOKEN")
    if not token:
        print("HF_TOKEN environment variable not found.")
        print("Please enter your Hugging Face token (it will not be displayed):")
        token = getpass.getpass("Token: ")
    
    try:
        login(token=token.strip())
        print("Login successful")
    except Exception as e:
        print(f"Login failed: {e}")

if __name__ == "__main__":
    text_eval_login()
