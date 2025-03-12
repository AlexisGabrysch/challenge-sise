import streamlit as st
import db_setup
import os
import subprocess
import sys
import threading
import time

# Set flag that we're running in cloud
os.environ["STREAMLIT_CLOUD"] = "true"

def run_fastapi():
    print("Starting FastAPI server...")
    env = os.environ.copy()
    env["PORT"] = "8888"  # Use a different port from Streamlit
    subprocess.Popen([sys.executable, "api.py"], env=env)

# Setup database
db_setup.setup_database()

# Start FastAPI in a separate process
thread = threading.Thread(target=run_fastapi)
thread.daemon = True
thread.start()

# Give FastAPI time to start
time.sleep(2)

# Import and run the Streamlit app
import app
app.main()