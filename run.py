import subprocess
import sys
import os
import time
import threading
import db_setup

# Determine if running in cloud environment or locally
IN_CLOUD = os.getenv("STREAMLIT_CLOUD", "") == "true"

def run_streamlit():
    print("Starting Streamlit app...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])

def run_fastapi():
    print("Starting FastAPI server...")
    # Use a different port in cloud environment
    env = os.environ.copy()
    if IN_CLOUD:
        env["PORT"] = "8888"  # Different from 8501 used by Streamlit 
    subprocess.run([sys.executable, "api.py"], env=env)

if __name__ == "__main__":
    # Setup database first
    print("Setting up database...")
    db_setup.setup_database()
    
    # In Streamlit Cloud, we don't want to start FastAPI this way
    # as it conflicts with the main app
    if not IN_CLOUD:
        # Start FastAPI in a separate thread
        fastapi_thread = threading.Thread(target=run_fastapi)
        fastapi_thread.daemon = True
        fastapi_thread.start()
        
        # Give FastAPI server time to start up
        time.sleep(2)
    
    # Run Streamlit in the main thread
    run_streamlit()