import json
import time
import requests
import openai
from flask import Flask, request

app = Flask(__name__)

# --- Configuración OpenAI ---
openai.api_key = "TU_API_KEY_OPENAI"

# --- Configuración Green API ---
API_TOKEN = "TU_API_TOKEN"
ID_INSTANCE = "TU_ID_INSTANCE"
API_URL = f"https://7105.api.greenapi.com/waInstance{ID_INSTANCE}/"

def send_message(phone_number, message):
    url = f"{API_URL}sendMessage/{API_TOKEN}"
    data = {
        "chatId": f"{phone_number}@c.us",
        "message": message
    }
    response = requests.post(url, json=data)
    print("📤 Respuesta de Green API:", response.text)
    return response.json()

def generate_response(mensaje):
    prompt = f"Responde de manera clara y amigable:\n{mensaje}"
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=150,
        temperature=0.7
    )
    return response.choices[0].text.strip()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📩 Webhook recibido:", json.dumps(data, indent=2, ensure_ascii=False))

    if data and "body" in data:
        msg_body = data["body"]

        if msg_body.get("typeWebhook") == "incomingMessageReceived":
            phone_number = msg_body["senderData"]["sender"]
            text = msg_body["messageData"]["textMessageData"]["textMessage"]

            print(f"👉 Mensaje de {phone_number}: {text}")

            reply = generate_response(text)
            time.sleep(2)
            send_message(phone_number, reply)
            print(f"🤖 Respuesta enviada: {reply}")

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
