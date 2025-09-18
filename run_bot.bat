@echo off
REM Setup script for captcha-bot
REM Install dependencies and run the bot

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Edit config.json if needed before running
python main.py
pause
