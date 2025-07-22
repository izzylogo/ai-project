import requests
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def ask_ai_with_history(chat_history):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost",
        "X-Title": "AIEmailAssistant"
    }
    
    data = {
        "model": "qwen/qwen3-235b-a22b-07-25:free",
        "messages": chat_history
    }

    response = requests.post(url, json=data, headers=headers)

    # Print the full response to inspect it
    print("AI Response:", response.json())  # This will show the full response for debugging

    # Handle error responses gracefully
    response_json = response.json()
    if 'error' in response_json:
        error_message = response_json['error'].get('message', 'Unknown error')
        return f"⚠️ Error: {error_message}"

    # Sanitize the response's "raw" field if present
    if 'metadata' in response_json.get('error', {}):
        raw_data = response_json['error']['metadata'].get('raw', '')
        # Replace single quotes with double quotes for valid JSON
        if raw_data:
            raw_data = raw_data.replace("'", '"')
            try:
                raw_json = json.loads(raw_data)
                return raw_json  # You can now safely work with the raw data
            except json.JSONDecodeError:
                return f"⚠️ Failed to parse error metadata: {raw_data}"

    # Return the standard AI response if no errors
    try:
        return response_json["choices"][0]["message"]["content"]
    except KeyError:
        return f"⚠️ Unexpected response format: {response_json}"
