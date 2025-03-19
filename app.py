from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
import time

# Función para mantener la app activa en Railway
def keep_alive():
    url = os.getenv('RAILWAY_URL')
    if not url:
        print("RAILWAY_URL no está configurada. Keep-alive deshabilitado.")
        return

    def ping():
        while True:
            try:
                requests.get(url)
                print(f"Ping enviado a {url}")
            except requests.exceptions.RequestException as e:
                print(f"Error en keep-alive: {e}")
            time.sleep(30)

    thread = threading.Thread(target=ping, daemon=True)
    thread.start()

keep_alive()

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100))
    descripcion = db.Column(db.String(200), nullable=False)
    servicio = db.Column(db.String(50), nullable=False)

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Error al crear la base de datos: {e}")

@app.route('/')
def home():
    return 'Bienvenido a la API de Ecolim'

# Validación de reCAPTCHA
def validar_recaptcha(token):
    secret_key = os.getenv('RECAPTCHA_SECRET_KEY')
    response = requests.post(
        'https://www.google.com/recaptcha/api/siteverify',
        data={'secret': secret_key, 'response': token}
    )
    return response.json().get('success', False)

# Envío de mensajes por UltraMsg
def enviar_mensaje_whatsapp(nombre, telefono, servicio, descripcion):
    try:
        url = "https://api.ultramsg.com/instance110288/messages/chat"
        payload = f"token=5l4autxy75b4vy6j&to=%2B56948425081&body=Nuevo contacto:\nNombre: {nombre}\nTeléfono: +56{telefono}\nServicio: {servicio}\nDescripción: {descripcion}"
        payload = payload.encode('utf8').decode('iso-8859-1')

        headers = {'content-type': 'application/x-www-form-urlencoded'}

        response = requests.request("POST", url, data=payload, headers=headers)
        print(f"Respuesta de UltraMsg: {response.text}")

        return response.text
    except Exception as e:
        print(f"Error al enviar mensaje: {e}")
        return {"error": str(e)}

# Endpoint para recibir datos del formulario
@app.route('/submit', methods=['POST'])
@limiter.limit("5 per minute")
def submit():
    recaptcha_token = request.form.get('g-recaptcha-response')
    if not recaptcha_token or not validar_recaptcha(recaptcha_token):
        return jsonify({'error': 'Error de validación de reCAPTCHA'}), 400

    try:
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        correo = request.form.get('correo')
        descripcion = request.form.get('descripcion')
        servicio = request.form.get('servicio')

        if not nombre or not telefono or not descripcion or not servicio:
            return jsonify({'error': 'Todos los campos obligatorios deben estar llenos'}), 400

        nuevo_usuario = Usuario(
            nombre=nombre,
            telefono=telefono,
            correo=correo,
            descripcion=descripcion,
            servicio=servicio
        )
        db.session.add(nuevo_usuario)
        db.session.commit()

        respuesta_ultramsg = enviar_mensaje_whatsapp(nombre, telefono, servicio, descripcion)
        if respuesta_ultramsg:
            print(f"Estado de la respuesta: {respuesta_ultramsg}")
        else:
            print("Error al enviar mensaje de WhatsApp.")

        return jsonify({'message': 'Datos enviados exitosamente!'}), 200
    except Exception as e:
        app.logger.error(f"Error al enviar datos: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
