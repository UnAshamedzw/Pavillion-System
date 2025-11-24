"""
run_app.py - Launcher script for Bus Management System EXE
This script properly launches Streamlit when compiled to EXE
"""

import sys
import os
from streamlit.web import cli as stcli

def main():
    """Launch the Streamlit application"""
    
    # Get the directory where the script is located
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        application_path = sys._MEIPASS
    else:
        # Running as script
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    # Change to application directory
    os.chdir(application_path)
    
    # Set the main script path
    main_script = os.path.join(application_path, "app.py")
    
    # Launch Streamlit
    sys.argv = [
        "streamlit",
        "run",
        main_script,
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.port=8501",
        "--server.address=localhost"
    ]
    
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
