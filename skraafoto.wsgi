import sys
import os

# Add your project directory to the sys.path
sys.path.insert(0, '/var/www/html2')

# Activate the virtual environment
activate_this = '/var/www/html2/.venv/bin/activate_this.py'
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})

# Set the Flask app's environment variables
os.environ['FLASK_ENV'] = 'production'
os.environ['PYTHONUNBUFFERED'] = '1'

# Import the Flask app
from postgress_connector import app as application
