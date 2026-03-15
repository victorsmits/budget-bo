from .base import *  # noqa

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Serve static files via Django in production
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
