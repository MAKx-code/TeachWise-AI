# Procfile — Railway, Heroku, and Gunicorn-aware platforms
# Seeds the CS201 synthetic dataset (idempotent) then starts Gunicorn.
# seed_academic.py is a no-op if data already exists, safe on every start.
web: python seed_academic.py && gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
