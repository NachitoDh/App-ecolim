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

# Cargar variables de entorno desde un archivo .env
load_dotenv()

app = Flask(__name__)
CORS(app)  # Permitir CORS para todas las rutas

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configuración de límite de tasa
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Definición del modelo de base de datos
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100))
    descripcion = db.Column(db.String(200), nullable=False)
    servicio = db.Column(db.String(50), nullable=False)

# Crear la tabla en la base de datos
with app.app_context():
    db.create_all()

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
    result = response.json()
    return result.get('success', False)

# Ruta para manejar el envío del formulario
@app.route('/submit', methods=['POST'])
@limiter.limit("5 per minute")  # Limitar la tasa de solicitudes
def submit():
    recaptcha_token = request.form.get('g-recaptcha-response')
    if not recaptcha_token or not validar_recaptcha(recaptcha_token):
        return jsonify({'error': 'Error de validación de reCAPTCHA'}), 400

    try:
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        correo = request.form['correo']
        descripcion = request.form['descripcion']
        servicio = request.form['servicio']

        # Validación adicional de los campos (ejemplo simple)
        if not nombre, not telefono, not descripcion, not servicio:
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

        response_data = {'message': 'Datos enviados exitosamente'}
        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error(f"Error al enviar datos: {e}")
        return jsonify({'error': str(e)}), 500

def keep_alive():
    while True:
        try:
            response = requests.get("http://localhost:5000")
            if response.status_code == 200:
                app.logger.info("Ping exitoso para mantener la aplicación activa")
            else:
                app.logger.error("Error al hacer ping a la aplicación")
        except Exception as e:
            app.logger.error(f"Excepción al hacer ping: {e}")
        time.sleep(240)  # Hacer ping cada 4 minutos

if __name__ == '__main__':
    # Iniciar el hilo para mantener la aplicación activa
    threading.Thread(target=keep_alive).start()
    app.run(debug=False)  # Deshabilitar depuración en producción
