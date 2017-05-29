"""
Django settings for shop project Django 1.11.1.
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = '87hai)pey)ay+z=^@5-oi3fv4gjo99ns2la9tttaqod@ijv!x1'
DEBUG = True
INSTALLED_APPS = ['shop']
ROOT_URLCONF = 'shop.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgres',
        'USER': 'shop',
        'PASSWORD': 'shop',
        'HOST': 'localhost',
        'PORT': '25432'
    }
}

TIME_ZONE = 'UTC'
USE_TZ = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django.db.models': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}
