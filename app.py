from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
import os
# En prod puedes omitir load_dotenv() si inyectas variables por el sistema
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from werkzeug.middleware.proxy_fix import ProxyFix
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Configuración base ---
load_dotenv()  # quítalo en prod si usas variables de entorno del sistema

app = Flask(__name__)
# Confiar en el proxy (Nginx/Cloudflare) para obtener IP y esquema correctos
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# CORS restringido (ajusta tus dominios)
CORS(app, resources={
    r"/*": {"origins": ["https://ecolim.cl", "https://www.ecolim.cl"]}
})

# Base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# --- Modelo ---
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
        app.logger.error(f"Error al crear la base de datos: {e}")

# --- Rutas básicas ---
@app.route('/')
def home():
    return 'Bienvenido a la API de Ecolim'

@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok"}), 200

# Handler 429 (rate limit)
@app.errorhandler(RateLimitExceeded)
def ratelimit_handler(e):
    return jsonify({"error": "Demasiadas solicitudes, intenta más tarde"}), 429

# --- reCAPTCHA ---
def validar_recaptcha(token: str) -> bool:
    secret_key = os.getenv('RECAPTCHA_SECRET_KEY')
    if not secret_key:
        app.logger.warning("RECAPTCHA_SECRET_KEY no está configurada.")
        return False
    try:
        resp = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={'secret': secret_key, 'response': token},
            timeout=10
        ).json()
        # Si usas v3 y definiste action=submit, puedes reforzar con score:
        # return resp.get('success') and resp.get('action') == 'submit' and resp.get('score', 0) >= 0.5
        return bool(resp.get('success'))
    except Exception as e:
        app.logger.error(f"Error validando reCAPTCHA: {e}")
        return False

# --- Telegram (texto plano + reintentos) ---
def enviar_mensaje_telegram(nombre: str, telefono: str, servicio: str, descripcion: str):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return {"error": "Faltan credenciales TELEGRAM"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = (
        "📩 Nuevo cliente (Formulario Ecolim)\n"
        f"• Nombre: {nombre}\n"
        f"• Teléfono: +56{telefono}\n"
        f"• Servicio: {servicio}\n"
        f"• Descripción: {descripcion}"
    )
    payload = {
        "chat_id": chat_id,
        "text": body,
        "disable_web_page_preview": True,
        "disable_notification": False
    }

    try:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(['POST'])
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        resp = session.post(url, json=payload, timeout=10)
        app.logger.info(f"Telegram status={resp.status_code} resp={resp.text}")
        return resp.json()
    except Exception as e:
        app.logger.error(f"Error enviando Telegram: {e}")
        return {"error": str(e)}

# --- Endpoint del formulario ---
@app.route('/submit', methods=['POST'])
@limiter.limit("5 per minute")
def submit():
    recaptcha_token = request.form.get('g-recaptcha-response')
    if not recaptcha_token or not validar_recaptcha(recaptcha_token):
        return jsonify({'error': 'Error de validación de reCAPTCHA'}), 400

    try:
        nombre = (request.form.get('nombre') or '').strip()
        telefono = (request.form.get('telefono') or '').strip()
        correo = (request.form.get('correo') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()
        servicio = (request.form.get('servicio') or '').strip()

        if not nombre or not telefono or not descripcion or not servicio:
            return jsonify({'error': 'Todos los campos obligatorios deben estar llenos'}), 400

        # Guardar en BD
        nuevo_usuario = Usuario(
            nombre=nombre,
            telefono=telefono,
            correo=correo if correo else None,
            descripcion=descripcion,
            servicio=servicio
        )
        db.session.add(nuevo_usuario)
        db.session.commit()

        # Notificación Telegram
        resp_telegram = enviar_mensaje_telegram(nombre, telefono, servicio, descripcion)
        if isinstance(resp_telegram, dict) and not resp_telegram.get("ok", True):
            app.logger.warning(f"Telegram error: {resp_telegram}")
        else:
            app.logger.info("Notificación Telegram enviada.")

        return jsonify({'message': 'Datos enviados exitosamente!'}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al enviar datos: {e}")
        return jsonify({'error': str(e)}), 500

# --- Servidor dev (en prod usa gunicorn) ---
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
