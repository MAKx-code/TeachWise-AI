import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Production: set FLASK_ENV=production (or omit) and PORT in environment.
    # Debug mode is only enabled when FLASK_DEBUG=1 is explicitly set.
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    port = int(os.getenv('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port)
