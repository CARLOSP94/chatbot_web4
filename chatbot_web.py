from flask import Flask, render_template, request, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import openai
import os
from dotenv import load_dotenv

# Cargar claves
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("ASSISTANT_ID")

app = Flask(__name__)
auth = HTTPBasicAuth()

# Usuarios válidos (puedes mover esto a un archivo .env si prefieres)
users = {
    "carlos": generate_password_hash("tu_contraseña_segura"),
    "admin": generate_password_hash("admin123")  # puedes eliminar o cambiar esto
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

# Página principal protegida
@app.route('/')
@auth.login_required
def index():
    return render_template('index.html')

# Ruta de chat protegida
@app.route('/chat', methods=['POST'])
@auth.login_required
def chat():
    user_message = request.json['message']

    thread = openai.beta.threads.create()
    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )

    run = openai.beta.threads.runs.create(
        assistant_id=assistant_id,
        thread_id=thread.id
    )

    while True:
        run_status = openai.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if run_status.status == "completed":
            break

    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    reply = messages.data[0].content[0].text.value
    return jsonify({'response': reply})

if __name__ == '__main__':
    app.run(debug=True)
