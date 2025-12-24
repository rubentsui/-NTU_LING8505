import requests
import os
import sys

def test_translation_api():
    url = "http://localhost:8000/translate"
    print(f"Testing Translation API at {url}...")
    
    # Read input from file if exists, else use default
    input_text = "Hello world"
    if os.path.exists("test_input.txt"):
        try:
             with open("test_input.txt", "r", encoding="utf-8") as f:
                 input_text = f.read()
        except Exception as e:
            print(f"Warning: Could not read test_input.txt: {e}")

    try:
        response = requests.post(url, json={
            "input_text": input_text,
            "full_doc_mode": True,
            "agent_type": "tool",
            "retrieval_method": "bm25",
            # Defaults will be used for other params
        })
        
        if response.status_code == 200:
            print("Success!")
            print(f"Translation: {response.json()['translation']}")
        else:
            print(f"Request failed with {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server at localhost:8000.")
        print("Make sure the server is running (e.g. 'docker-compose up' or 'python server.py').")

if __name__ == "__main__":
    test_translation_api()
