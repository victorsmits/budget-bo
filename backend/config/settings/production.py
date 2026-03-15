from .base import *  # noqa

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Serve static files via Django in production using whitenoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Add whitenoise middleware at the top
MIDDLEWARE.insert(0, 'whitenoise.middleware.WhiteNoiseMiddleware')
