from flask import Flask, request, jsonify

app = Flask(__name__)

sensor_data = {}

@app.route('/', methods=['POST'])
def update_sensor_data():
    global sensor_data
    sensor_data = request.json
    return jsonify(sensor_data)

@app.route('/', methods=['GET'])
def get_sensor_data():
    return jsonify(sensor_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
