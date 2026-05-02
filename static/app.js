// app.js

let APP_CONFIG = null;
let CITIES_ORDER = ["london", "miami"];
let LAST_RESULTS = JSON.parse(sessionStorage.getItem('LAST_RESULTS') || '{}');

function saveLastResults() {
    sessionStorage.setItem('LAST_RESULTS', JSON.stringify(LAST_RESULTS));
}

document.addEventListener("DOMContentLoaded", () => {
    initApp();
    
    // Checkbox auto AI listener
    document.getElementById("auto-ai-toggle").addEventListener("change", (e) => {
        if(e.target.checked) showStatus("Алго ИИ: Активен", "var(--color-buy)");
        else showStatus("Алго ИИ: Отключен", "var(--text-secondary)");
    });

    // Enter key sending
    document.getElementById("ai-input").addEventListener("keypress", (e) => {
        if(e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendChat();
        }
    });

    setInterval(updateClocks, 1000);
});

async function initApp() {
    try {
        const res = await fetch("/api/config");
        if (!res.ok) throw new Error("Failed to load config");
        APP_CONFIG = await res.json();
        
        buildControls();
        initAISettings();
        updateClocks();
        
    } catch(e) {
        showStatus("Ошибка связи с сервером!", "var(--color-sell)");
        console.error(e);
    }
}

function updateClocks() {
    const d = new Date();
    document.getElementById("time-utc").innerText = d.toISOString().substr(11, 5);
    
    const fmt = (tz) => new Intl.DateTimeFormat('en-GB', {timeZone: tz, hour: '2-digit', minute:'2-digit', hour12: false}).format(d);
    
    try {
        if(APP_CONFIG) {
            document.getElementById("time-lon").innerText = fmt('Europe/London');
            document.getElementById("time-mia").innerText = fmt('America/New_York');
        }
    } catch(e) {}
}

function setDate(cityKey, offsetDays) {
    const d = new Date();
    d.setDate(d.getDate() + offsetDays);
    const dateStr = d.toISOString().split('T')[0];
    const el = document.getElementById(`date-${cityKey}`);
    if(el) {
        el.value = dateStr;
        refreshMarketPrices(cityKey);
    }
}

function buildControls() {
    const container = document.getElementById("control-panels-container");
    const tmpl = document.getElementById("tmpl-control").innerHTML;

    CITIES_ORDER.forEach(ck => {
        const city = APP_CONFIG.cities[ck];
        
        let html = tmpl
            .replace(/{id}/g, ck)
            .replace(/{color}/g, city.color)
            .replace(/{flag}/g, city.flag)
            .replace(/{name}/g, city.name)
            .replace(/{station}/g, city.station);
            
        container.insertAdjacentHTML('beforeend', html);
        
        // Populate ranges
        const select = document.getElementById(`range-${ck}`);
        city.ranges.forEach((r, idx) => {
            const opt = document.createElement('option');
            opt.value = idx;
            opt.innerText = r;
            // set defaults intelligently
            if(ck === 'london' && idx === 5) opt.selected = true;
            if(ck === 'miami' && idx === 3) opt.selected = true;
            select.appendChild(opt);
        });

        // Set default date
        setDate(ck, 0);

        // Populate price grids
        const pg = document.getElementById(`prices-${ck}`);
        city.ranges.forEach((r, idx) => {
            const cell = document.createElement('div');
            cell.className = 'price-cell';
            cell.innerHTML = `<span>${r}</span><input type="text" id="price-${ck}-${idx}">`;
            pg.appendChild(cell);
        });

        // Add event listener for date change
        document.getElementById(`date-${ck}`).addEventListener("change", () => {
            refreshMarketPrices(ck);
        });
    });
}

function buildResultCard(ck) {
    const container = document.getElementById("results-grid");
    const existing = document.getElementById(`res-${ck}`);
    if(existing) return existing; // already built

    const city = APP_CONFIG.cities[ck];
    const tmpl = document.getElementById("tmpl-result").innerHTML;
    
    let html = tmpl
        .replace(/{id}/g, ck)
        .replace(/{color}/g, city.color)
        .replace(/{flag}/g, city.flag)
        .replace(/{name}/g, city.name);
        
    container.insertAdjacentHTML('beforeend', html);
    return document.getElementById(`res-${ck}`);
}

async function analyzeCity(cityKey) {
    console.log(`[UI] Starting analysis for ${cityKey}`);
    toggleButtons(true);
    showStatus(`Загрузка рыночных данных: ${APP_CONFIG.cities[cityKey].name}...`, "var(--color-highlight)");

    await doAnalyze(cityKey);
    console.log(`[UI] Analysis for ${cityKey} finished, calling wrapUpAnalysis`);
    wrapUpAnalysis([cityKey]);
}

async function analyzeBoth() {
    toggleButtons(true);
    showStatus("Синхронизация портфеля...", "var(--color-highlight)");

    await Promise.all([doAnalyze('london'), doAnalyze('miami')]);
    wrapUpAnalysis(['london', 'miami']);
}

async function doAnalyze(ck) {
    const dateStr = document.getElementById(`date-${ck}`).value;
    const rangeIdx = parseInt(document.getElementById(`range-${ck}`).value);
    const priceRaw = document.getElementById(`price-${ck}-${rangeIdx}`).value.trim();
    const marketPrice = priceRaw ? parseFloat(priceRaw) : null;

    try {
        const req = {
            city_key: ck,
            date_str: dateStr,
            range_index: rangeIdx,
            market_price: marketPrice
        };

        console.log(`[API] POST /api/analyze`, req);
        const res = await fetch("/api/analyze", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(req)
        });

        if(!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        console.log(`[API] Analysis received:`, data);
        
        LAST_RESULTS[ck] = data;
        saveLastResults();
        renderResult(ck, data);

    } catch(e) {
        console.error(`[API] Analysis failed:`, e);
        const card = buildResultCard(ck);
        if (card) {
            card.classList.add('active');
            const v_el = document.getElementById(`res-verdict-${ck}`);
            if(v_el) {
                v_el.innerText = "❌ ОШИБКА";
                v_el.style.color = "var(--color-sell)";
            }
        }
    }
}

function renderResult(ck, data) {
    const card = buildResultCard(ck);
    card.classList.add('active');

    const w = data.wunder;
    const a = data.analysis;
    const sc = data.score;
    const lt = data.local_time;

    const time_el = document.getElementById(`res-time-${ck}`);
    if(time_el) time_el.innerText = `[${data.date} | ${lt.local_str}]`;
    
    const icons = {0: "CLR", 1: "FEW", 2: "SCT", 3: "BKN", 45: "FG", 48: "FZFG", 51: "DZ", 53: "DZ", 61: "RA", 63: "RA", 65: "RA", 71: "SN", 73: "SN", 80: "SHRA", 82: "TSRA"};
    const icon_el = document.getElementById(`res-icon-${ck}`);
    if(icon_el) icon_el.innerText = icons[a.wx_code] || "OBS";

    const isF = ck === 'miami';
    const mainTemp = isF ? sc.best_max_f.toFixed(0) + "°F" : sc.best_max_c.toFixed(1) + "°C";
    const subTemp = isF ? sc.best_max_c.toFixed(1) + "°C" : sc.best_max_f.toFixed(0) + "°F";
    
    const tmain_el = document.getElementById(`res-temp-main-${ck}`);
    if(tmain_el) tmain_el.innerText = `Макс: ${mainTemp}`;
    const tsub_el = document.getElementById(`res-temp-sub-${ck}`);
    if(tsub_el) tsub_el.innerText = `(${subTemp})`;

    const w_el = document.getElementById(`res-wunder-${ck}`);
    if(w) {
        const cur = isF ? w.current_f : w.current_c;
        const u = isF ? "°F" : "°C";
        if(cur != null) w_el.innerText = `◉ ${w.source || 'METAR'}: ${cur.toFixed(1)}${u}`;
        else { w_el.innerText = "[METAR: НЕТ ДАННЫХ]"; w_el.style.color = "var(--text-muted)"; }
    } else {
        w_el.innerText = "[METAR: НЕДОСТУПЕН]"; w_el.style.color = "var(--text-muted)";
    }

    const m_el = document.getElementById(`res-match-${ck}`);
    m_el.innerText = `[TARGET] ${sc.in_range ? 'MATCH' : 'FAIL'} ${data.selected_range}`;
    m_el.style.color = sc.in_range ? "var(--color-buy)" : "var(--color-sell)";

    const pk_el = document.getElementById(`res-peak-${ck}`);
    pk_el.innerText = sc.peak_done ? "[PEAK: PASSED]" : (lt.during_peak ? "[PEAK: ACTIVE]" : "[PEAK: PENDING]");

    // Verdict area
    document.getElementById(`res-verdict-${ck}`).innerText = sc.verdict;
    document.getElementById(`res-verdict-${ck}`).style.color = sc.verdict.includes("ВХОДИТЬ") && !sc.verdict.includes("НЕ") ? "var(--color-buy)" : "var(--color-sell)";
    document.getElementById(`res-stake-${ck}`).innerText = `Объем: ${sc.bank}`;
    
    const rec_el = document.getElementById(`res-rec-${ck}`);
    if(rec_el) rec_el.innerText = sc.mkt_rec ? `★ Рекомендация: ${sc.mkt_rec}` : "";

    document.getElementById(`res-prob-${ck}`).innerText = `${sc.our_prob.toFixed(0)}%`;
    
    const e_el = document.getElementById(`res-edge-${ck}`);
    if(sc.edge !== null) {
        e_el.innerText = `${sc.edge > 0 ? '+':''}${sc.edge.toFixed(0)}%`;
        e_el.style.color = sc.edge > 10 ? "var(--color-buy)" : (sc.edge < -10 ? "var(--color-sell)" : "var(--color-warn)");
    } else {
        e_el.innerText = "—";
        e_el.style.color = "var(--text-muted)";
    }

    // Signals
    const sigCont = document.getElementById(`res-signals-${ck}`);
    if(sigCont) {
        sigCont.innerHTML = "";
        (sc.signals || []).forEach(sig => {
            const [colName, msg] = sig;
            let cHex = `var(--color-${colName})`;
            if(colName === 'dim') cHex = 'var(--text-muted)';
            if(colName === 'green') cHex = 'var(--color-buy)';
            if(colName === 'red') cHex = 'var(--color-sell)';
            if(colName === 'yellow') cHex = 'var(--color-warn)';
            
            const div = document.createElement('div');
            div.className = "sig-item";
            div.style.color = cHex;
            div.innerHTML = `<span>> ${msg}</span>`;
            sigCont.appendChild(div);
        });
    }
}

function wrapUpAnalysis(cityKeys) {
    toggleButtons(false);
    const timeStr = new Date().toLocaleTimeString();
    showStatus(`Данные синхронизированы: ${timeStr}`, "var(--text-secondary)");

    if(document.getElementById("auto-ai-toggle").checked && cityKeys.length > 0) {
        const target = cityKeys.length === 1 ? cityKeys[0] : "both";
        setTimeout(() => analyzeChatTarget(target), 500);
    }
}

function toggleButtons(disabled) {
    document.querySelectorAll('.btn').forEach(b => b.disabled = disabled);
}

function showStatus(text, color) {
    const el = document.getElementById("status-label");
    el.innerHTML = `<span class="status-dot" style="background: ${color}"></span> ${text}`;
    el.style.borderColor = color;
}

async function refreshMarketPrices(cityKey) {
    const dateStr = document.getElementById(`date-${cityKey}`).value;
    if(!dateStr) return;
    
    showStatus(`Парсинг стакана заявок: ${cityKey}...`, "var(--text-primary)");

    try {
        const res = await fetch(`/api/market-prices?city_key=${cityKey}&date_str=${dateStr}`);
        if(!res.ok) throw new Error("Price fetch failed");
        const data = await res.json();
        const prices = data.prices; // {idx: price}
        
        for (const idx in prices) {
            const input = document.getElementById(`price-${cityKey}-${idx}`);
            if(input) {
                input.value = prices[idx];
                input.classList.add('updated-pulse');
                setTimeout(() => input.classList.remove('updated-pulse'), 2000);
            }
        }
        showStatus("Стакан заявок обновлен", "var(--color-buy)");
        setTimeout(() => showStatus("Готов к торгам", "var(--text-secondary)"), 2000);
    } catch(e) {
        console.error(e);
        showStatus("Ошибка доступа к API Polymarket", "var(--color-sell)");
    }
}

let chatHistory = [];

function initAISettings() {
    const sel = document.getElementById("ai-model");
    if(!sel) return;
    sel.innerHTML = "";
    APP_CONFIG.ai_models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id; opt.innerText = m.label;
        sel.appendChild(opt);
    });
    
    if(APP_CONFIG.ai_settings.model) sel.value = APP_CONFIG.ai_settings.model;
}

async function saveSettings() {
    const mid = document.getElementById("ai-model").value;
    
    await fetch("/api/settings", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({model_id: mid})
    });
    
    const s_el = document.getElementById("ai-status-text");
    s_el.innerText = "КОНФИГУРАЦИЯ ПРИМЕНЕНА";
    s_el.style.color = "var(--color-buy)";
    setTimeout(()=> { s_el.innerText = "ГОТОВ"; s_el.style.color = "var(--text-secondary)"; }, 2000);
}

function appendMessage(role, text) {
    const cont = document.getElementById("chat-history");
    const div = document.createElement("div");
    
    if(role === 'you') {
        div.className = "msg msg-you";
        div.innerHTML = `<div class="msg-you-lbl">> USER_INPUT</div><div>${escapeHtml(text)}</div>`;
    } else if (role === 'ai') {
        div.className = "msg msg-ai";
        let parsed = escapeHtml(text).replace(/\n/g, "<br>");
        div.innerHTML = `<div class="msg-ai-lbl">> SYSTEM_RESPONSE</div><div>${parsed}</div>`;
        const match = text.match(/PRICES_JSON:\s*(\{.*?\})/s);
        if(match) {
            try { applyAiPrices(JSON.parse(match[1])); } catch(e){}
        }
    } else {
        div.className = "msg msg-sys";
        div.innerHTML = escapeHtml(text);
    }
    
    cont.appendChild(div);
    cont.scrollTop = cont.scrollHeight;
}

function clearChat() {
    document.getElementById("chat-history").innerHTML = "";
    chatHistory = [];
    document.getElementById("ai-status-text").innerText = "ЛОГ ОЧИЩЕН";
    setTimeout(()=> document.getElementById("ai-status-text").innerText = "ГОТОВ", 2000);
}

async function sendChat(presetMsg = null, forceContext = false) {
    const inp = document.getElementById("ai-input");
    const msg = presetMsg || inp.value.trim();
    if(!msg) return;
    if(!presetMsg) inp.value = "";
    
    appendMessage('you', msg);
    document.getElementById("ai-status-text").innerText = "ОБРАБОТКА...";
    document.getElementById("ai-status-text").style.color = "var(--color-highlight)";
    document.getElementById("btn-send").disabled = true;

    try {
        const ctx = Object.values(LAST_RESULTS);
        const req = {
            message: msg,
            history: chatHistory,
            data_context: ctx,
            force_context: forceContext
        };
        
        const res = await fetch("/api/chat", {
            method: "POST", headers:{"Content-Type":"application/json"},
            body: JSON.stringify(req)
        });
        
        const data = await res.json();
        if(data.error) throw new Error(data.reply || "Unknown AI Error");

        chatHistory.push({"role": "user", "content": msg});
        chatHistory.push({"role": "assistant", "content": data.reply});
        
        if(chatHistory.length > 10) chatHistory = chatHistory.slice(-10);
        appendMessage('ai', data.reply);
        
    } catch(e) {
        console.error(`[AI] Chat error:`, e);
        appendMessage('sys', `❌ AI Error: ${e.message}`);
    } finally {
        document.getElementById("ai-status-text").innerText = "ГОТОВ";
        document.getElementById("ai-status-text").style.color = "var(--text-secondary)";
        document.getElementById("btn-send").disabled = false;
    }
}

function analyzeChatTarget(target) {
    const results = Object.values(LAST_RESULTS);
    if(results.length === 0) { 
        appendMessage('sys', "⚠️ Нет данных для анализа. Запросите данные погоды."); 
        return; 
    }
    
    let ctxRes = results;
    if(target !== 'both') ctxRes = results.filter(r => r.city_key === target);
    if(ctxRes.length === 0) { 
        appendMessage('sys', `⚠️ Нет данных для выбранной цели.`); 
        return; 
    }
    
    sendChat("Проанализируй все данные по температуре на целевую дату. Дай математически обоснованный вердикт: стоит ли открывать позицию? ПРОАНАЛИЗИРУЙ САМОСТОЯТЕЛЬНО.", true);
}

async function freeSearch() {
    appendMessage('you', "🔍 Запрос к wttr.in...");
    document.getElementById("ai-status-text").innerText = "ПОИСК...";
    try {
        const res = await fetch("/api/search");
        const data = await res.json();
        appendMessage('ai', data.result + "\n\n💡 Нажмите 'Анализ' для обработки данных ИИ.");
    } catch(e) {
        appendMessage('sys', "Ошибка запроса");
    } finally {
        document.getElementById("ai-status-text").innerText = "ОЖИДАНИЕ";
    }
}

function applyAiPrices(pricesDict) {
    for (const ck in pricesDict) {
        const cityObj = APP_CONFIG.cities[ck];
        if(!cityObj) continue;
        const prices = pricesDict[ck];
        for (const rng in prices) {
            const idx = cityObj.ranges.indexOf(rng);
            if(idx !== -1) {
                const input = document.getElementById(`price-${ck}-${idx}`);
                if(input) input.value = prices[rng];
            }
        }
    }
}

function escapeHtml(unsafe) {
    return unsafe.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

let reloadState = { boot_id: null, last_mod: null };
async function checkHotReload() {
    try {
        const res = await fetch("/api/health");
        if (!res.ok) return;
        const data = await res.json();
        if (reloadState.boot_id && (data.boot_id !== reloadState.boot_id || data.last_mod > reloadState.last_mod)) {
            window.location.reload();
        }
        reloadState.boot_id = data.boot_id;
        reloadState.last_mod = data.last_mod;
    } catch (e) {}
}
setInterval(checkHotReload, 2000);
