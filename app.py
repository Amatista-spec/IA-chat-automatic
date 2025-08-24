import json
import os
import time
import requests
from flask import Flask, request
from groq import Groq

app = Flask(__name__)

# --- Configuración Groq (API gratuita) ---
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- Configuración Green API ---
API_TOKEN = os.getenv("GREEN_API_TOKEN")  # ✅ Ahora usa variable de entorno
ID_INSTANCE = os.getenv("GREEN_API_INSTANCE_ID")  # ✅ Ahora usa variable de entorno

if not API_TOKEN or not ID_INSTANCE:
    print("❌ ERROR: Faltan variables de entorno GREEN_API_TOKEN o GREEN_API_INSTANCE_ID")
    
API_URL = f"https://7105.api.greenapi.com/waInstance{ID_INSTANCE}/"

# --- Tu número de WhatsApp (para evitar bucles) ---
MY_NUMBER = f"{ID_INSTANCE}@c.us"  # Ajusta esto si es necesario

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
        
        url = f"{API_URL}sendMessage/{API_TOKEN}"
        data = {
            "chatId": chat_id,
            "message": message
        }
        
        print(f"📤 Enviando mensaje a {chat_id}: {message[:50]}...")
        response = requests.post(url, json=data, timeout=10)
        
        print(f"🔎 Respuesta Green API: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ Mensaje enviado exitosamente: {result}")
                return result
            except json.JSONDecodeError:
                print("⚠️ Respuesta no es JSON válido")
                return {"error": "Invalid JSON response"}
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return {"error": f"HTTP {response.status_code}", "details": response.text}
            
    except requests.exceptions.Timeout:
        print("⚠️ Timeout al enviar mensaje")
        return {"error": "Timeout"}
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")
        return {"error": str(e)}

# --- Función para generar respuesta con IA ---
def generate_response(mensaje):
    try:
        print(f"🤖 Generando respuesta para: {mensaje}")
        
        # Construir contexto con ejemplos del dataset
        system_message = "Responde como si fueras yo, de manera amigable y clara."
        
        if dataset:
            context = "Aquí hay algunos ejemplos de cómo suelo responder:\n\n"
            # Usar hasta 3 ejemplos del dataset
            for i, example in enumerate(dataset[:3]):
                if isinstance(example, dict):
                    if 'pregunta' in example and 'respuesta' in example:
                        context += f"Pregunta: {example['pregunta']}\nRespuesta: {example['respuesta']}\n\n"
                    elif 'mensaje' in example and 'respuesta' in example:
                        context += f"Mensaje: {example['mensaje']}\nRespuesta: {example['respuesta']}\n\n"
            
            system_message = f"{context}Basándote en estos ejemplos, mantén mi estilo y personalidad al responder."
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": mensaje}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        ai_response = response.choices[0].message.content.strip()
        print(f"✅ Respuesta de IA generada: {ai_response}")
        return ai_response
        
    except Exception as e:
        print(f"❌ Error con OpenAI: {e}")
        error_msg = "Lo siento, hubo un error procesando tu mensaje."
        
        # Mensajes de error más específicos
        if "api_key" in str(e).lower():
            print("❌ Error de API Key de OpenAI")
        elif "quota" in str(e).lower():
            print("❌ Cuota de OpenAI excedida")
        elif "timeout" in str(e).lower():
            error_msg = "Disculpa, la respuesta está tardando mucho. Inténtalo de nuevo."
            
        return error_msg

# --- Endpoint principal ---
@app.route("/", methods=["GET"])
def home():
    return {
        "status": "✅ Bot activo en Render con Green API",
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
        
        # Verificar que es un mensaje entrante
        if data.get("typeWebhook") != "incomingMessageReceived":
            print("⚠️ No es un mensaje entrante, ignorando")
            return "", 200
        
        # Extraer datos del mensaje
        sender_data = data.get("senderData", {})
        message_data = data.get("messageData", {})
        
        sender = sender_data.get("sender", "")
        text_data = message_data.get("textMessageData", {})
        text = text_data.get("textMessage", "")
        
        print(f"👤 Remitente: {sender}")
        print(f"💬 Mensaje: {text}")
        
        # Validaciones
        if not sender:
            print("⚠️ No hay remitente, ignorando")
            return "", 200
            
        if not text:
            print("⚠️ No hay texto en el mensaje, ignorando")
            return "", 200
        
        # Evitar responder a mis propios mensajes
        if sender == MY_NUMBER or ID_INSTANCE in sender:
            print("⚠️ Es mi propio mensaje, ignorando")
            return "", 200
            
        # Evitar mensajes muy cortos o comandos
        if len(text.strip()) < 2:
            print("⚠️ Mensaje muy corto, ignorando")
            return "", 200
        
        print(f"✅ Procesando mensaje de {sender}: {text}")
        
        # Generar respuesta con IA
        reply = generate_response(text)
        
        if reply:
            # Pequeña pausa para parecer más natural
            time.sleep(2)
            
            # Enviar mensaje
            result = send_message(sender, reply)
            
            if "error" not in result:
                print(f"✅ Respuesta enviada exitosamente: {reply}")
            else:
                print(f"❌ Error enviando respuesta: {result}")
        else:
            print("❌ No se pudo generar respuesta")
            
    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        import traceback
        traceback.print_exc()
    
    return "", 200

# --- Endpoint de prueba ---
@app.route("/test", methods=["POST"])
def test():
    """Endpoint para probar el bot manualmente"""
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
    print("🚀 Iniciando bot de WhatsApp...")
    print(f"📊 Dataset: {len(dataset)} ejemplos cargados")
    print(f"🔑 Groq API Key: {'✅ Configurada' if os.getenv('GROQ_API_KEY') else '❌ No configurada'}")
    print(f"🔑 Green API Token: {'✅ Configurada' if API_TOKEN else '❌ No configurada'}")
    print(f"🔑 Instance ID: {'✅ Configurada' if ID_INSTANCE else '❌ No configurada'}")
    
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
