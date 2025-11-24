@echo off
title Bus Management System
echo Starting Bus Management System...
echo.
echo The application will open in your web browser.
echo DO NOT CLOSE THIS WINDOW!
echo.

REM Navigate to the folder where app.py is located (optional if bat is in the same folder)
cd "C:\Users\ADMIN\Desktop\Accounts System"

REM Run Streamlit on all network interfaces on port 8501
python -m streamlit run app.py --server.address=192.168.100.31 --server.port=8501

pause
