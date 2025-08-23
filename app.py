import json
import time
import requests
import openai
from flask import Flask, request

app = Flask(__name__)

# --- Configuración OpenAI ---
openai.api_key = "sk-proj-XXXXX"  # 🔑 usa la variable de entorno en Render

# --- Configuración Green API ---
API_TOKEN = "572653d72da549d7b75e65edcb1eca5927a428feb8d8429897"
ID_INSTANCE = "7105307689"
API_URL = f"https://7105.api.greenapi.com/waInstance{ID_INSTANCE}/"

# --- Dataset opcional ---
DATASET_FILE = "dataset.json"
try:
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)
except:
    dataset = []


# --- Función para enviar mensajes ---
def send_message(chat_id, message):
    if not chat_id.endswith("@c.us"):
        chat_id = f"{chat_id}@c.us"

    url = f"{API_URL}sendMessage/{API_TOKEN}"
    data = {
        "chatId": chat_id,
        "message": message
    }

    print("📤 Enviando mensaje:", data)
    response = requests.post(url, json=data)
    print("🔎 Respuesta Green API:", response.status_code, response.text)

    try:
        return response.json()
    except:
        return {"error": response.text}


# --- Función para IA ---
def generate_response(mensaje):
    if dataset:
        import random
        ejemplo = random.choice(dataset)
        prompt = f"Ejemplo Input: {ejemplo['input']}\nEjemplo Output: {ejemplo['output']}\n\nMensaje: {mensaje}\nRespuesta:"
    else:
        prompt = f"Responde de manera clara y natural a este mensaje:\n{mensaje}"

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


# --- Endpoint principal ---
@app.route("/", methods=["GET"])
def home():
    return "✅ Bot activo en Render con Green API"


# --- Webhook ---
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📩 Webhook recibido:", json.dumps(data, indent=2, ensure_ascii=False))

    # Nuevo formato: messageData
    if data.get("typeWebhook") == "incomingMessageReceived":
        sender = data["senderData"]["sender"]
        text = data["messageData"].get("textMessageData", {}).get("textMessage", "")

        if sender and text:
            print(f"👤 Mensaje de {sender}: {text}")

            # Generar respuesta con IA
            reply = generate_response(text)
            time.sleep(2)

            # Enviar mensaje
            send_message(sender, reply)
            print(f"🤖 Respuesta enviada: {reply}")

    return "", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
