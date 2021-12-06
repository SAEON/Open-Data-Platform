import redis
from authlib.integrations.flask_client import OAuth
from flask import Flask
from flask_login import LoginManager, current_user
from sqlalchemy import select

from odp import ODPScope
from odp.config import config
from odp.db import Session
from odp.db.models import User, OAuth2Token

login_manager = LoginManager()
login_manager.login_view = 'hydra.login'

oauth = OAuth()


@login_manager.user_loader
def load_user(user_id):
    return Session.get(User, user_id)


def init_app(app: Flask):
    login_manager.init_app(app)
    cache = redis.Redis(
        host=config.REDIS.HOST,
        port=config.REDIS.PORT,
        db=config.REDIS.DB,
        decode_responses=True,
    )
    oauth.init_app(app, cache, fetch_token, update_token)
    oauth.register(
        name='hydra',
        access_token_url=f'{(hydra_url := config.HYDRA.PUBLIC.URL)}/oauth2/token',
        authorize_url=f'{hydra_url}/oauth2/auth',
        userinfo_endpoint=f'{hydra_url}/userinfo',
        client_id=config.ODP.UI.CLIENT_ID,
        client_secret=config.ODP.UI.CLIENT_SECRET,
        client_kwargs={'scope': ' '.join(['openid', 'offline'] + [s.value for s in ODPScope])},
    )


def fetch_token(hydra_name):
    return Session.get(OAuth2Token, current_user.id).dict()


def update_token(hydra_name, token, refresh_token=None, access_token=None):
    if refresh_token:
        token_model = Session.execute(
            select(OAuth2Token).
            where(OAuth2Token.refresh_token == refresh_token)
        ).scalar_one()
    elif access_token:
        token_model = Session.execute(
            select(OAuth2Token).
            where(OAuth2Token.access_token == access_token)
        ).scalar_one()
    else:
        return

    token_model.access_token = token.get('access_token')
    token_model.refresh_token = token.get('refresh_token')
    token_model.expires_at = token.get('expires_at')
    token_model.save()
