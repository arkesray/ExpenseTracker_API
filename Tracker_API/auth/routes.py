from datetime import datetime, timedelta

from . import auth
from .. import db
from ..models import User
from flask import request, jsonify, make_response, current_app
from ..helpers import to_iso_z
from werkzeug.security import generate_password_hash, check_password_hash

import jwt


@auth.route('/')
@auth.route('/home')
def home():
    return jsonify({"message": "This is Home Page"}), 200

@auth.route('/login', methods=["POST"])
def login():
    form_data = request.get_json()

    user = User.query.filter_by(username=form_data["Username"]).first()

    if not user:
        return make_response('User not found', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if check_password_hash(user.password_hash, form_data["Password"]):
        exp_dt = datetime.utcnow() + timedelta(days=3)
        token = jwt.encode({
                            'username': user.username,
                            'exp' : exp_dt
                            },
                        current_app.config['SECRET_KEY'],
                        algorithm="HS256"
                        )
        return jsonify({'token': token, 'expires_at': to_iso_z(exp_dt)}), 200

    return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})


@auth.route('/register', methods=['POST'])
def create_user():
    form_data = request.get_json()
    hashed_password = generate_password_hash(form_data['Password'], method='pbkdf2:sha256')

    new_user = User(
                    username=form_data['Username'],
                    password_hash=hashed_password,
                    name=form_data['Name'],
                    is_registered=True
    )
    db.session.add(new_user)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        return jsonify({'message' : 'Cant Create User'}), 500

    return jsonify({'message' : 'New user created!'}), 200


@auth.route('/add_guest_user', methods=['POST'])
def create_guest_user():
    form_data = request.get_json()

    hashed_password = generate_password_hash("Password", method='sha256')

    new_guest_user = User(
                        username=form_data['Username'],
                        password_hash=hashed_password,
                        name='',
                        is_registered=False   
    )
    db.session.add(new_guest_user)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        return jsonify({'message' : 'Cant Create Guest User'}), 500

    return jsonify({'id' : new_guest_user.id, 'username' : new_guest_user.username, 'message' : 'New Guest user created!'}), 200