@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  Cyber-Vault - Orchestrateur de Tests
echo ============================================

REM --- 1. Pytest (Backend) ---
echo.
echo [1/4] Pytest - Tests unitaires Backend...
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
pytest tests/ -v --tb=short
if errorlevel 1 (
    echo [ERREUR] Les tests backend ont echoue.
    exit /b 1
)
echo [OK] Backend tests passes.

REM --- 2. Seed de la base de test ---
echo.
echo [2/4] Seed - Injection des donnees de test...
cd /d "%~dp0"
python scripts/seed_test_db.py
if errorlevel 1 (
    echo [ERREUR] Le seed a echoue.
    exit /b 1
)
echo [OK] Base de test prete.

REM --- 3. Vitest (Frontend) ---
echo.
echo [3/4] Vitest - Tests unitaires Frontend...
cd /d "%~dp0frontend"
call npm run test
if errorlevel 1 (
    echo [ERREUR] Les tests frontend ont echoue.
    exit /b 1
)
echo [OK] Frontend tests passes.

REM --- 4. Playwright (E2E) ---
echo.
echo [4/4] Playwright - Tests E2E...
call npx playwright test
if errorlevel 1 (
    echo [ERREUR] Les tests E2E ont echoue.
    exit /b 1
)
echo [OK] Tests E2E passes.

echo.
echo ============================================
echo  Tous les tests sont passes avec succes !
echo ============================================
exit /b 0
