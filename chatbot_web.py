from flask import Flask, request, jsonify, render_template, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
import openai
import os
import io

app = Flask(__name__)
app.secret_key = "superclave"
app.config["SESSION_TYPE"] = "filesystem"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///historial.db"
Session(app)
db = SQLAlchemy(app)

# Configura tu API key de OpenAI desde variables de entorno
openai.api_key = os.getenv("OPENAI_API_KEY")

# Modelo de historial
class Historial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100))
    mensaje = db.Column(db.Text)

with app.app_context():
    db.create_all()

# Función para obtener respuesta del modelo de OpenAI
def obtener_respuesta(pregunta):
    respuesta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un experto en ambiente, sostenibilidad y cumplimiento ambiental en Ecuador."},
            {"role": "user", "content": pregunta},
        ]
    )
    return respuesta.choices[0].message.content.strip()

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

    # Guardar en sesión
    historial = session.get("historial", [])
    historial.append({"user": pregunta, "bot": respuesta})
    session["historial"] = historial

    # Guardar en base de datos
    db.session.add(Historial(usuario="usuario_demo", mensaje=f"Usuario: {pregunta}"))
    db.session.add(Historial(usuario="usuario_demo", mensaje=f"Chatbot: {respuesta}"))
    db.session.commit()

    return jsonify({"response": respuesta})

@app.route("/history")
def history():
    historial = session.get("historial", [])
    return jsonify(historial)

@app.route("/ver_historial")
def ver_historial():
    historial = Historial.query.filter_by(usuario="usuario_demo").all()
    return render_template("historial_completo.html", historial=historial)

@app.route("/descargar_historial/<tipo>")
def descargar_historial(tipo):
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
