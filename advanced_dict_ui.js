/**
 * advanced_dict_ui.js
 * ===================
 * 零干涉前端注入器 (卡片精準定位版)。
 * 解決：點擊空白處會直接開啟 HTML 的問題。
 * 策略：攔截空白處點擊、阻止預設跳轉、並模擬點擊最深層單字以喚出原系統選單。
 */

(function() {
    'use strict';

    let advancedData = {};
    let isDataLoaded = false;

    // 詞性縮寫翻譯字典
    const POS_MAPPING = {
        "NN": "單數名詞 (NN)", "NNS": "複數名詞 (NNS)",
        "VB": "動詞原形 (VB)", "VBD": "過去式動詞 (VBD)",
        "VBG": "現在分詞/動名詞 (VBG)", "VBN": "過去分詞 (VBN)",
        "VBP": "現在式動詞 (VBP)", "VBZ": "第三人稱單數動詞 (VBZ)",
        "JJ": "形容詞 (JJ)", "JJR": "比較級形容詞 (JJR)", "JJS": "最高級形容詞 (JJS)",
        "RB": "副詞 (RB)", "RBR": "比較級副詞 (RBR)", "RBS": "最高級副詞 (RBS)"
    };

    // 主題情境分類翻譯字典
    const LEXNAME_MAPPING = {
        "noun.Tops": "抽象概念 (Abstract)", "noun.act": "行為活動 (Action)",
        "noun.animal": "動物 (Animal)", "noun.artifact": "人造物品 (Artifact)",
        "noun.attribute": "屬性特質 (Attribute)", "noun.body": "身體部位 (Body)",
        "noun.cognition": "認知思想 (Cognition)", "noun.communication": "溝通表達 (Communication)",
        "noun.event": "事件 (Event)", "noun.feeling": "感覺情緒 (Feeling)",
        "noun.food": "飲食 (Food)", "noun.group": "群體組織 (Group)",
        "noun.location": "地點位置 (Location)", "noun.motive": "動機目的 (Motive)",
        "noun.object": "自然物體 (Object)", "noun.person": "人物角色 (Person)",
        "noun.phenomenon": "自然現象 (Phenomenon)", "noun.plant": "植物 (Plant)",
        "noun.possession": "財產所有權 (Possession)", "noun.process": "過程 (Process)",
        "noun.quantity": "數量單位 (Quantity)", "noun.relation": "關係 (Relation)",
        "noun.shape": "形狀 (Shape)", "noun.state": "狀態條件 (State)",
        "noun.substance": "物質材料 (Substance)", "noun.time": "時間 (Time)",
        "verb.body": "身體動作 (Body Action)", "verb.change": "改變變化 (Change)",
        "verb.cognition": "思考認知 (Thinking)", "verb.communication": "溝通交流 (Communication)",
        "verb.competition": "競爭對抗 (Competition)", "verb.consumption": "消耗飲食 (Consumption)",
        "verb.contact": "接觸動作 (Contact)", "verb.creation": "創造發明 (Creation)",
        "verb.emotion": "情緒反應 (Emotion)", "verb.motion": "移動行進 (Motion)",
        "verb.perception": "感知察覺 (Perception)", "verb.possession": "擁有轉讓 (Possession)",
        "verb.social": "社交互動 (Social)", "verb.stative": "狀態 (Stative)",
        "verb.weather": "天氣氣象 (Weather)",
        "adj.all": "一般形容詞 (Adjective)", "adj.pert": "關聯形容詞 (Relational)",
        "adj.ppl": "分詞形容詞 (Participle)", "adv.all": "副詞 (Adverb)"
    };

    fetch('/advanced_dict_data.json')
        .then(response => response.json())
        .then(data => {
            advancedData = data;
            isDataLoaded = true;
            console.log("✅ Advanced Dictionary Data Loaded:", Object.keys(data).length, "words");
        })
        .catch(err => console.warn("⚠️ 找不到 advanced_dict_data.json，請先執行 advanced_dict_engine.py"));

    const style = document.createElement('style');
    style.innerHTML = `
        #advDictPanel {
            position: fixed; top: 80px; right: 30px; width: 420px; max-height: 80vh;
            background: white; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            border: 1px solid #CBD5E1; border-radius: 12px; z-index: 9999;
            display: none; flex-direction: column; overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        #advDictPanel.open { display: flex; }
        .adv-header {
            background: #1E293B; color: white; padding: 15px; display: flex;
            justify-content: space-between; align-items: center; cursor: move;
            user-select: none; border-bottom: 3px solid #3B82F6;
        }
        .adv-header h2 { margin: 0; font-size: 16px; pointer-events: none; }
        .adv-close { cursor: pointer; font-weight: bold; font-size: 18px; padding: 0 5px; }
        .adv-close:hover { color: #EF4444; }
        .adv-content { padding: 15px; overflow-y: auto; flex-grow: 1; font-size: 14px; color: #333; }
        .adv-section { margin-bottom: 15px; background: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0; }
        .adv-section h3 { margin: 0 0 10px 0; font-size: 14px; color: #1D4ED8; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px; }
        .adv-row { margin-bottom: 6px; line-height: 1.4; }
        .adv-label { font-weight: 600; color: #475569; margin-right: 5px; }
        .adv-tag { display: inline-block; background: #E0E7FF; color: #3730A3; padding: 4px 8px; border-radius: 12px; font-size: 12px; margin: 2px; border: 1px solid #C7D2FE; }
        .adv-badge { background: #DCFCE7; color: #166534; border-color: #BBF7D0;}
        .adv-badge-warn { background: #FEF08A; color: #854D0E; border-color: #FDE047;}
    `;
    document.head.appendChild(style);

    const panel = document.createElement('div');
    panel.id = 'advDictPanel';
    panel.innerHTML = `
        <div class="adv-header" id="advDictHeader">
            <h2 id="advWordTitle">AI 進階字典</h2>
            <div class="adv-close" id="advCloseBtn">✕</div>
        </div>
        <div class="adv-content" id="advContent"></div>
    `;
    document.body.appendChild(panel);

    const header = document.getElementById('advDictHeader');
    let isDragging = false, offsetX, offsetY;

    header.addEventListener('mousedown', function(e) {
        if (e.target.id === 'advCloseBtn') return;
        isDragging = true;
        const rect = panel.getBoundingClientRect();
        offsetX = e.clientX - rect.left; offsetY = e.clientY - rect.top;
        panel.style.right = 'auto'; panel.style.bottom = 'auto';
        panel.style.left = rect.left + 'px'; panel.style.top = rect.top + 'px';
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    });

    function onMouseMove(e) {
        if (!isDragging) return;
        let newX = Math.max(0, Math.min(e.clientX - offsetX, window.innerWidth - panel.offsetWidth));
        let newY = Math.max(0, Math.min(e.clientY - offsetY, window.innerHeight - header.offsetHeight));
        panel.style.left = newX + 'px'; panel.style.top = newY + 'px';
    }

    function onMouseUp() {
        isDragging = false;
        document.removeEventListener('mousemove', onMouseMove); document.removeEventListener('mouseup', onMouseUp);
    }

    document.getElementById('advCloseBtn').addEventListener('click', () => panel.classList.remove('open'));

    // --- 🚀 尋找外層容器與單字 ---
    function findMainWordAndElement(startElem) {
        let current = startElem;
        let explicitNode = current.closest('[data-word]');
        if (explicitNode && explicitNode.dataset.word) {
            return { word: explicitNode.dataset.word.trim().toLowerCase(), element: explicitNode };
        }

        for (let i = 0; i < 4; i++) {
            if (!current || current === document.body || current === document.documentElement) break;
            
            let text = current.innerText; 
            if (text === undefined) text = current.textContent || "";
            text = text.trim();
            
            if (text.length > 0 && text.length <= 250) {
                let firstLine = text.split(/[\n\r]+/)[0].trim();
                let match = firstLine.match(/^([a-zA-Z\-\s]+)/);
                if (match && match[1]) {
                    let candidate = match[1].trim().replace(/\s+/g, ' ').toLowerCase();
                    
                    if (advancedData[candidate]) {
                        let uiLabels = ['full', 'essentials', 'layer', 'group', 'search', 'all', 'none'];
                        if (uiLabels.includes(candidate)) {
                            let p = current.parentElement;
                            if (p && p !== document.body) {
                                let pText = (p.innerText !== undefined ? p.innerText : p.textContent).trim();
                                if (pText.length > 0 && pText.length <= 250) {
                                    let pFirstLine = pText.split(/[\n\r]+/)[0].trim();
                                    let pMatch = pFirstLine.match(/^([a-zA-Z\-\s]+)/);
                                    if (pMatch && pMatch[1]) {
                                        let pCandidate = pMatch[1].trim().replace(/\s+/g, ' ').toLowerCase();
                                        if (advancedData[pCandidate] && pCandidate !== candidate) {
                                            return { word: pCandidate, element: p }; 
                                        }
                                    }
                                }
                            }
                        }
                        return { word: candidate, element: current };
                    }
                }
            }
            current = current.parentElement;
        }
        return null;
    }

    // --- 🚀 尋找最深層的文字節點 (原系統綁定點擊事件的目標) ---
    function getInnermostWordElement(container, word) {
        let target = container;
        let children = container.getElementsByTagName('*');
        for (let i = 0; i < children.length; i++) {
            let child = children[i];
            if (child.tagName === 'SCRIPT' || child.tagName === 'STYLE') continue;
            
            let text = child.innerText;
            if (text === undefined) text = child.textContent || "";
            text = text.trim();
            
            let firstLine = text.split(/[\n\r]+/)[0].trim().toLowerCase();
            let match = firstLine.match(/^([a-z\-\s]+)/);
            if (match && match[1]) {
                let candidate = match[1].trim().replace(/\s+/g, ' ');
                if (candidate === word) {
                    target = child; // 一路向下更新，直到最深層
                }
            }
        }
        return target;
    }

    // --- 攔截點擊事件 ---
    document.addEventListener('click', function(e) {
        // 不要攔截浮動面板本身的點擊
        if (e.target.closest('#advDictPanel')) return;
        if (!isDataLoaded) return;
        
        // 【極致防護】：忽略我們自己模擬的點擊，防止無窮迴圈
        if (!e.isTrusted) return;

        let result = findMainWordAndElement(e.target);

        if (result && advancedData[result.word]) {
            showAdvancedDict(result.word);

            // 尋找真正包含單字的最深層元素
            let innermost = getInnermostWordElement(result.element, result.word);
            
            let targetText = (e.target.innerText !== undefined ? e.target.innerText : e.target.textContent).trim();
            let targetFirstLine = targetText.split(/[\n\r]+/)[0].trim().toLowerCase();
            
            let isBlankSpace = false;
            
            // 判斷使用者是否點擊了「空白處」
            if (e.target === result.element) {
                // 點擊最外層容器 = 點擊背景空白
                isBlankSpace = true;
            } else if (targetFirstLine.startsWith(result.word)) {
                // 點擊的區塊包含單字，但並非最深層文字節點 (代表點在文字外圍 padding)
                isBlankSpace = (e.target !== innermost);
            } else {
                // 如果點擊的是沒有文字的結構元素 (且不是按鈕或標籤等互動元件)
                let isInteractive = e.target.closest('button, [class*="btn"], [class*="badge"], [class*="tag"]');
                if (targetText === "" && !isInteractive) {
                    isBlankSpace = true;
                }
            }

            // 【核心修復】：如果判定是點擊空白處
            if (isBlankSpace && innermost && e.target !== innermost) {
                e.preventDefault();   // 1. 擋下預設的 <a> 標籤跳轉行為，防止開啟 HTML
                e.stopPropagation();  // 2. 防止事件亂冒泡
                innermost.click();    // 3. 模擬精準點擊最深層單字，喚醒原系統的右側學習選單
            }
        }
    }, true);

    function showAdvancedDict(word) {
        const data = advancedData[word];
        const contentDiv = document.getElementById('advContent');
        document.getElementById('advWordTitle').innerText = word.toUpperCase();

        if (!data) {
            contentDiv.innerHTML = `<p style="color:red; text-align:center; padding:20px;">目前沒有 "${word}" 的進階字典資料。</p>`;
            panel.classList.add('open');
            return;
        }

        let html = '';

        if (data.wordnet && (data.wordnet.hypernyms.length > 0 || data.wordnet.rogets_thesaurus.synonyms.length > 0)) {
            html += `<div class="adv-section">
                <h3>📚 同義詞與上位詞 (WordNet & Thesaurus)</h3>
                <div class="adv-row"><span class="adv-label">上位詞 (Hypernyms):</span> ${data.wordnet.hypernyms.join(', ') || '無'}</div>
                <div class="adv-row"><span class="adv-label">同義詞 (Synonyms):</span> ${data.wordnet.rogets_thesaurus.synonyms.join(', ') || '無'}</div>
            </div>`;
        }

        if (data.topic_lexicon && data.topic_lexicon.topics && data.topic_lexicon.topics.length > 0) {
            html += `<div class="adv-section">
                <h3>🏷️ 主題情境分類 (Topic Lexicon)</h3>
                ${data.topic_lexicon.topics.map(t => `<span class="adv-tag">${LEXNAME_MAPPING[t] || t}</span>`).join('')}
            </div>`;
        }

        if (data.spacy && Object.keys(data.spacy).length > 0) {
            html += `<div class="adv-section">
                <h3>🤖 詞性與句法分析 (NLP Analysis)</h3>
                <span class="adv-tag adv-badge">詞性 (POS): ${data.spacy.pos}</span>
                <span class="adv-tag adv-badge">標籤 (TAG): ${data.spacy.tag}</span>
                <span class="adv-tag ${data.spacy.is_stop ? 'adv-badge-warn' : 'adv-badge'}">停用詞: ${data.spacy.is_stop ? '是' : '否'}</span>
            </div>`;
        }

        if (data.semantic_clustering) {
            const modelUsed = data.semantic_clustering.model_used || "預設模型";
            html += `<div class="adv-section">
                <h3>🌌 AI 語義群組聚類 (Semantic Clustering)</h3>
                <div class="adv-row"><span class="adv-label">群組編號 (Cluster ID):</span> 第 ${data.semantic_clustering.cluster_id} 群</div>
                <div class="adv-row"><span class="adv-label">聚類模型:</span> <span class="adv-tag">${modelUsed}</span></div>
                <div class="adv-row"><span class="adv-label">AI 關聯詞:</span><br>
                    ${data.semantic_clustering.bert_related_words.map(w => `<span class="adv-tag">${w}</span>`).join('') || '無'}
                </div>
            </div>`;
        }

        if (data.lemminflect && Object.keys(data.lemminflect).length > 0) {
            let inflectHtml = Object.entries(data.lemminflect)
                .map(([k, v]) => `<div class="adv-row"><span class="adv-label">${POS_MAPPING[k] || k}:</span> ${v.join(', ')}</div>`).join('');
            html += `<div class="adv-section">
                <h3>🔄 詞彙變形 (Word Forms)</h3>
                <div style="font-size:13px;">${inflectHtml}</div>
            </div>`;
        }

        if (data.spelling) {
            html += `<div class="adv-section">
                <h3>✅ 拼字校正與建議 (Spelling Check)</h3>
                <div class="adv-row"><span class="adv-label">字典驗證 (Enchant Valid):</span> ${data.spelling.pyenchant_valid ? '合法詞彙' : '拼字可疑'}</div>
                <div class="adv-row"><span class="adv-label">拼字建議:</span> ${data.spelling.symspell_suggestions.join(', ') || '無'}</div>
            </div>`;
        }

        contentDiv.innerHTML = html;
        panel.classList.add('open');
    }

})();