import subprocess
import sys
import os
import time
import threading
import db_setup

def run_streamlit():
    print("Starting Streamlit app...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])

def run_fastapi():
    print("Starting FastAPI server...")
    subprocess.run([sys.executable, "api.py"])

if __name__ == "__main__":
    # Setup database first
    print("Setting up database...")
    db_setup.setup_database()
    
    # Start FastAPI in a separate thread
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.daemon = True
    fastapi_thread.start()
    
    # Give FastAPI server time to start up
    time.sleep(2)
    
    # Run Streamlit in the main thread
    run_streamlit()