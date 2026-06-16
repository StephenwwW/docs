/**
 * 獨立語音擴充模組 (TTS Extension) - v7.1 (完美修復版)
 * 包含：直接點擊文字發音、完整 TTS 引擎清單支援。
 * 修復：移除了過度暴力的阻擋規則，改用「事件捕獲」技術完美隔離側邊欄，絕不誤殺主畫面。
 */

(function() {
    'use strict';
    
    if (typeof document === 'undefined' || typeof speechSynthesis === 'undefined') return;

    const TTS_CONFIG = {
        provider: 'Google TTS',
        speed: 1.0,
        language: 'en-US',
        persona: '', 
        providers: [
            'Google TTS', 
            'Microsoft TTS',
            'ElevenLabs', 
            'OpenAI', 
            'Play.ht', 
            'Murf.ai',
            'GPT-SoVITS', 
            'F5-TTS', 
            'Fish Speech', 
            'ChatTTS-WebUI / GPT-SoVITS-WebUI',
            'Open Voice OS / Piper'
        ]
    };

    let voicesLoaded = false;
    let currentVoicePersona = {};

    const LANGUAGES = {
        'en-US': { label: '🇺🇸 美式 English (US)' },
        'en-GB': { label: '🇬🇧 英式 English (UK)' },
        'en-CA': { label: '🇨🇦 加式 English (CA)' },
        'en-AU': { label: '🇦🇺 澳式 English (AU)' },
        'ja-JP': { label: '🇯🇵 日文 Japanese' }
    };

    const VOICE_MAP = {
        'google': { 
            'en-US': ['Google US English'], 
            'en-GB': ['Google UK English Female', 'Google UK English Male'], 
            'en-CA': [], 'en-AU': [], 
            'ja-JP': ['Google 日本語'] 
        },
        'microsoft': { 
            'en-US': ['Microsoft David', 'Microsoft Mark', 'Microsoft Zira'], 
            'en-GB': ['Microsoft George', 'Microsoft Hazel', 'Microsoft Susan'], 
            'en-CA': ['Microsoft Linda', 'Microsoft Richard'], 
            'en-AU': ['Microsoft James', 'Microsoft Catherine'], 
            'ja-JP': ['Microsoft Ayumi', 'Microsoft Haruka', 'Microsoft Ichiro', 'Microsoft Sayaka'] 
        }
    };

    function injectStyles() {
        if (document.getElementById('tts-filter-styles')) return;
        const style = document.createElement('style');
        style.id = 'tts-filter-styles';
        style.textContent = `
            .tts-text-flash { color: #3B82F6 !important; transition: color 0.15s ease-in-out; }
            #tts-floating-btn { position: fixed; bottom: 24px; right: 24px; width: 48px; height: 48px; background-color: #0F172A; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); cursor: pointer; z-index: 9999; transition: transform 0.2s, background-color 0.2s; }
            #tts-floating-btn:hover { transform: scale(1.05); background-color: #1E293B; }
            #tts-config-panel { position: fixed; bottom: 84px; right: 24px; width: 280px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.12); padding: 16px; z-index: 9998; opacity: 0; pointer-events: none; transform: translateY(10px); transition: opacity 0.3s, transform 0.3s; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            #tts-config-panel.open { opacity: 1; pointer-events: auto; transform: translateY(0); }
            #tts-config-panel h3 { margin: 0 0 12px 0; font-size: 16px; color: #0F172A; display: flex; align-items: center; gap: 8px; }
            .tts-form-group { margin-bottom: 12px; }
            .tts-form-group label { display: block; font-size: 12px; color: #64748B; margin-bottom: 6px; }
            .tts-form-group select { width: 100%; padding: 8px; border-radius: 6px; border: 1px solid #CBD5E1; background: #F8FAFC; color: #0F172A; font-size: 14px; outline: none; cursor: pointer; }
            .tts-form-group select:focus { border-color: #3B82F6; }
        `;
        document.head.appendChild(style);
    }

    function injectUI() {
        if (document.getElementById('tts-floating-btn')) return;

        const speakerIcon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>`;
        const settingsIcon = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>`;

        const btn = document.createElement('div');
        btn.id = 'tts-floating-btn';
        btn.innerHTML = settingsIcon;
        document.body.appendChild(btn);

        const panel = document.createElement('div');
        panel.id = 'tts-config-panel';
        
        let providerOptions = TTS_CONFIG.providers.map(p => `<option value="${p}" ${p === TTS_CONFIG.provider ? 'selected' : ''}>${p}</option>`).join('');
        let langOptions = Object.entries(LANGUAGES).map(([code, { label }]) => `<option value="${code}" ${code === TTS_CONFIG.language ? 'selected' : ''}>${label}</option>`).join('');
        let speedOptions = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0].map(s => `<option value="${s}" ${s === TTS_CONFIG.speed ? 'selected' : ''}>x${s.toFixed(2)}</option>`).join('');

        panel.innerHTML = `
            <h3>${speakerIcon} 語音進階設定</h3>
            <div class="tts-form-group">
                <label>發音引擎 (Engine)</label>
                <select id="tts-provider-select">${providerOptions}</select>
            </div>
            <div class="tts-form-group" id="tts-lang-group">
                <label>播放語言 (Language)</label>
                <select id="tts-lang-select">${langOptions}</select>
            </div>
            <div class="tts-form-group" id="tts-persona-group">
                <label>人物音色 (Persona)</label>
                <select id="tts-persona-select"></select>
            </div>
            <div class="tts-form-group">
                <label>播放語速 (Speed)</label>
                <select id="tts-speed-select">${speedOptions}</select>
            </div>
        `;
        document.body.appendChild(panel);

        btn.addEventListener('click', (e) => { e.stopPropagation(); panel.classList.toggle('open'); });
        document.addEventListener('click', (e) => { if (!panel.contains(e.target) && e.target !== btn) panel.classList.remove('open'); });

        document.getElementById('tts-provider-select').addEventListener('change', (e) => {
            TTS_CONFIG.provider = e.target.value;
            updatePersonaSelect();
        });
        document.getElementById('tts-lang-select').addEventListener('change', (e) => {
            TTS_CONFIG.language = e.target.value;
            updatePersonaSelect();
        });
        document.getElementById('tts-persona-select').addEventListener('change', (e) => {
            TTS_CONFIG.persona = e.target.value;
            const engineKey = TTS_CONFIG.provider.split(' ')[0].toLowerCase();
            currentVoicePersona[`${engineKey}-${TTS_CONFIG.language}`] = e.target.value || null;
        });
        document.getElementById('tts-speed-select').addEventListener('change', (e) => {
            TTS_CONFIG.speed = parseFloat(e.target.value);
        });

        updatePersonaSelect(); 
    }

    function updatePersonaSelect() {
        const personaSelect = document.getElementById('tts-persona-select');
        const personaGroup = document.getElementById('tts-persona-group');
        if (!personaSelect) return;
        
        personaSelect.innerHTML = '<option value="">自動選擇</option>';
        
        const engineKey = TTS_CONFIG.provider.split(' ')[0].toLowerCase();
        const isBrowserNative = ['google', 'microsoft'].includes(engineKey);
        
        if (isBrowserNative) {
            const voiceList = VOICE_MAP[engineKey]?.[TTS_CONFIG.language] || [];
            voiceList.forEach(voiceName => {
                const option = document.createElement('option');
                const persona = voiceName.replace(/^(Microsoft|Google)\s*/i, '').trim();
                let displayName = persona;
                if (voiceName.includes('UK English Female')) displayName = 'UK Female';
                else if (voiceName.includes('UK English Male')) displayName = 'UK Male';
                else if (voiceName.includes('US English')) displayName = 'US Default';
                
                option.value = persona;
                option.textContent = displayName;
                
                if (currentVoicePersona[`${engineKey}-${TTS_CONFIG.language}`] === persona) {
                    option.selected = true;
                    TTS_CONFIG.persona = persona;
                }
                personaSelect.appendChild(option);
            });
            personaGroup.style.display = voiceList.length > 0 ? 'block' : 'none';
        } else {
            personaGroup.style.display = 'none';
        }
    }

    function processForNaturalSpeech(text, lang) {
        if (!text || !lang.startsWith('en')) return text;
        return text.split(/\s+/).join(' ');
    }
    
    function splitIntoChunks(text, maxLength = 150) {
        if (text.length <= maxLength) return [text];
        const chunks = []; 
        const sentences = text.split(/([.!?;:，。！？；：]+\s*)/);
        let current = '';
        for (let i = 0; i < sentences.length; i++) {
            const part = sentences[i];
            if ((current + part).length > maxLength && current.length > 0) { 
                chunks.push(current.trim()); 
                current = part; 
            } else { current += part; }
        }
        if (current.trim()) chunks.push(current.trim());
        return chunks.length > 0 ? chunks : [text];
    }

    function extractEnglishWords(text) {
        if (!text || !/[a-zA-Z]/.test(text)) return null;

        const blockPatterns = [
            /第[一二三四五]層/i, /Scene Tags/i, /Etymology/i, /Core Meaning/i, /Brain-to-Mouth/i,
            /Meanings?\s*&\s*Contexts?/i, /Natural Dialogue/i, /Semantic Contrast/i, /Common Mistakes/i,
            /Spoken vs\.?\s*Written/i, /Cultural Notes/i, /Word Family/i, /High-Frequency Collocations/i,
            /Trigger phrases/i, /Transition phrases/i, /Reaction phrases/i, /Emotion Intensity Scale/i,
            /Session ID/i, /Target Word/i, /【嚴格輸出格式】/i, /^Meaning\s*\d+/i
        ];
        for (let pattern of blockPatterns) { if (pattern.test(text)) return null; }

        let cleaned = text;
        cleaned = cleaned.replace(/^[a-zA-Z0-9]{1,10}:\s*/g, ''); 
        cleaned = cleaned.replace(/^[\*\-・\d\s]*((例句|錯誤|正確|我可以這樣說|語境|翻譯|原因|記憶口訣|Template|Meaning)[^：]*：?)\s*/gi, '');
        cleaned = cleaned.replace(/[(（].*?[)）]/g, ' '); 
        cleaned = cleaned.replace(/[\[【][^\[\]【】]*[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+[^\[\]【】]*[\]】]/g, ' ');
        cleaned = cleaned.replace(/^[\d\s*.⭐\-]+\s*/g, '');

        const segments = cleaned.match(/[a-zA-Z\s'’.,!?-]+/g);
        if (!segments || segments.length === 0) return null;

        const valid = segments.map(s => s.trim()).filter(s => {
            if (!/[a-zA-Z]/.test(s)) return false; 
            if (s.length === 1 && !/^[IaA]$/.test(s)) return false; 
            if (/^(v|n|adj|adv|prep|conj|pron|phr|vi|vt)$/i.test(s.trim())) return false; 
            return true;
        });

        if (valid.length === 0) return null;
        const finalStr = valid.join(', ').trim();
        return /[a-zA-Z]/.test(finalStr) ? finalStr : null;
    }

    function selectBestVoice(lang) {
        const engineKey = TTS_CONFIG.provider.split(' ')[0].toLowerCase();
        if (!['google', 'microsoft'].includes(engineKey)) return null;

        const voices = speechSynthesis.getVoices();
        if (!voices || voices.length === 0) return null;
        
        const langPrefix = lang.split('-')[0];
        const personaKey = `${engineKey}-${lang}`;
        const preferredPersona = currentVoicePersona[personaKey];
        const voiceList = VOICE_MAP[engineKey]?.[lang] || [];

        if (preferredPersona) {
            const exactMatch = voices.find(v => v.name.includes(preferredPersona));
            if (exactMatch) return exactMatch;
        }
        for (const voiceName of voiceList) {
            const match = voices.find(v => v.name.includes(voiceName));
            if (match) return match;
        }

        let candidates = [];
        for (const voice of voices) {
            const voiceName = voice.name.toLowerCase();
            const engineMatch = voiceName.includes(engineKey);
            let score = 0;
            if (voice.lang === lang) score = engineMatch ? 4 : 2;
            else if (voice.lang.startsWith(langPrefix)) score = engineMatch ? 3 : 1;
            if (score > 0) candidates.push({ voice: voice, score: score });
        }
        
        if (candidates.length === 0) return voices.find(v => v.lang.startsWith(langPrefix)) || null;
        candidates.sort((a, b) => b.score - a.score);
        return candidates[0].voice;
    }

    async function speakWord(text, targetElement = null) {
        if (!text) return;
        
        let cleanedText = text.replace(/[^a-zA-Z0-9\s'’.,;:()\[\]!?-]/g, ''); 
        cleanedText = cleanedText.replace(/^[^a-zA-Z0-9('’]+|[^a-zA-Z0-9)'’.,!?]+$/g, '').trim();
        cleanedText = cleanedText.replace(/\s+/g, ' ').trim();
        if (!cleanedText) return;

        if (speechSynthesis.speaking) speechSynthesis.cancel();
        console.log(`[TTS] 播放: "${cleanedText}" | 引擎: ${TTS_CONFIG.provider} | 語速: ${TTS_CONFIG.speed}x`);

        if (targetElement) {
            targetElement.classList.add('tts-text-flash');
            setTimeout(() => targetElement.classList.remove('tts-text-flash'), 400);
        }

        const engineKey = TTS_CONFIG.provider.split(' ')[0].toLowerCase();
        const isBrowserNative = ['google', 'microsoft'].includes(engineKey);

        if (isBrowserNative) {
            const processedText = processForNaturalSpeech(cleanedText, TTS_CONFIG.language);
            const chunks = splitIntoChunks(processedText);
            const voice = selectBestVoice(TTS_CONFIG.language);

            let chunkIndex = 0;
            function playNext() {
                if (chunkIndex >= chunks.length) return;
                const utterance = new SpeechSynthesisUtterance(chunks[chunkIndex]);
                utterance.lang = TTS_CONFIG.language;
                const naturalRate = TTS_CONFIG.speed <= 1.0 ? TTS_CONFIG.speed * 0.95 : TTS_CONFIG.speed * 0.98;
                utterance.rate = Math.max(0.5, Math.min(2.0, naturalRate));
                if (voice) utterance.voice = voice;
                
                utterance.onend = () => { chunkIndex++; setTimeout(playNext, 80); };
                utterance.onerror = () => { chunkIndex++; setTimeout(playNext, 100); };
                window.speechSynthesis.speak(utterance);
            }
            playNext();
        } else {
            console.log(`[TTS提示] 準備呼叫外部伺服器 API: ${TTS_CONFIG.provider}`);
            const tempUtterance = new SpeechSynthesisUtterance(cleanedText);
            tempUtterance.lang = 'en-US';
            tempUtterance.rate = TTS_CONFIG.speed;
            window.speechSynthesis.speak(tempUtterance);
        }
    }

    function setupGlobalClickListener() {
        // 【關鍵技術】：這裡最後一個參數傳入 true (啟用事件捕獲階段)
        // 這能確保我們在 index.html 改變 DOM 結構之前，就能第一時間截獲點擊目標。
        document.addEventListener('click', (e) => {
            if (!e.target || typeof e.target.closest !== 'function') return;

            // 1. 【完美排除左側邊欄與上方標題】
            // 只要是在這兩個區域內的點擊，一律無視
            if (e.target.closest('.sidebar') || e.target.closest('#sidebar') || e.target.closest('.topbar')) {
                return;
            }

            // 2. 排除 TTS 設定面板與浮動按鈕
            if (e.target.closest('#tts-config-panel') || e.target.closest('#tts-floating-btn')) {
                return;
            }

            // 3. 排除原生功能標籤（避免干擾展開卡片、超連結等）
            if (e.target.closest('button') || e.target.closest('a') || e.target.closest('input') || e.target.closest('summary') || e.target.closest('details')) {
                return;
            }

            // 4. 取得點擊目標最直接的文字內容
            let text = "";
            for (let childNode of e.target.childNodes) {
                if (childNode.nodeType === Node.TEXT_NODE) {
                    text += childNode.nodeValue + " ";
                }
            }
            text = text.trim();
            if (!text) text = e.target.textContent?.trim() || "";

            // 5. 常見 UI 介面關鍵字防護 (點擊到卡片背景等)
            const uiKeywords = ['展開', '心智圖', 'essentials', 'Full', 'CEFR', '高頻', 'DOLCH', 'FRY', 'Group', 'Category', 'Tier'];
            if (uiKeywords.some(kw => text.includes(kw))) return;

            // 6. 萃取純英文，若符合條件則觸發發音
            const englishText = extractEnglishWords(text);
            if (englishText && englishText.length > 0 && englishText.length < 100) {
                // 不阻擋原本事件 (不用 preventDefault)，確保原本的 index.html 展開功能順利執行
                speakWord(englishText, e.target);
            }
        }, true); // <=== 啟動 Capture Phase，這是本次修復的核心
    }

    function initialize() { 
        injectStyles(); 
        injectUI(); 
        setupGlobalClickListener(); 
    }

    function waitForVoices(callback) {
        const voices = speechSynthesis.getVoices();
        if (voices.length > 0) { 
            voicesLoaded = true; 
            callback(); 
        } else { 
            setTimeout(() => waitForVoices(callback), 100); 
        }
    }

    if (document.readyState === 'loading') { 
        document.addEventListener('DOMContentLoaded', () => waitForVoices(initialize)); 
    } else { 
        waitForVoices(initialize); 
    }

    if (speechSynthesis.onvoiceschanged !== undefined) { 
        speechSynthesis.onvoiceschanged = () => { 
            if (!voicesLoaded) { voicesLoaded = true; initialize(); } 
        }; 
    }

    window.VocabTTS = {
        play: speakWord,
        getConfig: () => TTS_CONFIG
    };

})();