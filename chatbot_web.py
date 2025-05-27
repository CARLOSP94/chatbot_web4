from flask import Flask, request, jsonify, render_template, session, send_file
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
import openai
import os
import io
from gtts import gTTS

app = Flask(__name__)
app.secret_key = "superclave"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///historial.db"
Session(app)
db = SQLAlchemy(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

class Historial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100))
    mensaje = db.Column(db.Text)

with app.app_context():
    db.create_all()

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/set_cliente", methods=["POST"])
def set_cliente():
    tipo = request.json.get("tipo", "")
    session["tipo_cliente"] = tipo
    return jsonify({"message": "Tipo de cliente guardado"})

def obtener_respuesta(pregunta):
    tipo = session.get("tipo_cliente", "empresa")
    
    # Personaliza el sistema según tipo de cliente
    if tipo == "empresa":
        perfil = "Responde como si estuvieras asesorando a una empresa que busca cumplir con normativas ambientales."
    elif tipo == "gad":
        perfil = "Responde pensando en un GAD (Gobierno Autónomo Descentralizado) que busca soluciones sostenibles para su territorio."
    elif tipo == "consultor":
        perfil = "Responde como si estuvieras colaborando con un consultor ambiental que necesita soluciones prácticas y técnicas."
    elif tipo == "estudiante":
        perfil = "Responde de forma educativa, clara y sencilla para un estudiante universitario de ambiente."
    else:
        perfil = "Responde como experto en ambiente, sostenibilidad y cumplimiento ambiental en Ecuador."

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": perfil},
            {"role": "user", "content": pregunta},
        ],
    )
    return response.choices[0].message.content.strip()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    pregunta = data.get("message", "")
    if not pregunta:
        return jsonify({"response": "No se recibió ninguna pregunta"}), 400

    respuesta = obtener_respuesta(pregunta)

    historial = session.get("historial", [])
    historial.append({"user": pregunta, "bot": respuesta})
    session["historial"] = historial

    db.session.add(Historial(usuario="usuario_demo", mensaje=f"Usuario: {pregunta}"))
    db.session.add(Historial(usuario="usuario_demo", mensaje=f"Chatbot: {respuesta}"))
    db.session.commit()

    session["ultima_respuesta"] = respuesta
    return jsonify({"response": respuesta})

