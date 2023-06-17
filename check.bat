@echo off

echo Running black...
call black .

echo.

echo Running flake8...
call flake8 . --exclude venv/ --ignore E501
IF %ERRORLEVEL% EQU 0 echo Success - no issues found

echo.

echo Running mypy...
call mypy . --ignore-missing-imports