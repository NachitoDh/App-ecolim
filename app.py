from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://yoelchupa_admin:Nachitodeache11@mysql-yoelchupa.alwaysdata.net/yoelchupa_ecolimdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), nullable=True)
    telefono = db.Column(db.String(100), nullable=False)
    servicio = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)

@app.route('/submit_form', methods=['POST'])
def submit_form():
    data = request.form
    nuevo_usuario = Usuario(
        nombre=data.get('nombre'),
        correo=data.get('correo'),
        telefono=data.get('telefono'),
        servicio=data.get('servicio'),
        descripcion=data.get('descripcion')
    )
    db.session.add(nuevo_usuario)
    db.session.commit()
    return jsonify({"message": "Datos enviados con éxito"}), 200

if __name__ == '__main__':
    app.run(debug=True)
