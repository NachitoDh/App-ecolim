from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Permitir CORS para todas las rutas

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://yoelchupa_admin:Nachitodeache11@mysql-yoelchupa.alwaysdata.net/yoelchupa_ecolimdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

# Ruta para manejar el envío del formulario
@app.route('/submit', methods=['POST'])
def submit():
    try:
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        correo = request.form['correo']
        descripcion = request.form['descripcion']
        servicio = request.form['servicio']

       
            
        nuevo_usuario = Usuario(nombre=nombre, telefono=telefono, correo=correo, descripcion=descripcion, servicio=servicio)
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        # Prepara la respuesta JSON
        response_data = {'message': 'Datos enviados exitosamente'}
        return jsonify(response_data), 200
    except Exception as e:
        # Maneja la excepción y envía una respuesta JSON con el error
        app.logger.error(f"Error al enviar datos: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
