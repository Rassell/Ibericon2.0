import json
import secrets
import os

from werkzeug.security import generate_password_hash

from database import db, User, Conference, City
from api import bpApiAdmin, bpApiAuth


def createApp(app):
    with open("secret/config.json") as conf:
        config = json.load(conf)
        conf.close()
    
    # Sobrescribir con variables de entorno si están definidas
    env_mappings = {
        'SECRET_KEY': 'secret-key',
        'DB_URI': 'db-uri',
        'PORT': 'port',
        'HOST': 'host',
        'DEBUG': 'debug',
        'IMAGE_BB_KEY': 'image-bb-key',
        'IMAGE_BB_UPLOAD': 'image-bb-upload',
        'IMAGE_DEFAULT': 'image-default',
        'API_USER_URI': 'api-user-uri',
        'API_USER_DETAIL': 'api-user-detail',
        'API_USER_IMG': 'api-user-img',
        'API_USERS_URI': 'api-users-uri',
        'API_TEAM_URI': 'api-team-uri',
        'API_TEAM_PLACINGS_URI': 'api-team-placings-uri',
        'API_TEAMS_DETAIL': 'api-teams-detail',
        'API_EVENT_URI': 'api-event-uri',
        'API_EVENT_URI_NEW': 'api-event-uri-new',
        'API_EVENT_SEARCH': 'api-event-search',
        'API_EVENT_CHECK': 'api-event-check',
        'ADMIN_USERNAME': 'admin-name',
        'ADMIN_PASSWORD': 'admin-password',
        'ADMIN_MAIL': 'admin-mail',
        'COLLABORATOR_USERNAME': 'collab-name',
        'COLLABORATOR_PASSWORD': 'collab-password',
        'COLLABORATOR_MAIL': 'collab-mail',
        'JWT_SECRET_KEY': 'secret-key',
        'MONEY': 'money',
        'PERCENTAGE': 'percentage'
    }
    
    for env_var, config_key in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            # Convertir a booleano si es necesario
            if config_key == 'debug':
                config[config_key] = env_value.lower() in ('true', '1', 'yes')
            # Convertir a entero si es necesario
            elif config_key in ['port', 'money', 'percentage']:
                try:
                    config[config_key] = int(env_value)
                except ValueError:
                    config[config_key] = env_value
            else:
                config[config_key] = env_value
    
    # Parsear variables JSON complejas
    api_headers = os.getenv('API_HEADERS')
    if api_headers:
        try:
            config['api-headers'] = json.loads(api_headers)
        except json.JSONDecodeError:
            pass  # Mantener el valor del config.json si hay error
    
    conferences = os.getenv('CONFERENCES')
    if conferences:
        try:
            config['conferences'] = json.loads(conferences)
        except json.JSONDecodeError:
            pass  # Mantener el valor del config.json si hay error
    
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
    for key, value in app.config['CONFERENCES'].items():
        new_conference = Conference(name=key)
        app.config['database'].session.add(new_conference)
        for key1, value1 in app.config['CITIES'].items():
            if value1 in value:
                new_region = City(name=value1, code=int(key1), conference=new_conference)
                app.config['database'].session.add(new_region)
        app.config['database'].session.commit()
