import requests
import json

from datetime import timedelta

from flask import current_app, jsonify
from flask_login import login_user, logout_user
from flask_jwt_extended import set_access_cookies, create_access_token, unset_jwt_cookies

from database import User, City
from werkzeug.security import check_password_hash, generate_password_hash


def userSignup(form):
    # Verify the user's credentials in an external service (BCP)
    status, data = checkBCPUser(form)
    if status == 200:
        # Hash the user's password
        hashed_password = generate_password_hash(form['password'], method='scrypt')
        user = User.query.filter_by(bcpId=data['id']).first()
        city = City.query.filter_by(name=form['city']).first()
        if user:
            if not user.registered:
                # Update user data if the user already exists but is not registered
                user.bcpMail = data['email']
                user.infoMail = data['email']
                user.password = hashed_password
                user.registered = True
                user.conference = city.conference.id
                user.city = city.id
                current_app.config['database'].session.commit()
                # Create a response with user information and set cookies
                responseApi = jsonify({
                    "status": 200,
                    "message": "Registration successful",
                    "data": {
                        "id": user.bcpId,
                        "name": user.bcpName,
                        "mail": user.bcpMail,
                        "conference": city.conference.name,
                        "city": city.name
                    }
                })
                return setUserInfo(responseApi, user)
            return jsonify({
                "status": 401,
                "message": "User already registered",
                "data": {}
            })
        uri = current_app.config["BCP_API_USER_DETAIL"].replace("####userId####", data['id'])
        response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
        users = json.loads(response.text)
        imgUrl = current_app.config["IMAGE_DEFAULT"]
        if 'profileFileId' in users.keys():
            uri = current_app.config["BCP_API_USER_IMG"].replace("####img####", users['profileFileId'])
            response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
            img = json.loads(response.text)
            imgUrl = img['url']
        new_user = User(
            bcpId=data['id'],
            bcpMail=data['email'],
            infoMail=data['email'],
            password=hashed_password,
            bcpName=data['firstName'] + " " + data['lastName'],
            permissions=0,
            profilePic=imgUrl,
            city=city.id,
            conference=city.conference.id,
            registered=True
        )
        current_app.config['database'].session.add(new_user)
        current_app.config['database'].session.commit()
        # Create a response with user information and set cookies
        responseApi = jsonify({
            "status": 200,
            "message": "Registration successful",
            "data": {
                "id": new_user.bcpId,
                "name": new_user.bcpName,
                "mail": new_user.bcpMail,
                "conference": city.conference.name,
                "city": city.name
            }
        })
        return setUserInfo(responseApi, new_user)
    return jsonify({
        "status": 401,
        "message": "Your BCP credentials are incorrect",
        "data": {}
    })


def checkBCPUser(form):
    headers = current_app.config['BCP_API_HEADERS']
    r = requests.post('https://newprod-api.bestcoastpairings.com/v1/users/signin',
                      json={"username": form['email'], "password": form['password']},
                      headers=headers)
    if r.status_code == 200:
        tokens = json.loads(r.text)
        headers['Identity'] = tokens['idToken']
        headers['Authorization'] = 'Bearer ' + tokens['accessToken']
        r = requests.get('https://prod-api.bestcoastpairings.com/users/' + form['email'],
                         headers=headers)
        if r.status_code == 200:
            userData = json.loads(r.text)
            return r.status_code, userData
    return r.status_code, {}


def userLogin(form):
    user = User.query.filter_by(bcpMail=form['email']).first()
    if user:
        if check_password_hash(user.password, form['password']):
            city = City.query.filter_by(id=user.city).first()
            # Create a response with user information and set cookies
            responseApi = jsonify({
                "status": 200,
                "message": "Login successful",
                "data": {
                    "id": user.bcpId,
                    "name": user.bcpName,
                    "mail": user.bcpMail,
                    "conference": city.conference.name if city else None,
                    "city": city.name if city else None
                }
            })
            return setUserInfo(responseApi, user)
    else:
        userSignup(form)
    return jsonify({
        "status": 401,
        "message": "Could not verify",
        "data": {}
    })


def setUserInfo(response, user):
    set_access_cookies(response, create_access_token(identity=user.bcpId, expires_delta=timedelta(days=365)))
    login_user(user)
    return response


def resetUserInfo():
    responseApi = jsonify({
        "status": 200,
        "message": "Logout successful",
        "data": {}
    })
    logout_user()
    unset_jwt_cookies(responseApi)
    return responseApi


def getUserOnly(pl):
    return User.query.filter_by(id=pl).first()
