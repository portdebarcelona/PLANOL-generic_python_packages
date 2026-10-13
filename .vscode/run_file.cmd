@echo off
rem Run Python File de todas las carpetas. Elige el servicio por la ruta del fichero.
"C:\Users\ARREDOER\AppData\Local\miniconda3\python.exe" "C:\dev\python\PLANOL-generic_python_packages\.vscode\run_dev.py" %*
exit /b %ERRORLEVEL%
