import requests, json

resp = requests.post(
    "http://127.0.0.1:11434/api/generate",
    json={
        "model": "mistral:instruct",
        "prompt": "Say hello from Python",
        "stream": False,
    },
)
print(resp.status_code)
print(resp.text)
