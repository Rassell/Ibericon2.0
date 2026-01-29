from flask import current_app, jsonify
from sqlalchemy import desc
from database import (User, UserTournament, Tournament, City,
                      Conference, Faction, Club,
                      UserFaction, UserClub)


def getUsers(query, qty=0):
    conference = Conference.query.filter_by(name=query.conference).first()
    result = (current_app.config['database'].session.query(User, City)
              .order_by(desc(User.ibericonScore))
              .filter(User.bcpId != "0000000000")
              .filter(User.conference == conference.id if conference else User.conference != None)
              .join(City, City.id == User.city)
              .all())
    return jsonify({
        "status": 200,
        "message": "Successful",
        "data": [
            {
                'id': user.bcpId,
                'name': user.bcpName,
                'conference': {
                    "id": city.conference.id,
                    "name": city.conference.name
                },
                'city': {
                    "id": city.id,
                    "name": city.name
                },
                'score': user.ibericonScore,
                'profilePic': user.profilePic,
                'isClassified': user.isClassified
            }
            for user, city in result[0:qty-1]]
    })


def getUser(query):
    userBd = (current_app.config["database"].session.query(User, City)
            .filter(User.bcpId == query.bcpId)
            .join(City, City.id == User.city)
            .first())
    userDetail = (current_app.config["database"]
            .session.query(User, UserFaction, UserClub, Faction, Club)
            .filter(User.bcpId == query.bcpId)
            .join(UserFaction, UserFaction.userId == User.id)
            .join(UserClub, UserClub.userId == User.id)
            .join(Faction, Faction.id == UserFaction.factionId)
            .join(Club, Club.id == UserClub.clubId)
            .all())
    tournaments = (current_app.config["database"].session
                    .query(UserTournament, Tournament, City, Faction, Club)
                    .join(Tournament, Tournament.id == UserTournament.tournamentId)
                    .join(City, City.id == Tournament.city)
                    .join(Faction, Faction.id == UserTournament.factionId)
                    .join(Club, Club.id == UserTournament.clubId)
                    .filter(UserTournament.userId == userBd.User.id)
                    .order_by(desc(UserTournament.ibericonScore))
                    .all())
    factAux = []
    factions = []
    clubAux = []
    clubs = []
    for user, userFaction, userClub, faction, club in userDetail:
        if faction.name not in factAux:
            factAux.append(faction.name)
            factions.append({
                "id": faction.bcpId,
                "name": faction.name,
                "score": userFaction.ibericonScore
            })
        if club.name not in clubAux:
            clubAux.append(club.name)
            clubs.append({
                "id": club.bcpId,
                "name": club.name,
                "score": userClub.ibericonScore,
                "pic": club.profilePic
            })

    return jsonify({
        "status": 200,
        "message": "Successful",
        "data":
            {
                'id': userBd.User.bcpId,
                'name': userBd.User.bcpName,
                'conference': {
                    "id": userBd.City.conference.id,
                    "name": userBd.City.conference.name
                },
                'city': {
                    "id": userBd.City.id,
                    "name": userBd.City.name
                },
                'score': userBd.User.ibericonScore,
                'profilePic': userBd.User.profilePic,
                'isClassified': userBd.User.isClassified,
                'winRate': userBd.User.winRate,
                'factions': factions,
                'teams': [
                    {
                        "id": team.bcpId,
                        "name": team.name
                    }
                for team in userBd.User.teams],
                'clubs': clubs,
                'tournaments': [
                    {
                        "id": tournament.bcpId,
                        "uri": tournament.bcpUri,
                        "name": tournament.name,
                        "city": {
                            "id": city.id,
                            "name": city.name
                        },
                        "conference": {
                            "id": city.conference.id,
                            "name": city.conference.name
                        },
                        "date": tournament.date,
                        "isFinished": tournament.isFinished,
                        "isTeam": tournament.isTeam,
                        "rounds": tournament.rounds,
                        "totalPlayers": tournament.totalPlayers,
                        "score": userTournament.ibericonScore,
                        "isCounting": userTournament.countingScore,
                        "innerId": userTournament.innerId,
                        "position": userTournament.position,
                        "performance": userTournament.performance,
                        "won": userTournament.won,
                        "tied": userTournament.tied,
                        "lost": userTournament.lost,
                        "faction": {
                            "id": faction.bcpId,
                            "name": faction.name
                        } if faction else {},
                        "club": {
                            "id": club.bcpId,
                            "name": club.name
                        } if club else {},
                    }
                for userTournament, tournament, city, faction, club in tournaments]
            }
        }
    )


def getUserOnly(pl):
    return User.query.filter_by(bcpId=pl).first()
