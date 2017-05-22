@echo off

echo Reading settings.ini

rem %0 is the script file name (with path), %~0 removes the surrounding " " ("%~0" == %0)
rem Adding dp returns the drive and path to the file, instead of the file name itself
set INIFILE="%~dp0settings.ini"
 
call:getvalue %INIFILE% "gitfolder" GitFolder
call:getvalue %INIFILE% "helpdoc" HelpDoc
call:getvalue %INIFILE% "version" Version
call:getvalue %INIFILE% "sevenZipPath" SevenZipPath

echo GitFolder: %gitfolder%
echo HelpDoc: %helpdoc%
echo Version: %version%
echo SevenZipPath: %sevenZipPath%

set tool=pcwg_tool
set extractor=extractor

set toolpath=%gitfolder%\%tool%.py
set versionpath=%gitfolder%\version.py
set extractorpath=%gitfolder%\%extractor%.py

set outputfolder=%workingfolder%\%tool%
set outputZipPath=%workingfolder%\%tool%.zip
set versionZip=%tool%-%version%.zip

echo Checking version in %versionpath%
findstr /c:"version = ""%version%""" "%versionpath%" 

if %errorlevel%==0 (
echo "Correct version (%version%) detected in %versionpath%"
) else (
echo "Error: correct version (%version%) not detected in %versionpath%"
goto:eof
)

echo removing old files and folders
 
if exist "%versionZip%" del "%versionZip%"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%tool%" rmdir /s /q "%tool%"

echo building executable

mkdir %tool%
mkdir %tool%\Resources

copy %gitfolder%\Resources\logo.ico %tool%\Resources\logo.ico

PyInstaller --onefile --windowed --icon="%tool%\Resources\logo.ico" %toolpath%

xcopy /s /Y /q dist\%tool%.exe %tool%\

echo building launcher
PyInstaller --onefile %extractorpath%
xcopy /s /Y /q dist\%extractor%.exe %tool%\

echo copying ancialliary files

mkdir %tool%\Data\

copy %gitfolder%\Data\*.xml %tool%\Data\
copy %gitfolder%\Data\*.dat %tool%\Data\

copy "%gitfolder%\%helpdoc%" "%tool%\%helpdoc%"
copy "%gitfolder%\LICENSE" "%tool%\LICENSE"
copy "%gitfolder%\README.md" "%tool%\README.md"
copy "%gitfolder%\Share_X_template.xls" "%tool%\Share_X_template.xls"

echo zipping

"%sevenZipPath%" a %versionZip% %tool%

echo Cleaning up

rmdir /s /q %tool%
rmdir /s /q build
rmdir /s /q dist

echo Done, build avialable at %versionZip%

goto:eof

:getvalue
 rem This function reads a value from an INI file and stored it in a variable
 rem %1 = name of ini file to search in.
 rem %2 = search term to look for
 rem %3 = variable to place search result
FOR /F "eol=; eol=[ tokens=1,2* delims==" %%i in ('findstr /b /l /i %~2= %1') DO set %~3=%%~j
goto:eof

pause