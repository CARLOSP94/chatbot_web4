from flask import Flask, render_template, request, jsonify
import openai
import os
from dotenv import load_dotenv

# Cargar claves del archivo .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("ASSISTANT_ID")

# Iniciar la app Flask
app = Flask(__name__)

# Página principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para procesar mensajes del usuario
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']

    # Crear un hilo de conversación
    thread = openai.beta.threads.create()

    # Enviar mensaje del usuario
    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )

    # Ejecutar el Assistant
    run = openai.beta.threads.runs.create(
        assistant_id=assistant_id,
        thread_id=thread.id
    )

    # Esperar a que el Assistant responda
    while True:
        run_status = openai.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if run_status.status == "completed":
            break

    # Obtener respuesta
    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    reply = messages.data[0].content[0].text.value
    return jsonify({'response': reply})

# Ejecutar el servidor local
if __name__ == '__main__':
    app.run(debug=True)
