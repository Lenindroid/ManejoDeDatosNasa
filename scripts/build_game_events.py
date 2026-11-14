"""Filtra los eventos DONKI relevantes para la base lunar y los traduce a efectos de juego.
Uso: python -I scripts/build_game_events.py donki_data eventos_juego.json"""
import json, os, sys, collections as C

SRC, OUT = sys.argv[1], sys.argv[2]
L = lambda t: json.load(open(os.path.join(SRC, t + ".json")))

# Stats del juego: energia y salud.
# Efecto por severidad (1-5):
#   energia: % de produccion electrica perdida mientras dura el evento
#   salud:   puntos de salud que pierde la tripulacion si esta expuesta (fuera del refugio)
EFECTO_ENERGIA = {1: -5, 2: -10, 3: -20, 4: -35, 5: -50}
EFECTO_SALUD   = {1: -1, 2: -3,  3: -8,  4: -15, 5: -30}

def recursos(tipo, sev):
    """Que stats afecta cada tipo de evento."""
    if tipo == "SEP": return ["salud", "energia"] if sev >= 5 else ["salud"]  # SEP extrema degrada paneles
    if tipo == "FLR": return ["energia", "salud"] if sev >= 4 else ["energia"]  # clase X: radiacion directa
    return ["energia"]  # CME, IPS, HSS

def links(x): return [l["activityID"] for l in (x.get("linkedEvents") or [])]

def flare_sev(cls):
    letter, mag = cls[0], float(cls[1:] or 1)
    if letter == "X": return 5 if mag >= 5 else 4
    if letter == "M": return 3 if mag >= 5 else 2
    return None  # C/B descartadas: impacto despreciable

events = []
def add(tipo, eid, t, sev, datos, link, linked):
    rs = recursos(tipo, sev)
    ef = {}
    if "energia" in rs: ef["energia"] = EFECTO_ENERGIA[sev]
    if "salud" in rs: ef["salud"] = EFECTO_SALUD[sev]
    events.append({"id": eid, "tipo": tipo, "fecha": t, "severidad": sev,
                   "recursos_afectados": rs, "efectos": ef,
                   "datos": datos, "eventos_vinculados": linked, "link": link})

for x in L("FLR"):
    s = flare_sev(x.get("classType") or "C")
    if s: add("FLR", x["flrID"], x["peakTime"], s,
              {"clase": x["classType"], "inicio": x["beginTime"], "fin": x["endTime"], "region": x.get("sourceLocation")},
              x["link"], links(x))

for x in L("CME"):
    an = [a for a in (x.get("cmeAnalyses") or []) if a.get("isMostAccurate")]
    if not an: continue
    a = an[0]; sp = a.get("speed") or 0
    arrival = next((e.get("estimatedShockArrivalTime") for e in (a.get("enlilList") or [])
                    if e.get("estimatedShockArrivalTime")), None)
    glancing = any(e.get("isEarthGB") for e in (a.get("enlilList") or []))
    if not (arrival or glancing) and sp < 1000: continue   # no llega a la Tierra-Luna y es lenta
    s = 5 if sp >= 1500 else 4 if sp >= 1000 else 3 if sp >= 700 else 2 if sp >= 500 else 1
    if (arrival or glancing): s = min(5, s + 1)
    add("CME", x["activityID"], x["startTime"], s,
        {"velocidad_kms": sp, "medio_angulo": a.get("halfAngle"), "tipo_cme": a.get("type"),
         "llegada_estimada": arrival, "roce_lateral": glancing},
        x["link"], links(x))

for x in L("SEP"):
    inst = [i["displayName"] for i in x.get("instruments", [])]
    s = 5 if any("GOES" in i and ">10" in i or "100" in i for i in inst) else 4
    add("SEP", x["sepID"], x["eventTime"], s, {"instrumentos": inst}, x["link"], links(x))


for x in L("IPS"):
    if x.get("location") != "Earth": continue   # solo choques que llegan a la zona Tierra-Luna
    add("IPS", x["activityID"], x["eventTime"], 2, {"ubicacion": x["location"]}, x["link"], links(x))

for t, key, idk, sev in [("HSS","eventTime","hssID",1)]:
    for x in L(t):
        add(t, x[idk], x[key], sev, {}, x["link"], links(x))

events.sort(key=lambda e: e["fecha"])
out = {
 "fuente": "NASA CCMC DONKI - https://ccmc.gsfc.nasa.gov/DONKI/WS/get/{TIPO}",
 "periodo": {"inicio": "2025-11-14", "fin": "2026-11-14"},
 "stats": ["energia", "salud"],
 "escala_severidad": {"1": "menor", "2": "moderado", "3": "fuerte", "4": "severo", "5": "extremo"},
 "efecto_por_severidad": {"energia_pct_produccion": EFECTO_ENERGIA, "salud_puntos": EFECTO_SALUD},
 "excluidos": "GST, RBE y MPC (solo afectan la magnetosfera terrestre/comunicaciones)",
 "resumen": {
   "total": len(events),
   "por_tipo": dict(C.Counter(e["tipo"] for e in events)),
   "por_stat": {r: sum(1 for e in events if r in e["recursos_afectados"]) for r in ("energia", "salud")},
   "por_severidad": dict(sorted(C.Counter(e["severidad"] for e in events).items())),
   "por_mes": dict(sorted(C.Counter(e["fecha"][:7] for e in events).items())),
 },
 "eventos": events,
}
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out["resumen"], indent=1))
