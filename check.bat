@echo off

echo Running black...
call black .
echo.

echo Running flake8...
call flake8 . --exclude venv/ --ignore E501