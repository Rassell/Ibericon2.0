import json
import secrets
import os

from werkzeug.security import generate_password_hash

from database import db, User, Conference, City
from api import bpApiAdmin, bpApiAuth


def createApp(app):
    # Intentar leer config.json desde /etc/secrets/ primero, luego desde secret/
    config_paths = ["/etc/secrets/config.json", "secret/config.json"]
    config = None
    
    for config_path in config_paths:
        if os.path.exists(config_path):
            with open(config_path) as conf:
                config = json.load(conf)
                conf.close()
            break
    
    if config is None:
        raise FileNotFoundError("No se encontró config.json en /etc/secrets/ ni en secret/")
    
    app.config["SECRET_KEY"] = handleSecretKey(config)
    app.config['PORT'] = config['port']
    app.config['HOST'] = config['host']
    app.config['DEBUG'] = config['debug']

    app.config["JWT_SECRET_KEY"] = handleSecretKey(config)
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_COOKIE_SECURE"] = True  # Requiere HTTPS
    app.config["JWT_COOKIE_HTTPONLY"] = True  # Previene acceso desde JavaScript
    app.config["JWT_COOKIE_SAMESITE"] = "None"  # Permite cross-domain
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # Desactiva CSRF protection si usas SameSite=None

    app.config["SQLALCHEMY_DATABASE_URI"] = config['db-uri']
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["IMAGE_BB_KEY"] = config['image-bb-key']
    app.config["IMAGE_BB_UPLOAD"] = config['image-bb-upload']
    app.config["IMAGE_DEFAULT"] = config['image-default']

    app.config["BCP_API_EVENT"] = config['api-event-uri']
    app.config["BCP_API_EVENT_NEW"] = config['api-event-uri-new']
    app.config["BCP_API_EVENT_SEARCH"] = config['api-event-search']
    app.config["BCP_API_EVENT_CHECK"] = config['api-event-check']

    app.config["BCP_API_USER"] = config['api-user-uri']
    app.config["BCP_API_USER_DETAIL"] = config['api-user-detail']
    app.config["BCP_API_USER_IMG"] = config['api-user-img']
    app.config["BCP_API_USERS"] = config['api-users-uri']

    app.config["BCP_API_TEAM"] = config['api-team-uri']
    app.config["BCP_API_TEAM_PLACINGS"] = config['api-team-placings-uri']
    app.config["BCP_API_TEAMS_DETAIL"] = config['api-teams-detail']
    app.config["BCP_API_HEADERS"] = config['api-headers']

    app.config["CITIES"] = config["cities"]
    app.config["CONFERENCES"] = config["conferences"]

    app.config["ADMIN_USERNAME"] = config['admin-name']
    app.config["ADMIN_PASSWORD"] = config['admin-password']
    app.config["ADMIN_MAIL"] = config['admin-mail']

    app.config["COLLABORATOR_USERNAME"] = config['collab-name']
    app.config["COLLABORATOR_PASSWORD"] = config['collab-password']
    app.config["COLLAB_MAIL"] = config['collab-mail']

    app.config["MONEY"] = config['money']
    app.config["PERCENTAGE"] = config['percentage']

    bpApiAuth.loginManager.init_app(app)
    app.config["loginManager"] = bpApiAuth.loginManager
    bpApiAuth.jwt.init_app(app)
    app.config["jwt"] = bpApiAuth.jwt
    db.init_app(app)
    app.config["database"] = db
    bpApiAdmin.limiter.init_app(app)
    app.config["limiter"] = bpApiAdmin.limiter

    return app


def createDatabase(app):
    with app.app_context():
        if os.path.exists('database.txt'):
            pass
        else:
            createTables(app.config['database'])
            createAdmin(app)
            createCollaborator(app)
            createRegions(app)
            file = open('database.txt', 'w')
            file.write("Database Created")
            file.close()


def handleSecretKey(keys):
    if keys['secret-key']:
        return keys['secret-key']
    else:
        key = secrets.token_hex(16)
        keys['secret-key'] = key
        json.dump(keys, open("secret/config.json", 'w'), indent=4)
        return key


def createTables(database):
    database.create_all()
    database.session.commit()


def createAdmin(app):
    # Verificar si el admin ya existe
    existing_admin = User.query.filter_by(bcpMail=app.config["ADMIN_MAIL"]).first()
    if existing_admin:
        return
    
    new_user = User(
        bcpId="0000000000",
        bcpMail=app.config["ADMIN_MAIL"],
        bcpName=app.config["ADMIN_USERNAME"],
        conference=1,
        city=1,
        profilePic=app.config["IMAGE_DEFAULT"],
        password=generate_password_hash(app.config["ADMIN_PASSWORD"], method='scrypt'),
        permissions=15,
        registered = False
    )
    app.config['database'].session.add(new_user)
    app.config['database'].session.commit()


def createCollaborator(app):
    # Verificar si el collaborator ya existe
    existing_collab = User.query.filter_by(bcpMail=app.config["COLLAB_MAIL"]).first()
    if existing_collab:
        return
    
    new_user = User(
        bcpId="0000000000",
        bcpMail=app.config["COLLAB_MAIL"],
        bcpName=app.config["COLLABORATOR_USERNAME"],
        conference=1,
        city=1,
        password=generate_password_hash(app.config["COLLABORATOR_PASSWORD"], method='scrypt'),
        permissions=13,
        registered = False
    )
    app.config['database'].session.add(new_user)
    app.config['database'].session.commit()


def createRegions(app):
    # Verificar si ya existen conferencias
    if Conference.query.count() > 0:
        return
    
    for key, value in app.config['CONFERENCES'].items():
        new_conference = Conference(name=key)
        app.config['database'].session.add(new_conference)
        for key1, value1 in app.config['CITIES'].items():
            if value1 in value:
                new_region = City(name=value1, code=int(key1), conference=new_conference)
                app.config['database'].session.add(new_region)
        app.config['database'].session.commit()
