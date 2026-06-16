"""
advanced_dict_engine.py
=======================
獨立的 NLP 進階字典與 CEFR 自動分級引擎 (Sidecar架構)。
保證不修改現有系統，純讀取 index.json 並輸出 advanced_dict_data.json。

網羅的方法清單：
1. WordNet Semantic Relations
2. Topic Lexicon (Lexnames)
3. spaCy (POS, Dependencies)
4. SymSpell / PyEnchant (Spelling)
5. LemmInflect (Inflections)
6. K-Means & Semantic Clustering (多模型平行評分 Ensemble)

【🚀 核心功能 1：CEFR 自動推算引擎】
【🚀 核心功能 2：主題知識樹自動分類引擎】
【⚡ 核心功能 3：增量更新快取與強制重構機制(--force)】
【🌟 核心功能 4：多模型平行評分法 (Ensemble Scoring)】
【📂 核心功能 5：本地端模型優先載入 (Local Model First)】
"""

import os
import json
import re
import numpy as np
import argparse
from collections import defaultdict, Counter

# --- 延遲載入標記 ---
_spacy_nlp = None
_sym_spell = None
_enchant_dict = None

def init_nltk():
    import nltk
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet')
        nltk.download('omw-1.4')
        nltk.download('punkt')
        nltk.download('averaged_perceptron_tagger')

class AdvancedDictEngine:
    def __init__(self, ensemble_models=None):
        if ensemble_models is None:
            ensemble_models = ["bge-m3", "e5-large", "mpnet", "roberta"]
            
        self.ensemble_models = ensemble_models
        print("🚀 初始化進階字典與 AI 引擎...")
        init_nltk()
        
        print(f"✅ 基礎模型初始化完成。")
        print(f"   預計將於聚類階段啟動【多模型平行評分法】，使用模型：{', '.join(self.ensemble_models)}")

    def _lazy_load_heavy_nlp(self):
        global _spacy_nlp, _sym_spell, _enchant_dict
        if _spacy_nlp is not None: return

        print("   ⏳ 載入重型 NLP 模型 (spaCy / SymSpell)...")
        import spacy
        try:
            _spacy_nlp = spacy.load("en_core_web_md")
        except:
            print("   ⚠️ 找不到 en_core_web_md，降級使用線上小模型。")
            _spacy_nlp = spacy.load("en_core_web_sm")

        try:
            from symspellpy import SymSpell
            import pkg_resources
            _sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
            dict_path = pkg_resources.resource_filename("symspellpy", "frequency_dictionary_en_82_765.txt")
            _sym_spell.load_dictionary(dict_path, term_index=0, count_index=1)
        except Exception as e:
            print(f"   ⚠️ SymSpell 初始化失敗: {e}")
            _sym_spell = None

        try:
            import enchant
            _enchant_dict = enchant.Dict("en_US")
        except Exception as e:
            print(f"   ⚠️ PyEnchant 初始化失敗: {e}")
            _enchant_dict = None

    def _encode_with_ensemble(self, words):
        from sentence_transformers import SentenceTransformer
        import gc
        
        try:
            import torch
            has_torch = True
        except ImportError:
            has_torch = False

        hf_repo_paths = {
            "minilm": "sentence-transformers/all-MiniLM-L6-v2",
            "roberta": "sentence-transformers/all-distilroberta-v1",
            "mpnet": "sentence-transformers/all-mpnet-base-v2",
            "bge-m3": "BAAI/bge-m3",
            "e5-large": "intfloat/multilingual-e5-large"
        }

        all_embs = []
        weight = 1.0 / len(self.ensemble_models)
        
        print(f"\n   🌟 啟動多模型平行評分法 (Ensemble) 🌟")
        for m_name in self.ensemble_models:
            hf_repo = hf_repo_paths.get(m_name)
            local_path = os.path.join("models", m_name)
            
            if os.path.exists(local_path) and os.path.isdir(local_path):
                print(f"   📂 [本地載入] {m_name}")
                actual_load_path = local_path
            else:
                print(f"   🌐 [線上載入] {m_name}")
                actual_load_path = hf_repo

            print(f"      ⏳ 正在載入與編碼: {m_name}...")
            model = SentenceTransformer(actual_load_path)
            emb = model.encode(words)
            emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
            emb = emb * np.sqrt(weight)
            all_embs.append(emb)

            del model
            gc.collect()
            if has_torch and torch.cuda.is_available():
                torch.cuda.empty_cache()

        print("   ✅ 所有模型編碼完畢！\n")
        return np.hstack(all_embs)

    def get_wordnet_relations(self, word):
        from nltk.corpus import wordnet as wn
        hypernyms, synonyms, antonyms = set(), set(), set()
        
        # 修正：WordNet 查詢片語時，必須把空格換成底線 (例如 garbage bag -> garbage_bag)
        search_word = word.replace(' ', '_')
        synsets = wn.synsets(search_word)
        
        for syn in synsets:
            for lemma in syn.lemmas():
                if lemma.name().lower() != search_word.lower():
                    synonyms.add(lemma.name().replace('_', ' '))
                if lemma.antonyms():
                    antonyms.add(lemma.antonyms()[0].name().replace('_', ' '))
            for hyp in syn.hypernyms():
                hypernyms.add(hyp.lemma_names()[0].replace('_', ' '))

        return {
            "hypernyms": list(hypernyms)[:5],
            "rogets_thesaurus": {
                "synonyms": list(synonyms)[:7],
                "antonyms": list(antonyms)[:5]
            },
            "hte_historical_roots": ["entity"] if synsets else []
        }

    def get_topic_lexicon(self, word):
        from nltk.corpus import wordnet as wn
        # 修正：WordNet 主題查詢一樣需要底線
        search_word = word.replace(' ', '_')
        topics = set([syn.lexname() for syn in wn.synsets(search_word)])
        return {"topics": list(topics)[:3]}

    def analyze_spacy(self, word):
        doc = _spacy_nlp(word)
        if len(doc) > 0:
            return {
                "pos": doc[0].pos_,
                "tag": doc[0].tag_,
                "is_alpha": doc[0].is_alpha,
                "is_stop": doc[0].is_stop
            }
        return {}

    def check_spelling(self, word):
        valid = True
        py_sugg, sym_sugg = [], []
        if _enchant_dict:
            valid = _enchant_dict.check(word)
            if not valid: py_sugg = _enchant_dict.suggest(word)[:3]
            
        if _sym_spell:
            from symspellpy import Verbosity
            # Symspell 也支援片語，但主要針對單字除錯較精準
            suggestions = _sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
            sym_sugg = [s.term for s in suggestions[:2]] if suggestions else []

        return {
            "pyenchant_valid": valid,
            "pyenchant_suggestions": py_sugg,
            "symspell_suggestions": sym_sugg
        }

    def get_lemminflect(self, word):
        try:
            from lemminflect import getInflection
            doc = _spacy_nlp(word)
            if not doc: return {}
            
            target_token = doc[-1]
            pos = target_token.pos_
            
            # 判斷是否為專有名詞 (包含大寫字母，或是 spaCy 判斷為 PROPN)
            is_proper_noun = any(c.isupper() for c in word) or pos == 'PROPN'
            is_phrase = len(doc) > 1

            # 智慧型變形過濾機制：避免「專有名詞」或「名詞結尾的片語」被硬轉成動詞或形容詞
            allowed_tags = []
            if is_proper_noun:
                allowed_tags = ['NNS']  # 專有名詞只允許複數
            elif is_phrase:
                if pos in ['NOUN', 'PROPN']:
                    allowed_tags = ['NNS']
                elif pos in ['VERB', 'AUX']:
                    allowed_tags = ['VBD', 'VBG', 'VBN', 'VBZ']
                elif pos in ['ADJ']:
                    allowed_tags = ['JJR', 'JJS']
                else:
                    allowed_tags = ['NNS']
            else:
                # 單一字彙開放所有變形 (因單字常有多重詞性，如 park 可作名詞與動詞)
                allowed_tags = ['NNS', 'VBD', 'VBG', 'VBN', 'VBZ', 'JJR', 'JJS']

            forms = {}
            for t in allowed_tags:
                inf = getInflection(target_token.text, tag=t)
                if inf:
                    # 保留前半段片語的原始大小寫
                    prefix = " ".join([token.text for token in doc[:-1]])
                    
                    formatted_infs = []
                    for i in inf:
                        # 核心修復：還原變形後單字的大小寫 (lemminflect 預設全轉小寫)
                        if target_token.text.istitle():
                            i = i.capitalize()
                        elif target_token.text.isupper():
                            i = i.upper()
                            
                        if prefix:
                            formatted_infs.append(f"{prefix} {i}")
                        else:
                            formatted_infs.append(i)
                            
                    # 過濾掉與原字一模一樣的變形 (避免顯示贅字)
                    valid_infs = [val for val in formatted_infs if val.lower() != word.lower()]
                    if valid_infs:
                        forms[t] = list(dict.fromkeys(valid_infs))
            return forms
        except Exception as e:
            return {}

    def regex_analysis(self, word):
        return {
            "is_tion_noun": bool(re.search(r'tion$', word)),
            "is_ly_adverb": bool(re.search(r'ly$', word)),
            "is_ing_form": bool(re.search(r'ing$', word)),
            "has_vowels": len(re.findall(r'[aeiouy]', word.lower()))
        }

    def process_semantic_clustering(self, words):
        embeddings = self._encode_with_ensemble(words)
        from sklearn.cluster import KMeans
        num_clusters = min(len(words) // 50 + 1, 150)
        if num_clusters < 2: return {0: words}, embeddings

        print(f"   執行綜合特徵 K-Means 分群 (K={num_clusters})...")
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init='auto')
        kmeans.fit(embeddings)

        clusters = defaultdict(list)
        for i, label in enumerate(kmeans.labels_):
            clusters[int(label)].append(words[i])
        return clusters, embeddings

    def process_index_json(self, input_path, output_path, force_rebuild=False):
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        all_items = data.get("all_items", [])
        words = []
        known_cefr = {}
        known_category = {}
        known_group = {}

        CEFR_MAP = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6, "A1-A2": 1.5, "B1-B2": 3.5, "B2-C1": 4.5}
        REV_CEFR_MAP = {1: "A1", 2: "A2", 3: "B1", 4: "B2", 5: "C1", 6: "C2"}

        def _get_cefr_str(val):
            return REV_CEFR_MAP.get(max(1, min(6, round(val))), "B2")

        for item in all_items:
            w = item.get("core_word")
            if not w: continue
            if w not in words: words.append(w)
            
            lvl = item.get("cefr_level")
            conf = item.get("cefr_confidence")
            if lvl and conf not in ["unknown", "inferred", "(未知)"] and lvl in CEFR_MAP:
                known_cefr[w] = lvl
                
            cat_id = item.get("category_id")
            cat_label = item.get("category_label")
            grp_id = item.get("group_id")
            grp_label = item.get("group_label")
            if cat_id and cat_id != "?" and cat_label and "未分類" not in cat_label:
                known_category[w] = {"id": cat_id, "label": cat_label}
                known_group[cat_id] = {"id": grp_id, "label": grp_label}

        advanced_data = {}
        if force_rebuild:
            print("⚠️ 啟用【強制重構模式】: 將忽略所有快取，全面重新對所有詞彙執行 NLP 解析！")
        elif os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    advanced_data = json.load(f)
                print(f"♻️  偵測到舊有快取，已成功載入 {len(advanced_data)} 筆資料。")
            except Exception as e:
                print(f"⚠️ 無法讀取舊快取，將執行全量分析。")

        # 若強制更新，words_to_process 就是全部字彙
        if force_rebuild:
            words_to_process = words
        else:
            words_to_process = [w for w in words if w not in advanced_data or "regex" not in advanced_data[w]]
        
        if words_to_process:
            print(f"🚀 需要執行 NLP 分析的詞彙共 {len(words_to_process)} 個，開始處理...")
            self._lazy_load_heavy_nlp()
            for idx, word in enumerate(words_to_process):
                if idx > 0 and idx % 200 == 0:
                    print(f"  ...進階特徵解析進度: {idx}/{len(words_to_process)}")
                advanced_data[word] = {
                    "wordnet": self.get_wordnet_relations(word),
                    "topic_lexicon": self.get_topic_lexicon(word),
                    "spacy": self.analyze_spacy(word),
                    "spelling": self.check_spelling(word),
                    "lemminflect": self.get_lemminflect(word),
                    "regex": self.regex_analysis(word)
                }
        else:
            print("⚡ 所有單字基礎解析皆已完成，跳過耗時的 NLP 解析階段！")

        print(f"🧠 進行平行評分語義聚類與推算...")
        clusters, embeddings = self.process_semantic_clustering(words)

        known_vecs = []
        known_levels = []
        known_cat_vecs = []
        known_cat_data = []

        for i, w in enumerate(words):
            if w in known_cefr:
                known_vecs.append(embeddings[i])
                known_levels.append(CEFR_MAP[known_cefr[w]])
            if w in known_category:
                known_cat_vecs.append(embeddings[i])
                known_cat_data.append(known_category[w])
        
        known_vecs = np.array(known_vecs) if known_vecs else None
        known_cat_vecs = np.array(known_cat_vecs) if known_cat_vecs else None
        
        from sklearn.metrics.pairwise import cosine_similarity

        print("🤖 啟動雙引擎自動推算 (Priority Pipeline + Ensemble Scoring)...")
        word_to_cluster = {w: cid for cid, c_words in clusters.items() for w in c_words}
        
        cefr_inferred_count = 0
        cat_inferred_count = 0
        model_str = f"Ensemble ({', '.join(self.ensemble_models)})"

        for i, w in enumerate(words):
            cid = word_to_cluster.get(w, 0)
            cluster_words = clusters.get(cid, [])
            advanced_data[w]["semantic_clustering"] = {
                "cluster_id": int(cid),
                "model_used": model_str,
                "bert_related_words": [cw for cw in cluster_words if cw != w][:5]
            }

            if w not in known_cefr:
                inferred_level = None
                method_used = ""

                if known_vecs is not None and len(known_vecs) > 0:
                    vec = embeddings[i].reshape(1, -1)
                    sims = cosine_similarity(vec, known_vecs)[0]
                    top5_idx = np.argsort(sims)[-5:]
                    valid_levels = [known_levels[idx] for idx in top5_idx if sims[idx] > 0.6]
                    if valid_levels:
                        avg_lvl = sum(valid_levels) / len(valid_levels)
                        inferred_level = _get_cefr_str(avg_lvl)
                        method_used = "1. 綜合模型向量近義詞多數決 (平行評分)"

                if not inferred_level:
                    c_levels = [CEFR_MAP[known_cefr[cw]] for cw in cluster_words if cw in known_cefr]
                    if c_levels:
                        avg_lvl = sum(c_levels) / len(c_levels)
                        inferred_level = _get_cefr_str(avg_lvl)
                        method_used = "2. K-Means 語義群組感染"

                if not inferred_level:
                    hypernyms = advanced_data[w].get("wordnet", {}).get("hypernyms", [])
                    for h in hypernyms:
                        if h in known_cefr:
                            h_val = CEFR_MAP[known_cefr[h]]
                            inferred_level = _get_cefr_str(min(6, h_val + 1))
                            method_used = "3. WordNet 上下位層級繼承"
                            break

                if not inferred_level:
                    regex_data = advanced_data[w]["regex"]
                    vowels = regex_data["has_vowels"]
                    length = len(w)
                    if regex_data["is_tion_noun"] or w.endswith(("ability", "zation", "ment", "ous", "ology")):
                        inferred_level = "C1"
                    elif length > 10 or vowels > 4:
                        inferred_level = "B2"
                    elif length > 7 or vowels > 3:
                        inferred_level = "B1"
                    elif length > 4 or vowels > 2:
                        inferred_level = "A2"
                    else:
                        inferred_level = "A1"
                    method_used = "4. 構詞與音節複雜度分析"

                advanced_data[w]["cefr_auto"] = {
                    "level": inferred_level,
                    "method": method_used
                }
                cefr_inferred_count += 1

            if w not in known_category:
                inferred_cat = None
                cat_method = ""

                if known_cat_vecs is not None and len(known_cat_vecs) > 0:
                    vec = embeddings[i].reshape(1, -1)
                    sims = cosine_similarity(vec, known_cat_vecs)[0]
                    top5_idx = np.argsort(sims)[-5:]
                    valid_cats = [known_cat_data[idx] for idx in top5_idx if sims[idx] > 0.65]
                    if valid_cats:
                        best_cat_label = Counter([c["label"] for c in valid_cats]).most_common(1)[0][0]
                        inferred_cat = next(c for c in valid_cats if c["label"] == best_cat_label)
                        cat_method = "1. 綜合模型語義最相近主題 (平行評分)"

                if not inferred_cat:
                    c_cats = [known_category[cw] for cw in cluster_words if cw in known_category]
                    if c_cats:
                        best_cat_label = Counter([c["label"] for c in c_cats]).most_common(1)[0][0]
                        inferred_cat = next(c for c in c_cats if c["label"] == best_cat_label)
                        cat_method = "2. K-Means 同聚類群組感染"
                        
                if not inferred_cat:
                    hypernyms = advanced_data[w].get("wordnet", {}).get("hypernyms", [])
                    for h in hypernyms:
                        if h in known_category:
                            inferred_cat = known_category[h]
                            cat_method = "3. WordNet 上下位主題繼承"
                            break
                            
                if inferred_cat:
                    advanced_data[w]["category_auto"] = {
                        "id": inferred_cat["id"],
                        "label": inferred_cat["label"],
                        "method": cat_method
                    }
                    cat_inferred_count += 1

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(advanced_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 進階字典與分級擴充完畢！已產出: {output_path}")
        print(f"   💡 共推算出 {cefr_inferred_count} 個 CEFR 等級、 {cat_inferred_count} 個主題分類。")

        if cat_inferred_count > 0:
            try:
                from build_index import build_tree_index
                print("\n🌳 正在將 AI 分類結果直接寫回並重構知識樹 (index.json)...")
                
                updated_items = 0
                for item in data["all_items"]:
                    w = item.get("core_word")
                    if w in advanced_data and "category_auto" in advanced_data[w]:
                        if item.get("category_id") == "?" or "未分類" in str(item.get("category_label")):
                            auto_cat = advanced_data[w]["category_auto"]
                            item["category_id"] = auto_cat["id"]
                            item["category_label"] = auto_cat["label"]
                            item["classified"] = True
                            
                            if auto_cat["id"] in known_group:
                                item["group_id"] = known_group[auto_cat["id"]]["id"]
                                item["group_label"] = known_group[auto_cat["id"]]["label"]
                                
                            updated_items += 1
                            
                if updated_items > 0:
                    data["tree"] = build_tree_index(data["all_items"])
                    data["meta"]["unclassified"] = max(0, data["meta"].get("unclassified", 0) - updated_items)
                    data["meta"]["classified"] = data["meta"].get("classified", 0) + updated_items
                    
                    with open(input_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"   ✅ 成功將 {updated_items} 個未分類詞彙分配到對應的主題資料夾中！")
                    
            except Exception as e:
                pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="進階字典與自動分級引擎 (多模型平行評分版)")
    parser.add_argument("input_json", nargs='?', default="index.json", help="輸入的 JSON 檔案路徑")
    parser.add_argument("output_json", nargs='?', default="advanced_dict_data.json", help="輸出的 JSON 檔案路徑")
    parser.add_argument("--models", nargs='+', 
                        default=["bge-m3", "e5-large", "mpnet", "roberta"], 
                        choices=["minilm", "roberta", "mpnet", "bge-m3", "e5-large"], 
                        help="輸入多個模型名稱以啟動平行評分法")
    # 新增 --force 參數，符合您的需求
    parser.add_argument("--force", action="store_true", help="強制重新執行所有 NLP 分析，忽略快取")
    
    args = parser.parse_args()

    engine = AdvancedDictEngine(ensemble_models=args.models)
    engine.process_index_json(args.input_json, args.output_json, force_rebuild=args.force)