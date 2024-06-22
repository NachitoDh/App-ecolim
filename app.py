from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

app = Flask(app)
CORS(app)

# Configuración de la base de datos MySQL usando variables de entorno
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
database = os.getenv('DB_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://{username}:{password}@{host}/{database}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de la base de datos
class FormData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), nullable=True)
    telefono = db.Column(db.String(20), nullable=False)
    servicio = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<FormData {self.nombre}>'

# Ruta para recibir los datos del formulario
@app.route('/', methods=['POST'])
def receive_data():
    try:
        data = request.form
        nuevo_dato = FormData(
            nombre=data['nombre'],
            correo=data.get('correo'),  # Correo puede ser opcional
            telefono=data['telefono'],
            servicio=data['servicio'],
            descripcion=data['descripcion']
        )
        db.session.add(nuevo_dato)
        db.session.commit()
        return jsonify({'message': 'Datos enviados con éxito'}), 200
    except Exception as e:
        return jsonify({'message': 'Error al enviar datos', 'error': str(e)}), 500

if __name__ == '__main__':
    # Crear las tablas de la base de datos si no existen
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)
