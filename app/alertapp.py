from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://alertapp:alertapp@db/alertapp'
db = SQLAlchemy(app)

@app.route('/receive', methods=['POST'])
def get_data():
    if request.method == 'POST':
        data = request.get_json()

    return jsonify(data)

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=1080)
