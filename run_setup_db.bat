@echo off
REM Setup the MySQL database for the InS_management_system project.
REM Adjust MySQL credentials below if needed.

SET MYSQL_USER=root
SET MYSQL_PASSWORD=123456
SET MYSQL_DB=ins_db

echo Creating database %MYSQL_DB% if not exists...
mysql -u %MYSQL_USER% -p%MYSQL_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS %MYSQL_DB%;"
if ERRORLEVEL 1 (
    echo Failed to connect to MySQL. Please check your MySQL installation and credentials.
    pause
    exit /b 1
)

echo Loading schema...
mysql -u %MYSQL_USER% -p%MYSQL_PASSWORD% %MYSQL_DB% < "database\setup.sql"
if ERRORLEVEL 1 (
    echo Failed to load schema from database\setup.sql
    pause
    exit /b 1
)

echo Loading sample data...
mysql -u %MYSQL_USER% -p%MYSQL_PASSWORD% %MYSQL_DB% < "database\samples.sql"
if ERRORLEVEL 1 (
    echo Failed to load sample data from database\samples.sql
    pause
    exit /b 1
)

echo Database setup completed successfully.
pause
