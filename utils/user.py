import statistics

import requests
import json
import base64
import operator
from statistics import mode
from flask import current_app
from sqlalchemy import desc

from werkzeug.security import generate_password_hash, check_password_hash

from database import User, UserFaction, UserTournament, Tournament, Conference, Faction


def setPlayerPermission(database, userId, form):
    try:
        lvl = form['permission']
        usr = User.query.filter_by(id=userId).first()
        usr.permissions = int(lvl)
        database.session.commit()
    except:
        return False
    return True


def getUser(pl):
    return current_app.config["database"].session.query(UserTournament, User, Tournament
                                                        ).order_by(desc(UserTournament.ibericonScore)).filter(UserTournament.userId == pl
                                                                 ).join(Tournament,
                                                                        Tournament.id == UserTournament.tournamentId
                                                                        ).join(User,
                                                                               User.id == UserTournament.userId).all()


def getUserBestTournaments(pl):
    return UserTournament.query.filter_by(userId=int(pl)).order_by(desc(UserTournament.ibericonScore)).limit(4).all()


def getUserOnly(pl):
    return User.query.filter_by(id=pl).first()


def getUserConference(cn):
    return Conference.query.filter_by(id=cn).first()


def getUserMostPlayedFaction(usr):
    mostUsed = 0
    for fct in usr.factions:
        count = 0
        for usT in UserTournament.query.filter_by(factionId=fct.id).filter_by(userId=usr.id).all():
            count += usT.won + usT.tied + usT.lost
        mostUsed = fct.id if count > mostUsed else mostUsed
    fct = Faction.query.filter_by(id=mostUsed).first()
    return fct if fct else None


def getUserMostPlayedClub(usr):
    cl = usr.clubs
    return mode(cl) if cl else None


def getUserLastFaction(usr):
    usT = usr.tournaments
    usT.sort(key=operator.attrgetter('date'))
    usFct = UserTournament.query.filter_by(userId=usr.id).filter_by(tournamentId=usT[-1].id).first()
    fct = Faction.query.filter_by(id=usFct.factionId).first()
    return fct if fct else None


def getUserFactions(usr):
    return current_app.config['database'].session.query(Faction, UserFaction).outerjoin(UserFaction, Faction.id == UserFaction.factionId).filter(UserFaction.userId==usr.id).all()


def getUserByBcpId(user):
    return User.query.filter_by(bcpId=user['userId']).first()


def getUsers(qty=0):
    from sqlalchemy.orm import make_transient
    if qty > 0:
        result = User.query.filter(User.bcpId != "0000000000").order_by(desc(User.ibericonScore)).all()
        return result[0:qty-1]
    else:
        us = User.query.filter(User.bcpId != "0000000000").order_by(desc(User.ibericonScore)).all()
        conferences = {c.id: c.name for c in Conference.query.all()}
        for i, u in enumerate(us):
            if u.conference in conferences:
                # Detach from session to prevent autoflush
                make_transient(u)
                us[i].conference = conferences[u.conference]
        return us


def getUsersWinRate(qty=0):
    if qty > 0:
        result = User.query.filter(User.bcpId != "0000000000").order_by(desc(User.winRate)).all()
        return result[0:qty-1]
    else:
        return User.query.filter(User.bcpId != "0000000000").order_by(desc(User.winRate)).all()


def getUserGlobalPosition(usr):
    users = User.query.filter(User.bcpId != "0000000000").order_by(desc(User.ibericonScore)).all()
    return users.index(usr) + 1


def getUserConferencePosition(usr):
    users = User.query.filter(User.bcpId != "0000000000").filter_by(conference=usr.conference).order_by(desc(User.ibericonScore)).all()
    return users.index(usr) + 1

def updateProfile(usr, form):
    usr = User.query.filter_by(id=usr.id).first()
    usr.bcpName = form['name'] if form['name'] else usr.bcpName
    usr.infoMail = form['email'] if form['email'] else usr.infoMail
    usr.conference = int(form['conference'])
    current_app.config['database'].session.commit()
    return usr


def updatePicture(usr, form):
    file = form['file']
    img = base64.b64encode(file.read())
    response = requests.post(current_app.config['IMAGE_BB_UPLOAD'],
                             params={'key': current_app.config['IMAGE_BB_KEY']},
                             data={'image': img})
    u = User.query.filter_by(id=usr.id).first()
    try:
        u.profilePic = json.loads(response.text)['data']['url']
    except KeyError:
        return 400
    current_app.config['database'].session.commit()
    return 200

# UPDATE DE REGION, de aquí hasta abajo
def updateUserRegionByMostPlayedTournaments(user_id):
    """
    Actualiza la región (conference) de un usuario basándose en la región
    donde más torneos ha jugado.
    
    Args:
        user_id: ID del usuario a actualizar
    
    Returns:
        La nueva conference_id del usuario o None si no hay torneos
    """
    # Obtener el usuario
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return None
    
    # Obtener todos los torneos del usuario
    user_tournaments = UserTournament.query.filter_by(userId=user_id).all()
    
    if not user_tournaments:
        return None
    
    # Contar torneos por región
    conference_count = {}
    for ut in user_tournaments:
        tournament = Tournament.query.filter_by(id=ut.tournamentId).first()
        if tournament and tournament.conference:
            conference_id = tournament.conference
            conference_count[conference_id] = conference_count.get(conference_id, 0) + 1
    
    if not conference_count:
        return None
    
    # Encontrar la región con más torneos
    most_played_conference = max(conference_count.items(), key=lambda x: x[1])[0]
    
    # Actualizar la región del usuario si es diferente
    if user.conference != most_played_conference:
        user.conference = most_played_conference
        current_app.config['database'].session.commit()
        
        # Log del cambio para debugging
        print(f"Usuario {user.bcpName} (ID: {user_id}) actualizado a región {most_played_conference}")
    
    return most_played_conference


def updateAllUsersRegions():
    """
    Actualiza la región de todos los usuarios basándose en donde más torneos han jugado.
    Útil para hacer una actualización masiva.
    
    Returns:
        Número de usuarios actualizados
    """
    users = User.query.filter(User.bcpId != "0000000000").all()
    updated_count = 0
    
    for user in users:
        old_conference = user.conference
        new_conference = updateUserRegionByMostPlayedTournaments(user.id)
        if new_conference and old_conference != new_conference:
            updated_count += 1
    
    return updated_count
