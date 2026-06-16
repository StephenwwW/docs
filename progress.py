"""
progress.py
===========
SM-2 間隔重複（Spaced Repetition）進度追蹤引擎。

儲存格式（progress.json）：
{
  "words": {
    "abandon": {
      "word":        "abandon",
      "status":      "learning",   // "new" | "learning" | "mastered"
      "ease":        2.5,          // SM-2 易度因子（≥1.3）
      "interval":    1,            // 下次複習間隔（天）
      "repetitions": 0,            // 連續答對次數
      "due":         "2026-01-15", // 下次複習日期（ISO）
      "last_seen":   "2026-01-14", // 最後複習日期
      "first_seen":  "2026-01-14", // 第一次學習日期
      "history":     [3, 4, 5]     // 歷次評分（0-5）
    }
  },
  "meta": {
    "total_seen":    42,
    "total_mastered": 10,
    "last_updated":  "2026-01-15"
  }
}

API（由 serve.py 呼叫）：
  GET  /progress            → 回傳完整進度摘要
  GET  /progress/due        → 回傳今日到期詞彙清單
  POST /progress/rate       → 評分一個詞彙
    body: {"word": "abandon", "rating": 3}
    rating: 0=完全忘記, 1=很難, 2=困難, 3=剛好記得, 4=容易, 5=完全記得
"""

import os
import json
from datetime import date, timedelta, datetime
from pathlib import Path


# ── SM-2 核心算法 ─────────────────────────────────────────────────────────────

def sm2_next(ease: float, interval: int, repetitions: int, rating: int) -> tuple:
    """
    SM-2 算法：根據評分計算下次複習參數。

    Args:
        ease:        當前易度因子（Easiness Factor，初始 2.5）
        interval:    當前複習間隔（天）
        repetitions: 連續答對次數（rating >= 3 算答對）
        rating:      本次評分（0–5）

    Returns:
        (new_ease, new_interval, new_repetitions)
    """
    # 更新易度因子
    new_ease = ease + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
    new_ease = max(1.3, new_ease)  # 易度因子下限 1.3

    if rating < 3:
        # 答錯：重置
        new_repetitions = 0
        new_interval    = 1
    else:
        # 答對：推進
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = round(interval * new_ease)

    return new_ease, new_interval, new_repetitions


# ── ProgressStore ─────────────────────────────────────────────────────────────

class ProgressStore:
    """進度檔案管理，提供讀寫與 SM-2 計算。"""

    def __init__(self, progress_path: str):
        self.path = progress_path
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"words": {}, "meta": {
            "total_seen": 0, "total_mastered": 0, "last_updated": ""
        }}

    def _save(self):
        # 更新 meta
        words = self._data["words"]
        self._data["meta"]["total_seen"]     = len(words)
        self._data["meta"]["total_mastered"] = sum(
            1 for w in words.values() if w.get("status") == "mastered"
        )
        self._data["meta"]["last_updated"] = date.today().isoformat()

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ── 公開 API ──────────────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        """回傳進度摘要（給前端顯示用）。"""
        words  = self._data["words"]
        today  = date.today().isoformat()

        new_count      = sum(1 for w in words.values() if w["status"] == "new")
        learning_count = sum(1 for w in words.values() if w["status"] == "learning")
        mastered_count = sum(1 for w in words.values() if w["status"] == "mastered")
        due_count      = sum(
            1 for w in words.values()
            if w.get("due", "9999") <= today
        )

        return {
            "total":    len(words),
            "new":      new_count,
            "learning": learning_count,
            "mastered": mastered_count,
            "due":      due_count,
            "meta":     self._data["meta"],
        }

    def get_due(self) -> list:
        """回傳今日到期（需複習）的詞彙清單，依到期日排序。"""
        today = date.today().isoformat()
        due = [
            w for w in self._data["words"].values()
            if w.get("due", "9999") <= today
        ]
        due.sort(key=lambda w: w.get("due", "9999"))
        return due

    def get_word(self, word: str) -> dict | None:
        """取得單一詞彙的進度記錄。"""
        return self._data["words"].get(word)

    def rate_word(self, word: str, rating: int) -> dict:
        """
        評分一個詞彙並更新 SM-2 排程。

        Args:
            word:   詞彙（小寫）
            rating: 0–5 評分

        Returns:
            更新後的詞彙進度記錄
        """
        rating = max(0, min(5, int(rating)))
        today  = date.today().isoformat()
        words  = self._data["words"]

        if word not in words:
            # 第一次學習：建立記錄
            words[word] = {
                "word":        word,
                "status":      "learning",
                "ease":        2.5,
                "interval":    1,
                "repetitions": 0,
                "due":         today,
                "last_seen":   today,
                "first_seen":  today,
                "history":     [],
            }

        entry = words[word]
        entry["history"].append(rating)
        entry["last_seen"] = today

        # SM-2 計算
        new_ease, new_interval, new_reps = sm2_next(
            entry["ease"], entry["interval"], entry["repetitions"], rating
        )
        entry["ease"]        = round(new_ease, 3)
        entry["interval"]    = new_interval
        entry["repetitions"] = new_reps

        # 計算下次到期日
        next_due = date.today() + timedelta(days=new_interval)
        entry["due"] = next_due.isoformat()

        # 更新狀態
        if new_reps >= 3 and new_interval >= 7:
            entry["status"] = "mastered"
        elif new_reps > 0:
            entry["status"] = "learning"

        self._save()
        return entry

    def mark_seen(self, word: str) -> dict:
        """
        標記詞彙為「已學習」（不帶評分，等同 rating=3 的初始化）。
        用於使用者點開學習檔案時自動記錄。
        """
        today = date.today().isoformat()
        words = self._data["words"]

        if word not in words:
            words[word] = {
                "word":        word,
                "status":      "new",
                "ease":        2.5,
                "interval":    1,
                "repetitions": 0,
                "due":         today,
                "last_seen":   today,
                "first_seen":  today,
                "history":     [],
            }
            self._save()

        return words[word]

    def get_all(self) -> dict:
        """回傳全部詞彙進度（字典格式）。"""
        return self._data["words"]

    def reset_word(self, word: str) -> bool:
        """重置單一詞彙的進度。"""
        if word in self._data["words"]:
            del self._data["words"][word]
            self._save()
            return True
        return False
