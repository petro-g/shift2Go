import os
from dotenv import load_dotenv
from dotenv.main import find_dotenv

load_dotenv(find_dotenv('.env'))

PROJECT_NAME = "shift2go"

SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL","postgresql://shift2go_user:password@postgres:5432/shift2go_user")
# SQLALCHEMY_DATABASE_URI = "postgresql://shift2go_test:password@127.0.0.1:5432/my_data"
"postgresql://postgres:aMbROISeStiVIN@database-1.cxnpwdvrh2yh.us-east-2.rds.amazonaws.com:5432/postgres"

API_V1_STR = os.getenv("API_V1_STR")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "3000000"))
SHIFT2GO_PERCENTAGE = int(os.getenv("SHIFT2GO_PERCENTAGE", "45"))

EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = bool(os.getenv('EMAIL_USE_TLS'))
EMAIL_USE_SSL = bool(os.getenv('EMAIL_USE_SSL'))

SENGRID_API_KEY = os.getenv('SENGRID_API_KEY')
DOMAIN = os.getenv('DOMAIN')
FRONTEND_DOMAIN = os.getenv('FRONTEND_DOMAIN', 'http://3.130.10.151')
BACKEND_DOMAIN = os.getenv('BACKEND_DOMAIN', 'http://3.143.59.184')
DOMAIN_LOCAL = os.getenv('DOMAIN_LOCAL')

LOCAL_HOST = os.getenv("LOCAL_HOST")
LOCAL_PORT = int(os.getenv("LOCAL_PORT", "80"))
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

PAGE_LIMIT = int(os.getenv('PAGE_LIMIT', '50'))

MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY', '92c0ec5fc0abe0de2f37f0dc0d957850-443ec20e-2b739a5b')
MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN', 'iosinstall.com')