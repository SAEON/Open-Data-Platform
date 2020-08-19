import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('IDENTITY_FLASK_KEY')

    HYDRA_ADMIN_URL = os.getenv('HYDRA_ADMIN_URL')
    DATABASE_URL = os.getenv('DATABASE_URL')
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '25'))

    # number of seconds to remember a successful login
    HYDRA_LOGIN_EXPIRY = int(os.getenv('HYDRA_LOGIN_EXPIRY', '86400'))
