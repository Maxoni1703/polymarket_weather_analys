import json
import os
import requests as _req
import traceback
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from config import CITIES, T
from weather import fetch_multimodel_forecast, fetch_wunderground, analyze_forecast, compute_score
from polymarket import fetch_prices_for_ranges
from utils import get_local_time
from ai_chat import free_weather_search, load_ai_config, save_ai_config, _SYS, MODELS, GENAPI_URL
import uuid

BOOT_ID = str(uuid.uuid4())

def health_check(request):
    # Returns the boot ID and the last modification time of the static folder to trigger reloads
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
    last_mod = 0
    if os.path.exists(static_dir):
        last_mod = max(os.path.getmtime(os.path.join(static_dir, f)) for f in os.listdir(static_dir) if os.path.isfile(os.path.join(static_dir, f)))
    
    return JsonResponse({
        "boot_id": BOOT_ID,
        "last_mod": last_mod
    })

def root(request):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_file = os.path.join(base_dir, "static", "index.html")
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read())
    return HttpResponse("UI not built yet.", status=404)

def get_config(request):
    ai_cfg = load_ai_config()
    cities_payload = {}
    for k, v in CITIES.items():
        cities_payload[k] = {
            "name": v["name"],
            "flag": v["flag"],
            "ranges": v["ranges"],
            "station": v["station"],
            "color": v["color"]
        }
    return JsonResponse({
        "cities": cities_payload,
        "ai_settings": ai_cfg,
        "ai_models": [{"id": m[0], "label": m[1]} for m in MODELS]
    })

@csrf_exempt
def update_settings(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    if request.content_type != "application/json":
        return HttpResponseBadRequest("Content-Type must be application/json")
    try:
        data = json.loads(request.body)
        save_ai_config(data.get('api_key', ''), data.get('model_id', ''))
        return JsonResponse({"status": "ok"})
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def analyze_city(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    if request.content_type != "application/json":
        return HttpResponseBadRequest("Content-Type must be application/json")
    try:
        data = json.loads(request.body)
        ck = data.get('city_key')
        date_str = data.get('date_str')
        market_price = data.get('market_price')
        range_index = data.get('range_index', 0)

        if ck not in CITIES:
            return JsonResponse({"detail": "Invalid city"}, status=400)

        om_data, agg = fetch_multimodel_forecast(ck, date_str=date_str)
        wunder = fetch_wunderground(ck)
        lt = get_local_time(ck)

        cc = agg.get("consensus_max_c") if agg else None
        a = analyze_forecast(om_data, ck, consensus_max_c=cc)

        rec = compute_score(
            a, wunder, lt, ck,
            market_price, range_index, False,
            agg_signals=agg.get("signals", []) if agg else [],
            models_raw=agg.get("models_raw", []) if agg else []
        )
        
        # Save to DB for self-learning
        from database import save_analysis
        try:
            save_analysis(ck, date_str, market_price, CITIES[ck]["ranges"][range_index], rec, a)
        except Exception as db_err:
            print(f"DB Error: {db_err}")

        return JsonResponse({
            "city_key": ck,
            "analysis": a,
            "score": rec,
            "wunder": wunder,
            "local_time": lt,
            "date": date_str,
            "selected_range": CITIES[ck]["ranges"][range_index] if range_index < len(CITIES[ck]["ranges"]) else "",
            "market_price": market_price
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"detail": str(e)}, status=500)

def get_market_prices(request):
    city_key = request.GET.get('city_key')
    date_str = request.GET.get('date_str')
    if city_key not in CITIES:
        return JsonResponse({"detail": "Invalid city"}, status=400)
    try:
        ranges = CITIES[city_key]["ranges"]
        matched_prices = fetch_prices_for_ranges(city_key, ranges, date_str)
        return JsonResponse({"prices": matched_prices})
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)

def trigger_search(request):
    try:
        res = free_weather_search()
        return JsonResponse({"result": res})
    except Exception as e:
        return JsonResponse({"detail": str(e)}, status=500)

def _build_context(city_data):
    if not city_data: return ""
    lines = [f"🚨 TARGET DATE: {city_data[0].get('date','?')}", ""]
    for d in city_data:
        ck, ao, res = d.get("city_key"), d.get("analysis",{}), d.get("score",{})
        m_price = d.get("market_price", "?")
        u = "°F" if ck=="miami" else "°C"
        t_val = res.get('best_max_c' if u=='°C' else 'best_max_f', 0)
        lines += [
            f"### {ck} ({d.get('selected_range','?')})",
            f"T_max: {t_val:.1f}{u} | Rain: {ao.get('precip_prob',0)}% | Wind: {ao.get('wind_max',0):.0f}km/h",
            f"Market Price: {m_price}%",
            f"Verdict: {res.get('verdict','')} ({res.get('our_prob',0):.1f}%)", ""
        ]
    return "\n".join(lines)

@csrf_exempt
def chat_with_ai(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    if request.content_type != "application/json":
        return HttpResponseBadRequest("Content-Type must be application/json")
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        history = data.get('history', [])
        data_context = data.get('data_context', [])
        force_context = data.get('force_context', False)

        cfg = load_ai_config()
        key = cfg.get("key")
        model = cfg.get("model")

        if not key:
            return JsonResponse({"reply": "⚠️ Provide GenAPI API Key in settings.", "error": True})

        msgs = [{"role": "system", "content": _SYS}]

        if data_context and (not history or len(history) < 2 or force_context):
            ctx = _build_context(data_context)
            msgs.append({"role": "user", "content": f"Here is the latest weather data:\n{ctx}"})
            msgs.append({"role": "assistant", "content": "Data received. Awaiting your request."})

        for h in history:
            msgs.append(h)

        msgs.append({"role": "user", "content": message})

        payload = {
            "model": model,
            "messages": msgs,
            "max_tokens": 1500,
        }

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        r = _req.post(GENAPI_URL, headers=headers, json=payload, timeout=240)
        
        if r.status_code != 200:
            err_data = {}
            try: err_data = r.json()
            except: pass
            detail = err_data.get("error", {}).get("message", r.text)
            return JsonResponse({"reply": f"❌ Error: {detail}", "error": True})

        res_data = r.json()
        reply = res_data["choices"][0]["message"]["content"].strip()
        return JsonResponse({"reply": reply, "error": False})

    except _req.exceptions.Timeout:
        return JsonResponse({"reply": "❌ Timeout. Check your internet connection.", "error": True})
    except Exception as e:
        return JsonResponse({"reply": f"❌ Connection Error: {str(e)}", "error": True})
