"""
mindmap.py
==========
WordNet 語義心智圖引擎。

根據輸入詞彙，從 WordNet 抽取真實語義關係：
  • sense     — 詞義（同一詞的不同詞義）
  • synonym   — 同義詞（同一詞義集的其他詞形）
  • antonym   — 反義詞
  • hypernym  — 上位詞（更廣義的概念）
  • hyponym   — 下位詞（更具體的概念）
  • similar   — 形容詞相似詞

輸出格式（JSON）：
{
  "word": "work",
  "nodes": [
    {"id": "root:work",  "label": "work",     "type": "root",    "pos": "",   "definition": ""},
    {"id": "sense:0",    "label": "work",     "type": "sense",   "pos": "名詞", "definition": "..."},
    {"id": "syn:0:1",    "label": "labour",   "type": "synonym", "pos": "名詞", "definition": ""},
    ...
  ],
  "edges": [
    {"source": "root:work", "target": "sense:0",  "relation": "sense"},
    {"source": "sense:0",   "target": "syn:0:1",  "relation": "synonym"},
    ...
  ]
}
"""

import re

# ── NLTK / WordNet 初始化 ──────────────────────────────────
try:
    import nltk
    from nltk.corpus import wordnet as wn
    from nltk.stem import WordNetLemmatizer

    _downloads = [("corpora/wordnet","wordnet"),
                  ("corpora/omw-1.4","omw-1.4")]
    for path, pkg in _downloads:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(pkg, quiet=True)

    _lemmatizer  = WordNetLemmatizer()
    _WN_ENABLED  = True

except ImportError:
    _WN_ENABLED  = False
    wn           = None
    _lemmatizer  = None


# ── 常數 ──────────────────────────────────────────────────
POS_LABEL = {"n": "名詞", "v": "動詞", "a": "形容詞",
             "r": "副詞", "s": "形容詞衛星"}

# 節點類型 → 前端顯示顏色（與 v4 架構色彩系統對齊）
NODE_COLORS = {
    "root":     "#0F172A",   # 深黑，中心詞
    "sense":    "#2563EB",   # 藍，詞義
    "synonym":  "#059669",   # 綠，同義詞
    "antonym":  "#E11D48",   # 紅，反義詞
    "hypernym": "#7C3AED",   # 紫，上位詞
    "hyponym":  "#0891B2",   # 青，下位詞
    "similar":  "#D97706",   # 橙，形容詞相似詞
}

# 連線類型 → 標籤
RELATION_LABELS = {
    "sense":    "詞義",
    "synonym":  "同義",
    "antonym":  "反義",
    "hypernym": "上位",
    "hyponym":  "下位",
    "similar":  "相似",
}


def _lemmatize(word: str) -> str:
    """嘗試將詞形還原為原形"""
    if not _lemmatizer:
        return word
    for pos in ("v", "n", "a"):
        lemma = _lemmatizer.lemmatize(word, pos=pos)
        if lemma != word:
            return lemma
    return word


def get_mindmap(
    word: str,
    max_senses:   int = 4,
    max_synonyms: int = 5,
    max_antonyms: int = 2,
    max_hypernyms:int = 2,
    max_hyponyms: int = 4,
    max_similar:  int = 4,
) -> dict:
    """
    從 WordNet 建立詞彙語義心智圖資料。

    Args:
        word:         目標詞彙（英文）
        max_senses:   最多顯示幾個詞義
        max_synonyms: 每個詞義最多顯示幾個同義詞
        max_antonyms: 每個詞義最多顯示幾個反義詞
        max_hypernyms:每個詞義最多顯示幾個上位詞
        max_hyponyms: 每個詞義最多顯示幾個下位詞
        max_similar:  形容詞每個詞義最多顯示幾個相似詞

    Returns:
        {"word": str, "nodes": list, "edges": list, "legend": dict}
        若 WordNet 不可用或詞彙未找到，回傳 {"error": str}
    """
    if not _WN_ENABLED:
        return {"error": "WordNet 未安裝。請執行：pip install nltk 並下載 wordnet 語料庫。"}

    # 嘗試詞形還原
    base = _lemmatize(word.lower().strip())
    synsets = wn.synsets(base)
    if not synsets:
        # 再嘗試原始輸入
        synsets = wn.synsets(word.lower().strip())
    if not synsets:
        return {"error": f"找不到「{word}」的 WordNet 詞義，請確認英文拼寫。"}

    nodes: dict[str, dict] = {}
    edges: list[dict]      = []
    seen_edges: set        = set()

    def add_node(nid: str, label: str, ntype: str,
                 pos: str = "", definition: str = "",
                 in_list: bool = False) -> None:
        if nid not in nodes:
            nodes[nid] = {
                "id":         nid,
                "label":      label,
                "type":       ntype,
                "pos":        pos,
                "definition": definition[:100],
                "color":      NODE_COLORS.get(ntype, "#64748B"),
                "in_list":    in_list,
            }

    def add_edge(src: str, tgt: str, relation: str) -> None:
        key = f"{src}|{tgt}|{relation}"
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append({
                "source":   src,
                "target":   tgt,
                "relation": relation,
                "label":    RELATION_LABELS.get(relation, relation),
            })

    # ── 根節點 ────────────────────────────────────────────
    root_id = f"root:{base}"
    add_node(root_id, base, "root", definition=f'"{word}" 的語義網絡')

    # ── 詞義節點 ──────────────────────────────────────────
    for sense_idx, ss in enumerate(synsets[:max_senses]):
        pos_label   = POS_LABEL.get(ss.pos(), ss.pos())
        sense_label = ss.lemmas()[0].name().replace("_", " ")
        sense_id    = f"sense:{sense_idx}"
        definition  = ss.definition()

        add_node(sense_id, sense_label, "sense", pos_label, definition)
        add_edge(root_id, sense_id, "sense")

        # ── 同義詞（同一 synset 的其他 lemma）─────────────
        for lem in ss.lemmas()[1: max_synonyms + 1]:
            syn_word = lem.name().replace("_", " ")
            if syn_word.lower() == base.lower():
                continue
            syn_id = f"syn:{sense_idx}:{syn_word}"
            add_node(syn_id, syn_word, "synonym", pos_label)
            add_edge(sense_id, syn_id, "synonym")

            # ── 反義詞（從 lemma 的 antonyms）────────────
            for ant in lem.antonyms()[:max_antonyms]:
                ant_word = ant.name().replace("_", " ")
                ant_id   = f"ant:{ant_word}"
                add_node(ant_id, ant_word, "antonym",
                         POS_LABEL.get(ant.synset().pos(), ""))
                add_edge(sense_id, ant_id, "antonym")

        # 從 lemma[0] 也查反義詞
        for ant in ss.lemmas()[0].antonyms()[:max_antonyms]:
            ant_word = ant.name().replace("_", " ")
            ant_id   = f"ant:{ant_word}"
            if ant_id not in nodes:
                add_node(ant_id, ant_word, "antonym",
                         POS_LABEL.get(ant.synset().pos(), ""))
                add_edge(sense_id, ant_id, "antonym")

        # ── 上位詞（hypernym：更廣義概念）────────────────
        for hyper in ss.hypernyms()[:max_hypernyms]:
            hw     = hyper.lemmas()[0].name().replace("_", " ")
            hid    = f"hyper:{hyper.name()}"
            h_def  = hyper.definition()
            add_node(hid, hw, "hypernym", pos_label, h_def)
            add_edge(sense_id, hid, "hypernym")

        # ── 下位詞（hyponym：更具體概念）─────────────────
        for hypo in ss.hyponyms()[:max_hyponyms]:
            hw     = hypo.lemmas()[0].name().replace("_", " ")
            hid    = f"hypo:{sense_idx}:{hypo.name()}"
            h_def  = hypo.definition()
            add_node(hid, hw, "hyponym", pos_label, h_def)
            add_edge(sense_id, hid, "hyponym")

        # ── 形容詞相似詞（similar_tos）────────────────────
        if ss.pos() in ("a", "s"):
            for sim in ss.similar_tos()[:max_similar]:
                sw  = sim.lemmas()[0].name().replace("_", " ")
                sid = f"sim:{sense_idx}:{sim.name()}"
                add_node(sid, sw, "similar", pos_label, sim.definition())
                add_edge(sense_id, sid, "similar")

    return {
        "word":   base,
        "input":  word,
        "nodes":  list(nodes.values()),
        "edges":  edges,
        "legend": {
            ntype: {"color": color, "label": RELATION_LABELS.get(ntype, ntype)}
            for ntype, color in NODE_COLORS.items()
        },
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "senses":      min(len(synsets), max_senses),
        },
    }


def get_mindmap_for_phrase(phrase: str) -> dict:
    """
    對多詞片語：取最重要的單字展開語義圖。
    選取策略：優先取動詞或名詞的頭詞。
    """
    words  = phrase.lower().split()
    # 過濾停用詞
    stops  = {"a","an","the","of","in","on","at","to","for","with",
               "by","from","up","out","off","over","under","into","about"}
    content = [w for w in words if w not in stops and len(w) > 2]
    if not content:
        content = words

    # 找第一個在 WordNet 中有記錄的詞
    if _WN_ENABLED:
        for w in content:
            if wn.synsets(w):
                return get_mindmap(w)

    return get_mindmap(content[0] if content else phrase)
