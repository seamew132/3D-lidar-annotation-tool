@echo off
title ADO Web Tool Dual Server Launcher (Ports 5000 & 5050)
color 0A

echo ========================================================
echo     ADO Web Annotation Tool + FastCheck 3D Viewer
echo ========================================================
echo.
echo [1/2] Dang khoi chay Standalone FastCheck Server tai http://localhost:5050/ ...
start /B "" "C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe" "%~dp0fast_check_app.py"

echo [2/2] Dang khoi chay Main Web Annotation Server tai http://localhost:5000/ ...
echo.
echo Ca 2 Server deu dang chay song song trong cung 1 bang CMD nay!
echo Trinh duyet se tu dong mo 2 tab cho ca 2 cong cu!
echo.

"C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe" "%~dp0web_app\server.py"

pause
