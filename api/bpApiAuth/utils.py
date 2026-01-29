from utils.auth import userSignup, userLogin, getUserOnly, resetUserInfo


def userSignupApi(database, form):
    apiResult = userSignup({"email": form.email, "password": form.password})
    return apiResult


def userLoginApi(form):
    apiResult = userLogin({"email": form.mail, "password": form.password})
    return apiResult


def getUserOnlyApi(pl):
    return getUserOnly(pl)


def resetUserInfoApi():
    apiResult = resetUserInfo()
    return apiResult
