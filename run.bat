@echo off
:: =================================================================
:: 專案啟動器 - 整合版 (伺服器 + 自動套件安裝 + 進階字典引擎)
:: 修正 CMD 括號解析閃退問題 + 自動偵測本地 spaCy 離線模型 + 雙線程啟動
:: =================================================================

:: 步驟 0: 設定環境
chcp 65001 >nul
TITLE 專案啟動器 - 伺服器與進階字典

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

:: --- 新增步驟：自動安裝原始專案與 NLP 進階字典必要套件 ---
echo.
echo [3/5] 正在檢查並自動安裝所需的依賴套件...

:: 【補回】原始專案的套件安裝過程 (注意: 批次檔的 IF 區塊內不可使用括號，已改為中括號)
IF EXIST "requirements.txt" (
    echo      - 正在安裝原始專案的必要套件 [requirements.txt]...
    pip install -r requirements.txt --disable-pip-version-check
) ELSE (
    echo      - ⚠️ 未偵測到 requirements.txt [若您有自訂 pip 指令請在此替換]
)

echo      - 正在安裝/檢查基礎 NLP 與機器學習套件 [可能需要一些時間]...
pip install spacy nltk sentence-transformers scikit-learn lemminflect symspellpy pyenchant --disable-pip-version-check

:: 自動偵測並安裝您放在根目錄的 spaCy 中型離線模型 wheel 檔
IF EXIST "en_core_web_md-3.8.0-py3-none-any.whl" (
    echo      - 【偵測成功】找到本地 en_core_web_md-3.8.0-py3-none-any.whl
    echo        正在進行本地離線安裝模型...
    pip install "en_core_web_md-3.8.0-py3-none-any.whl" --disable-pip-version-check
) ELSE (
    echo      - ⚠️ 未偵測到本地 en_core_web_md 模型檔。
    echo        正在自動下載小型模型 en_core_web_sm 作為線上備用...
    python -m spacy download en_core_web_sm
)

:: --- 第 3 步：設定 Python 快取路徑 ---
echo.
echo [4/5] 正在設定 Python 快取路徑...
mkdir "%CACHE_DIR%" >nul 2>&1
set "PYTHONPYCACHEPREFIX=%CACHE_DIR%"
echo      - 所有 .pyc 快取將被重導向至 "%CACHE_DIR%"

:: --- 第 4 步：雙線程啟動核心程式 ---
echo.
echo [5/5] 正在同時啟動「字典引擎」與「本地伺服器」...

:: 【重點】使用 start 指令另開一個 cmd 視窗執行字典引擎
:: 帶入相同的虛擬環境與快取設定，背景默默地跑字典擴充
:: 👇👇👇 請選擇以下【其中一種】情境，並將另外兩種加上 :: 註解掉 👇👇👇

:: [情境 1] 預設 4 個模型一起上 (四大金剛平分 25% 權重) - 目前啟用這行
start "進階字典引擎 (處理中...)" cmd /c "CALL venv\Scripts\activate.bat && set PYTHONPYCACHEPREFIX=%CACHE_DIR% && python advanced_dict_engine.py --force && echo. && echo ✅ 處理完畢，請按任意鍵關閉此視窗... && pause >nul"

:: [情境 2] 自訂任意模型搭配 (例：只想要 BGE + E5 平分，各佔 50%)
:: start "進階字典引擎 (處理中...)" cmd /c "CALL venv\Scripts\activate.bat && set PYTHONPYCACHEPREFIX=%CACHE_DIR% && python advanced_dict_engine.py --force --models bge-m3 e5-large && echo. && echo ✅ 處理完畢，請按任意鍵關閉此視窗... && pause >nul"

:: [情境 3] 保留舊版單一模型模式 (100% 權重，使用原本的 Sentence-BERT)
:: start "進階字典引擎 (處理中...)" cmd /c "CALL venv\Scripts\activate.bat && set PYTHONPYCACHEPREFIX=%CACHE_DIR% && python advanced_dict_engine.py --force --models minilm && echo. && echo ✅ 處理完畢，請按任意鍵關閉此視窗... && pause >nul"

:: 在當前主視窗啟動伺服器
echo      - 伺服器已啟動於主視窗
python serve.py

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