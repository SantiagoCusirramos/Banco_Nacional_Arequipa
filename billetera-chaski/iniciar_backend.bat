@echo off
title Chaski - API
cd /d "%~dp0backend"
if not exist node_modules call npm install
echo Iniciando la API de Chaski... (deja esta ventana abierta)
call npm start
pause
