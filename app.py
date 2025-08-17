from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Cargar variables de entorno desde .env al inicio
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

# ---- reCAPTCHA ----
def validar_recaptcha(token: str) -> bool:
    secret_key = os.getenv('RECAPTCHA_SECRET_KEY')
    if not secret_key:
        print("RECAPTCHA_SECRET_KEY no está configurada.")
        return False
    try:
        resp = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={'secret': secret_key, 'response': token},
            timeout=10
        )
        data = resp.json()
        return bool(data.get('success', False))
    except Exception as e:
        print(f"Error validando reCAPTCHA: {e}")
        return False

# ---- Telegram ----
def escape_markdown_v2(text: str) -> str:
    """
    Escape básico para MarkdownV2 de Telegram (por si activas parse_mode='MarkdownV2').
    Si NO usas Markdown, puedes omitir esto.
    """
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for ch in special_chars:
        text = text.replace(ch, f'\\{ch}')
    return text

def enviar_mensaje_telegram(nombre: str, telefono: str, servicio: str, descripcion: str):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token:
        return {"error": "TELEGRAM_BOT_TOKEN no configurado"}
    if not chat_id:
        return {"error": "TELEGRAM_CHAT_ID no configurado"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Mensaje en texto plano (seguro) — no usar Markdown si no es necesario
    body = (
        "📩 *Nuevo cliente (Formulario Ecolim)*\n"
        f"• *Nombre:* {nombre}\n"
        f"• *Teléfono:* +56{telefono}\n"
        f"• *Servicio:* {servicio}\n"
        f"• *Descripción:* {descripcion}"
    )

    # Si quieres 100% seguridad de formato, descomenta escape y usa MarkdownV2:
    # body = (
    #     "📩 *Nuevo cliente (Formulario Ecolim)*\n"
    #     f"• *Nombre:* {escape_markdown_v2(nombre)}\n"
    #     f"• *Teléfono:* {escape_markdown_v2('+56' + telefono)}\n"
    #     f"• *Servicio:* {escape_markdown_v2(servicio)}\n"
    #     f"• *Descripción:* {escape_markdown_v2(descripcion)}"
    # )

    payload = {
        "chat_id": chat_id,
        "text": body,
        "parse_mode": "Markdown"  # o "MarkdownV2" si aplicas escape
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        # Log simple para debugging
        print(f"Telegram status={resp.status_code} resp={resp.text}")
        return resp.json()
    except Exception as e:
        print(f"Error enviando Telegram: {e}")
        return {"error": str(e)}

# ---- Endpoint formulario ----
@app.route('/submit', methods=['POST'])
@limiter.limit("5 per minute")
def submit():
    recaptcha_token = request.form.get('g-recaptcha-response')
    if not recaptcha_token or not validar_recaptcha(recaptcha_token):
        return jsonify({'error': 'Error de validación de reCAPTCHA'}), 400

    try:
        nombre = request.form.get('nombre', '').strip()
        telefono = request.form.get('telefono', '').strip()
        correo = request.form.get('correo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        servicio = request.form.get('servicio', '').strip()

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

        # Enviar Telegram (reemplaza UltraMsg)
        resp_telegram = enviar_mensaje_telegram(nombre, telefono, servicio, descripcion)
        if isinstance(resp_telegram, dict) and not resp_telegram.get("ok", True):
            # Telegram devolvió un error
            app.logger.warning(f"Telegram error: {resp_telegram}")
        else:
            app.logger.info("Notificación Telegram enviada.")

        return jsonify({'message': 'Datos enviados exitosamente!'}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al enviar datos: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
