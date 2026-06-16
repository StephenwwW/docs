@echo off
:: =================================================================
:: 專案啟動器 v6.1 (防殘檔最終修正版)
:: 修正 echo 輸出殘留檔案問題 + 確保清理完全
:: =================================================================

:: 步驟 0: 設定環境
chcp 65001 >nul
TITLE 專案啟動器 v6.1 - VideoFileAnalyzer

:: --- 第 1 步：定義快取資料夾並進行啟動前清理 ---
SET "CACHE_DIR=pycache_temp"
echo [1/5] 正在進行啟動前清理...
IF EXIST "%CACHE_DIR%\" (
    rmdir /s /q "%CACHE_DIR%"
)
echo      - 舊的暫存已清理完畢。

:: --- 第 2 步: 建立並啟用虛擬環境 ---
echo.
echo [2/5] 正在檢查並啟用虛擬環境...
IF NOT EXIST "venv\" (
    echo      - 正在建立虛擬環境...
    python -m venv venv
)
CALL "venv\Scripts\activate.bat"

:: --- 第 3 步：設定 Python 快取路徑 ---
echo.
echo [3/5] 正在設定 Python 快取路徑...
mkdir "%CACHE_DIR%" >nul 2>&1
set "PYTHONPYCACHEPREFIX=%CACHE_DIR%"
echo      - 所有 .pyc 快取將被重導向至 "%CACHE_DIR%"

:: --- 第 4 步：安裝套件 ---
echo.
echo [4/5] 正在安裝 sentence-transformers ，Tier 3 BERT  套件...
pip install sentence-transformers

:: --- 第 5 步：執行主程式 ---
echo.
echo [5/5] 正在執行主程式 (build_index.py)...
echo --------------------------------------------------
echo.
python build_index.py
echo.
echo --------------------------------------------------
echo 程式執行完畢。

:: --- 最終清理步驟 ---
echo.
echo 正在進行最終清理...
IF EXIST "%CACHE_DIR%\" (
    rmdir /s /q "%CACHE_DIR%"
    echo      - 暫存資料夾 "%CACHE_DIR%" 已被徹底刪除！
)

:: --- 結束 ---
echo.
echo 按任意鍵關閉此視窗...
pause >nul
exit /b
