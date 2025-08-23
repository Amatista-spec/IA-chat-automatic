import re
import json

MY_NAME = "🏴"  # <-- pon exactamente como aparece en el chat

messages = []

with open("chat.txt", "r", encoding="utf-8") as f:
    for raw in f:
        line = raw.rstrip("\n")
        # intento robusto: separar timestamp del resto por la primera " - "
        if " - " in line:
            left, right = line.split(" - ", 1)
            # si la izquierda parece una fecha (simple comprobación), tratamos como nuevo mensaje
            if re.match(r'^\s*\d{1,2}/\d{1,2}/\d{2,4},', left):
                if ": " in right:
                    sender, content = right.split(": ", 1)
                else:
                    # mensajes de sistema sin "sender: content"
                    sender, content = right, ""
                messages.append({"sender": sender.strip(), "content": content.strip()})
                continue
        # si no es inicio, es continuación: añadir al último mensaje
        if messages:
            messages[-1]["content"] += ("\n" + line).strip()

# debug básico: cuántos mensajes y remitentes únicos
print(f"parsed messages: {len(messages)}")
senders = sorted({m["sender"] for m in messages})
print(f"unique senders (sample): {senders[:20]}")

# Construir dataset: cuando quien responde sea MY_NAME tomamos el mensaje anterior como "input"
dataset = []
for i in range(1, len(messages)):
    prev = messages[i - 1]
    cur = messages[i]
    if cur["sender"] == MY_NAME and prev["content"].strip() and prev["sender"] != MY_NAME:
        dataset.append({"input": prev["content"].strip(), "output": cur["content"].strip()})

# Si queda vacío, mostrar primeros mensajes para depurar
if not dataset:
    print("⚠️ dataset vacío — primeros 10 mensajes parseados:")
    for m in messages[:10]:
        print(f'{m["sender"]!r}: {m["content"]!r}')

# Guardar dataset
with open("dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print(f"✅ Dataset generado, {len(dataset)} ejemplos")
