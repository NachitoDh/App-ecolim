from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import pymysql

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://yoelchupa_admin:Nachitodeache11@mysql-yoelchupa.alwaysdata.net/yoelchupa_ecolimdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True
}
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

# Ruta para mostrar el formulario
@app.route('/')
def formulario():
    return render_template('formulario.html')

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
        
        flash('Datos enviados exitosamente')
        return redirect('/')
    except pymysql.err.OperationalError as e:
        db.session.rollback()
        flash(f'Error de conexión a la base de datos: {str(e)}')
        return redirect('/')
    except Exception as e:
        db.session.rollback()
        flash(f'Ocurrió un error: {str(e)}')
        return redirect('/')
        
if __name__ == '__main__':
    app.run(debug=True)
