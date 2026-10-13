@echo off
rem Interprete de Run Python File: python del servicio python_packages.
"C:\Users\ARREDOER\AppData\Local\miniconda3\python.exe" "C:\dev\python\PLANOL-generic_python_packages\.vscode\run_dev.py" --service python_packages --container-root /project --host-root "%~dp0.." --compose-file "%~dp0..\docker-compose.yml" --docker-arg --no-deps --docker-arg -w --docker-arg /project -- %*
exit /b %ERRORLEVEL%
