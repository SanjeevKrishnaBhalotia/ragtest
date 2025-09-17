@echo off
REM LocalRAG Complete Installation Script for Windows with Laragon
REM This script sets up the complete LocalRAG environment with all features

echo ========================================
echo LocalRAG - Secure Local AI Assistant
echo Complete Installation Script for Windows
echo ========================================
echo.

REM Check if Laragon is installed
if not exist "C:\laragon\bin\php" (
    echo ERROR: Laragon not found at C:\laragon
    echo Please install Laragon first from https://laragon.org
    echo.
    pause
    exit /b 1
)

echo [1/8] Laragon detected at C:\laragon
echo.

REM Navigate to Laragon www directory
cd /d "C:\laragon\www"

REM Create LocalRAG directory
if not exist "LocalRAG" (
    mkdir LocalRAG
    echo [2/8] Created LocalRAG directory
) else (
    echo [2/8] LocalRAG directory already exists
)

cd LocalRAG

REM Copy application files (assuming they're in the same directory as this script)
echo [3/8] Copying application files...
xcopy /E /I /Q "%~dp0LocalRAG_assets\*" .

REM Check if Python is available in Laragon
if not exist "C:\laragon\bin\python" (
    echo [4/8] Python not found in Laragon. Please add Python to Laragon first.
    echo You can download Python via Laragon Quick Add menu.
    echo.
    pause
    exit /b 1
) else (
    echo [4/8] Python found in Laragon
)

REM Set up Python path
set PATH=C:\laragon\bin\python;C:\laragon\bin\python\Scripts;%PATH%

REM Install uv package manager
echo [5/8] Installing uv package manager...
python -m pip install uv
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install uv package manager
    pause
    exit /b 1
)

REM Create virtual environment using uv
echo [6/8] Creating virtual environment...
uv venv venv
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo [7/8] Installing Python dependencies (this may take 3-5 minutes)...
uv pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install dependencies
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

REM Create run script
echo [8/8] Creating run script and desktop shortcut...
(
echo @echo off
echo echo Starting LocalRAG - Secure Local AI Assistant...
echo cd /d "C:\laragon\www\LocalRAG"
echo call venv\Scripts\activate.bat
echo python app\main.py
echo pause
) > run_localrag.bat

REM Create desktop shortcut
echo Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), 'LocalRAG.lnk')); $Shortcut.TargetPath = '%CD%\run_localrag.bat'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.Description = 'LocalRAG - Secure Local AI Assistant'; $Shortcut.Save()"

echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo Your secure LocalRAG system is now ready!
echo.
echo Next steps:
echo 1. Launch LocalRAG using the desktop shortcut
echo 2. Create a master password (WRITE IT DOWN!)
echo 3. Download AI models from the Models tab
echo 4. Create your first knowledge base
echo 5. Import documents and start querying
echo.
echo Features installed:
echo - Query Assistant with real-time feedback
echo - Multi-database management with AES-256 encryption
echo - Swappable AI models (Llama 3.2, Phi-3)
echo - Prompt Workshop with chaining support
echo - Document processing (PDF, DOCX, CSV, Excel)
echo - HIPAA-compliant security and audit logging
echo.
echo Installation location: C:\laragon\www\LocalRAG
echo.
pause
