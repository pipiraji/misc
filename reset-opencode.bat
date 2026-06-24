@echo off
chcp 65001 >nul
title OpenCode Full Reset

echo ⚠ OpenCode Full Reset
echo 이 스크립트는 모든 opencode 관련 데이터를 삭제합니다.
set /p confirm="계속하시겠습니까? (y/N): "
if /i not "%confirm%"=="y" (
  echo 취소됨.
  pause
  exit /b
)

:: 1. Global config
if exist "%USERPROFILE%\.config\opencode" (
  rmdir /s /q "%USERPROFILE%\.config\opencode"
  echo ✓ ~\.config\opencode 삭제됨
)

:: 2. State
if exist "%USERPROFILE%\.local\state\opencode" (
  rmdir /s /q "%USERPROFILE%\.local\state\opencode"
  echo ✓ ~\.local\state\opencode 삭제됨
)

:: 3. Share data (DB, logs)
if exist "%USERPROFILE%\.local\share\opencode" (
  rmdir /s /q "%USERPROFILE%\.local\share\opencode"
  echo ✓ ~\.local\share\opencode 삭제됨
)

:: 4. Cache
if exist "%USERPROFILE%\.cache\opencode" (
  rmdir /s /q "%USERPROFILE%\.cache\opencode"
  echo ✓ ~\.cache\opencode 삭제됨
)

:: 5. Project node_modules
if exist "%~dp0package.json" (
  if exist "%~dp0node_modules\opencode-ai" (
    rmdir /s /q "%~dp0node_modules\opencode-ai"
    echo ✓ node_modules\opencode-ai 삭제됨
  )
  if exist "%~dp0node_modules\oh-my-opencode" (
    rmdir /s /q "%~dp0node_modules\oh-my-opencode"
    echo ✓ node_modules\oh-my-opencode 삭제됨
  )
  if exist "%~dp0node_modules\oh-my-openagent" (
    rmdir /s /q "%~dp0node_modules\oh-my-openagent"
    echo ✓ node_modules\oh-my-openagent 삭제됨
  )
)

echo ✅ OpenCode 전체 리셋 완료.
echo 재설치하려면: npm install
pause
