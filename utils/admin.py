from flask import current_app, jsonify, make_response
from datetime import datetime, timedelta
import requests
import json
from json.decoder import JSONDecodeError
import base64
from sqlalchemy import desc
from database import *
from utils.user import updateUserRegionByMostPlayedTournaments


def checkTournaments():
    for t in Tournament.query.filter_by(isFinished=False).all():
        uri = current_app.config["BCP_API_EVENT_CHECK"].replace("####eventId####", t.bcpId)
        response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
        info = json.loads(response.text)
        if info['ended']:
            tor = Tournament.query.filter_by(bcpId=info['id']).first()
            if tor:
                _ = deleteTournament(tor)
            newTournament(info)


def getFutureTournaments():
    current_datetime = datetime.utcnow()
    now = current_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    one_year_later = current_datetime + timedelta(days=365)  # Approximation, not accounting for leap years
    one_year_later_formatted = one_year_later.strftime("%Y-%m-%dT%H:%M:%SZ")

    uri = current_app.config["BCP_API_EVENT_SEARCH"].replace("####startDate####", now)
    uri = uri.replace("####endDate####", one_year_later_formatted)
    response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
    info = json.loads(response.text)

    for t in info['data']:
        tor = Tournament.query.filter_by(bcpId=t['id']).first()
        if tor:
            _ = deleteTournament(tor)
        newTournament(t)


def setPlayerPermission(database, userId, level, fromApi=False):
    lvl = level
    usr = User.query.filter_by(bcpId=userId).first()
    oldPermission = usr.permissions
    usr.permissions = int(lvl)
    database.session.commit()
    if fromApi:
        return jsonify({
            "status": 200,
            "message": "Ok",
            "data": {
                "id": usr.bcpId,
                "name": usr.bcpName,
                "permission": usr.permissions,
                "oldPermissions": oldPermission
            }
        })
    return 200


def setTeamLeader(database, userId, teamId, fromApi=False):
    club = Club.query.filter_by(bcpId=teamId).first()
    usr = User.query.filter_by(bcpId=userId).first()
    oldLeader = User.query.filter_by(id=club.leader).first()
    club.leader = usr.id
    usr.permissions = 4 if usr.permissions < 4 else usr.permissions
    database.session.commit()
    if fromApi:
        return jsonify({
            "status": 200,
            "message": "Ok",
            "data": {
                "id": usr.bcpId,
                "name": usr.bcpName,
                "permission": usr.permissions,
                "oldLeader": oldLeader.bcpId if oldLeader else None
            }
        })
    return 200


def algorithm(user, totalUsers):
    performance = [0, 0, 0]
    playerModifier = 1 + totalUsers / 100
    try:
        roundModifier = (10 + len(user['games'])) / len(user['games'])
    except ZeroDivisionError:
        roundModifier = 1
    points = 0
    malus = 1.0
    for game in user['total_games']:
        if game['gameResult'] == 2:
            points += 3 * malus
            malus = 1.0
        else:
            if game['gameResult'] == 1:
                points += 1 * malus
            else:
                malus = 0.9
        performance[game['gameResult']] += 1
    finalPoints = points
    return finalPoints * playerModifier * roundModifier


def newTournament(tor):
    finished = tor['ended']
    if finished:
        uri = current_app.config["BCP_API_EVENT_NEW"].replace("####event####", tor['id'])
    else:
        uri = current_app.config["BCP_API_EVENT_NEW"].replace("####event####", tor['id'])
    response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
    users = json.loads(response.text)
    tor = manageTournament(tor)
    if tor:
        if tor.isTeam:
            # manageTeams(tor)
            manageUsers(tor, users)
        else:
            manageUsers(tor, users)
        if finished:
            result = updateStats()
            return Tournament.query.filter_by(id=tor.id).first(), result.status_code
        return Tournament.query.filter_by(id=tor.id).first(), 200
    return tor, 400


def manageTournament(info):
    isTeamTournament = info['teamEvent']
    city = City.query.filter_by(name=current_app.config["CITIES"][info['zip'][0:2]]).first()  #info['zip'][0:2]
    try:
        if 'formatted_address' in info.keys():
            location = info['formatted_address']
        else:
            location = info['formatted'] + ' ' + info['streetNum'] + ' - ' + info['city']
    except KeyError:
        location = city.name
    try:
        players = info['totalPlayers'] - info['droppedPlayers']
    except KeyError:
        players = info['queryNumPlayers']
    except:
        return None
    current_app.config['database'].session.add(Tournament(
        bcpId=info['id'],
        bcpUri="https://www.bestcoastpairings.com/event/" + info['id'],
        imgUri=info['photoUrl'] if 'photoUrl' in info.keys() else current_app.config["IMAGE_DEFAULT"],
        name=info['name'].strip(),
        shortName=info['name'].replace(" ", "").lower(),
        city=city.id,
        address=location,
        conference=city.conference_id,
        isTeam=isTeamTournament,
        date=info['eventDate'].split("T")[0],
        totalPlayers=players,
        isFinished=info['ended'],
        rounds=info['numberOfRounds']
    ))
    current_app.config['database'].session.commit()
    return Tournament.query.filter_by(bcpId=info['id']).first()


def manageUsers(tor, users):
    if tor.isFinished:
        uri = current_app.config["BCP_API_USERS"].replace("####event####", tor.bcpId)
        response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
        users = json.loads(response.text)
    totalUsers = len(users['data'])
    for user in users['data']:
        usr = addUserFromTournament(user, tor)
        if not usr:
            # Skip this user if we couldn't add them
            continue
        fct = addFactionFromTournament(user)
        cl = addClubFromTournament(user, tor)
        tor.users.append(usr)
        usrTor = UserTournament.query.filter_by(userId=usr.id).filter_by(tournamentId=tor.id).first()
        if tor.isFinished:
            usrTor.position = user['placing']
            usrTor.opponents = user['opponentIds']
            usrTor.performance = json.dumps(user['total_games'])
            usrTor.won = len([gameRes['gameResult'] for gameRes in user['total_games'] if gameRes['gameResult'] == 2])
            usrTor.tied = len([gameRes['gameResult'] for gameRes in user['total_games'] if gameRes['gameResult'] == 1])
            usrTor.lost = len([gameRes['gameResult'] for gameRes in user['total_games'] if gameRes['gameResult'] == 0])
            usrTor.innerId = user['playerId']
            usrTor.ibericonScore = algorithm(user, totalUsers)

        if fct:
            if fct not in usr.factions:
                usr.factions.append(fct)
            usrTor.factionId = fct.id
        if cl:
            if cl not in usr.clubs:
                usr.clubs.append(cl)
            usrTor.clubId = cl.id
        current_app.config['database'].session.commit()
        
        # Actualizar la región del usuario basándose en donde más torneos ha jugado
        updateUserRegionByMostPlayedTournaments(usr.id)


def addUserFromTournament(usr, tor):
    # Get userId - handle different API response structures
    user_id = usr.get('userId') or usr.get('id')
    if not user_id:
        print(f"⚠️ Warning: User object missing userId/id: {usr.keys()}")
        return None
    
    if not User.query.filter_by(bcpId=user_id).first():
        uri = current_app.config["BCP_API_USER_DETAIL"].replace("####userId####", user_id)
        response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
        users = json.loads(response.text)
        imgUrl = current_app.config["IMAGE_DEFAULT"]
        if 'profileFileId' in users.keys():
            uri = current_app.config["BCP_API_USER_IMG"].replace("####img####", users['profileFileId'])
            response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
            img = json.loads(response.text)
            imgUrl = img['url']
        
        # Handle user name - could be nested or flat structure
        if 'user' in usr and usr['user']:
            first_name = usr['user'].get('firstName', '').strip()
            last_name = usr['user'].get('lastName', '').strip()
        else:
            first_name = usr.get('firstName', '').strip()
            last_name = usr.get('lastName', '').strip()
        
        current_app.config['database'].session.add(User(
            bcpId=user_id,
            bcpName=f"{first_name} {last_name}",
            conference=tor.conference,
            profilePic=imgUrl,
            city=tor.city,
            permissions=0,
            registered=False
        ))
        current_app.config['database'].session.commit()
    return User.query.filter_by(bcpId=user_id).first()


def addFactionFromTournament(fct):
    if fct['army']:
        if not Faction.query.filter_by(bcpId=fct['armyId']).first():
            current_app.config['database'].session.add(Faction(
                bcpId=fct['armyId'],
                name=fct['army']['name'].strip(),
                shortName=fct['army']['name'].replace(" ", "").lower()
            ))
            current_app.config['database'].session.commit()
    return Faction.query.filter_by(bcpId=fct['armyId']).first() if fct['army'] else None


def addClubFromTournament(te, tor):
    if te['team']:
        uri = current_app.config["BCP_API_TEAMS_DETAIL"].replace("####teamId####", te['teamId'])
        response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
        team = json.loads(response.text)
        imgUrl = current_app.config["IMAGE_DEFAULT"]
        if 'profileFileId' in team.keys():
            uri = current_app.config["BCP_API_USER_IMG"].replace("####img####", team['profileFileId'])
            response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
            img = json.loads(response.text)
            imgUrl = img['url']
            res = requests.get(imgUrl, stream=True)
            img = base64.b64encode(res.content)
            response = requests.post(current_app.config['IMAGE_BB_UPLOAD'],
                                     params={'key': current_app.config['IMAGE_BB_KEY']},
                                     data={'image': img})
            try:
                imgUrl = json.loads(response.text)['data']['url']
            except KeyError or JSONDecodeError:
                pass
        if not Club.query.filter_by(bcpId=te['teamId']).first():
            current_app.config['database'].session.add(Club(
                bcpId=te['teamId'],
                name=te['team']['name'].strip(),
                conference=tor.conference,
                profilePic=imgUrl,
                shortName=te['team']['name'].replace(" ", "").lower()
            ))
        current_app.config['database'].session.commit()
    return Club.query.filter_by(bcpId=te['teamId']).first() if te['team'] else None


def addTeamFromTournament(te, tor):
    teId = te['name'].replace(" ", "-").lower()
    if not Team.query.filter_by(bcpId=teId).first():
        current_app.config['database'].session.add(Team(
            bcpId=teId,
            name=te['name'].strip(),
            conference=tor.conference,
            shortName=te['name'].replace(" ", "").lower()
        ))
    current_app.config['database'].session.commit()
    return Team.query.filter_by(bcpId=teId).first()


def updateStats():
    # Actualizar regiones de todos los usuarios antes de actualizar estadísticas
    print("Actualizando regiones de usuarios basándose en torneos jugados...")
    from utils.user import updateAllUsersRegions
    updated_users = updateAllUsersRegions()
    print(f"Se actualizaron las regiones de {updated_users} usuarios")
    
    for usr in User.query.all():
        # User Faction Rates
        for fct in usr.factions:
            tournaments = UserTournament.query.filter_by(userId=usr.id).filter_by(factionId=fct.id).all()
            usrFct = UserFaction.query.filter_by(userId=usr.id).filter_by(factionId=fct.id).first()
            usrFct.won = 0
            usrFct.tied = 0
            usrFct.lost = 0
            for to in tournaments:
                if to.position:
                    usrFct.won += to.won
                    usrFct.tied += to.tied
                    usrFct.lost += to.lost
            try:
                usrFct.winRate = 100*usrFct.won / (usrFct.won + usrFct.tied + usrFct.lost)
            except ZeroDivisionError:
                usrFct.winRate = 0.0
        best = current_app.config['database'].session.query(UserTournament, Tournament).order_by(desc(UserTournament.ibericonScore)).filter(
            UserTournament.userId == usr.id).join(Tournament, Tournament.id == UserTournament.tournamentId).all()
        score = 0
        counter = 0
        won = 0
        tied = 0
        lost = 0
        for to in best:
            to.UserTournament.countingScore = False
            if counter < 5:
                score += to.UserTournament.ibericonScore
                to.UserTournament.countingScore = True
                counter += 1
            won += to.UserTournament.won
            tied += to.UserTournament.tied
            lost += to.UserTournament.lost
        usr.ibericonScore = score
        try:
            usr.winRate =100 * won / (won + tied + lost)
        except ZeroDivisionError:
            usr.winRate = 0
        for usrFct in UserFaction.query.filter_by(userId=usr.id).all():
            score = 0
            count = 0
            for t in best:
                if t.UserTournament.factionId == usrFct.factionId:
                    count += 1
                    score += t.UserTournament.ibericonScore
                if count == 4:
                    break
            usrFct.ibericonScore = score
        for usrCl in UserClub.query.filter_by(userId=usr.id).all():
            score = 0
            count = 0
            for t in best:
                if t.UserTournament.clubId == usrCl.clubId:
                    count += 1
                    score += t.UserTournament.ibericonScore
                if count == 3:
                    break
            usrCl.ibericonScore = score
    for tm in Team.query.all():
        best = current_app.config['database'].session.query(UserTournament, Tournament).order_by(desc(UserTournament.ibericonTeamScore)).filter(
            UserTournament.teamId == tm.id).join(Tournament, Tournament.id == UserTournament.tournamentId).all()
        tm.ibericonScore = sum([t.UserTournament.ibericonTeamScore for t in best[:4]]) / 3  # Team Players
    for cl in Club.query.all():
        clubScore = []
        for player in UserClub.query.filter_by(clubId=cl.id).all():
            for best in current_app.config['database'].session.query(UserTournament).order_by(desc(UserTournament.ibericonScore)).filter(
                    UserTournament.userId == player.userId).limit(3).all():
                clubScore.append(best.ibericonScore)
        clubScore.sort(reverse=True)
        cl.ibericonScore = sum(clubScore[:10])
    # Faction Rates
    totalPicks = sum([t.totalPlayers for t in Tournament.query.filter_by(isFinished=True).all()])
    for fct in Faction.query.all():
        totalFactionPicks = UserTournament.query.filter_by(factionId=fct.id).all()
        try:
            fct.pickRate = 100 * len(totalFactionPicks) / totalPicks
        except ZeroDivisionError:
            fct.pickRate = 0
        for uf in totalFactionPicks:
            fct.won += uf.won
            fct.tied += uf.tied
            fct.lost += uf.lost
        try:
            fct.winRate = 100* fct.won / (fct.won + fct.tied + fct.lost)
        except ZeroDivisionError:
            fct.winRate = 0
    current_app.config['database'].session.commit()
    return jsonify({
        "status": 200,
        "message": "Ok"
    })


def updateAlgorithm():
    for tor in Tournament.query.all():
        if tor.isFinished:
            uri = current_app.config["BCP_API_USERS"].replace("####event####", tor.bcpId)
            response = requests.get(uri, headers=current_app.config["BCP_API_HEADERS"])
            info = json.loads(response.text)
            totalUsers = len(info['data'])
            for user in info['data']:
                try:
                    user_id = user.get('userId') or user.get('id')
                    if not user_id:
                        continue
                    usr = User.query.filter_by(bcpId=user_id).first()
                    if not usr:
                        continue
                    usrTor = UserTournament.query.filter_by(userId=usr.id).filter_by(tournamentId=tor.id).first()
                    if not usrTor:
                        continue
                    usrTor.position = user['placing']
                    usrTor.performance = json.dumps(user['total_games'])
                    usrTor.ibericonScore = algorithm(user, totalUsers)
                    current_app.config['database'].session.commit()
                except:
                    print(tor.name)
                    print(user)
            print(tor.name, 'OK')
    _ = updateStats()
    return jsonify({
        "status": 200,
        "message": "Ok"
    })


def deleteTournament(tor):
    UserTournament.query.filter_by(tournamentId=tor.id).delete()
    current_app.config['database'].session.delete(Tournament.query.filter_by(id=tor.id).first())
    current_app.config['database'].session.commit()
    _ = updateStats()
    return jsonify({
        "status": 200,
        "message": "Ok"
    })


def updateThings(form):
    current_app.config['MONEY'] = form['pasta'].replace('€', '') if 'pasta' in form.keys() else current_app.config['MONEY']
    current_app.config['PERCENTAGE'] = form['porcentaje'].replace('%', '') if 'porcentaje' in form.keys() else current_app.config['PERCENTAGE']
    with open("secret/config.json", 'r') as conf:
        config = json.load(conf)
        conf.close()
    config['money'] = current_app.config['MONEY']
    config['percentage'] = current_app.config['PERCENTAGE']
    with open("secret/config.json", 'w') as conf:
        json.dump(config, conf, indent=4)
        conf.close()
    return make_response("OK", 200)


def resetUser(userEmail):
    u = User.query.filter_by(bcpMail=userEmail).first()
    if u:
        u.bcpMail = None
        u.infoMail = None
        u.password = None
        u.registered = False
        current_app.config['database'].session.commit()
        return 200
    return 404
