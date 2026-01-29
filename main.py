import os

from flask import redirect, url_for, render_template, request, make_response, flash
from flask_openapi3 import Info
from flask_openapi3 import OpenAPI
from flask_login import login_required, current_user
from flask_cors import CORS

import api
from utils import (getUsers, getClubs, getAllTournaments, getUsersWinRate, getFactions, getUserConferencePosition,
                   getUserFactions, getUserGlobalPosition, getUserOnly, getUserConference, getUserMostPlayedFaction,
                   getUserMostPlayedClub, getUserLastFaction, getPastTournamentsByUser, getFutureTournamentsByUser,
                   updateProfile, getConferences, updatePicture, updateStats, createApp, createDatabase, decorators,
                   updateTeamPicture, getFactionOnly, getFaction, getClub, getClubOnly, getFutureTournaments,
                   checkTournaments, getCities, updateThings, resetUserInfo, userLogin, userSignup, resetUser)


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

# Generic
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    # if current_user.is_anonymous:
    #    return redirect(url_for('login'))
    usr = getUsers()
    clb = getClubs()
    tour = getAllTournaments()
    tours = [{
        "bcpUri": u.Tournament.bcpUri,
        "name": u.Tournament.name,
        "date": u.Tournament.date,
        "rounds": u.Tournament.rounds,
        "players": len(u.Tournament.users),
        "conference": u.Conference.name,
        "imgUri": u.Tournament.imgUri
    } for u in tour if not u.Tournament.isFinished]
    return render_template(
        'general.html',
        title="General",
        subtitle="Visión general",
        users=usr,
        clubs=clb,
        tournaments=tours,
        numUsers=len(usr),
        numTour=len(tour),
        amountGolden=app.config['MONEY'],
        amountTrips=app.config['PERCENTAGE'],
        user=current_user if not current_user.is_anonymous else None
    )
@app.route("/ranking", methods={"GET", "POST"})
def ranking():
    usr = getUsers()
    cls = getClubs()
    usr = [{"id": u.id, "conference": u.conference, "profilePic": u.profilePic, "bcpName": u.bcpName, "ibericonScore": u.ibericonScore} for u in usr]
    cls = [{"id": c.id, "conference": "caca","profilePic": c.profilePic, "bcpName": c.name, "ibericonScore": c.ibericonScore} for c in cls]
    return render_template(
        'ranking.html',
        title="Ranking",
        subtitle="Ranking",
        users=usr,
        norte=[u for u in usr if u['conference']=='Norte'],
        noreste=[u for u in usr if u['conference']=='Noreste'],
        este=[u for u in usr if u['conference']=='Este'],
        centro=[u for u in usr if u['conference']=='Centro'],
        sur=[u for u in usr if u['conference']=='Sur'],
        teams=cls,
        user=current_user if not current_user.is_anonymous else None
    )
@app.route("/winrates", methods={"GET", "POST"})
def winRatesEndPoint():
    usr = getUsersWinRate()
    fctO, _ = getFactions()
    usr = [{"id": u.id, "profilePic": u.profilePic, "bcpName": u.bcpName, "winRate": u.winRate} for u in usr if u.winRate]
    fct = [{"id": f.id, "bcpName": f.name, "winRate": f.winRate, "profilePic": url_for('static', filename="factions/white/" + f.shortName + ".svg")} for f in sorted(fctO, key=lambda d: d.winRate, reverse=True) if f.winRate]
    fctPr = [{"id": f.id, "bcpName": f.name, "winRate": f.pickRate, "profilePic": url_for('static', filename="factions/white/" + f.shortName + ".svg")} for f in sorted(fctO, key=lambda d: d.pickRate, reverse=True) if f.pickRate]
    return render_template(
        'winrates.html',
        title="Winrates",
        subtitle="Winrates",
        users=usr,
        factions=fct,
        factionsPick=fctPr,
        user=current_user if not current_user.is_anonymous else None
    )

# User
@app.route("/user/<us>", methods={"GET", "POST"})
def userEndPoint(us):
    if not current_user.is_anonymous:
        if int(us) == current_user.id:
            return redirect(url_for('position'))
    usr = getUserOnly(us)
    if usr:
        conference = getUserConference(usr.conference)
        mostCommon = getUserMostPlayedFaction(usr)
        lastFaction = getUserLastFaction(usr)
        ratesFactions = getUserFactions(usr)
        club = getUserMostPlayedClub(usr)
        future = getFutureTournamentsByUser(usr)
        past = getPastTournamentsByUser(usr)
        globalClass = getUserGlobalPosition(usr)
        conferenceClass = getUserConferencePosition(usr)
        future = [{"img": t.imgUri, "name": t.name, "id": t.id, "position": t.date, "bcpUri": t.bcpUri} for t in future]
        past = [{"img": t["tournament"].imgUri, "name": t['tournament'].name, "id": t['tournament'].id, "position": t['userTournament'].position, "score":t['userTournament'].ibericonScore, "bcpUri": t['tournament'].bcpUri} for t in past]
        ratesFactions = [{"name": f.Faction.name, "id": f.Faction.id, "position": "%.2f" % f.UserFaction.winRate, "img": url_for('static', filename="factions/white/" + f.Faction.shortName + ".svg")} for f in ratesFactions]
        return render_template(
            'user.html',
            title=usr.bcpName,
            subtitle="Posición de " + usr.bcpName,
            conference=conference,
            last=lastFaction,
            common=mostCommon,
            club=club,
            usr=usr,
            future=future,
            past=sorted(past, key=lambda x:x['score'], reverse=True),
            globalClass=globalClass,
            conferenceClass=conferenceClass,
            ratesFactions=ratesFactions,
            user=current_user if not current_user.is_anonymous else None
        )
    return redirect(url_for('dashboard'))
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        updateProfile(current_user, request.form)
        return redirect(url_for('profile'))
    usr = getUserOnly(current_user.id)
    if usr:
        conference = getUserConference(usr.conference)
        mostCommon = getUserMostPlayedFaction(usr)
        lastFaction = getUserLastFaction(usr)
        club = getUserMostPlayedClub(usr)
        conferences = getConferences()
        return render_template(
            'profile.html',
            title=usr.bcpName,
            subtitle="Tu perfil",
            conference=conference,
            last=lastFaction,
            common=mostCommon,
            club=club,
            usr=usr,
            conferences=conferences,
            user=current_user if not current_user.is_anonymous else None
        )
    return redirect(url_for('dashboard'))
@app.route('/new-image', methods=['POST'])
@login_required
def newImage():
    if request.method == 'POST':
        return make_response("result", updatePicture(current_user, request.files))
    return make_response("Not ok", 400)
@app.route('/new-team-image/<cl>', methods=['POST'])
@login_required
@decorators.only_team_leader
def newTeamImage(cl):
    if request.method == 'POST':
        return make_response("result", updateTeamPicture(cl, request.files))
    return make_response("Not ok", 400)
@app.route('/position', methods=['GET', 'POST'])
@login_required
def position():
    usr = getUserOnly(current_user.id)
    if usr:
        conference = getUserConference(usr.conference)
        mostCommon = getUserMostPlayedFaction(usr)
        lastFaction = getUserLastFaction(usr)
        ratesFactions = getUserFactions(usr)
        club = getUserMostPlayedClub(usr)
        future = getFutureTournamentsByUser(usr)
        past = getPastTournamentsByUser(usr)
        globalClass = getUserGlobalPosition(usr)
        conferenceClass = getUserConferencePosition(usr)
        future = [{"img": t.imgUri, "name": t.name, "id": t.id, "position": t.date, "bcpUri": t.bcpUri} for t in future]
        past = [{"img": t["tournament"].imgUri, "name": t['tournament'].name, "id": t['tournament'].id, "position": t['userTournament'].position, "score":t['userTournament'].ibericonScore, "bcpUri": t['tournament'].bcpUri} for t in past]
        ratesFactions = [{"name": f.Faction.name, "id": f.Faction.id, "position": "%.2f" % f.UserFaction.winRate, "img": url_for('static', filename="factions/white/" + f.Faction.shortName + ".svg")} for f in ratesFactions]
        return render_template(
            'position.html',
            title=usr.bcpName,
            subtitle="Tu posición",
            conference=conference,
            last=lastFaction,
            common=mostCommon,
            club=club,
            usr=usr,
            future=future,
            past=sorted(past, key=lambda x:x['score'], reverse=True),
            globalClass=globalClass,
            conferenceClass=conferenceClass,
            ratesFactions=ratesFactions,
            user=current_user if not current_user.is_anonymous else None
        )
    return redirect(url_for('dashboard'))

# Faction
@app.route("/faction/<fact>", methods={"GET"})
def factionEndPoint(fact):
    faction = getFactionOnly(fact)
    fct = getFaction(fact)
    fct = [{"bcpName": u.User.bcpName, "profilePic": u.User.profilePic, "ibericonScore": u.UserFaction.ibericonScore, "id":u.User.id} for u in fct]
    return render_template(
        'faction.html',
        title=faction.name,
        subtitle=faction.name,
        user=current_user if not current_user.is_anonymous else None,
        faction=fct,
        fctOnly=faction
    )
@app.route("/factions", methods={"GET"})
def factionsEndPoint():
    fct, usrFct = getFactions()
    fct = [{
        "id": f.bcpId,
        "name": f.name,
        "winRate": f.winRate,
        "pickRate": f.pickRate,
        "img": url_for('static', filename="factions/white/" + f.shortName + ".svg"),
        "imgSelector": url_for('static', filename="factions/black/" + f.shortName + ".svg"),
        "tournaments": len(f.tournaments),
        "renderingInfo": {
            "paginationId": f.bcpId + "Pagination",
            "bodyId": f.bcpId + "Body"
        },
        "users": [{
            "id": u.User.id,
            "bcpName": u.User.bcpName,
            "profilePic": u.User.profilePic,
            "ibericonScore": u.UserFaction.ibericonScore
        } for u in getFaction(f.id)]
    } for f in fct]
    return render_template(
        'factions.html',
        title="Facciones",
        subtitle="Facciones",
        user=current_user if not current_user.is_anonymous else None,
        factions=fct,
        usrFct=usrFct
    )

# Club
@app.route("/club/<cl>", methods={"GET"})
def clubEndPoint(cl):
    club = getClubOnly(cl)
    clTor = getClub(cl)
    position = getClubs().index(club) + 1
    return render_template(
        'club.html',
        title=club.name,
        subtitle=club.name,
        position=position,
        club=club,
        clTor=clTor,
        user=current_user if not current_user.is_anonymous else None
    )

#Auth
@app.route('/login', methods=['GET', 'POST'])
def login():
    cities = getCities()
    if request.method == 'POST':
        response, _ = userLogin(request.form)
        return response
    return render_template('landing.html', title="Login", cities=cities, user=current_user if not current_user.is_anonymous else None)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    cities = getCities()
    if request.method == 'POST':
        response, _ = userSignup(request.form)
        return response
    return render_template('landing.html', title="Registro", cities=cities, user=current_user if not current_user.is_anonymous else None)
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    response, _ = resetUserInfo()
    return response

#Admin
@app.route('/get-tournaments', methods=['GET'])
@decorators.only_collaborator
def getTournaments():
    getFutureTournaments()
    return redirect(url_for('dashboard'))
@app.route('/check-tournaments', methods=['GET'])
@decorators.only_collaborator
def checkTournamentsAdmin():
    checkTournaments()
    return redirect(url_for('dashboard'))
@app.route('/update-stats', methods=['GET'])
@decorators.only_collaborator
def updateStatsAdmin():
    updateStats()
    return redirect(url_for('dashboard'))
@app.route("/add/tournament", methods={"GET", "POST"})
@login_required
@decorators.only_collaborator
def addNewTournamentAdmin():
    from api.bpApiAdmin.utils import newTournamentApi
    if request.method == 'POST':
        response = newTournamentApi(request.form['uri'])
        if response.status == 200:
            if updateStats().status == 200:
                flash("OK")
            else:
                flash("No OK")
        else:
            flash("No OK")
        return redirect(url_for('dashboard'))
    return render_template(
        'add.html',
        title="Añadir Torneo",
        subtitle="Añadir torneo",
        user=current_user if not current_user.is_anonymous else None
    )
@app.route("/collaborator", methods={"GET", "POST"})
@login_required
@decorators.only_collaborator
def collaboratorAdmin():
    if request.method == 'POST':
        response = updateThings(request.form)
        if response.status == 200:
            flash("OK")
        else:
            flash("No OK")
        return redirect(url_for('dashboard'))
    return render_template(
        'collaborator.html',
        title="Espacio de colaborador",
        subtitle="El súper selecto espacio de los máquinas",
        user=current_user if not current_user.is_anonymous else None
    )
@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method == 'POST':
        os.system('bash ib2-command-pull-event.sh')
        return 'Updated PythonAnywhere successfully', 200
    else:
        return 'Wrong event type', 400
@app.route("/reset-user/<mail>", methods={"GET", "POST"})
@login_required
@decorators.only_admin
def resetUserEndPoint(mail):
    response = resetUser(mail)
    if response == 200:
        flash("OK", 'info')
    else:
        flash("No OK", "error")
    return redirect(url_for('dashboard'))

# Sponsors
@app.route("/sponsors", methods={"GET"})
def sponsorsEndPoint():
    # Lista de sponsors con sus datos
    # Puedes actualizar esta lista con los sponsors reales
    # Las imágenes deben estar en la carpeta static/sponsors/
    sponsors = [
        #{
        #    "id": 1,
        #    "name": "Games Workshop",
        #    "logo": "https://via.placeholder.com/300x200/FF0000/FFFFFF?text=Games+Workshop",
        #    "url": "https://www.games-workshop.com"
        #}
    ]
    
    # Si tienes imágenes locales, puedes usar:
    # "logo": url_for('static', filename='sponsors/nombre_imagen.png')
    
    return render_template(
        'sponsors.html',
        title="Sponsors",
        subtitle="Nuestros Sponsors",
        sponsors=sponsors,
        user=current_user if not current_user.is_anonymous else None
    )

# Tournaments
@app.route("/tournaments", methods={"GET", "POST"})
def tournamentsEndPoint():
    tournaments = getAllTournaments()
    sorted_tournaments = sorted(tournaments, key=lambda x: x[0].date, reverse=True)
    tors = [{
        "bcpUri": u.Tournament.bcpUri,
        "name": u.Tournament.name,
        "date": u.Tournament.date,
        "rounds": u.Tournament.rounds,
        "players": len(u.Tournament.users),
        "conference": u.Conference.name,
        "imgUri": u.Tournament.imgUri
    } for u in sorted_tournaments if not u.Tournament.isFinished]
    past = [{
        "bcpUri": u.Tournament.bcpUri,
        "name": u.Tournament.name,
        "date": u.Tournament.date,
        "rounds": u.Tournament.rounds,
        "players": len(u.Tournament.users),
        "conference": u.Conference.name,
        "imgUri": u.Tournament.imgUri
    } for u in sorted_tournaments if u.Tournament.isFinished]
    return render_template(
        'tournaments.html',
        title="Torneos",
        subtitle="Torneos",
        user=current_user if not current_user.is_anonymous else None,
        torN=[tor for tor in tors if tor['conference'] == 'Norte'],
        torNE=[tor for tor in tors if tor['conference'] == 'Noreste'],
        torE=[tor for tor in tors if tor['conference'] == 'Este'],
        torC=[tor for tor in tors if tor['conference'] == 'Centro'],
        torS=[tor for tor in tors if tor['conference'] == 'Sur'],
        past=past,
        future=tors
    )

if __name__ == '__main__':
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'])

# TODO
#  Meter el porcentaje alrededor del icono
#  Meter el valor objetivo y hacer un porcentaje
#  Mirar algo para saber que hay más páginas (esferitas)


# TODO
#  problemas:
#  Logos, necesito los ultimos


# TODO Futuro
#  mysql
#  detalles de torneos
#  buy me a coffee
#  seccion about
#  sponsor.
