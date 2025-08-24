import json 
import os
import time
import requests
from flask import Flask, request
from groq import Groq

app = Flask(__name__)

# --- Configuración Groq ---
groq_client = None
groq_api_key = os.getenv("GROQ_API_KEY")

if groq_api_key:
    try:
        groq_client = Groq(api_key=groq_api_key)
        print("✅ Cliente Groq inicializado correctamente")
    except Exception as e:
        print(f"❌ Error inicializando Groq: {e}")
else:
    print("⚠️ GROQ_API_KEY no encontrada")

# --- Configuración Green API ---
API_TOKEN = os.getenv("GREEN_API_TOKEN")
ID_INSTANCE = os.getenv("GREEN_API_INSTANCE_ID")

if not API_TOKEN:
    print("❌ ERROR: GREEN_API_TOKEN no encontrada")
    API_TOKEN = "TOKEN_DE_PRUEBA"  # SOLO para test local

if not ID_INSTANCE:
    print("❌ ERROR: GREEN_API_INSTANCE_ID no encontrada")
    ID_INSTANCE = "ID_DE_PRUEBA"  # SOLO para test local

API_URL = f"https://7105.api.greenapi.com/waInstance{ID_INSTANCE}/"

# --- Tu número de WhatsApp (para evitar bucles) ---
MY_NUMBER = f"{ID_INSTANCE}@c.us"

# --- Dataset opcional ---
DATASET_FILE = "dataset.json"
try:
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    print(f"✅ Dataset cargado: {len(dataset)} ejemplos")
except Exception as e:
    print(f"⚠️ No se pudo cargar dataset: {e}")
    dataset = []

# --- Función para enviar mensajes ---
def send_message(chat_id, message):
    try:
        if not chat_id.endswith("@c.us"):
            chat_id = f"{chat_id}@c.us"
        
        url = f"https://7105.api.greenapi.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"
        data = {"chatId": chat_id, "message": message}
        headers = {"Content-Type": "application/json"}

        print(f"📤 Enviando mensaje a {chat_id}: {message[:50]}...")
        response = requests.post(url, json=data, headers=headers, timeout=15)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text[:300]}")
            return {"error": f"HTTP {response.status_code}"}

    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")
        return {"error": str(e)}

# --- Función para generar respuesta con Groq ---
def generate_response(mensaje):
    try:
        print(f"🤖 Generando respuesta para: {mensaje}")

        # Construir contexto con ejemplos
        system_message = "Responde como si fueras yo, de manera amigable y clara."
        if dataset:
            context = "Aquí hay algunos ejemplos de cómo suelo responder:\n\n"
            for i, example in enumerate(dataset[:3]):
                if isinstance(example, dict):
                    if 'pregunta' in example and 'respuesta' in example:
                        context += f"Pregunta: {example['pregunta']}\nRespuesta: {example['respuesta']}\n\n"
                    elif 'mensaje' in example and 'respuesta' in example:
                        context += f"Mensaje: {example['mensaje']}\nRespuesta: {example['respuesta']}\n\n"
            system_message = f"{context}Basándote en estos ejemplos, mantén mi estilo y personalidad al responder."

        if not groq_client:
            return "Lo siento, no puedo responder en este momento."

        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",  # 👈 Puedes cambiar a otro modelo soportado
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": mensaje}
            ],
            temperature=0.7,
            max_tokens=150
        )

        ai_response = response.choices[0].message.content.strip()
        return ai_response

    except Exception as e:
        print(f"❌ Error con Groq: {e}")
        return "Lo siento, hubo un error procesando tu mensaje."

# --- Endpoint principal ---
@app.route("/", methods=["GET"])
def home():
    return {
        "status": "✅ Bot activo en Render con Green API y Groq",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_loaded": len(dataset) > 0,
        "dataset_size": len(dataset)
    }

# --- Webhook ---
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("📩 Webhook recibido:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        if data.get("typeWebhook") != "incomingMessageReceived":
            return "", 200

        sender_data = data.get("senderData", {})
        message_data = data.get("messageData", {})
        sender = sender_data.get("sender", "")
        text_data = message_data.get("textMessageData", {})
        text = text_data.get("textMessage", "")

        if not sender or not text:
            return "", 200

        if sender == MY_NUMBER or ID_INSTANCE in sender:
            return "", 200

        if len(text.strip()) < 2:
            return "", 200

        reply = generate_response(text)
        if reply:
            time.sleep(2)  # Simula respuesta humana
            send_message(sender, reply)

    except Exception as e:
        print(f"❌ Error en webhook: {e}")

    return "", 200

# --- Endpoint de prueba manual ---
@app.route("/test", methods=["POST"])
def test():
    try:
        data = request.json
        mensaje = data.get("mensaje", "Hola, ¿cómo estás?")
        chat_id = data.get("chat_id", "")
        if not chat_id:
            return {"error": "chat_id requerido"}, 400

        respuesta = generate_response(mensaje)
        result = send_message(chat_id, respuesta)

        return {
            "mensaje_original": mensaje,
            "respuesta_ia": respuesta,
            "envio_resultado": result
        }
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    print("🚀 Iniciando bot de WhatsApp con Groq...")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
