import os
import sys

# Add the directory containing your app to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as application

