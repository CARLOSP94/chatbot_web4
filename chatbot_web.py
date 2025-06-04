from flask import Flask, request, jsonify, render_template, session, send_file, redirect, url_for
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
import openai
import os
import io
import json

app = Flask(__name__)
app.secret_key = "superclave"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///historial.db"
Session(app)
db = SQLAlchemy(app)

# Configura tu API key de OpenAI desde variables de entorno
openai.api_key = os.getenv("OPENAI_API_KEY")

# Ruta absoluta del archivo users.json
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

# Modelo de historial
class Historial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100))
    mensaje = db.Column(db.Text)

with app.app_context():
    db.create_all()

# Función para obtener respuesta del modelo

def obtener_respuesta(pregunta):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": (
                "Eres un experto en ambiente, sostenibilidad y cumplimiento ambiental en Ecuador. "
                "Responde de forma clara, útil y amigable, incluyendo emoticones apropiados relacionados al contenido "
                "(por ejemplo: 🌱, ♻️, 📄, 📈, ✅, 💬, 🔍, etc.)."
            )},
            {"role": "user", "content": pregunta},
        ],
    )
    return response.choices[0].message.content.strip()

# Cargar usuarios desde JSON
def cargar_usuarios():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("⚠️ Error cargando usuarios:", e)
        return {}

# LOGIN
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["username"].strip()
        clave = request.form["password"].strip()
        usuarios = cargar_usuarios()

        if usuario in usuarios and usuarios[usuario] == clave:
            session["usuario"] = usuario
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Usuario o contraseña incorrectos.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# DASHBOARD CON MODULOS
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", usuario=session["usuario"])

# MODULO: CHATBOT
@app.route("/chatbot")
def chatbot():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html", usuario=session["usuario"])

@app.route("/chat", methods=["POST"])
def chat():
    if "usuario" not in session:
        return jsonify({"response": "No autorizado"}), 401

    data = request.get_json()
    pregunta = data.get("message", "")
    if not pregunta:
        return jsonify({"response": "No se recibió ninguna pregunta"}), 400

    respuesta = obtener_respuesta(pregunta)

    historial = session.get("historial", [])
    historial.append({"user": pregunta, "bot": respuesta})
    session["historial"] = historial

    db.session.add(Historial(usuario=session["usuario"], mensaje=f"Usuario: {pregunta}"))
    db.session.add(Historial(usuario=session["usuario"], mensaje=f"Chatbot: {respuesta}"))
    db.session.commit()

    return jsonify({"response": respuesta})

# VER HISTORIAL
@app.route("/ver_historial")
def ver_historial():
    if "usuario" not in session:
        return redirect(url_for("login"))

    historial = Historial.query.filter_by(usuario=session["usuario"]).all()
    return render_template("historial_completo.html", historial=historial)

# DESCARGAR HISTORIAL
@app.route("/descargar_historial/<tipo>")
def descargar_historial(tipo):
    if "usuario" not in session:
        return redirect(url_for("login"))

    historial = session.get("historial", [])
    contenido = "\n".join([f"Usuario: {h['user']}\nChatbot: {h['bot']}" for h in historial])

    if tipo == 'txt':
        return send_file(io.BytesIO(contenido.encode()), mimetype='text/plain',
                         as_attachment=True, download_name='historial.txt')

    elif tipo == 'pdf':
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for linea in contenido.split("\n"):
            pdf.multi_cell(0, 10, linea)
        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf',
                         as_attachment=True, download_name='historial.pdf')

    return "Tipo no soportado", 400

if __name__ == "__main__":
    app.run(debug=True)

