from flask_openapi3 import Info
from flask_openapi3 import OpenAPI
from flask_cors import CORS

import api
from utils import createApp, createDatabase


info = Info(title="Ibericon API", version="1.0.0")
app = OpenAPI(__name__, info=info)

# API
app.register_api(api.adminApiBP)
app.register_api(api.authApiBP)
app.register_api(api.userApiBP)
app.register_api(api.clubApiBP)
app.register_api(api.factionApiBP)
app.register_api(api.teamApiBP)
app.register_api(api.tournamentApiBP)

# Configure CORS only for /api/* endpoints
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:8080",
            "https://ibericon-web.vercel.app",
            "https://ibericon.com",
            "https://www.ibericon.com",
            "https://vercel.app"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

app = createApp(app)
createDatabase(app)

if __name__ == '__main__':
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'])
