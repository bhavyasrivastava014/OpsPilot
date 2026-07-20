import requests
from app.config.settings import settings

url = (settings.OLLAMA_URL or "http://localhost:11434").rstrip("/")

try:
    resp = requests.post(f"{url}/api/generate", json={"model": settings.OLLAMA_MODEL, "prompt": "Say hello"}, timeout=10)
    resp.raise_for_status()
    print("Ollama response:", resp.text[:1000])
except Exception as e:
    print("Ollama test failed:", e)