"""Curates the DONKI events that reach a lunar base and turns them into game-ready entries.
Usage: python -I scripts/build_game_events.py donki_data eventos_juego.json

Each event has: robot dialog (2 strings), radiation points, blackout flag, arrival time (minutes)
and the chain it belongs to (events linked by DONKI, e.g. flare -> particle storm -> CME impact)."""
import json, os, sys, math, datetime as dt, collections as C

SRC, OUT = sys.argv[1], sys.argv[2]
L = lambda t: json.load(open(os.path.join(SRC, t + ".json")))
AU_KM = 149_597_870
SUN_LIGHT_MIN = 8  # sunlight reaches the Earth-Moon system in ~8.3 minutes

def ts(s): return dt.datetime.strptime(s, "%Y-%m-%dT%H:%MZ")
def minutes(a, b): return round((ts(b) - ts(a)).total_seconds() / 60)
def nice_date(s): d = ts(s); return f"{d:%B} {d.day}, {d.year}"
def links(x): return [l["activityID"] for l in (x.get("linkedEvents") or [])]

# ---------------------------------------------------------------- who detected it
DETECTORS = {  # DONKI instrument prefix -> friendly spacecraft name
    "GOES-P": "NOAA's GOES weather satellite", "GOES-S": "NOAA's backup GOES weather satellite",
    "GOES": "NOAA's GOES-19 satellite (CCOR-1 coronagraph)",
    "SOHO": "the NASA/ESA SOHO observatory", "STEREO A": "NASA's STEREO-A spacecraft",
    "ACE": "NASA's ACE spacecraft", "DSCOVR": "NOAA's DSCOVR satellite",
    "SOLAR-1": "NOAA's SOLAR-1 space weather observatory", "IMAP": "NASA's IMAP spacecraft",
    "MODEL": "NASA's REleASE early-warning system",
}
NEAR_EARTH = ("GOES", "SOHO", "ACE", "DSCOVR", "SOLAR-1", "IMAP", "MODEL")  # STEREO-A is far from the Moon

def spacecraft(inst):
    names = []
    for i in sorted(inst, key=lambda i: i.startswith("MODEL")):  # real spacecraft first
        n = DETECTORS.get(i.split(":")[0])
        if n and n not in names: names.append(n)
    return names

def who(inst):
    n = spacecraft(inst)[:2] or ["NASA's space weather team"]
    return " and ".join(n)

def detected(names, what, date, verb="has"):
    verb = "have" if " and " in names else verb
    s = f"{names} {verb} detected {what}"
    return s[0].upper() + s[1:] + f" (based on a real event recorded in NASA's DONKI database on {nice_date(date)})."

# ---------------------------------------------------------------- explanations (one per event type)
EXPLAIN = {
 "FLR": ("A solar flare is a sudden, extremely bright flash on the Sun. It happens when twisted magnetic fields "
         "above a sunspot snap and reconnect, releasing in minutes more energy than humanity uses in thousands of years. "
         "The flash is made of X-rays and ultraviolet light, which travel at the speed of light and reach the Moon in about "
         "8 minutes. On Earth the atmosphere blocks these rays, but the Moon has no air, so they hit the surface directly. "
         "Flares are ranked C, M and X, and each letter is 10 times stronger than the one before. Big flares are often "
         "the first warning of something worse: a storm of fast particles or a coronal mass ejection."),
 "SEP": ("A solar energetic particle event is a storm of tiny pieces of atoms, mostly protons, that a solar flare or the "
         "shock wave of a coronal mass ejection speeds up to almost the speed of light. They can reach the Moon in minutes "
         "to a few hours. Earth's magnetic field and atmosphere shield people on the ground, but the Moon has neither, so "
         "these particles go through spacesuits, thin walls and the human body, damaging cells and DNA. They also wear out "
         "solar panels and can make electronics glitch. It is the most dangerous kind of space weather for astronauts: the "
         "best protection is to stay behind thick shielding, like rock, water or heavy equipment, until it passes."),
 "CME": ("A coronal mass ejection is a gigantic cloud of electrically charged gas (plasma) and magnetic field that the Sun "
         "throws into space. It can weigh billions of tons and travel at hundreds to thousands of kilometers per second, "
         "so it takes about one to four days to cover the 150 million kilometers to the Earth-Moon system. Earth's magnetic "
         "field deflects most of it, but the Moon has no magnetic field: the plasma hits the surface directly and charges "
         "the ground, the base and its equipment with static electricity. Sudden electric discharges can damage circuits "
         "and knock out power systems, and the shock wave in front of the cloud can bring extra radiation."),
 "IPS": ("An interplanetary shock is a sudden wall in the solar wind, the stream of gas that always flows out of the Sun. "
         "At the shock, the speed, density and magnetic field of that gas jump all at once, a bit like the sonic boom of a "
         "supersonic jet. Most shocks are pushed ahead of a fast coronal mass ejection; others form where fast solar wind "
         "crashes into slower wind. When a shock sweeps over the Moon it speeds up nearby particles, adding some radiation, "
         "and suddenly changes the electric charge of the lunar surface and of everything standing on it."),
 "HSS": ("A high speed stream is a river of solar wind blowing about twice as fast as usual. It pours out of a coronal hole, "
         "a dark region of the Sun where the magnetic field opens into space and lets gas escape freely. Because the Sun "
         "rotates once every 27 days, these streams sweep past the Moon like the jet of a rotating garden sprinkler, and the "
         "same stream often returns a month later. They are much less violent than other events, but they raise the "
         "electric charge of the lunar surface, which makes the fine, sharp moon dust lift and cling to solar panels "
         "and equipment."),
}
NAMES = {"FLR": "Solar Flare", "SEP": "Solar Energetic Particle Event", "CME": "Coronal Mass Ejection",
         "IPS": "Interplanetary Shock", "HSS": "High Speed Solar Wind Stream"}

# ---------------------------------------------------------------- radiation scale (0-100 game points)
# DONKI does not give a radiation dose, so points are derived from what it does measure:
#   FLR: X-ray peak flux (log scale)  M1 = 5, X1 = 10, X10 = 15
#   SEP: highest proton energy measured near Earth  >10 MeV = 25, ~30-50 MeV = 40, >100 MeV = 60
#   IPS: shock-accelerated particles = 5;  CME direct hit (shock + plasma) = 5;  HSS = 0
def flare_flux(cls): return {"A": 1e-8, "B": 1e-7, "C": 1e-6, "M": 1e-5, "X": 1e-4}[cls[0]] * float(cls[1:] or 1)
def flare_points(cls): return max(1, round(5 * math.log10(flare_flux(cls) / 1e-6)))

def sep_energy(inst):
    """Highest energy channel (MeV) measured by near-Earth instruments."""
    best = 0
    for i in inst:
        if not i.startswith(NEAR_EARTH): continue
        rng = i.split()[-2].lstrip(">")  # ">10", "15.8-39.8", ">100"
        best = max(best, float(rng.split("-")[0]))
    return best

def sep_points(mev): return 60 if mev >= 100 else 40 if mev >= 28 else 25

events = {}
def add(tipo, eid, date, rad, blackout, arrival, source, first_line, data, link, linked):
    events[eid] = {"id": eid, "type": tipo, "name": NAMES[tipo], "date": date,
                   "dialog": [first_line, EXPLAIN[tipo]],
                   "radiation_points": rad, "blackout": blackout,
                   "arrival_minutes": arrival, "arrival_source": source,
                   "data": data, "link": link, "_links": linked}

# ---------------------------------------------------------------- FLR: M and X class (C and below are negligible)
for x in L("FLR"):
    cls = x.get("classType") or "C"
    if cls[0] not in "MX": continue
    rise = max(SUN_LIGHT_MIN, minutes(x["beginTime"], x["peakTime"]))
    region = f" from sunspot region {x['activeRegionNum']}" if x.get("activeRegionNum") else ""
    add("FLR", x["flrID"], x["beginTime"], flare_points(cls), False, rise, "observed: minutes from flare start to peak",
        detected(who([i["displayName"] for i in x["instruments"]]), f"a class {cls} solar flare{region}", x["beginTime"]),
        {"class": cls, "peak_time": x["peakTime"], "source_location": x.get("sourceLocation")}, x["link"], links(x))

# ---------------------------------------------------------------- IPS at Earth: real arrival time of CME shocks
ips = {x["activityID"]: x for x in L("IPS") if x.get("location") == "Earth"}

# ---------------------------------------------------------------- CME: only those that reach the Earth-Moon system
for x in L("CME"):
    an = next((a for a in (x.get("cmeAnalyses") or []) if a.get("isMostAccurate")), None)
    if not an: continue
    enlil = an.get("enlilList") or []
    model_arrival = next((e["estimatedShockArrivalTime"] for e in enlil if e.get("estimatedShockArrivalTime")), None)
    glancing = any(e.get("isEarthGB") for e in enlil) and not model_arrival
    if not (model_arrival or glancing): continue
    speed = an.get("speed") or 0
    shock_ids = [i for i in links(x) if i in ips]
    shock = sorted(ips[i]["eventTime"] for i in shock_ids)
    if shock:
        arrival, source = minutes(x["startTime"], shock[0]), "observed: shock measured at Earth"
    elif model_arrival:
        arrival, source = minutes(x["startTime"], model_arrival), "forecast: NASA WSA-ENLIL model"
    else:
        arrival, source = round(AU_KM / speed / 60), "estimate: 1 AU / measured speed"
    hit = "will hit the Earth-Moon system" if not glancing else "will graze the Earth-Moon system"
    add("CME", x["activityID"], x["startTime"], 0 if glancing else 5, not glancing and speed >= 700, arrival, source,
        detected(who([i["displayName"] for i in x["instruments"]]),
                 f"a coronal mass ejection traveling at {round(speed)} km/s that {hit}", x["startTime"]),
        {"speed_kms": speed, "half_angle_deg": an.get("halfAngle"), "glancing_blow": glancing,
         "shock_arrival": shock[0] if shock else model_arrival},
        x["link"], links(x))
    for i in shock_ids: ips[i]["_merged"] = True  # the shock is the CME arriving: not a separate event

# ---------------------------------------------------------------- SEP: only particle storms measured near Earth/Moon
for x in L("SEP"):
    inst = [i["displayName"] for i in x["instruments"]]
    mev = sep_energy(inst)
    if not mev: continue
    parents = [e for e in links(x) if e in events or e.split("-")[-2] in ("FLR", "CME")]
    starts = [events[p]["date"] for p in parents if p in events]
    if starts:
        arrival, source = max(1, minutes(min(starts), x["eventTime"])), "observed: minutes after its flare/CME began"
    else:
        arrival, source = None, None  # filled later with the typical delay
    add("SEP", x["sepID"], x["eventTime"], sep_points(mev), mev >= 100, arrival, source,
        detected(who(inst), f"a storm of solar protons with energies above {mev:g} MeV", x["eventTime"]),
        {"max_energy_mev": mev, "instruments": inst}, x["link"], links(x))

# ---------------------------------------------------------------- IPS not caused by a known CME
for i, x in ips.items():
    if x.get("_merged"): continue
    add("IPS", i, x["eventTime"], 5, False, None, None,
        detected(who([d["displayName"] for d in x["instruments"]]), "a shock wave in the solar wind arriving at Earth and the Moon", x["eventTime"]),
        {"location": x["location"]}, x["link"], links(x))

# ---------------------------------------------------------------- HSS seen near Earth
for x in L("HSS"):
    inst = [i["displayName"] for i in x["instruments"]]
    if not any(i.startswith(NEAR_EARTH) for i in inst): continue
    add("HSS", x["hssID"], x["eventTime"], 0, False, round(AU_KM / 650 / 60), "estimate: 1 AU at a typical 650 km/s",
        detected(who(inst), "a high speed stream of solar wind", x["eventTime"]),
        {}, x["link"], links(x))

# ---------------------------------------------------------------- merge duplicate SEPs
# DONKI logs one SEP per instrument/energy channel; those starting within 12 h are the same storm.
seps = sorted((e for e in events.values() if e["type"] == "SEP"), key=lambda e: e["date"])
groups = []
for e in seps:
    if groups and minutes(groups[-1][0]["date"], e["date"]) <= 12 * 60: groups[-1].append(e)
    else: groups.append([e])
for group in groups:
    keep = max(group, key=lambda e: e["data"]["max_energy_mev"])
    inst = sorted({i for e in group for i in e["data"]["instruments"]})
    mev = keep["data"]["max_energy_mev"]
    keep.update(date=group[0]["date"], radiation_points=sep_points(mev), blackout=mev >= 100)
    keep["data"]["instruments"] = inst
    keep["dialog"][0] = detected(who(inst), f"a storm of solar protons with energies above {mev:g} MeV", group[0]["date"])
    known = [e for e in group if e["arrival_source"]]
    if known:
        first = min(known, key=lambda e: e["arrival_minutes"])
        keep["arrival_minutes"], keep["arrival_source"] = first["arrival_minutes"], first["arrival_source"]
    for d in group:
        if d is keep: continue
        keep["_links"] += d["_links"]
        keep.setdefault("merged_ids", []).append(d["id"])
        del events[d["id"]]

# fill unknown arrival times with the typical observed delay of their type
for t in ("SEP", "IPS"):
    known = sorted(e["arrival_minutes"] for e in events.values() if e["type"] == t and e["arrival_minutes"])
    typical = known[len(known) // 2] if known else (60 if t == "SEP" else 2 * 24 * 60)
    for e in events.values():
        if e["type"] == t and e["arrival_minutes"] is None:
            e["arrival_minutes"], e["arrival_source"] = typical, f"estimate: typical delay of {t} events in this dataset"

# ---------------------------------------------------------------- chains (connected events)
alias = {m: e["id"] for e in events.values() for m in e.get("merged_ids", [])}
adj = C.defaultdict(set)
for e in events.values():
    for l in e["_links"]:
        l = alias.get(l, l)
        if l in events and l != e["id"]: adj[e["id"]].add(l); adj[l].add(e["id"])
chains, seen = {}, set()
for eid in sorted(events, key=lambda i: events[i]["date"]):
    if eid in seen or not adj[eid]: continue
    comp, stack = [], [eid]; seen.add(eid)
    while stack:
        c = stack.pop(); comp.append(c)
        for n in adj[c]:
            if n not in seen: seen.add(n); stack.append(n)
    comp.sort(key=lambda i: (events[i]["date"], i))
    cid = f"chain-{len(chains) + 1:03d}"
    chains[cid] = comp
    for step, i in enumerate(comp, 1): events[i]["chain"] = {"id": cid, "step": step, "length": len(comp)}
for e in events.values():
    e.setdefault("chain", None); del e["_links"]

ordered = sorted(events.values(), key=lambda e: e["date"])
out = {
 "source": "NASA CCMC DONKI - https://ccmc.gsfc.nasa.gov/DONKI/ (real events, 2025-11-14 to 2026-11-14)",
 "setting": "Lunar base: only events that reach the Earth-Moon system are included.",
 "fields": {
   "dialog": "[0] who detected what (real DONKI event + date), [1] explanation of the event type",
   "radiation_points": "Extra radiation added to the environment, 0-100 game scale (see radiation_scale)",
   "blackout": "True if the event can knock out the base's power",
   "arrival_minutes": "Minutes from the robot's warning until the event hits the base",
   "arrival_source": "observed (real DONKI times), forecast (NASA model) or estimate (physics/typical value)",
   "chain": "Linked events (e.g. flare -> particle storm -> CME). Play them in 'step' order; null = standalone",
 },
 "radiation_scale": {
   "FLR": "X-ray peak flux, log scale: M1 = 5, X1 = 10, X10 = 15",
   "SEP": "Highest proton energy measured near Earth: >10 MeV = 25, ~30-50 MeV = 40, >100 MeV = 60",
   "CME": "Direct hit = 5 (shock particles), glancing blow = 0",
   "IPS": "5 (shock-accelerated particles)",
   "HSS": "0 (low-energy solar wind)",
 },
 "blackout_rules": {
   "CME": "Direct hit at >= 700 km/s: plasma charges the base and electric discharges can trip the power system",
   "SEP": "Only >100 MeV storms: particles cause electronic faults in the power system",
   "FLR": "No: light does not cut power on the Moon", "IPS": "No", "HSS": "No",
 },
 "excluded": "GST, RBE and MPC only happen inside Earth's magnetic field; CMEs not aimed at Earth; "
             "particles and solar wind measured only by STEREO-A (far from the Moon); C-class flares (negligible).",
 "summary": {
   "total": len(ordered),
   "by_type": dict(C.Counter(e["type"] for e in ordered)),
   "blackouts": sum(e["blackout"] for e in ordered),
   "with_radiation": sum(e["radiation_points"] > 0 for e in ordered),
   "chains": len(chains),
   "standalone": sum(e["chain"] is None for e in ordered),
 },
 "chains": chains,
 "events": ordered,
}
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out["summary"], indent=1))
