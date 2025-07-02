from flask import Flask, request, jsonify
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

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            phone TEXT UNIQUE,
            name TEXT,
            user_type TEXT,
            status TEXT DEFAULT 'offline',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id UUID PRIMARY KEY,
            passenger_id UUID,
            driver_id UUID,
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            accepted_at TIMESTAMP,
            completed_at TIMESTAMP,
            phone TEXT,
            FOREIGN KEY (passenger_id) REFERENCES users (id),
            FOREIGN KEY (driver_id) REFERENCES users (id)
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS driver_locations (
            driver_id UUID PRIMARY KEY,
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES users (id)
        );
    ''')
    conn.commit()
    conn.close()

# API برای ثبت‌نام کاربر
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    user_id = str(uuid.uuid4())
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (id, phone, name, user_type)
            VALUES (%s, %s, %s, %s)
        ''', (user_id, data['phone'], data['name'], data['user_type']))
        
        conn.commit()
        
        return jsonify({
            'status': 'ok',
            'user_id': user_id,
            'message': 'User registered successfully'
        })
    except psycopg2.IntegrityError:
        return jsonify({
            'status': 'error',
            'message': 'Phone number already exists'
        }), 400
    finally:
        conn.close()

# API برای ورود کاربر
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, user_type, status FROM users WHERE phone = %s', (data['phone'],))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'status': 'ok',
            'user_id': user[0],
            'name': user[1],
            'user_type': user[2],
            'status': user[3]
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404

# API برای تغییر وضعیت راننده
@app.route('/driver/status', methods=['POST'])
def update_driver_status():
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET status = %s WHERE id = %s', (data['status'], data['driver_id']))
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
    # Get passenger phone from users table
    cursor.execute('SELECT phone FROM users WHERE id = %s', (data['passenger_id'],))
    phone_row = cursor.fetchone()
    phone = phone_row[0] if phone_row else None
    
    cursor.execute('''
        INSERT INTO requests (id, passenger_id, lat, lon, status, phone)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (request_id, data['passenger_id'], data['lat'], data['lon'], 'pending', phone))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'request_id': request_id,
        'message': 'Request created successfully'
    })

# API برای دریافت درخواست‌های در انتظار (برای رانندگان)
@app.route('/requests/pending', methods=['GET'])
def get_pending_requests():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT r.id, r.lat, r.lon, r.created_at, u.name as passenger_name
        FROM requests r
        JOIN users u ON r.passenger_id = u.id
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
    cursor.execute('UPDATE users SET status = %s WHERE id = %s', ('busy', data['driver_id']))
    
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
    cursor.execute('UPDATE users SET status = %s WHERE id = %s', ('online', data['driver_id']))
    
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
        SELECT r.status, r.driver_id, u.name as driver_name, u.phone as driver_phone
        FROM requests r
        LEFT JOIN users u ON r.driver_id = u.id
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
            'driver_phone': result[3]
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
        SELECT r.id, r.lat, r.lon, r.created_at, u.name as passenger_name, u.phone as passenger_phone
        FROM requests r
        JOIN users u ON r.passenger_id = u.id
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
        UPDATE users 
        SET status = %s 
        WHERE id = (SELECT driver_id FROM requests WHERE id = %s)
    ''', ('online', data['request_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'message': 'Request cancelled successfully'
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
