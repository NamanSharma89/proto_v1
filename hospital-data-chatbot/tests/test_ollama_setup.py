# scripts/test_ollama.py
import requests
import json
import argparse

def test_ollama(model, host="http://localhost:11434"):
    """Test if Ollama is working with the specified model."""
    print(f"Testing Ollama with model {model} at {host}...")
    
    try:
        # Check if Ollama is running
        response = requests.get(f"{host}/api/health")
        if response.status_code != 200:
            print(f"Error: Ollama service not responding properly: {response.status_code}")
            return False
        
        print("✅ Ollama service is running")
        
        # Check if the model is loaded
        payload = {
            "model": model,
            "prompt": "Generate a simple SQL query to count all patients.",
            "stream": False
        }
        
        response = requests.post(
            f"{host}/api/generate",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"Error: Failed to generate response with model {model}: {response.status_code}")
            return False
        
        result = response.json()
        print("✅ Model is working correctly")
        print("\nSample output:")
        print(result.get("response", "No response"))
        return True
        
    except Exception as e:
        print(f"Error connecting to Ollama: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Ollama setup")
    parser.add_argument("--model", default="qwen2.5-coder:14b", help="Model to test")
    parser.add_argument("--host", default="http://localhost:11434", help="Ollama host")
    
    args = parser.parse_args()
    success = test_ollama(args.model, args.host)
    exit(0 if success else 1)