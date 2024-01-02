from fastapi import FastAPI
import fastapi
from starlette.responses import RedirectResponse
from modules import script_callbacks


def custom_logout(_, app: FastAPI):

    @app.get("/logout")
    def logout(request: fastapi.Request):
        response = RedirectResponse(url="/", status_code=302)
        response.delete_cookie(key=f"access-token")
        response.delete_cookie(key=f"access-token-unsecure")
        return response


script_callbacks.on_app_started(custom_logout)
