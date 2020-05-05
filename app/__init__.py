from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://alertapp:alertapp@localhost/alertapp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config.from_object('config')
db = SQLAlchemy(app)
manager = LoginManager(app)

from app import alertapp

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=1080, debug=True)