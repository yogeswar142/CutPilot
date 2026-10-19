@echo off
rem CutPilot - DaVinci Resolve Launcher with x64 Python Environment
rem Injects Python311-x64 into Resolve's process PATH so fuscript.exe loads python3.dll (x64) without modifying global PATH or breaking native ARM64 Python.
set "PYTHON3HOME=%LOCALAPPDATA%\Programs\Python\Python311-x64"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311-x64;%PATH%"
start "" "C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe" %*
