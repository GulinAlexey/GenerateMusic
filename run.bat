if "%~1" == "" (start "" /min "%comspec%" /c "%~f0" any_word & exit /b)
venv\Scripts\python.exe GenerateMusic.py