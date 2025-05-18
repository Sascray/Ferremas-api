from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Importa CORS

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

# Crear las tablas
with app.app_context():
    db.create_all()

# Endpoint para agregar un producto al carrito
@app.route('/carrito/agregar', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    # Verificar si el producto existe
    product = Producto.query.get(product_id)
    if not product:
        return jsonify({'error': 'Producto no encontrado'}), 404

    # Verificar si el carrito ya existe para el usuario
    carrito = Carrito.query.filter_by(user_id=user_id, product_id=product_id).first()

    if carrito:
        carrito.quantity += quantity  # Si ya existe, solo actualiza la cantidad
    else:
        new_carrito = Carrito(user_id=user_id, product_id=product_id, quantity=quantity)
        db.session.add(new_carrito)

    db.session.commit()

    return jsonify({'msg': 'Producto agregado al carrito'}), 201

# Endpoint para ver el contenido del carrito de un usuario
@app.route('/carrito/<int:user_id>', methods=['GET'])
def view_cart(user_id):
    carritos = Carrito.query.filter_by(user_id=user_id).all()
    if not carritos:
        return jsonify({'error': 'Carrito vacío o no encontrado'}), 404

    cart_items = [{
        'product': {
            'id': carrito.producto.id,
            'name': carrito.producto.name,
            'price': carrito.producto.price
        },
        'quantity': carrito.quantity
    } for carrito in carritos]

    return jsonify({'cart': cart_items}), 200

# Endpoint para crear un pedido (simula una compra)
@app.route('/pedido', methods=['POST'])
def create_order():
    data = request.get_json()
    user_id = data.get('user_id')

    # Verificar si el usuario tiene un carrito
    carritos = Carrito.query.filter_by(user_id=user_id).all()
    if not carritos:
        return jsonify({'error': 'Carrito vacío o no encontrado'}), 404

    # Calcular el total del pedido
    total_price = sum(carrito.producto.price * carrito.quantity for carrito in carritos)

    # Simula la creación de un pedido y vacía el carrito
    for carrito in carritos:
        db.session.delete(carrito)

    db.session.commit()

    return jsonify({'msg': 'Pedido creado exitosamente', 'total_price': total_price}), 201

# Endpoint para eliminar un producto del carrito
@app.route('/carrito/eliminar', methods=['DELETE'])
def remove_from_cart():
    data = request.get_json()
    user_id = data.get('user_id')
    product_id = data.get('product_id')

    carrito = Carrito.query.filter_by(user_id=user_id, product_id=product_id).first()

    if not carrito:
        return jsonify({'error': 'Producto no encontrado en el carrito'}), 404

    db.session.delete(carrito)
    db.session.commit()

    return jsonify({'msg': 'Producto eliminado del carrito'}), 200

# Iniciar la aplicación
if __name__ == '__main__':
    app.run(debug=True)
