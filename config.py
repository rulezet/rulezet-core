import os

from dotenv import load_dotenv


class Config:
    load_dotenv()

    SECRET_KEY = os.environ.get('SECRET_KEY')

    FLASK_URL = os.environ.get('FLASK_URL', '127.0.0.1')
    FLASK_PORT = int(os.environ.get('FLASK_PORT', 7009))
    INSTANCE_PUBLIC_URL  = os.environ.get('INSTANCE_PUBLIC_URL')   # e.g. https://myinstance.example.com
    IS_OFFICIAL_INSTANCE = os.environ.get('IS_OFFICIAL_INSTANCE', 'false').lower() == 'true'

    MAIL_SERVER   = os.environ.get('MAIL_SERVER',   'smtp.gmail.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS',  'true').lower() == 'true'
    MAIL_USE_SSL  = os.environ.get('MAIL_USE_SSL',  'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME', ''))
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
   
    



class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql:///rulezet')
    SESSION_COOKIE_NAME = os.environ.get('SESSION_COOKIE_NAME', 'session')

    

    SESSION_TYPE = "sqlalchemy"
    SESSION_SQLALCHEMY_TABLE = "flask_sessions"
    
    @classmethod
    def init_app(cls, app):
        print('THIS APP IS IN DEBUG MODE. YOU SHOULD NOT SEE THIS IN PRODUCTION.')

class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "testing-secret-key-do-not-use-in-production"
    SQLALCHEMY_DATABASE_URI = "sqlite:///rulezet-test.sqlite"
    WTF_CSRF_ENABLED = False

    
    SESSION_TYPE = "filesystem" # else error with session

    @classmethod
    def init_app(cls, app):
        print('THIS APP IS IN TESTING MODE. YOU SHOULD NOT SEE THIS IN PRODUCTION.')

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "postgresql:///rulezet" 
    SESSION_TYPE = "sqlalchemy"
    SESSION_SQLALCHEMY_TABLE = "flask_sessions"

    @classmethod
    def init_app(cls, app):
        print('APP IS IN PRODUCTION MODE.')




config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
