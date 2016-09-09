@echo off

rem To ensure compatibility with both 32bit and 64bit end users, building the executable requires that Anaconda 32 bit is installed.
rem The script assumes that two versions of anaconda are installed in side-by-side folders 
rem e.g C:\Users\UserName\AppData\Local\Continuum\Anaconda32 and C:\Users\UserName\AppData\Local\Continuum\Anaconda64
rem when installing Anaconda32 parallel to Anaconda32 select the following options:
rem 'use as default python' = No
rem 'add to PATH' = No
rem this script with temporarily redirect the PATH variable to the 32 anaconda installation

rem Remember to install xlutils in Anaconda32 (conda install xlutils)

rem Note: during an issue with PyInstaller's treatment of numpy's dependencies you may need to install 
rem       pyinstall using the following specific commit:
rem       https://github.com/pyinstaller/pyinstaller/archive/13458ec7d74e9665cae14a8a91da7adde5db66e8.zip
rem       see this link for more info https://github.com/pyinstaller/pyinstaller/issues/1881

echo Reading settings.ini

rem %0 is the script file name (with path), %~0 removes the surrounding " " ("%~0" == %0)
rem Adding dp returns the drive and path to the file, instead of the file name itself
set INIFILE="%~dp0settings.ini"
 
call:getvalue %INIFILE% "gitfolder" GitFolder
call:getvalue %INIFILE% "helpdoc" HelpDoc
call:getvalue %INIFILE% "version" Version
call:getvalue %INIFILE% "sevenZipPath" SevenZipPath
call:getvalue %INIFILE% "anacondaFolder32" AnacondaFolder32
call:getvalue %INIFILE% "anacondaFolder64" AnacondaFolder64

echo GitFolder: %gitfolder%
echo HelpDoc: %helpdoc%
echo Version: %version%
echo SevenZipPath: %sevenZipPath%
echo AnacondaFolder32: %anacondaFolder32%
echo AnacondaFolder64: %anacondaFolder64%

IF NOT EXIST %anacondaFolder32% (
echo "Anaconda32 Folder Does Not Exist (%anacondaFolder32%)"
goto:eof
) else (
echo "Anaconda32 Folder Found (%anacondaFolder32%)"
)

IF NOT EXIST %anacondaFolder64% (
echo "Anaconda64 Folder Does Not Exists (%anacondaFolder64%)"
goto:eof
) else (
echo "Anaconda64 Folder Found (%anacondaFolder64%)"
)

IF NOT EXIST %anacondaFolder64% (
echo "Anaconda64 Folder Does Not Exists (%anacondaFolder64%)"
goto:eof
) else (
echo "Anaconda64 Folder Found (%anacondaFolder64%)"
)

echo Set path to 32 bit Anaconda32 (for duration of this BAT script)
set PATH=%PATH:Anaconda64=Anaconda32%
echo %Path%

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

rem https://github.com/pyinstaller/pyinstaller/issues/1584
echo "TKInter workaround"

set tkFolder=%anacondaFolder32%\Lib\lib-tk
set guiFolder=%gitfolder%\pcwg\gui
set guiBackUpFolder=%gitfolder%\pcwg\gui_back_up

if exist %guiBackUpFolder% rmdir /s /q %guiBackUpFolder%

mkdir %guiBackUpFolder%

copy %guiFolder%\*.* %guiBackUpFolder%

if not exist %guiBackUpFolder% (
	echo Coult not create gui back up folder.
	goto:eof
)

rem workaround: copy tk code directly into gui folder
copy %tkFolder%\*.py %guiFolder%

echo building executable

mkdir %tool%
mkdir %tool%\Resources

copy %gitfolder%\Resources\logo.ico %tool%\Resources\logo.ico

PyInstaller --onefile --windowed --icon="%tool%\Resources\logo.ico" %toolpath%

xcopy /s /Y /q dist\%tool%.exe %tool%\

rem restore original gui code
rmdir /s /q %guiFolder%
mkdir %guiFolder%
copy %guiBackUpFolder%\*.* %guiFolder%

if exist %guiFolder%\root.py rmdir /s /q %guiBackUpFolder%

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
copy "%gitfolder%\Share_1_template.xls" "%tool%\Share_1_template.xls"
copy "%gitfolder%\Share_1_template.xls" "%tool%\Share_1_template.xls"

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