from datetime import datetime, timedelta
# import pytz
  
# # it will get the time zone 
# # of the specified location
# IST = pytz.timezone('Asia/Kolkata')

from . import auth
from .. import db
from ..models import tbl_users
from flask import request, jsonify, make_response, current_app
from werkzeug.security import generate_password_hash, check_password_hash

import jwt


@auth.route('/')
@auth.route('/home')
def home():
    return jsonify({"message": "This is Home Page"}), 200

@auth.route('/login', methods=["POST"])
def login():
    form_data = request.get_json()

    user = tbl_users.query.filter_by(Username=form_data["Username"]).first()

    if not user:
        return make_response('User not found', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if check_password_hash(user.Password, form_data["Password"]):
        token = jwt.encode({
                            'Username' : user.Username, 
                            'exp' : datetime.now() + timedelta(seconds=30)
                            },
                        current_app.config['SECRET_KEY'],
                        algorithm="HS256"
                        )
        return jsonify({'token' : token, 'expires_at' : datetime.now() + timedelta(seconds=30)}), 200

    return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})


@auth.route('/register', methods=['POST'])
def create_user():
    form_data = request.get_json()
    hashed_password = generate_password_hash(form_data['Password'], method='sha256')

    new_user = tbl_users(
                    Username=form_data['Username'],
                    Password=hashed_password,
                    Name=form_data['Name'],
                    isRegistered=True
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

    new_guest_user = tbl_users(
                        Username=form_data['Username'],
                        Name='',
                        isRegistered=False   
    )
    db.session.add(new_guest_user)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        return jsonify({'message' : 'Cant Create Guest User'}), 500

    return jsonify({'message' : 'New Guest user created!'}), 200