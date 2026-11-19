# Procfile — used by IBM Code Engine, Heroku, and Gunicorn-aware platforms
# Gunicorn is the production WSGI server (not Flask's built-in dev server).
# run:app → module run.py exposes the `app` Flask object.
web: gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
