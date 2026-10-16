@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale Python 3.10+ e marque Add Python to PATH.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
where ffmpeg >nul 2>nul
if errorlevel 1 echo AVISO: FFmpeg nao encontrado. A interface abre, mas a exportacao MP4 fica indisponivel.
python -m streamlit run app.py
pause
