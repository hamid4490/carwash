from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import json
import time
import threading
from datetime import datetime
import uuid
import os

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')
PHOTO_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'photos')
os.makedirs(PHOTO_UPLOAD_FOLDER, exist_ok=True)

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passengers (
            id UUID PRIMARY KEY,
            name TEXT,
            phone TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drivers (
            id UUID PRIMARY KEY,
            name TEXT,
            id_card_number TEXT,
            address TEXT,
            phone TEXT UNIQUE,
            photo TEXT,
            is_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id UUID PRIMARY KEY,
            passenger_id UUID REFERENCES passengers(id),
            driver_id UUID REFERENCES drivers(id),
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            accepted_at TIMESTAMP,
            completed_at TIMESTAMP,
            phone TEXT
        );
    ''')
    conn.commit()
    conn.close()

# --- Passenger Registration ---
@app.route('/register/passenger', methods=['POST'])
def register_passenger():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    passenger_id = str(uuid.uuid4())
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO passengers (id, name, phone)
            VALUES (%s, %s, %s)
        ''', (passenger_id, data['name'], data['phone']))
        conn.commit()
        return jsonify({'status': 'ok', 'user_id': passenger_id, 'message': 'Passenger registered successfully'})
    except psycopg2.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Phone number already exists'}), 400
    finally:
        conn.close()

# --- Driver Registration (with photo upload) ---
@app.route('/register/driver', methods=['POST'])
def register_driver():
    name = request.form.get('name')
    id_card_number = request.form.get('id_card_number')
    address = request.form.get('address')
    phone = request.form.get('phone')
    photo_file = request.files.get('photo')
    if not all([name, id_card_number, address, phone, photo_file]):
        return jsonify({'status': 'error', 'message': 'All fields and photo are required'}), 400
    driver_id = str(uuid.uuid4())
    # Save photo
    if not photo_file or not hasattr(photo_file, 'filename') or not photo_file.filename:
        return jsonify({'status': 'error', 'message': 'Invalid or missing photo file'}), 400
    filename = photo_file.filename
    ext = os.path.splitext(filename)[1]
    if not ext:
        return jsonify({'status': 'error', 'message': 'Photo file must have an extension'}), 400
    photo_filename = f"{driver_id}{ext}"
    photo_path = os.path.join(PHOTO_UPLOAD_FOLDER, photo_filename)
    try:
        photo_file.save(photo_path)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to save photo: {str(e)}'}), 500
    # Store relative path for serving
    photo_url = f"/photos/{photo_filename}"
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO drivers (id, name, id_card_number, address, phone, photo, is_verified)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (driver_id, name, id_card_number, address, phone, photo_url, False))
        conn.commit()
        return jsonify({'status': 'ok', 'user_id': driver_id, 'message': 'Driver registered successfully'})
    except psycopg2.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Phone number already exists'}), 400
    finally:
        conn.close()

# --- Passenger Login ---
@app.route('/login/passenger', methods=['POST'])
def login_passenger():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM passengers WHERE phone = %s', (data['phone'],))
    user = cursor.fetchone()
    conn.close()
    if user:
        return jsonify({'status': 'ok', 'user_id': user[0], 'name': user[1]})
    else:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

# --- Driver Login ---
@app.route('/login/driver', methods=['POST'])
def login_driver():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM drivers WHERE phone = %s', (data['phone'],))
    user = cursor.fetchone()
    conn.close()
    if user:
        return jsonify({'status': 'ok', 'user_id': user[0], 'name': user[1]})
    else:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

# API برای تغییر وضعیت راننده
@app.route('/driver/status', methods=['POST'])
def update_driver_status():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE drivers SET status = %s WHERE id = %s', (data['status'], data['driver_id']))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok', 'message': 'Status updated'})

# API برای به‌روزرسانی موقعیت راننده
@app.route('/driver/location', methods=['POST'])
def update_driver_location():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO driver_locations (driver_id, lat, lon, last_updated)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
    ''', (data['driver_id'], data['lat'], data['lon']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'ok', 'message': 'Location updated'})

# API برای ارسال درخواست کارواش
@app.route('/request/create', methods=['POST'])
def create_request():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    request_id = str(uuid.uuid4())
    conn = get_db()
    cursor = conn.cursor()
    # Get passenger phone from passengers table
    cursor.execute('SELECT phone FROM passengers WHERE id = %s', (data['passenger_id'],))
    phone_row = cursor.fetchone()
    phone = phone_row[0] if phone_row else None
    cursor.execute('''
        INSERT INTO requests (id, passenger_id, lat, lon, status, phone)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (request_id, data['passenger_id'], data['lat'], data['lon'], 'pending', phone))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'request_id': request_id, 'message': 'Request created successfully'})

# API برای دریافت درخواست‌های در انتظار (برای رانندگان)
@app.route('/requests/pending', methods=['GET'])
def get_pending_requests():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT r.id, r.lat, r.lon, r.created_at, p.name as passenger_name
        FROM requests r
        JOIN passengers p ON r.passenger_id = p.id
        WHERE r.status = 'pending'
        ORDER BY r.created_at DESC
    ''')
    
    requests = []
    for row in cursor.fetchall():
        requests.append({
            'request_id': row[0],
            'lat': row[1],
            'lon': row[2],
            'created_at': row[3],
            'passenger_name': row[4]
        })
    
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'requests': requests
    })

# API برای پذیرش درخواست توسط راننده
@app.route('/request/accept', methods=['POST'])
def accept_request():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    conn = get_db()
    cursor = conn.cursor()
    # بررسی احراز هویت راننده
    cursor.execute('SELECT is_verified FROM drivers WHERE id = %s', (data['driver_id'],))
    verified_row = cursor.fetchone()
    if not verified_row or not verified_row[0]:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Driver is not verified'}), 403
    # بررسی اینکه درخواست هنوز در انتظار است
    cursor.execute('SELECT status FROM requests WHERE id = %s', (data['request_id'],))
    request_status = cursor.fetchone()
    if not request_status or request_status[0] != 'pending':
        conn.close()
        return jsonify({
            'status': 'error',
            'message': 'Request not available'
        }), 400
    # پذیرش درخواست
    cursor.execute('''
        UPDATE requests 
        SET driver_id = %s, status = %s, accepted_at = CURRENT_TIMESTAMP
        WHERE id = %s
    ''', (data['driver_id'], 'accepted', data['request_id']))
    # تغییر وضعیت راننده به مشغول
    cursor.execute('UPDATE drivers SET status = %s WHERE id = %s', ('busy', data['driver_id']))
    conn.commit()
    conn.close()
    return jsonify({
        'status': 'ok',
        'message': 'Request accepted successfully'
    })

# API برای تکمیل درخواست
@app.route('/request/complete', methods=['POST'])
def complete_request():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE requests 
        SET status = %s, completed_at = CURRENT_TIMESTAMP
        WHERE id = %s
    ''', ('completed', data['request_id']))
    
    # تغییر وضعیت راننده به آنلاین
    cursor.execute('UPDATE drivers SET status = %s WHERE id = %s', ('online', data['driver_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'message': 'Request completed successfully'
    })

# API برای بررسی وضعیت درخواست (برای مسافر)
@app.route('/request/status/<request_id>', methods=['GET'])
def get_request_status(request_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT r.status, r.driver_id, d.name as driver_name, d.phone as driver_phone, d.photo as driver_photo
        FROM requests r
        LEFT JOIN drivers d ON r.driver_id = d.id
        WHERE r.id = %s
    ''', (request_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return jsonify({
            'status': 'ok',
            'request_status': result[0],
            'driver_id': result[1],
            'driver_name': result[2],
            'driver_phone': result[3],
            'driver_photo': result[4]
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Request not found'
        }), 404

# API برای دریافت درخواست‌های فعال راننده
@app.route('/driver/active_requests/<driver_id>', methods=['GET'])
def get_driver_active_requests(driver_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT r.id, r.lat, r.lon, r.created_at, p.name as passenger_name, p.phone as passenger_phone
        FROM requests r
        JOIN passengers p ON r.passenger_id = p.id
        WHERE r.driver_id = %s AND r.status IN (%s, %s)
        ORDER BY r.accepted_at DESC
    ''', (driver_id, 'accepted', 'in_progress'))
    
    requests = []
    for row in cursor.fetchall():
        requests.append({
            'request_id': row[0],
            'lat': row[1],
            'lon': row[2],
            'created_at': row[3],
            'passenger_name': row[4],
            'passenger_phone': row[5]
        })
    
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'requests': requests
    })

# API برای لغو درخواست
@app.route('/request/cancel', methods=['POST'])
def cancel_request():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE requests 
        SET status = %s
        WHERE id = %s
    ''', ('cancelled', data['request_id']))
    
    # اگر راننده داشت، وضعیتش را به آنلاین برگردان
    cursor.execute('''
        UPDATE drivers 
        SET status = %s 
        WHERE id = (SELECT driver_id FROM requests WHERE id = %s)
    ''', ('online', data['request_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'message': 'Request cancelled successfully'
    })

# --- Serve Driver Photos ---
@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(PHOTO_UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
