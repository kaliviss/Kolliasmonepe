@echo off
:: -----------------------------
:: Πλήρης setup και εκκίνηση Dashboard
:: -----------------------------

:: 1️⃣ Ορισμός φακέλου του dashboard
SET DASHBOARD_FOLDER=C:\Users\kaliv\Desktop\Final
cd /d "%DASHBOARD_FOLDER%"

:: 2️⃣ Έλεγχος για Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python δεν βρέθηκε. Εγκατάστησε Python 3.11 ή νεότερη: https://www.python.org/downloads/
    pause
    exit /b
)

:: 3️⃣ Αναβάθμιση pip
python -m pip install --upgrade pip

:: 4️⃣ Εγκατάσταση απαιτούμενων πακέτων
python -m pip install --upgrade streamlit pandas matplotlib numpy scipy openpyxl

:: 5️⃣ Εκκίνηση Dashboard με Streamlit
echo Τρέχω το Dashboard...
streamlit run dashboard.py

pause