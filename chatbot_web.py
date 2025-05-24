from flask import Flask, render_template, request, jsonify, session
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import openai
import os
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("ASSISTANT_ID")

app = Flask(__name__)
auth = HTTPBasicAuth()

# Configuración de sesión
app.secret_key = 'clave-secreta-para-sesiones'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Cargar usuarios desde JSON y encriptar contraseñas
with open('users.json', 'r') as f:
    users_plain = json.load(f)

users = {user: generate_password_hash(pw) for user, pw in users_plain.items()}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

@app.route('/')
@auth.login_required
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
@auth.login_required
def chat():
    user_message = request.json['message']

    thread = openai.beta.threads.create()
    openai.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_message)
    run = openai.beta.threads.runs.create(assistant_id=assistant_id, thread_id=thread.id)

    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break

    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    reply = messages.data[0].content[0].text.value

    # Guardar conversación en la sesión del usuario
    if 'history' not in session:
        session['history'] = []
    session['history'].append({'user': user_message, 'bot': reply})
    session.modified = True

    return jsonify({'response': reply})

@app.route('/history', methods=['GET'])
@auth.login_required
def get_history():
    return jsonify(session.get('history', []))

if __name__ == '__main__':
    app.run(debug=True)
    