import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/hoist-beam-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6").strip()
CUSTOM_HOIST = os.environ.get("CUSTOM_HOIST", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_hoists.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Hoist / Crane Scenario, Rated Load Lbs, Span Length Ft, AISC Beam Designation, Moment of Inertia Ix [in^4], Flange Width In, Hoist Power Spec)
SEED_HOISTS = [
    ("1-Ton (2,000 Lb) Gantry Crane on 10-Ft Span (W6×12 I-Beam)", 2000, 10, "W6×12 Wide-Flange", 22.1, 4.00, "120V 1-Phase Electric Hoist"),
    ("1-Ton (2,000 Lb) Gantry Crane on 12-Ft Span (W8×15 I-Beam)", 2000, 12, "W8×15 Wide-Flange", 48.0, 4.01, "120V 1-Phase Electric Hoist"),
    ("1-Ton (2,000 Lb) Gantry Crane on 15-Ft Span (W8×18 I-Beam)", 2000, 15, "W8×18 Wide-Flange", 61.9, 5.25, "120V 1-Phase Electric Hoist"),
    ("2-Ton (4,000 Lb) Gantry Crane on 10-Ft Span (W8×18 I-Beam)", 4000, 10, "W8×18 Wide-Flange", 61.9, 5.25, "120V/240V Electric Chain Hoist"),
    ("2-Ton (4,000 Lb) Gantry Crane on 12-Ft Span (W8×24 I-Beam)", 4000, 12, "W8×24 Wide-Flange", 82.7, 6.50, "120V/240V Electric Chain Hoist"),
    ("2-Ton (4,000 Lb) Gantry Crane on 15-Ft Span (W10×26 I-Beam)", 4000, 15, "W10×26 Wide-Flange", 144.0, 5.77, "120V/240V Electric Chain Hoist"),
    ("2-Ton (4,000 Lb) Gantry Crane on 20-Ft Span (W12×35 I-Beam)", 4000, 20, "W12×35 Wide-Flange", 285.0, 6.56, "240V Heavy-Duty Chain Hoist"),
    ("3-Ton (6,000 Lb) Gantry Crane on 12-Ft Span (W10×26 I-Beam)", 6000, 12, "W10×26 Wide-Flange", 144.0, 5.77, "240V 3-Ton Electric Hoist"),
    ("3-Ton (6,000 Lb) Gantry Crane on 15-Ft Span (W12×30 I-Beam)", 6000, 15, "W12×30 Wide-Flange", 238.0, 6.52, "240V 3-Ton Electric Hoist"),
    ("5-Ton (10,000 Lb) Shop Bridge Crane on 15-Ft Span (W12×45)", 10000, 15, "W12×45 Wide-Flange", 348.0, 8.05, "240V/480V Industrial Hoist"),
    ("1/2-Ton (1,000 Lb) Garage Hoist on 12-Ft Span (S6×12.5 Beam)", 1000, 12, "S6×12.5 Standard I-Beam", 22.1, 3.33, "120V 1,000-Lb Electric Hoist"),
    ("Harrington NER / ER 1-Ton & 2-Ton Electric Chain Hoist", 4000, 12, "W8×24 Wide-Flange", 82.7, 6.50, "H4 Continuous Duty Hoist"),
    ("CM Lodestar 1-Ton (Model L) & 2-Ton (Model R) Chain Hoist", 4000, 12, "W8×24 Wide-Flange", 82.7, 6.50, "120V / 240V Heavy-Duty Hoist"),
    ("JET SSC-1A (1-Ton) & SSC-2A (2-Ton) 120V Electric Chain Hoist", 2000, 12, "W8×18 Wide-Flange", 61.9, 5.25, "120V 15A Single-Phase Hoist"),
    ("Prowinch 1-Ton & 2-Ton 110V/220V Electric Chain Hoist w/ Trolley", 4000, 12, "W8×24 Wide-Flange", 82.7, 6.50, "Power Motorized Beam Trolley"),
    ("VEVOR 2200-Lb (1-Ton) & 4400-Lb (2-Ton) Electric Wire/Chain Hoist", 2200, 10, "W6×12 / S6×12.5 Beam", 22.1, 4.00, "120V Wireless Remote Hoist"),
    ("Coffing JLC 1-Ton & 2-Ton Heavy-Duty Electric Chain Hoist", 4000, 12, "W8×24 Wide-Flange", 82.7, 6.50, "120V / 240V Industrial Hoist"),
    ("Vestil A-Frame Steel Gantry Crane (2,000 Lb & 4,000 Lb) Sizing", 4000, 10, "S8×18.4 Standard I-Beam", 57.6, 4.00, "Adjustable Height 8'–12'"),
    ("Spanco / Gorbel Work Station Jib & Gantry Crane Beam Sizing", 2000, 12, "W8×18 Wide-Flange", 61.9, 5.25, "Enclosed Track / I-Beam"),
    ("S6×12.5 vs W6×12 Steel I-Beam Trolley & Point-Load Capacity", 2000, 10, "S6×12.5 vs W6×12 Beam", 22.1, 4.00, "Tapered S-Flange vs Flat W-Flange"),
    ("S8×18.4 vs W8×18 Steel I-Beam Deflection & Hoist Capacity", 4000, 12, "S8×18.4 vs W8×18 Beam", 61.9, 5.25, "CMAA L/600 Span Deflection"),
    ("W10×22 vs W10×26 Steel Wide-Flange Beam Hoist Capacity", 4000, 15, "W10×26 Wide-Flange", 144.0, 5.77, "CMAA L/600 Span Deflection"),
    ("W12×26 vs W12×35 Garage Ceiling Ridge Beam Hoist Capacity", 4000, 18, "W12×35 Wide-Flange", 285.0, 6.56, "CMAA L/600 Span Deflection"),
    ("ASME B30.9 2-Leg & 4-Leg Chain Sling Angle Tension (60° vs 45° vs 30°)", 4000, 12, "Grade 80 / 100 Alloy Chain", 82.7, 6.50, "2x Tension Penalty at 30° Angle"),
    ("3/8-Inch vs 1/2-Inch Grade 100 Alloy Overhead Lifting Chain Sling", 6000, 12, "W10×26 Wide-Flange", 144.0, 5.77, "8,800 Lb Single-Leg WLL (3/8\")"),
    ("Push vs Geared vs Motorized I-Beam Trolley Flange Width Sizing", 4000, 12, "W8×24 Wide-Flange", 82.7, 6.50, "1/8\" Flange Spacer Washer Rule"),
    ("Automotive V8 Engine & Transmission Pull (1,500 Lb) Gantry Setup", 2000, 10, "W6×12 Wide-Flange", 22.1, 4.00, "1-Ton Hoist + Leveler Sling"),
    (" Tractor & Skid-Steer Implement Service (4,000 Lb) Shop Crane", 4000, 14, "W10×22 Wide-Flange", 118.0, 5.75, "2-Ton Hoist + Geared Trolley"),
    ("1-Ton & 2-Ton Lever Chain Come-Along & Manual Hand Chain Fall", 4000, 12, "W8×24 Wide-Flange", 82.7, 6.50, "Grade 80 Load Chain + Beam Clamp"),
    ("Wood Garage Ceiling Joist vs Steel I-Beam Hoist Support Sizing", 2000, 12, "W8×18 Steel Retrofit", 61.9, 5.25, "Independent Jack Post Columns")
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=4000.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_hoist_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Tonnage × Span × Beam Permutator.
    """
    discovered = []
    seeds = [
        "what size i beam for ",
        "gantry crane beam calculator ",
        "electric chain hoist ",
        "rigging sling angle calculator "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref or "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        ton_m = re.search(r"\b(1|2|3|5)\s*ton\b", cleaned)
                        tons_v = int(ton_m.group(1)) if ton_m else 2
                        lbs_v = tons_v * 2000
                        bm_s = "W8×18 Wide-Flange" if tons_v <= 1 else ("W8×24 Wide-Flange" if tons_v == 2 else "W10×26 Wide-Flange")
                        ix_v = 61.9 if tons_v <= 1 else (82.7 if tons_v == 2 else 144.0)
                        discovered.append((cleaned.title(), lbs_v, 12, bm_s, ix_v, 5.50, "120V/240V Electric Chain Hoist"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    loads = [
        (1000, "1/2-Ton (1,000 Lb)"),
        (2000, "1-Ton (2,000 Lb)"),
        (3000, "1.5-Ton (3,000 Lb)"),
        (4000, "2-Ton (4,000 Lb)"),
        (6000, "3-Ton (6,000 Lb)"),
        (10000, "5-Ton (10,000 Lb)")
    ]
    spans = [8, 10, 12, 14, 16, 18, 20]
    for ld_lbs, ld_desc in loads:
        for sp_ft in spans:
            combo_title = f"{ld_desc} Overhead Hoist on {sp_ft}-Ft Span"
            test_slug = slugify(f"{combo_title}-ibeam-sling-calculator")
            if test_slug not in published_slugs:
                # Hitung minimum Ix agar defleksi <= L/600
                p_design = ld_lbs * 1.15
                l_in = sp_ft * 12.0
                max_defl = l_in / 600.0
                req_ix = (p_design * (l_in ** 3)) / (48.0 * 29000000.0 * max_defl)
                if req_ix <= 22.1:
                    b_lbl, ix_val, fl_w = ("W6×12 Wide-Flange", 22.1, 4.00)
                elif req_ix <= 61.9:
                    b_lbl, ix_val, fl_w = ("W8×18 Wide-Flange", 61.9, 5.25)
                elif req_ix <= 82.7:
                    b_lbl, ix_val, fl_w = ("W8×24 Wide-Flange", 82.7, 6.50)
                elif req_ix <= 144.0:
                    b_lbl, ix_val, fl_w = ("W10×26 Wide-Flange", 144.0, 5.77)
                elif req_ix <= 238.0:
                    b_lbl, ix_val, fl_w = ("W12×30 Wide-Flange", 238.0, 6.52)
                else:
                    b_lbl, ix_val, fl_w = ("W12×45 Wide-Flange", 348.0, 8.05)
                discovered.append((combo_title, ld_lbs, sp_ft, b_lbl, ix_val, fl_w, "Electric Chain Hoist + Trolley"))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_hoist_data(hoist_tuple):
    """
    LAPIS 3: Mesin Fisika Struktur Baja AISC (Defleksi L/600) & Trigonometri Sling ASME B30.9 (100% Bebas Gagal).
    """
    item_name, rated_lbs, span_ft, beam_spec, ix_in4, flange_in, power_spec = hoist_tuple

    tons = round(rated_lbs / 2000.0, 1)
    # 1. Faktor Kejut Dinamis Hoist Elektrik (CMAA Specification #74 = +15% Impact + Berat Trolley/Hoist ~120 lbs):
    design_point_load_lbs = int(round((rated_lbs * 1.15) + 120.0))

    # 2. Defleksi Tengah Bentang (Center-Span Point Load Deflection in Inches):
    # Delta = (P * L^3) / (48 * E * Ix), dengan E_steel = 29,000,000 PSI dan L dalam inci (span_ft * 12)
    span_in = span_ft * 12.0
    actual_deflection_in = round((design_point_load_lbs * (span_in ** 3)) / (48.0 * 29000000.0 * max(10.0, float(ix_in4))), 3)
    allowable_l600_in = round(span_in / 600.0, 3)

    # 3. Ketegangan Kaki Rantai/Sabuk Angkat 2-Kaki (ASME B30.9 2-Leg Bridle Sling Tension):
    # Tension per Leg = Load / (2 * sin(Angle_from_Horizontal))
    # sin(60°) = 0.866 -> 57.7% beban per kaki; sin(45°) = 0.707 -> 70.7% beban per kaki; sin(30°) = 0.500 -> 100% beban per kaki!
    leg_tension_60deg_lbs = int(round(rated_lbs / (2.0 * 0.8660)))
    leg_tension_45deg_lbs = int(round(rated_lbs / (2.0 * 0.7071)))
    leg_tension_30deg_lbs = int(round(rated_lbs / (2.0 * 0.5000)))

    chain_grade_size = "9/32\" (1/4\") Grade 100" if rated_lbs <= 2500 else ("3/8\" Grade 80 / Grade 100" if rated_lbs <= 6000 else "1/2\" Grade 100 Alloy")

    return {
        "hoist_name": item_name,
        "beam_spec": beam_spec,
        "seo_title": f"{item_name} I-Beam Deflection, Trolley & Sling Angle Calculator (2026)",
        "meta_description": f"Calculate exact A36 steel I-beam deflection ({actual_deflection_in}\" vs {allowable_l600_in}\" L/600 limit on {beam_spec}), {flange_in}\" trolley flange fit, and ASME B30.9 2-leg sling tension ({leg_tension_60deg_lbs:,} lbs @ 60°) for {item_name}.",
        "specs": {
            "rated_load_lbs": rated_lbs,
            "rated_tons": tons,
            "dynamic_design_load_lbs": design_point_load_lbs,
            "beam_span_ft": span_ft,
            "recommended_beam_spec": beam_spec,
            "moment_of_inertia_ix": ix_in4,
            "flange_width_in": flange_in,
            "actual_deflection_in": actual_deflection_in,
            "allowable_l600_deflection_in": allowable_l600_in,
            "sling_leg_60deg_lbs": leg_tension_60deg_lbs,
            "sling_leg_45deg_lbs": leg_tension_45deg_lbs,
            "sling_leg_30deg_lbs": leg_tension_30deg_lbs,
            "chain_sling_spec": chain_grade_size,
            "power_spec": power_spec
        },
        "structural_verdict": f"Lifting a {rated_lbs:,}-lb ({tons:g}-Ton) live load at the center of a {span_ft}-foot clear span imposes a dynamic point load of {design_point_load_lbs:,} lbs (including the CMAA 15% electric hoist impact factor and trolley deadweight). Using an AISC {beam_spec} steel beam ($I_x = {ix_in4}\\text{{ in}}^4$, {flange_in}\" flange width) limits mid-span bending deflection to {actual_deflection_in} inches—well within the CMAA $L/600$ crane stiffness ceiling of {allowable_l600_in} inches so the trolley never rolls downhill uncontrollably. Under ASME B30.9 rigging rules, a 2-leg {chain_grade_size} chain sling carries {leg_tension_60deg_lbs:,} lbs per leg at a 60° horizontal angle, rising to {leg_tension_45deg_lbs:,} lbs/leg at 45° and {leg_tension_30deg_lbs:,} lbs/leg at a shallow 30° angle.",
        "hardware_bundle": [
            {
                "badge": f"{tons:g}-Ton Electric Chain Hoist",
                "title": f"{tons:g}-Ton ({rated_lbs:,} Lb) {power_spec} w/ Pendant & Electromagnetic Load Brake",
                "price_range": "$179 - $1,399",
                "amazon_query": f"{tons:g} Ton {rated_lbs} lb Electric Chain Hoist 110V 120V Harrington Jet Prowinch",
                "hst_note": f"Grade-80 load chain and mechanical slip clutch lift {rated_lbs:,} lbs smoothly with zero load drift."
            },
            {
                "badge": f"{tons:g}-Ton Gantry Crane Frame",
                "title": f"{tons:g}-Ton ({rated_lbs:,} Lb) Adjustable-Height Steel A-Frame Shop Gantry Crane w/ Locking Casters",
                "price_range": "$459 - $1,699",
                "amazon_query": f"{tons:g} Ton {rated_lbs} lb Adjustable Steel Gantry Crane Shop A Frame",
                "hst_note": f"Freestanding structural steel A-frame supports {span_ft}-ft spans without stressing wooden garage roof trusses."
            },
            {
                "badge": f"{flange_in}\" Flange Beam Trolley",
                "title": f"{tons:g}-Ton Heavy-Duty Geared / Push I-Beam Trolley (Adjustable 2.7\"–{max(6.5, flange_in + 1.5):.1f}\" Flange) + Beam Clamp",
                "price_range": "$69 - $219",
                "amazon_query": f"{tons:g} Ton Push Geared I Beam Trolley Adjustable Flange Beam Clamp",
                "hst_note": f"Dual-tapered cast steel wheels fit both flat-flange {beam_spec} W-beams and tapered American Standard S-beams."
            },
            {
                "badge": f"{chain_grade_size.split()[0]} G80/G100 Sling",
                "title": f"Grade 80 / Grade 100 Alloy Steel 2-Leg & 4-Leg Lifting Chain Sling ({chain_grade_size}) + Crosby Shackles",
                "price_range": "$84 - $269",
                "amazon_query": "Grade 80 Grade 100 Lifting Chain Sling 2 Leg 4 Leg Overhead Hoist",
                "hst_note": f"Rated for {leg_tension_45deg_lbs:,}+ lbs per leg at 45°–60° bridle angles with positive-locking foundry grab hooks."
            }
        ],
        "rigging_checklist": [
            f"Size your overhead crane beam by the CMAA $L/600$ Stiffness Rule ({allowable_l600_in}\" max deflection on a {span_ft}-ft span), not just yield strength: if a beam sags more than $L/600$, a loaded push-trolley will roll toward the center on its own.",
            f"Watch the ASME B30.9 Sling Angle Trap ($T = W \\div [N \\times \\sin\\theta]$): never rig a 2-leg bridle sling at an angle flatter than 45° from horizontal! At 30°, each single sling leg experiences {leg_tension_30deg_lbs:,} lbs of tension—equal to 100% of the entire {rated_lbs:,}-lb load.",
            f"Set your I-Beam Trolley Spacer Washers so the wheel flanges have 1/8 inch (3mm) total side-to-side running clearance on your {flange_in}\"-wide {beam_spec} flange, and bolt steel End-Stop Bumpers at both ends of the beam.",
            "Never hang a 1-Ton or 2-Ton hoist from residential 2×6 or 2×8 wooden garage ceiling trusses (which are engineered for only 10–20 psf dead load)—always use a freestanding steel A-frame gantry crane or steel jack-post columns."
        ],
        "faqs": [
            {
                "q": f"What size steel I-beam do I need for {item_name} ({rated_lbs:,} lbs on a {span_ft}-ft span)?",
                "a": f"Including a 15% dynamic hoist impact factor ({design_point_load_lbs:,} lbs design load), keeping mid-span deflection below the CMAA $L/600$ limit ({allowable_l600_in} inches) over a {span_ft}-foot span requires an AISC {beam_spec} beam ($I_x = {ix_in4}\\text{{ in}}^4$, {flange_in}\" flange width), which deflects only {actual_deflection_in} inches at full load."
            },
            {
                "q": f"How does rigging sling angle affect chain tension when lifting {rated_lbs:,} lbs?",
                "a": f"Per ASME B30.9, tension per leg equals $\\text{{Load}} \\div (N \\times \\sin\\theta)$. On a 2-leg sling lifting {rated_lbs:,} lbs: at 90° vertical each leg holds {rated_lbs // 2:,} lbs; at 60° each leg holds {leg_tension_60deg_lbs:,} lbs (1.15x); at 45° each leg holds {leg_tension_45deg_lbs:,} lbs (1.41x); and at 30° each leg holds {leg_tension_30deg_lbs:,} lbs (2.0x)."
            },
            {
                "q": f"What is the difference between a W-Beam ({beam_spec}) and an S-Beam for a hoist trolley?",
                "a": f"Wide-Flange (W-Shapes) have wider, parallel flat flanges ({flange_in}\" wide) with higher lateral stability over long spans, whereas American Standard I-Beams (S-Shapes) have narrower, 16.7% sloped inner flanges crafted specifically for traditional tapered trolley wheels. Universal dual-tread trolleys ride smoothly on both."
            }
        ]
    }


def generate_hoist_data(hoist_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_hoist_data(hoist_tuple)

    item_name, rated_lbs, span_ft, beam_spec, ix_in4, flange_in, power_spec = hoist_tuple
    det_fallback = build_deterministic_hoist_data(hoist_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Licensed Structural PE (AISC Steel Manual & CMAA Crane Specification #74 Specialist) & ASME B30.9 Master Rigging Engineer. Create an accurate 2026 overhead shop gantry crane, electric chain hoist, steel I-beam deflection (L/600), and rigging sling angle tension guide for: "{item_name}".
Baseline specs: Rated Load={rated_lbs} lbs ({sp['rated_tons']} Tons, Dynamic Load={sp['dynamic_design_load_lbs']} lbs), Clear Span={span_ft} ft, Steel Beam={beam_spec} (Ix={ix_in4} in^4, Flange={flange_in}"), Actual Deflection={sp['actual_deflection_in']}" (Allowable L/600={sp['allowable_l600_deflection_in']}"), 2-Leg Sling Tension: 60 deg={sp['sling_leg_60deg_lbs']} lbs/leg, 45 deg={sp['sling_leg_45deg_lbs']} lbs/leg, 30 deg={sp['sling_leg_30deg_lbs']} lbs/leg ({sp['chain_sling_spec']}).
Return ONLY a valid JSON object matching this exact schema:
{{
  "hoist_name": "{item_name}",
  "beam_spec": "{beam_spec}",
  "seo_title": "{item_name} I-Beam Deflection, Trolley & Sling Angle Calculator (2026)",
  "meta_description": "Calculate exact AISC steel I-beam mid-span deflection, CMAA L/600 limit, trolley flange width, and ASME B30.9 sling angle tension for {item_name}.",
  "specs": {{
    "rated_load_lbs": {rated_lbs},
    "rated_tons": {sp['rated_tons']},
    "dynamic_design_load_lbs": {sp['dynamic_design_load_lbs']},
    "beam_span_ft": {span_ft},
    "recommended_beam_spec": "{beam_spec}",
    "moment_of_inertia_ix": {ix_in4},
    "flange_width_in": {flange_in},
    "actual_deflection_in": {sp['actual_deflection_in']},
    "allowable_l600_deflection_in": {sp['allowable_l600_deflection_in']},
    "sling_leg_60deg_lbs": {sp['sling_leg_60deg_lbs']},
    "sling_leg_45deg_lbs": {sp['sling_leg_45deg_lbs']},
    "sling_leg_30deg_lbs": {sp['sling_leg_30deg_lbs']},
    "chain_sling_spec": "{sp['chain_sling_spec']}",
    "power_spec": "{power_spec}"
  }},
  "structural_verdict": "3-sentence technical summary stating dynamic point load (with 15% impact), {beam_spec} mid-span deflection vs CMAA L/600 limit, trolley flange width, and 2-leg sling tension at 60 vs 30 degrees.",
  "hardware_bundle": [
    {{
      "badge": "{sp['rated_tons']:g}-Ton Electric Hoist",
      "title": "{sp['rated_tons']:g}-Ton ({rated_lbs:,} Lb) {power_spec} w/ Pendant Control",
      "price_range": "$179 - $1,399",
      "amazon_query": "{sp['rated_tons']:g} Ton {rated_lbs} lb Electric Chain Hoist 120V Harrington Jet",
      "hst_note": "1-sentence H4 duty cycle and electromagnetic brake note"
    }},
    {{
      "badge": "{sp['rated_tons']:g}-Ton Gantry Frame",
      "title": "{sp['rated_tons']:g}-Ton Adjustable-Height Steel A-Frame Shop Gantry Crane",
      "price_range": "$459 - $1,699",
      "amazon_query": "{sp['rated_tons']:g} Ton Adjustable Steel Gantry Crane Shop A Frame",
      "hst_note": "1-sentence freestanding structural support note"
    }},
    {{
      "badge": "{flange_in}\" Flange Beam Trolley",
      "title": "{sp['rated_tons']:g}-Ton Heavy-Duty Push / Geared I-Beam Trolley + Beam Clamp",
      "price_range": "$69 - $219",
      "amazon_query": "{sp['rated_tons']:g} Ton Push Geared I Beam Trolley Adjustable Flange",
      "hst_note": "1-sentence dual-tread wheel flange clearance note"
    }},
    {{
      "badge": "Grade 80/100 Chain Sling",
      "title": "Grade 80 / Grade 100 Alloy 2-Leg & 4-Leg Lifting Chain Sling + Crosby Shackles",
      "price_range": "$84 - $269",
      "amazon_query": "Grade 80 Grade 100 Lifting Chain Sling 2 Leg 4 Leg Hoist",
      "hst_note": "1-sentence ASME B30.9 angle WLL safety note"
    }}
  ],
  "rigging_checklist": [
    "Step 1 regarding CMAA L/600 mid-span deflection limit ({sp['allowable_l600_deflection_in']} inches)",
    "Step 2 regarding ASME B30.9 sling angle tension multiplier (avoiding angles under 45 degrees)",
    "Step 3 regarding 1/8-inch trolley wheel flange clearance and beam end-stops",
    "Step 4 regarding never hanging hoists from wood roof trusses"
  ],
  "faqs": [
    {{"q": "What size steel I-beam do I need for {item_name}?", "a": "Exact dynamic load, Moment of Inertia Ix, and actual vs L/600 deflection."}},
    {{"q": "How much tension is on each sling leg when lifting {rated_lbs} lbs at 60, 45, and 30 degrees?", "a": "Exact trigonometry tension numbers in lbs per leg."}},
    {{"q": "Should I use a W-beam or S-beam for my shop hoist trolley?", "a": "Direct structural comparison of Wide-Flange stability vs S-beam tapered flanges."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{item_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{item_name}': {e}")
                break

    return det_fallback


def build_hoist_html_page(data, slug, mon_cfg):
    hst_name = data.get("hoist_name", "Overhead Shop Hoist & Gantry Crane")
    sp = data.get("specs", {})
    load_lbs = int(safe_float(sp.get("rated_load_lbs", 4000), 4000))
    tons = round(safe_float(sp.get("rated_tons", 2.0), 2.0), 1)
    span_ft = int(safe_float(sp.get("beam_span_ft", 12), 12))
    beam_s = sp.get("recommended_beam_spec", "W8×24 Wide-Flange")
    ix_val = round(safe_float(sp.get("moment_of_inertia_ix", 82.7), 82.7), 1)
    flange_in = round(safe_float(sp.get("flange_width_in", 6.50), 6.50), 2)
    act_def = round(safe_float(sp.get("actual_deflection_in", 0.148), 0.148), 3)
    lim_def = round(safe_float(sp.get("allowable_l600_deflection_in", 0.240), 0.240), 3)
    leg_60 = int(safe_float(sp.get("sling_leg_60deg_lbs", 2309), 2309))
    leg_30 = int(safe_float(sp.get("sling_leg_30deg_lbs", 4000), 4000))

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Electric+Chain+Hoist+Gantry+Crane+I+Beam+Trolley"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{hst_name} I-Beam Deflection & Sling Angle Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Electric Chain Hoist Gantry Crane")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-amber-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Rigging Hardware')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$79+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">🏗️ {item.get('hst_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build AISC Steel I-Beam Section vs Moment of Inertia, Flange Width & Span Capacity Matrix Table
    beam_tiers = [
        ("W6×12 (or S6×12.5)", "22.1 in⁴", "4.00\" Flange", "1-Ton up to 10 Ft Span", "1-Ton Push Trolley"),
        ("W8×18 (or S8×18.4)", "61.9 in⁴", "5.25\" Flange", "1-Ton @ 15' / 2-Ton @ 10'", "1–2 Ton Geared Trolley"),
        ("W8×24 Wide-Flange", "82.7 in⁴", "6.50\" Flange", "2-Ton up to 12 Ft Span", "2-Ton Wide-Flange Trolley"),
        ("W10×26 Wide-Flange", "144.0 in⁴", "5.77\" Flange", "2-Ton @ 15' / 3-Ton @ 12'", "2–3 Ton Heavy Trolley"),
        ("W12×35 Wide-Flange", "285.0 in⁴", "6.56\" Flange", "2-Ton @ 20' / 3-Ton @ 16'", "3–5 Ton Industrial Trolley"),
        ("W12×45 Wide-Flange", "348.0 in⁴", "8.05\" Flange", "5-Ton up to 15 Ft Span", "5-Ton Motorized Trolley")
    ]
    matrix_rows_html = ""
    for b_lbl, ix_lbl, fl_lbl, cp_lbl, tr_lbl in beam_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{b_lbl}</td>
          <td class="py-3 px-4 text-zinc-300">{ix_lbl}</td>
          <td class="py-3 px-4 font-bold text-amber-400">{fl_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{cp_lbl}</td>
          <td class="py-3 px-4 text-xs text-zinc-300">{tr_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("rigging_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-amber-500 rounded cursor-pointer hst-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>CMAA / ASME Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', hst_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', hst_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-amber-500 text-zinc-950 px-2 py-0.5 rounded font-black">HOIST</span>BeamIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Hoists, Cranes & Trolleys →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-amber-500 text-zinc-950 px-3 py-1 rounded-full">{tons:g}-Ton ({load_lbs:,} Lb) | {span_ft}' Span</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Beam: {beam_s} ({act_def}" Deflection)</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">60° Sling: {leg_60:,} lb/leg | 30°: {leg_30:,} lb/leg</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', hst_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-amber-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>AISC Structural & ASME B30.9 Rigging Verdict:</strong> {data.get('structural_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE I-BEAM SPAN DEFLECTION, HOIST CAPACITY & SLING ANGLE CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {hst_name} Beam Deflection & Sling Angle Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Adjust your lifted load weight, unsupported I-beam span length, AISC steel beam section, and 2-leg rigging sling angle to verify CMAA L/600 beam deflection and sling leg tension.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="loadSlider" class="text-zinc-300">Hoist Lifted Load Weight (Lbs)</label>
              <span class="text-amber-400 font-bold"><span id="loadVal">{load_lbs:,}</span> lbs ({tons:g} Ton)</span>
            </div>
            <input id="loadSlider" type="range" min="500" max="10000" step="250" value="{load_lbs}" class="w-full accent-amber-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="beamSelect" class="block text-xs font-medium text-zinc-400 mb-1">AISC Steel I-Beam Section</label>
              <select id="beamSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="22.1|W6×12 (4.0&quot; Flange)" {"selected" if ix_val <= 25 else ""}>W6×12 / S6×12.5 (Ix=22.1 in⁴)</option>
                <option value="61.9|W8×18 (5.25&quot; Flange)" {"selected" if 25 < ix_val <= 65 else ""}>W8×18 / S8×18.4 (Ix=61.9 in⁴)</option>
                <option value="82.7|W8×24 (6.5&quot; Flange)" {"selected" if 65 < ix_val <= 95 else ""}>W8×24 Wide-Flange (Ix=82.7 in⁴)</option>
                <option value="144.0|W10×26 (5.77&quot; Flange)" {"selected" if 95 < ix_val <= 180 else ""}>W10×26 Wide-Flange (Ix=144 in⁴)</option>
                <option value="285.0|W12×35 (6.56&quot; Flange)" {"selected" if 180 < ix_val <= 300 else ""}>W12×35 Wide-Flange (Ix=285 in⁴)</option>
                <option value="348.0|W12×45 (8.05&quot; Flange)" {"selected" if ix_val > 300 else ""}>W12×45 Wide-Flange (Ix=348 in⁴)</option>
              </select>
            </div>
            <div>
              <label for="angleSelect" class="block text-xs font-medium text-zinc-400 mb-1">2-Leg Sling Horizontal Angle</label>
              <select id="angleSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="1.000|90° Vertical">90° Vertical Basket (0.50x/leg)</option>
                <option value="0.866|60° Standard" selected>60° Recommended Angle (0.58x/leg)</option>
                <option value="0.707|45° Wide">45° Minimum Safe Angle (0.71x/leg)</option>
                <option value="0.500|30° Danger!">30° Shallow Angle (1.00x/leg!)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="spanSlider" class="text-zinc-300">Unsupported I-Beam Span Between Columns (Feet)</label>
              <span class="text-amber-400 font-bold"><span id="spanVal">{span_ft}</span> ft Span</span>
            </div>
            <input id="spanSlider" type="range" min="6" max="24" step="1" value="{span_ft}" class="w-full accent-amber-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-amber-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-amber-400 font-bold">Mid-Span Deflection</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="deflOut">{act_def}</span>"</div>
            <p id="l600NoteOut" class="text-xs text-emerald-400 font-semibold mt-1">✅ Passes L/600 ({lim_def}" Max)</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Tension Per Sling Leg</span>
            <div class="text-2xl sm:text-3xl font-black text-emerald-400 mt-1"><span id="slingOut">{leg_60:,}</span> <span class="text-xs font-normal text-zinc-400">lbs</span></div>
            <p id="recBeamOut" class="text-xs text-zinc-300 font-semibold mt-1">Min Beam: {beam_s.split()[0]}</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="hstAdviceBanner" class="text-sm text-amber-100 font-medium"></div>
        <a id="dynamicHstBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Hoist, Trolley & Sling on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {hst_name} Hoist, Gantry & Rigging Bundle</h2>
        <span class="text-xs text-zinc-400">CMAA #74 & ASME B30.16 / B30.9 Compliant</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">AISC Steel I-Beam Section, Moment of Inertia ($I_x$), Flange Width & Hoist Capacity Chart</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">AISC Beam Size</th>
              <th class="py-3.5 px-4">Inertia ($I_x$)</th>
              <th class="py-3.5 px-4 text-amber-400">Flange Width</th>
              <th class="py-3.5 px-4 text-emerald-400">L/600 Span Capacity</th>
              <th class="py-3.5 px-4">Matched Trolley Tier</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">CMAA & ASME B30.9 Beam Deflection, Trolley Clearance & Sling Angle Checklist</h2>
        <span id="hstBadge" class="text-xs font-bold bg-zinc-800 text-amber-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({hst_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} HoistBeamIndex. Independent Overhead Crane I-Beam Deflection & ASME Rigging Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const loadSlider = document.getElementById('loadSlider');
    const beamSelect = document.getElementById('beamSelect');
    const angleSelect = document.getElementById('angleSelect');
    const spanSlider = document.getElementById('spanSlider');
    const loadVal = document.getElementById('loadVal');
    const spanVal = document.getElementById('spanVal');
    const deflOut = document.getElementById('deflOut');
    const l600NoteOut = document.getElementById('l600NoteOut');
    const slingOut = document.getElementById('slingOut');
    const recBeamOut = document.getElementById('recBeamOut');
    const hstAdviceBanner = document.getElementById('hstAdviceBanner');
    const dynamicHstBtn = document.getElementById('dynamicHstBtn');

    function recalculateHoist() {{
      const loadLbs = parseInt(loadSlider.value, 10);
      const beamParts = beamSelect.value.split('|');
      const ixVal = parseFloat(beamParts[0]);
      const beamName = beamParts[1];
      const angleParts = angleSelect.value.split('|');
      const sinTheta = parseFloat(angleParts[0]);
      const spanFt = parseInt(spanSlider.value, 10);

      const tonsVal = (loadLbs / 2000.0).toFixed(1);
      loadVal.textContent = `${{loadLbs.toLocaleString()}} lbs (${{tonsVal}}T)`;
      spanVal.textContent = spanFt;

      const pDesign = (loadLbs * 1.15) + 120.0;
      const spanIn = spanFt * 12.0;
      const actualDefl = (pDesign * Math.pow(spanIn, 3)) / (48.0 * 29000000.0 * ixVal);
      const allowL600 = spanIn / 600.0;

      // Minimum Ix needed to pass L/600
      const minIxNeeded = (pDesign * Math.pow(spanIn, 3)) / (48.0 * 29000000.0 * allowL600);
      let minBeamRec = "W6×12";
      if (minIxNeeded <= 22.1) minBeamRec = "W6×12";
      else if (minIxNeeded <= 61.9) minBeamRec = "W8×18";
      else if (minIxNeeded <= 82.7) minBeamRec = "W8×24";
      else if (minIxNeeded <= 144.0) minBeamRec = "W10×26";
      else if (minIxNeeded <= 285.0) minBeamRec = "W12×35";
      else minBeamRec = "W12×45+";

      const legTension = Math.round(loadLbs / (2.0 * sinTheta));
      const stdHoistTon = loadLbs <= 1000 ? "1/2-Ton" : (loadLbs <= 2200 ? "1-Ton" : (loadLbs <= 4400 ? "2-Ton" : (loadLbs <= 6600 ? "3-Ton" : "5-Ton")));

      deflOut.textContent = actualDefl.toFixed(3);
      if (actualDefl <= allowL600) {{
        l600NoteOut.textContent = `✅ Passes L/600 (${{allowL600.toFixed(3)}}" Max)`;
        l600NoteOut.className = "text-xs text-emerald-400 font-semibold mt-1";
      }} else {{
        l600NoteOut.textContent = `⚠️ Exceeds L/600! Upgrade to ${{minBeamRec}}`;
        l600NoteOut.className = "text-xs text-amber-400 font-bold mt-1";
      }}

      slingOut.textContent = legTension.toLocaleString();
      recBeamOut.textContent = `Min L/600 Beam: ${{minBeamRec}}`;

      hstAdviceBanner.innerHTML = `🏗️ <strong>CMAA & ASME Spec:</strong> Lifting ${{loadLbs.toLocaleString()}} lbs across a ${{spanFt}}-ft span requires at least a <strong>${{minBeamRec}} Steel I-Beam</strong>, a <strong>${{stdHoistTon}} Electric Chain Hoist + Geared Beam Trolley</strong>, and a <strong>Grade-100 2-Leg Chain Sling</strong> (${{legTension.toLocaleString()}} lbs tension/leg).`;
      dynamicHstBtn.href = `https://${{amzDomain}}/s?k=${{encodeURIComponent(stdHoistTon)}}+Electric+Chain+Hoist+I+Beam+Trolley+Grade+80+Chain+Sling&tag=${{amzTag}}`;
    }}

    loadSlider.addEventListener('input', recalculateHoist);
    beamSelect.addEventListener('change', recalculateHoist);
    angleSelect.addEventListener('change', recalculateHoist);
    spanSlider.addEventListener('input', recalculateHoist);
    recalculateHoist();

    const checks = document.querySelectorAll('.hst-check');
    const badge = document.getElementById('hstBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Electric+Chain+Hoist+Gantry+Crane+I+Beam+Trolley"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-amber-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-amber-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('tons', 2.0):g}-Ton ({item.get('span_ft', 12)}' Span)</span>
            <span class="text-xs text-zinc-400">{item.get('beam', 'W8×24')} | {item.get('defl', 0.148)}" Defl</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-amber-400 transition">{item['hoist_name']}</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-amber-400">Calculate I-Beam Deflection & Sling Angle →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HoistBeamIndex — Overhead Gantry Crane I-Beam Deflection, Hoist & Sling Angle Calculator (2026)</title>
  <meta name="description" content="Calculate exact AISC steel I-beam mid-span deflection (CMAA L/600 rule), electric chain hoist and trolley sizing, and ASME B30.9 rigging sling angle tension for 1-ton, 2-ton, 3-ton, and 5-ton shop cranes.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="HoistBeamIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-amber-500 text-zinc-950 px-2 py-0.5 rounded font-black">HOIST</span>BeamIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Hoists, Cranes & Trolleys →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Overhead Gantry Crane I-Beam Deflection, Hoist & Sling Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your electric chain hoist tonnage, gantry span, or AISC W-beam/S-beam section below to verify CMAA L/600 center-span deflection, trolley flange clearance, and ASME B30.9 sling leg tension.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search tonnage, span, or beam (e.g. 2-Ton Gantry, 15-Ft Span, W8x18, W10x26, Harrington Hoist, Sling Angle...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-amber-500">
      </div>
    </div>

    <div id="hstGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} HoistBeamIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('hstGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>HoistBeamIndex Overhead Gantry Crane & Rigging Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Gantry Crane Steel I-Beam Deflection, Electric Chain Hoist & Sling Angle Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_HOIST:
        candidates.append((CUSTOM_HOIST.strip(), 4000, 12, "W8×24 Wide-Flange", 82.7, 6.50, "120V/240V Electric Chain Hoist"))
    candidates.extend(SEED_HOISTS)
    candidates.extend(discover_google_hoist_queries(published_slugs))

    new_urls = []
    count = 0

    for hoist_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        h_name = hoist_tuple[0]
        slug = slugify(f"{h_name}-ibeam-sling-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating gantry crane I-beam deflection & hoist calculator for: {h_name}...")
        try:
            data = generate_hoist_data(hoist_tuple)
            build_hoist_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "hoist_name": data.get("hoist_name", h_name),
                "slug": slug,
                "title": data.get("seo_title", f"{h_name} Hoist & Beam Calculator"),
                "description": data.get("meta_description", ""),
                "tons": round(safe_float(sp.get("rated_tons", round(hoist_tuple[1] / 2000.0, 1)), 2.0), 1),
                "span_ft": int(safe_float(sp.get("beam_span_ft", hoist_tuple[2]), hoist_tuple[2])),
                "beam": sp.get("recommended_beam_spec", hoist_tuple[3]).split()[0],
                "defl": round(safe_float(sp.get("actual_deflection_in", 0.148), 0.148), 3),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {h_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new overhead hoist & I-beam deflection calculator pages.")


if __name__ == "__main__":
    main()
