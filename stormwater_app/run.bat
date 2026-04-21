@echo off
cd /d "%~dp0"
title Stormwater Report Generator

python launch.py
if %ERRORLEVEL% NEQ 0 pause
