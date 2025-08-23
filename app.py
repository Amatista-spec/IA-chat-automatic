import json
import time
import requests
import openai
from flask import Flask, request

app = Flask(__name__)

# --- Configuración OpenAI ---
openai.api_key = "sk-proj-XXXXX"  # 🔑 pon tu API Key de OpenAI en Render (env vars)

# --- Configuración Green API ---
API_TOKEN = "572653d72da549d7b75e65edcb1eca5927a428feb8d8429897"
ID_INSTANCE = "7105307689"
API_URL = f"https://7105.api.greenapi.com/waInstance{ID_INSTANCE}/"

# --- Cargar dataset de chats (opcional) ---
DATASET_FILE = "dataset.json"
try:
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)
except:
    dataset = []

# --- Función para enviar mensajes a WhatsApp ---
def send_message(phone_number, message):
    chat_id = phone_number if "@c.us" in phone_number else f"{phone_number}@c.us"

    url = f"{API_URL}sendMessage/{API_TOKEN}"
    data = {
        "chatId": chat_id,
        "message": message
    }

    print("📤 Intentando enviar:", data, "→", url)
    response = requests.post(url, json=data)
    print("🔎 Respuesta de Green API:", response.status_code, response.text)

    try:
        return response.json()
    except:
        return {"error": response.text}

# --- Función para generar respuesta con OpenAI ---
def generate_response(mensaje):
    if dataset:
        import random
        ejemplo = random.choice(dataset)
        prompt = f"Responde este mensaje como si fueras yo:\nEjemplo Input: {ejemplo['input']}\nEjemplo Output: {ejemplo['output']}\nMensaje a responder: {mensaje}"
    else:
        prompt = f"Responde este mensaje de manera clara y amigable:\n{mensaje}"

    try:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print("⚠️ Error con OpenAI:", str(e))
        return "Lo siento, hubo un error procesando tu mensaje."

# --- Endpoint principal para pruebas ---
@app.route("/", methods=["GET"])
def home():
    return "✅ Servidor Flask con Green API y OpenAI funcionando"

# --- Webhook de WhatsApp ---
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📩 Webhook recibido:", json.dumps(data, indent=2, ensure_ascii=False))

    if "messages" in data:
        for message in data["messages"]:
            phone_number = message.get("sender")
            text = message.get("text", {}).get("body", "")

            if not text or not phone_number:
                continue

            print(f"👤 Mensaje de {phone_number}: {text}")

            # Generar respuesta con IA
            reply = generate_response(text)
            time.sleep(2)

            # Enviar respuesta
            send_message(phone_number, reply)
            print(f"🤖 Respuesta enviada a {phone_number}: {reply}")

    return "", 200

# --- Ejecutar servidor Flask ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
