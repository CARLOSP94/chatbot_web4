from flask import Flask, request, jsonify, render_template, session, send_file, redirect, url_for
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF
import openai
import os
import io
import json
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

# Ruta absoluta del archivo users.json
USERS_FILE = r"C:\Users\HP\chatbot_web\users.json"

def cargar_usuarios():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            usuarios = json.load(f)
            print("Usuarios disponibles:", usuarios)  # Depuración
            return usuarios
    except Exception as e:
        print("⚠️ Error al leer users.json:", e)
        return {}

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["username"]
        clave = request.form["password"]
        usuarios = cargar_usuarios()

        if usuario in usuarios and usuarios[usuario] == clave:
            session["usuario"] = usuario
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Usuario o contraseña incorrectos.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/index")
def index():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html")

# Aquí irían las demás rutas que tienes definidas, por ejemplo /chat, /tts, /history, etc.

if __name__ == "__main__":
    app.run(debug=True)
