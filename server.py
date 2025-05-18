from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import re
import hashlib
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")  # Make sure .env has MONGO_URI
client = MongoClient(MONGO_URI)
db = client['car_rental']
users_collection = db['users']
bookings_collection = db['bookings']

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_email(email):
    return re.match(r'^\S+@\S+\.\S+$', email)

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "errors": {"general": "No input data provided"}}), 400

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    agree_terms = data.get('agreeTerms', False)

    errors = {}
    if not name:
        errors['name'] = 'Name is required'
    if not email:
        errors['email'] = 'Email is required'
    elif not is_valid_email(email):
        errors['email'] = 'Invalid email format'
    if not password:
        errors['password'] = 'Password is required'
    elif len(password) < 6:
        errors['password'] = 'Password must be at least 6 characters'
    if not agree_terms:
        errors['agreeTerms'] = 'You must agree to the terms and conditions'

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    if users_collection.find_one({'email': email}):
        return jsonify({"success": False, "errors": {"email": "Email already registered"}}), 400

    users_collection.insert_one({
        'name': name,
        'email': email,
        'password': hash_password(password),
        'agreeTerms': agree_terms,
        'created_at': datetime.utcnow()
    })

    return jsonify({"success": True, "message": "Signup successful!"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400

    user = users_collection.find_one({'email': email})
    if not user or user['password'] != hash_password(password):
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    return jsonify({
        "success": True,
        "message": "Login successful!",
        "user": {
            "id": str(user['_id']),
            "name": user['name'],
            "email": user['email']
        }
    }), 200

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    user_id = request.args.get('user_id', '1')
    bookings = list(bookings_collection.find({"user_id": user_id}))
    for b in bookings:
        b['id'] = str(b['_id'])
        del b['_id']
    return jsonify({"success": True, "bookings": bookings})

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    data = request.get_json()
    required_fields = ['user_id', 'car_id', 'car_name', 'car_image', 'start_date', 'end_date', 'location', 'price']
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400

    data['status'] = data.get('status', 'Upcoming')
    bookings_collection.insert_one(data)
    return jsonify({"success": True, "message": "Booking created successfully"}), 201

@app.route('/api/profile', methods=['GET'])
def profile():
    user = users_collection.find_one()  # For demo only
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    created = user.get('created_at', datetime.utcnow())
    member_since = created.strftime('%B %Y')

    return jsonify({
        "success": True,
        "user": {
            "id": str(user['_id']),
            "name": user['name'],
            "email": user['email'],
            "avatar": "https://randomuser.me/api/portraits/men/32.jpg",
            "memberSince": member_since
        }
    })

def insert_demo_data():
    if bookings_collection.count_documents({}) == 0:
        demo = [
            {
                "user_id": "1",
                "car_id": "1",
                "car_name": "Tesla Model 3",
                "car_image": "https://images.unsplash.com/photo-1560958089-b8a1929cea89?auto=format&fit=crop&w=2071&q=80",
                "start_date": "2023-07-15",
                "end_date": "2023-07-18",
                "location": "New York",
                "status": "Upcoming",
                "price": 267
            }
        ]
        bookings_collection.insert_many(demo)

if __name__ == '__main__':
    insert_demo_data()  # Insert demo data manually before app start
    app.run(host='0.0.0.0', port=5000, debug=True)
