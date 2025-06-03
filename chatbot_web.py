from flask import Flask, request, jsonify, render_template, session, send_file, redirect
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
import openai
import os
import io
from gtts import gTTS
import json

app = Flask(__name__)
app.secret_key = "superclave"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///historial.db"
Session(app)
db = SQLAlchemy(app)

# Configurar tu clave de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Modelo para guardar historial en base de datos
class Historial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100))
    mensaje = db.Column(db.Text)

with app.app_context():
    db.create_all()

# Ruta de login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            with open(r"C:\Users\HP\chatbot_web\users.json", "r") as f:
                usuarios = json.load(f)
        except FileNotFoundError:
            return render_template("login.html", error="Archivo de usuarios no encontrado.")
        except json.JSONDecodeError:
            return render_template("login.html", error="Error al leer el archivo de usuarios.")

        user_data = usuarios.get(username)

        if user_data and user_data["password"] == password:
            session["usuario"] = username
            return redirect("/")
        else:
            return render_template("login.html", error="Credenciales inválidas.")

    return render_template("login.html")

# Ruta para cerrar sesión
@app.route("/logout")
def logout():
    session.pop("usuario", None)
    session.pop("tipo_cliente", None)
    session.pop("historial", None)
    return redirect("/login")

@app.route("/set_cliente", methods=["POST"])
def set_cliente():
    if "usuario" not in session:
        return redirect("/login")
    tipo = request.json.get("tipo", "")
    session["tipo_cliente"] = tipo
    return jsonify({"message": "Tipo de cliente guardado"})

# Lógica de respuesta con OpenAI
def obtener_respuesta(pregunta):
    tipo = session.get("tipo_cliente", "empresa")

    if tipo == "empresa":
        perfil = "Responde como si estuvieras asesorando a una empresa que busca cumplir con normativas ambientales en Ecuador."
    elif tipo == "gad":
        perfil = "Responde pensando en un GAD (Gobierno Autónomo Descentralizado) que busca soluciones sostenibles para su territorio."
    elif tipo == "consultor":
        perfil = "Responde como si estuvieras colaborando con un consultor ambiental que necesita soluciones prácticas y técnicas."
    elif tipo == "estudiante":
        perfil = "Responde de forma educativa, clara y sencilla para un estudiante universitario de ambiente."
    else:
        perfil = "Responde como experto en ambiente, sostenibilidad y cumplimiento ambiental en Ecuador."

    perfil += " Incluye emoticones apropiados como 🌱, ♻️, 📄, 📊, ✅, 💬, 🔍, etc."

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": perfil},
            {"role": "user", "content": pregunta},
        ],
    )
    return response.choices[0].message.content.strip()

@app.route("/")
def index():
    if "usuario" not in session:
        return redirect("/login")
    return render_template("chat.html")

@app.route("/chat", methods=["POST"])
def chat():
    if "usuario" not in session:
        return redirect("/login")

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

    session["ultima_respuesta"] = respuesta  # Guardar última respuesta para TTS

    return jsonify({"response": respuesta})

@app.route("/tts", methods=["POST"])
def tts():
    if "usuario" not in session:
        return redirect("/login")

    texto = session.get("ultima_respuesta", "")
    if not texto:
        return "Primero envía una pregunta para generar audio.", 400

    tts = gTTS(text=texto, lang="es")
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)

    return send_file(mp3_fp, mimetype="audio/mpeg", as_attachment=False, download_name="respuesta.mp3")

@app.route("/history")
def history():
    if "usuario" not in session:
        return redirect("/login")
    historial = session.get("historial", [])
    return jsonify(historial)

@app.route("/ver_historial")
def ver_historial():
    if "usuario" not in session:
        return redirect("/login")
    historial = Historial.query.filter_by(usuario=session["usuario"]).all()
    return render_template("historial_completo.html", historial=historial)

@app.route("/descargar_historial/<tipo>")
def descargar_historial(tipo):
    if "usuario" not in session:
        return redirect("/login")

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

        pdf_output = pdf.output(dest='S').encode('latin1')
        buffer = io.BytesIO(pdf_output)
        buffer.seek(0)

        return send_file(buffer, mimetype='application/pdf',
                         as_attachment=True, download_name='historial.pdf')

    return "Tipo no soportado", 400

if __name__ == "__main__":
    app.run(debug=True)


