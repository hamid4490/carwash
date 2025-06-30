from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# دیتابیس ساده در حافظه (برای تست و سرور رایگان)
locations = {}

# توکن ساده برای امنیت پایه
API_TOKEN = "my_secret_token"

@app.route('/send_location', methods=['POST'])
@app.route('/send_location', methods=['POST'])
def send_location():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
    user_id = data.get('user_id')
    lat = data.get('lat')
    lon = data.get('lon')
    token = data.get('token')
    if token != API_TOKEN:
        return jsonify({'status': 'error', 'message': 'Invalid token'}), 403
    if not user_id or lat is None or lon is None:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400
    locations[user_id] = {'lat': lat, 'lon': lon}
    return jsonify({'status': 'ok'})

@app.route('/get_location/<user_id>', methods=['GET'])
def get_location(user_id):
    token = request.args.get('token')
    if token != API_TOKEN:
        return jsonify({'status': 'error', 'message': 'Invalid token'}), 403
    loc = locations.get(user_id)
    if not loc:
        return jsonify({'status': 'error', 'message': 'Not found'}), 404
    return jsonify({'status': 'ok', 'lat': loc['lat'], 'lon': loc['lon']})

@app.route('/')
def home():
    return 'Taxi Location Server is running!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
