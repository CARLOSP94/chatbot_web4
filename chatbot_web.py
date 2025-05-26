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

# Modelo de historial
class Historial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100))
    mensaje = db.Column(db.Text)

with app.app_context():
    db.create_all()

def obtener_respuesta(pregunta):
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": (
                "Eres un experto en ambiente, sostenibilidad y cumplimiento ambiental en Ecuador. "
                "Responde de forma clara, útil y amigable, incluyendo emoticones apropiados relacionados al contenido "
                "(por ejemplo: 🌱, ♻️, 📄, 📊, ✅, 💬, 🔍, etc.)."
            )},
            {"role": "user", "content": pregunta},
        ],
    )
    return response.choices[0].message.content.strip()

@app.route("/")
def index():
    return render_template("chat.html")

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

    session["ultima_respuesta"] = respuesta  # Guardar última respuesta para TTS

    return jsonify({"response": respuesta})

@app.route("/tts", methods=["POST"])
def tts():
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
    historial = session.get("historial", [])
    return jsonify(historial)

@app.route("/ver_historial")
def ver_historial():
    historial = Historial.query.filter_by(usuario="usuario_demo").all()
    return render_template("historial_completo.html", historial=historial)

@app.route("/historial_completo/<tipo>")
def historial_completo(tipo):
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
