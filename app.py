from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from models import db, User, Ride, RideRequest
import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
import sqlalchemy

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# Initialize CORS and JWT
CORS(app)
jwt = JWTManager(app)

# Initialize Cloud SQL connection
def getconn():
    connector = Connector()
    conn = connector.connect(
        os.getenv('INSTANCE_CONNECTION_NAME'),
        "pymysql",
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        db=os.getenv('DB_NAME'),
    )
    return conn

# Create SQLAlchemy engine with connection pooling
pool = sqlalchemy.create_engine(
    "mysql+pymysql://",
    creator=getconn,
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800,
)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = pool.url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 1800,
}

# Initialize database
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

# Auth Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User(
        email=data['email'],
        name=data['name']
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    access_token = create_access_token(identity=user.id)
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name
        }
    })

# Ride Routes
@app.route('/api/rides', methods=['POST'])
@jwt_required()
def create_ride():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    ride = Ride(
        start_location=data['start_location'],
        end_location=data['end_location'],
        available_seats=data['available_seats'],
        departure_time=datetime.fromisoformat(data['departure_time']),
        price=data['price'],
        driver_id=current_user_id
    )
    
    db.session.add(ride)
    db.session.commit()
    
    return jsonify({
        'message': 'Ride created successfully',
        'ride_id': ride.id
    }), 201

@app.route('/api/rides/search', methods=['GET'])
def search_rides():
    start = request.args.get('start')
    end = request.args.get('end')
    date = request.args.get('date')
    
    query = Ride.query.filter_by(status='active')
    
    if start:
        query = query.filter(Ride.start_location.ilike(f'%{start}%'))
    if end:
        query = query.filter(Ride.end_location.ilike(f'%{end}%'))
    if date:
        date_obj = datetime.fromisoformat(date)
        query = query.filter(Ride.departure_time >= date_obj)
    
    rides = query.all()
    return jsonify([{
        'id': ride.id,
        'start_location': ride.start_location,
        'end_location': ride.end_location,
        'available_seats': ride.available_seats,
        'departure_time': ride.departure_time.isoformat(),
        'price': ride.price,
        'driver': {
            'id': ride.driver.id,
            'name': ride.driver.name
        }
    } for ride in rides])

@app.route('/api/rides/<int:ride_id>', methods=['GET'])
def get_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    return jsonify({
        'id': ride.id,
        'start_location': ride.start_location,
        'end_location': ride.end_location,
        'available_seats': ride.available_seats,
        'departure_time': ride.departure_time.isoformat(),
        'price': ride.price,
        'status': ride.status,
        'driver': {
            'id': ride.driver.id,
            'name': ride.driver.name
        },
        'requests': [{
            'id': req.id,
            'status': req.status,
            'passenger': {
                'id': req.passenger.id,
                'name': req.passenger.name
            }
        } for req in ride.requests]
    })

@app.route('/api/rides/<int:ride_id>/request', methods=['POST'])
@jwt_required()
def request_ride(ride_id):
    current_user_id = get_jwt_identity()
    ride = Ride.query.get_or_404(ride_id)
    
    if ride.status != 'active':
        return jsonify({'error': 'Ride is not active'}), 400
    
    if ride.available_seats <= 0:
        return jsonify({'error': 'No seats available'}), 400
    
    existing_request = RideRequest.query.filter_by(
        ride_id=ride_id,
        passenger_id=current_user_id
    ).first()
    
    if existing_request:
        return jsonify({'error': 'You have already requested this ride'}), 400
    
    request = RideRequest(
        ride_id=ride_id,
        passenger_id=current_user_id
    )
    
    db.session.add(request)
    db.session.commit()
    
    return jsonify({'message': 'Ride request sent successfully'}), 201

@app.route('/api/ride-requests/<int:request_id>', methods=['PATCH'])
@jwt_required()
def update_ride_request(request_id):
    current_user_id = get_jwt_identity()
    ride_request = RideRequest.query.get_or_404(request_id)
    
    # Check if the current user is the driver of the ride
    if ride_request.ride.driver_id != current_user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['accepted', 'rejected']:
        return jsonify({'error': 'Invalid status'}), 400
    
    ride_request.status = new_status
    
    if new_status == 'accepted':
        ride_request.ride.available_seats -= 1
    
    db.session.commit()
    
    return jsonify({'message': 'Ride request updated successfully'})

if __name__ == '__main__':
    app.run(debug=True) 