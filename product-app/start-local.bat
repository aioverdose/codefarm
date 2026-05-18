@echo off
setlocal
set "BUNDLE_ROOT=%~dp0"
set "CODEFARM_HOME=%BUNDLE_ROOT%runtime\codefarm"
set "CODEFARM_API_URL=http://127.0.0.1:8765"
set "CODEFARM_FUNCTIONS_TOKEN=local-functions-token"
set "HOSTNAME=127.0.0.1"
set "PORT=3000"
cd /d "%BUNDLE_ROOT%app"
echo Starting Local Agent App Factory at http://127.0.0.1:3000
node server.js