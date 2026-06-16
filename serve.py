"""
serve.py
========
啟動本地 HTTP 伺服器，提供 index.html 和學習檔案存取。

執行方式：
    python serve.py
    python serve.py --config my_config.json
    python serve.py --port 9090

路由總覽：
  GET  /                  → index.html
  GET  /index.json        → 詞彙索引
  GET  /config            → 讀取設定（含路徑狀態）
  POST /config            → 寫入設定（安全欄位白名單）
  POST /rebuild           → 觸發 build_index.py 重建（非阻塞背景執行）
  GET  /rebuild/status    → 查詢重建進度、log、成功與否
  GET  /mindmap?word=...  → WordNet 語義心智圖
  GET  /export?format=... → 匯出詞彙（csv / anki）
  GET  /progress          → 進度摘要
  GET  /progress/due      → 今日待複習
  GET  /progress/word?w=  → 單一詞彙進度
  GET  /progress/all      → 全部進度
  POST /progress/rate     → 評分詞彙
  POST /progress/seen     → 標記已學習
  POST /progress/reset    → 重置詞彙進度
  GET  /file?path=...     → 本機學習 HTML（路徑安全檢查）
"""

import os
import json
import argparse
import webbrowser
import threading
import urllib.parse
import subprocess
import time
import csv
import io
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ── 索引重建狀態（全局，跨請求共享） ────────────────────────────────────────
_rebuild_lock   = threading.Lock()
_rebuild_status = {
    "running":    False,
    "last_start": None,   # ISO 時間字串
    "last_end":   None,
    "success":    None,   # True / False / None（未曾執行）
    "message":    "",
    "log":        [],     # 最近 50 行輸出
}

# ── 允許透過 /config POST 修改的安全欄位 ────────────────────────────────────
_SAFE_CONFIG_KEYS = {
    "essentials_path", "full_path",
    "dolch_txt_path", "fry_txt_paths", "ngsl_csv_path",
    "server_port", "output_json", "progress_json", "cefr_review_csv",
}

# 語義心智圖引擎
try:
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mindmap import get_mindmap, get_mindmap_for_phrase
    _MINDMAP_ENABLED = True
except ImportError:
    _MINDMAP_ENABLED = False

# SM-2 進度追蹤引擎
try:
    from progress import ProgressStore
    _PROGRESS_ENABLED = True
except ImportError:
    _PROGRESS_ENABLED = False
    ProgressStore = None


def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        print(f"❌ 找不到設定檔: {config_path}，使用預設值")
        return {}
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


class LearningHandler(BaseHTTPRequestHandler):
    """
    自訂 HTTP Handler：
    - GET /               → 回傳 index.html
    - GET /index.json     → 回傳 index.json
    - GET /file?path=...  → 回傳指定的本機 HTML 學習檔案
    - GET /mindmap?word=  → 回傳 WordNet 語義心智圖 JSON
    - GET /static/...     → 靜態資源
    """

    # 從外部注入
    essentials_path: str = ""
    full_path: str = ""
    base_dir: str = ""
    config_path: str = ""
    progress_store = None   # ProgressStore 實例（由 make_handler 注入）

    def log_message(self, format, *args):
        # 只顯示錯誤，避免每次 request 都刷螢幕
        if args and str(args[1]) not in ("200", "304"):
            super().log_message(format, *args)

    def send_file(self, filepath: str, content_type: str = "text/html; charset=utf-8"):
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404, f"找不到檔案: {filepath}")
        except Exception as e:
            self.send_error(500, str(e))

    def send_json(self, data: dict):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_download(self, data: bytes, filename: str, content_type: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _load_index_items(self) -> list:
        index_path = os.path.join(self.base_dir, "index.json")
        if not os.path.exists(index_path):
            raise FileNotFoundError("index.json 尚未產生，請先執行 build_index.py")
        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("all_items", [])

    def _get_progress_map(self) -> dict:
        if _PROGRESS_ENABLED and self.progress_store:
            return self.progress_store.get_all()
        return {}

    def _read_config(self) -> dict:
        if self.config_path and os.path.exists(self.config_path):
            with open(self.config_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _write_config(self, config: dict) -> None:
        if not self.config_path:
            raise FileNotFoundError("config_path 未設定")
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            f.write("\n")

    @staticmethod
    def _path_info(path: str) -> dict:
        if not path:
            return {"path": "", "exists": False, "is_dir": False, "is_file": False}
        return {
            "path": path,
            "exists": os.path.exists(path),
            "is_dir": os.path.isdir(path),
            "is_file": os.path.isfile(path),
        }

    def _config_payload(self, config: dict) -> dict:
        output_json = config.get("output_json", "index.json")
        progress_json = config.get("progress_json", "progress.json")
        cefr_review_csv = config.get("cefr_review_csv", "cefr_review.csv")
        return {
            "config": config,
            "config_path": self.config_path,
            "base_dir": self.base_dir,
            "runtime": {
                "essentials_path": self.essentials_path,
                "full_path": self.full_path,
                "server_port": config.get("server_port", 8080),
            },
            "status": {
                "essentials_path": self._path_info(config.get("essentials_path", "")),
                "full_path": self._path_info(config.get("full_path", "")),
                "dolch_txt_path": self._path_info(config.get("dolch_txt_path", "")),
                "ngsl_csv_path": self._path_info(config.get("ngsl_csv_path", "")),
                "output_json": self._path_info(os.path.join(self.base_dir, output_json)),
                "progress_json": self._path_info(os.path.join(self.base_dir, progress_json)),
                "cefr_review_csv": self._path_info(os.path.join(self.base_dir, cefr_review_csv)),
            },
        }

    def _save_config_from_payload(self, payload: dict) -> dict:
        current = self._read_config()
        incoming = payload.get("config") if isinstance(payload.get("config"), dict) else payload
        allowed = {
            "essentials_path", "full_path", "dolch_txt_path", "fry_txt_paths",
            "ngsl_csv_path", "server_port", "output_json", "progress_json",
            "cefr_review_csv",
        }

        for key in allowed:
            if key not in incoming:
                continue
            value = incoming[key]
            if key == "server_port":
                try:
                    value = int(value)
                except Exception:
                    raise ValueError("server_port 必須是數字")
                if value < 1 or value > 65535:
                    raise ValueError("server_port 必須介於 1 到 65535")
            elif key == "fry_txt_paths":
                if value in ("", None):
                    value = None
                elif not isinstance(value, list):
                    value = [str(value)]
            else:
                if value == "":
                    value = None if key in ("dolch_txt_path", "ngsl_csv_path") else ""
                elif value is not None:
                    value = str(value)
            current[key] = value

        self._write_config(current)
        self.essentials_path = current.get("essentials_path", "")
        self.full_path = current.get("full_path", "")

        if _PROGRESS_ENABLED and ProgressStore:
            prog_path = os.path.join(self.base_dir, current.get("progress_json", "progress.json"))
            self.progress_store = ProgressStore(prog_path)

        return current

    def _filter_export_items(self, items: list, params: dict) -> list:
        type_filter = params.get("type", ["all"])[0]
        query = urllib.parse.unquote(params.get("q", [""])[0]).strip().lower()
        group = urllib.parse.unquote(params.get("group", [""])[0]).strip()
        category = urllib.parse.unquote(params.get("category", [""])[0]).strip()
        cefr = urllib.parse.unquote(params.get("cefr", [""])[0]).strip()

        result = items
        if group:
            result = [i for i in result if i.get("group_id") == group]
        if category:
            result = [i for i in result if i.get("category_id") == category]
        if cefr:
            if cefr.startswith("CEFR-"):
                result = [i for i in result if cefr in (i.get("cefr_subtags") or [])]
            else:
                result = [i for i in result if i.get("cefr_level") == cefr]

        if type_filter == "essentials":
            result = [i for i in result if i.get("file_type") == "essentials"]
        elif type_filter == "full":
            result = [i for i in result if i.get("file_type") == "full"]
        elif type_filter == "tagged":
            result = [i for i in result if i.get("tags")]
        elif type_filter == "cefr":
            result = [i for i in result if i.get("cefr_level")]
        elif type_filter == "cefr-confirmed":
            result = [i for i in result if i.get("cefr_confidence") == "confirmed"]
        elif type_filter == "cefr-inferred":
            result = [i for i in result if i.get("cefr_confidence") == "inferred"]
        elif type_filter == "cefr-bert":
            result = [i for i in result if i.get("cefr_confidence") == "bert"]

        if query:
            result = [
                i for i in result
                if query in (i.get("core_word") or "").lower()
                or query in (i.get("filename") or "").lower()
            ]

        return sorted(result, key=lambda i: ((i.get("core_word") or "").lower(), i.get("file_type") or ""))

    @staticmethod
    def _join(value, sep: str = "|") -> str:
        if isinstance(value, list):
            return sep.join(str(v) for v in value)
        return "" if value is None else str(value)

    @staticmethod
    def _anki_tag(text: str) -> str:
        text = re.sub(r"\s+", "_", str(text).strip())
        return re.sub(r"[^\w:\-]", "", text)

    def _build_csv_export(self, items: list, progress: dict) -> bytes:
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=[
            "core_word", "file_type", "filename", "category_id", "category_label",
            "group_id", "group_label", "tags", "cefr_level", "cefr_confidence",
            "cefr_subtags", "classified", "progress_status", "due", "ease",
            "interval", "repetitions", "path"
        ])
        writer.writeheader()
        for item in items:
            p = progress.get((item.get("core_word") or "").lower(), {})
            writer.writerow({
                "core_word": item.get("core_word", ""),
                "file_type": item.get("file_type", ""),
                "filename": item.get("filename", ""),
                "category_id": item.get("category_id", ""),
                "category_label": item.get("category_label", ""),
                "group_id": item.get("group_id", ""),
                "group_label": item.get("group_label", ""),
                "tags": self._join(item.get("tags")),
                "cefr_level": item.get("cefr_level") or "",
                "cefr_confidence": item.get("cefr_confidence") or "",
                "cefr_subtags": self._join(item.get("cefr_subtags")),
                "classified": item.get("classified", False),
                "progress_status": p.get("status", ""),
                "due": p.get("due", ""),
                "ease": p.get("ease", ""),
                "interval": p.get("interval", ""),
                "repetitions": p.get("repetitions", ""),
                "path": item.get("path", ""),
            })
        return ("\ufeff" + out.getvalue()).encode("utf-8")

    def _build_anki_export(self, items: list, progress: dict) -> bytes:
        rows = []
        for item in items:
            word = item.get("core_word", "")
            p = progress.get(word.lower(), {})
            badges = [
                item.get("file_type", ""),
                item.get("cefr_level") or "",
                self._join(item.get("tags"), ", "),
            ]
            meta = " / ".join(x for x in badges if x)
            back_parts = [
                f"<b>{word}</b>",
                f"Category: {item.get('category_label', '')}",
                f"CEFR: {item.get('cefr_level') or '-'} ({item.get('cefr_confidence') or 'unknown'})",
                f"Tags: {self._join(item.get('tags'), ', ') or '-'}",
            ]
            if p:
                back_parts.append(f"Progress: {p.get('status', 'new')} / due {p.get('due', '-')}")
            back_parts.append(f"File: {item.get('filename', '')}")
            tags = [
                "enn",
                self._anki_tag(item.get("file_type", "")),
                self._anki_tag(item.get("cefr_level") or ""),
                *[self._anki_tag(t) for t in (item.get("tags") or [])],
            ]
            clean_tags = " ".join(t for t in tags if t)
            rows.append([word, "<br>".join(back_parts), meta, clean_tags])

        out = io.StringIO()
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerows(rows)
        return out.getvalue().encode("utf-8")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path

        # 讀取 body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        # 儲存設定：POST /config
        if path == "/config":
            try:
                config = self._save_config_from_payload(payload)
                self.send_json({"ok": True, **self._config_payload(config)})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)})

        # 評分詞彙：POST /progress/rate  body: {"word":"...", "rating":3}
        elif path == "/progress/rate":
            if not _PROGRESS_ENABLED or not self.progress_store:
                self.send_json({"error": "progress.py 未找到"})
                return
            word   = str(payload.get("word", "")).strip().lower()
            rating = payload.get("rating", 3)
            if not word:
                self.send_json({"error": "缺少 word 欄位"})
                return
            entry = self.progress_store.rate_word(word, rating)
            self.send_json({"ok": True, "entry": entry})

        # 標記已學習：POST /progress/seen  body: {"word":"..."}
        elif path == "/progress/seen":
            if not _PROGRESS_ENABLED or not self.progress_store:
                self.send_json({"ok": False})
                return
            word = str(payload.get("word", "")).strip().lower()
            if word:
                entry = self.progress_store.mark_seen(word)
                self.send_json({"ok": True, "entry": entry})
            else:
                self.send_json({"error": "缺少 word 欄位"})

        # 重置詞彙：POST /progress/reset  body: {"word":"..."}
        elif path == "/progress/reset":
            if not _PROGRESS_ENABLED or not self.progress_store:
                self.send_json({"error": "progress.py 未找到"})
                return
            word = str(payload.get("word", "")).strip().lower()
            ok   = self.progress_store.reset_word(word) if word else False
            self.send_json({"ok": ok})

        # ── 觸發重建索引：POST /rebuild ──────────────────────────────────────
        elif path == "/rebuild":
            with _rebuild_lock:
                if _rebuild_status["running"]:
                    self.send_json({"ok": False, "error": "重建已在執行中，請稍後再試"})
                    return
            build_script = os.path.join(self.base_dir, "build_index.py")
            if not os.path.exists(build_script):
                self.send_json({"error": f"找不到 build_index.py：{build_script}"})
                return
            t = threading.Thread(
                target=_run_rebuild,
                args=(build_script, self.base_dir),
                daemon=True,
            )
            t.start()
            self.send_json({"ok": True, "message": "重建已開始，請用 GET /rebuild/status 查詢進度"})

        else:
            self.send_error(404, f"找不到: {path}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # 根路徑 → index.html
        if path in ("/", "/index.html"):
            html_path = os.path.join(self.base_dir, "index.html")
            self.send_file(html_path)

        # index.json
        elif path == "/index.json":
            json_path = os.path.join(self.base_dir, "index.json")
            if os.path.exists(json_path):
                self.send_file(json_path, "application/json; charset=utf-8")
            else:
                self.send_json({"error": "index.json 尚未產生，請先執行 build_index.py"})

        # 設定資訊：GET /config
        elif path == "/config":
            try:
                self.send_json(self._config_payload(self._read_config()))
            except Exception as e:
                self.send_json({"error": str(e)})

        # 語義心智圖：GET /mindmap?word=<word>
        elif path == "/mindmap":
            word = urllib.parse.unquote(params.get("word", [""])[0]).strip()
            if not word:
                self.send_json({"error": "請提供 ?word= 參數"})
            elif not _MINDMAP_ENABLED:
                self.send_json({"error": "mindmap.py 未找到，請確認檔案與 serve.py 在同一資料夾"})
            else:
                # 多詞片語 vs 單字
                if " " in word:
                    result = get_mindmap_for_phrase(word)
                else:
                    result = get_mindmap(word)
                self.send_json(result)

        # 匯出詞彙：GET /export?format=csv|anki&type=...&q=...&category=...&cefr=...
        elif path == "/export":
            fmt = params.get("format", ["csv"])[0].strip().lower()
            try:
                items = self._filter_export_items(self._load_index_items(), params)
            except FileNotFoundError as e:
                self.send_json({"error": str(e)})
                return
            except Exception as e:
                self.send_error(500, f"匯出失敗: {e}")
                return

            progress = self._get_progress_map()
            if fmt == "csv":
                body = self._build_csv_export(items, progress)
                self.send_download(body, "enn_export.csv", "text/csv; charset=utf-8")
            elif fmt in ("anki", "tsv"):
                body = self._build_anki_export(items, progress)
                self.send_download(body, "enn_anki.tsv", "text/tab-separated-values; charset=utf-8")
            else:
                self.send_json({"error": "format 僅支援 csv 或 anki"})

        # 進度摘要：GET /progress
        elif path == "/progress":
            if not _PROGRESS_ENABLED or not self.progress_store:
                self.send_json({"error": "progress.py 未找到"})
            else:
                self.send_json(self.progress_store.get_summary())

        # 今日到期詞彙：GET /progress/due
        elif path == "/progress/due":
            if not _PROGRESS_ENABLED or not self.progress_store:
                self.send_json({"error": "progress.py 未找到"})
            else:
                due = self.progress_store.get_due()
                self.send_json({"due": due, "count": len(due)})

        # 單一詞彙進度：GET /progress/word?w=<word>
        elif path == "/progress/word":
            word = urllib.parse.unquote(params.get("w", [""])[0]).strip().lower()
            if not word:
                self.send_json({"error": "請提供 ?w= 參數"})
            elif not _PROGRESS_ENABLED or not self.progress_store:
                self.send_json({"error": "progress.py 未找到"})
            else:
                entry = self.progress_store.get_word(word)
                self.send_json(entry if entry else {"status": "new", "word": word})

        # 全部進度：GET /progress/all
        elif path == "/progress/all":
            if not _PROGRESS_ENABLED or not self.progress_store:
                self.send_json({"error": "progress.py 未找到"})
            else:
                self.send_json(self.progress_store.get_all())

        # ── 重建狀態：GET /rebuild/status ────────────────────────────────────
        elif path == "/rebuild/status":
            with _rebuild_lock:
                self.send_json(dict(_rebuild_status))

        # 開啟學習檔案：GET /file?path=<絕對路徑>
        elif path == "/file":
            raw_path = params.get("path", [""])[0]
            file_path = urllib.parse.unquote(raw_path)

            # 安全檢查：只允許存取 essentials 或 full 資料夾內的檔案
            ess_real = os.path.realpath(self.essentials_path) if self.essentials_path else ""
            ful_real = os.path.realpath(self.full_path) if self.full_path else ""
            req_real = os.path.realpath(file_path)

            allowed = (
                (ess_real and req_real.startswith(ess_real)) or
                (ful_real and req_real.startswith(ful_real))
            )

            if not allowed:
                self.send_error(403, "存取被拒：路徑不在允許範圍內")
                return

            if not os.path.exists(file_path):
                self.send_error(404, f"找不到檔案: {file_path}")
                return

            self.send_file(file_path)

        # 其他靜態資源（CSS、JS、圖片等）
        else:
            static_path = os.path.join(self.base_dir, path.lstrip("/"))
            if os.path.isfile(static_path):
                ext = os.path.splitext(static_path)[1].lower()
                mime = {
                    ".css": "text/css",
                    ".js": "application/javascript",
                    ".json": "application/json",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".svg": "image/svg+xml",
                }.get(ext, "application/octet-stream")
                self.send_file(static_path, mime)
            else:
                # favicon 靜默忽略，其餘回傳英文訊息避免 latin-1 編碼錯誤
                if path == "/favicon.ico":
                    self.send_response(404)
                    self.end_headers()
                else:
                    self.send_error(404, f"Not found: {path}")     


def _run_rebuild(build_script: str, base_dir: str) -> None:
    """
    背景執行緒：呼叫 build_index.py 重建索引，並即時更新 _rebuild_status。

    - 以 subprocess.Popen 執行，合流 stdout/stderr
    - log 最多保留最近 50 行
    - 執行期間 running=True，結束後更新 success / message / last_end
    """
    start_time = time.strftime("%Y-%m-%dT%H:%M:%S")
    with _rebuild_lock:
        _rebuild_status.update({
            "running":    True,
            "last_start": start_time,
            "last_end":   None,
            "success":    None,
            "message":    "重建中...",
            "log":        [],
        })

    lines = []
    try:
        proc = subprocess.Popen(
            ["python", build_script],
            cwd=base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in proc.stdout:
            line = line.rstrip("\n")
            lines.append(line)
            with _rebuild_lock:
                _rebuild_status["log"] = lines[-50:]
        proc.wait()
        success = (proc.returncode == 0)
        msg = "重建完成 ✅" if success else f"重建失敗（returncode={proc.returncode}）❌"
    except Exception as e:
        success = False
        msg = f"執行錯誤：{e}"
        lines.append(msg)

    end_time = time.strftime("%Y-%m-%dT%H:%M:%S")
    with _rebuild_lock:
        _rebuild_status.update({
            "running":  False,
            "last_end": end_time,
            "success":  success,
            "message":  msg,
            "log":      lines[-50:],
        })
    print(f"  🔧 /rebuild [{start_time} → {end_time}] {msg}")


def make_handler(essentials_path: str, full_path: str, base_dir: str,
                 config_path: str,
                 progress_store=None):
    """動態產生 Handler class，注入路徑設定"""
    class Handler(LearningHandler):
        pass
    Handler.essentials_path = essentials_path
    Handler.full_path       = full_path
    Handler.base_dir        = base_dir
    Handler.config_path     = config_path
    Handler.progress_store  = progress_store
    return Handler


def open_browser(port: int, delay: float = 1.2):
    """延遲後開啟瀏覽器"""
    import time
    time.sleep(delay)
    webbrowser.open(f"http://localhost:{port}")


def main():
    parser = argparse.ArgumentParser(description="serve.py — 英文學習菜單本地伺服器")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--port",   type=int, default=None)
    args = parser.parse_args()

    config_path    = os.path.abspath(args.config)
    config        = load_config(config_path)
    port          = args.port or config.get("server_port", 8080)
    essentials    = config.get("essentials_path", "")
    full          = config.get("full_path", "")
    base_dir      = os.path.dirname(config_path)

    print("=" * 60)
    print("  🌐 英文學習菜單 — 本地 HTTP 伺服器")
    print("=" * 60)
    print(f"  essentials : {essentials or '(未設定)'}")
    print(f"  full       : {full or '(未設定)'}")
    print(f"  伺服器根目錄: {base_dir}")
    print(f"  連線位址   : http://localhost:{port}")
    print()

    # 檢查 index.json 是否存在
    index_json = os.path.join(base_dir, "index.json")
    if not os.path.exists(index_json):
        print("  ⚠️  尚未找到 index.json")
        print("     請先執行：python build_index.py")
        print("     伺服器仍會啟動，但前端會顯示提示訊息。")
        print()

    # 初始化進度追蹤
    prog_store = None
    if _PROGRESS_ENABLED:
        prog_path = os.path.join(base_dir, config.get("progress_json", "progress.json"))
        prog_store = ProgressStore(prog_path)
        due_count  = len(prog_store.get_due())
        total      = prog_store.get_summary()["total"]
        print(f"  📊 進度追蹤  : {total} 個詞彙已記錄，今日待複習 {due_count} 個")
        print()

    handler = make_handler(essentials, full, base_dir, config_path, prog_store)

    try:
        server = HTTPServer(("localhost", port), handler)
    except OSError:
        print(f"  ❌ 埠號 {port} 已被佔用，請改用其他埠號：")
        print(f"     python serve.py --port 8081")
        return

    # 背景執行緒開啟瀏覽器
    t = threading.Thread(target=open_browser, args=(port,), daemon=True)
    t.start()

    print(f"  🔧 重建索引  : POST http://localhost:{port}/rebuild")
    print(f"  🔧 重建狀態  : GET  http://localhost:{port}/rebuild/status")
    print(f"  ✅ 伺服器已啟動，正在開啟瀏覽器...")
    print(f"  🔴 按 Ctrl+C 停止伺服器")
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  🛑 伺服器已停止。")


if __name__ == "__main__":
    main()
