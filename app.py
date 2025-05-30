from flask import Flask, jsonify, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Importa CORS
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import requests

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas las rutas
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ferremas.db'  # Usa SQLite o cambia la URI según tu base de datos
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de Producto
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)

# Modelo de Carrito de Compras
class Carrito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    producto = db.relationship('Producto', backref=db.backref('carritos', lazy=True))

# Modelo de Usuario
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  # Guardar hash de contraseña

# Crear las tablas
with app.app_context():
    db.create_all()

# --- CRUD Productos ---

@app.route('/producto', methods=['POST'])
def crear_producto():
    data = request.get_json()
    name = data.get('name')
    price = data.get('price')

    if not name or price is None:
        return jsonify({"error": "Nombre y precio son obligatorios"}), 400

    nuevo_producto = Producto(name=name, price=price)
    db.session.add(nuevo_producto)
    db.session.commit()

    return jsonify({"msg": "Producto creado exitosamente", "id": nuevo_producto.id}), 201

@app.route('/productos', methods=['GET'])
def obtener_productos():
    productos = Producto.query.all()
    resultado = [{"id": p.id, "name": p.name, "price": p.price} for p in productos]
    return jsonify(resultado), 200

@app.route('/producto/<int:id>', methods=['PUT'])
def actualizar_producto(id):
    producto = Producto.query.get(id)
    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404

    data = request.get_json()
    name = data.get('name')
    price = data.get('price')

    if name:
        producto.name = name
    if price is not None:
        producto.price = price

    db.session.commit()
    return jsonify({"msg": "Producto actualizado exitosamente"}), 200

@app.route('/producto/<int:id>', methods=['DELETE'])
def eliminar_producto(id):
    producto = Producto.query.get(id)
    if not producto:
        return jsonify({"error": "Producto no encontrado"}), 404

    db.session.delete(producto)
    db.session.commit()
    return jsonify({"msg": "Producto eliminado exitosamente"}), 200

# --- Endpoints de carrito existentes ---

@app.route('/carrito/agregar', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    product = Producto.query.get(product_id)
    if not product:
        return jsonify({'error': 'Producto no encontrado'}), 404

    carrito = Carrito.query.filter_by(user_id=user_id, product_id=product_id).first()
    if carrito:
        carrito.quantity += quantity
    else:
        new_carrito = Carrito(user_id=user_id, product_id=product_id, quantity=quantity)
        db.session.add(new_carrito)

    db.session.commit()
    return jsonify({'msg': 'Producto agregado al carrito'}), 201

@app.route('/carrito/<int:user_id>', methods=['GET'])
def view_cart(user_id):
    carritos = Carrito.query.filter_by(user_id=user_id).all()
    if not carritos:
        return jsonify({'error': 'Carrito vacío o no encontrado'}), 404

    cart_items = [({
        'product': {
            'id': c.producto.id,
            'name': c.producto.name,
            'price': c.producto.price
        },
        'quantity': c.quantity
    }) for c in carritos]

    return jsonify({'cart': cart_items}), 200

@app.route('/pedido', methods=['POST'])
def create_order():
    data = request.get_json()
    user_id = data.get('user_id')

    carritos = Carrito.query.filter_by(user_id=user_id).all()
    if not carritos:
        return jsonify({'error': 'Carrito vacío o no encontrado'}), 404

    total_price = sum(c.producto.price * c.quantity for c in carritos)

    for c in carritos:
        db.session.delete(c)

    db.session.commit()

    return jsonify({'msg': 'Pedido creado exitosamente', 'total_price': total_price}), 201

@app.route('/carrito/eliminar', methods=['DELETE'])
def remove_from_cart():
    data = request.get_json()
    user_id = data.get('user_id')
    product_id = data.get('product_id')

    if product_id:
        carrito = Carrito.query.filter_by(user_id=user_id, product_id=product_id).first()
        if not carrito:
            return jsonify({'error': 'Producto no encontrado en el carrito'}), 404

        db.session.delete(carrito)
        db.session.commit()
        return jsonify({'msg': 'Producto eliminado del carrito'}), 200
    else:
        # Eliminar todo el carrito si no se pasa product_id
        carritos = Carrito.query.filter_by(user_id=user_id).all()
        for carrito in carritos:
            db.session.delete(carrito)
        db.session.commit()
        return jsonify({'msg': 'Carrito vaciado correctamente'}), 200

# --- API Usuarios ---

@app.route('/usuario/registro', methods=['POST'])
def registrar_usuario():
    data = request.get_json()
    nombre = data.get('nombre')
    email = data.get('email')
    password = data.get('password')

    if not nombre or not email or not password:
        return jsonify({"error": "Faltan datos requeridos"}), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({"error": "Email ya registrado"}), 400

    hashed_password = generate_password_hash(password)
    nuevo_usuario = Usuario(nombre=nombre, email=email, password=hashed_password)
    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({"msg": "Usuario registrado exitosamente", "id": nuevo_usuario.id}), 201

@app.route('/usuario/login', methods=['POST'])
def login_usuario():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario or not check_password_hash(usuario.password, password):
        return jsonify({"error": "Credenciales inválidas"}), 401

    return jsonify({"msg": "Login exitoso", "usuario": {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email}}), 200

@app.route('/usuario/<int:id>', methods=['GET'])
def obtener_usuario(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    return jsonify({"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email}), 200

@app.route('/usuario/<int:id>', methods=['PUT'])
def actualizar_usuario(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    data = request.get_json()
    nombre = data.get('nombre')
    email = data.get('email')

    if nombre:
        usuario.nombre = nombre
    if email:
        if Usuario.query.filter(Usuario.email == email, Usuario.id != id).first():
            return jsonify({"error": "Email ya en uso"}), 400
        usuario.email = email

    db.session.commit()
    return jsonify({"msg": "Usuario actualizado exitosamente"}), 200

@app.route('/usuario/<int:id>', methods=['DELETE'])
def eliminar_usuario(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"msg": "Usuario eliminado exitosamente"}), 200

# --- Ruta para iniciar pago simulado ---

@app.route('/pago/iniciar', methods=['POST'])
def iniciar_pago():
    data = request.get_json()
    user_id = data.get('user_id')
    metodo_pago = data.get('metodo_pago')

    # Validar usuario y carrito
    carritos = Carrito.query.filter_by(user_id=user_id).all()
    if not carritos:
        return jsonify({"error": "Carrito vacío o no encontrado"}), 404

    # Calcular total
    total_price = sum(c.producto.price * c.quantity for c in carritos)

    # Simulación de URL de pago según método
    if metodo_pago == 'tarjeta':
        url_redirect = f"http://localhost:5500/webpay?user_id={user_id}&total={total_price}"
    elif metodo_pago == 'transferencia':
        url_redirect = f"http://localhost:5500/transferencia?user_id={user_id}&total={total_price}"
    else:
        return jsonify({"error": "Método de pago no soportado"}), 400

    return jsonify({"url_redirect": url_redirect}), 200

# --- INTEGRACION PAYPAL SANDBOX ---

PAYPAL_CLIENT_ID = 'ARE_IekSwYj8N98RBPJIBi-a8NH9AImYg5yxgjkCUG-qScEhsMOT0zRznATj7PkPLHoCpyic7MFPurSG'
PAYPAL_SECRET = 'EPn7DE4ZvSI7zQZ2SwYvvHs9lEjNY2bHE7FNmNg3omeA9_DSu7Rg_0lhVWThTZ4RTrbwtwf0duQZYWvN'
PAYPAL_BASE_URL = 'https://api-m.sandbox.paypal.com'

def get_paypal_access_token():
    auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials"
    }
    r = requests.post(f"{PAYPAL_BASE_URL}/v1/oauth2/token", headers=headers, data=data)
    r.raise_for_status()
    return r.json()['access_token']

@app.route('/paypal/crear-pedido', methods=['POST'])
def paypal_crear_pedido():
    data = request.get_json()
    total = data.get('total')
    if total is None:
        return jsonify({"error": "Total no especificado"}), 400

    access_token = get_paypal_access_token()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    order_payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": f"{total:.2f}"
                }
            }
        ],
        "application_context": {
            "return_url": "http://localhost:5000/paypal/pago-exitoso",
            "cancel_url": "http://localhost:5000/paypal/pago-cancelado"
        }
    }

    response = requests.post(f"{PAYPAL_BASE_URL}/v2/checkout/orders", headers=headers, json=order_payload)
    if response.status_code != 201:
        return jsonify({"error": "Error creando el pedido en PayPal"}), 500

    order = response.json()
    for link in order['links']:
        if link['rel'] == 'approve':
            return jsonify({"id": order['id'], "approve_url": link['href']})

    return jsonify({"error": "No se encontró link de aprobación"}), 500

@app.route('/paypal/pago-exitoso')
def paypal_pago_exitoso():
    token = request.args.get('token')
    if not token:
        return "Token no proporcionado", 400

    access_token = get_paypal_access_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    capture_resp = requests.post(f"{PAYPAL_BASE_URL}/v2/checkout/orders/{token}/capture", headers=headers)
    if capture_resp.status_code == 201:
        # Aquí puedes limpiar carrito o registrar pedido en DB si quieres
        return "Pago realizado con éxito. ¡Gracias por su compra!"
    else:
        return f"Error capturando el pago: {capture_resp.text}", 500

@app.route('/paypal/pago-cancelado')
def paypal_pago_cancelado():
    return "Pago cancelado por el usuario."

if __name__ == '__main__':
    app.run(debug=True)
