from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    rides_offered = db.relationship('Ride', backref='driver', lazy=True)
    ride_requests = db.relationship('RideRequest', backref='passenger', lazy=True)

    def set_password(self, password):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_location = db.Column(db.String(200), nullable=False)
    end_location = db.Column(db.String(200), nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    requests = db.relationship('RideRequest', backref='ride', lazy=True)

class RideRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=False)
    passenger_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 