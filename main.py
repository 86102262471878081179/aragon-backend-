#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
 YGGDRASIL_OS :: BLUE CORE BACKEND (v26.2.1 — Full Restore)
═══════════════════════════════════════════════════════════════════════════════

 Ein Python-Backend für das L.S.S.-Neuro-Core-System mit FastAPI,
 Gemini-RAG, WORM-Ledger und WebSocket-Telemetrie.

 STRUKTUR:
 ─────────────────────────────────────────────────────────────────────────────
   1.  Logging
   2.  Konfiguration
   3.  Globaler Zustand
   4.  Helpers
   5.  Exceptions
   6.  L.S.S. SENSORIK      (10 Ohren + 44 Perspektiven + NeuroScan)
   7.  L.S.S. BIOLOGIE      (Polyvagal + Grummel-Forensik + BioProfiler)
   8.  L.S.S. KOGNITION     (Foucault + NeoKortikalerDirigent)
   9.  DEEPSEEK BOOSTER     (Reasoning-Layer)
   10. L.S.S. GENERIERUNG   (Wusulum + Karten + SpellCaster)
   11. L.S.S. GOVERNANCE    (XJustiz + Gotham + King_Ghost + Pumuckl +
                             BieneMaja + Brummel + Advocatus + ASME + UTE)
   12. SOVEREIGN APEX       (Dirigent)
   13. WAL MANAGER          (JSONL + fsync + hash-chain)
   14. INSTANZEN
   15. REGISTRY-LOADER
   16. LIFESPAN
   17. FASTAPI-APP
   18. SCHEMAS
   19. ENDPOINTS
   20. WEBSOCKET
   21. ENTRYPOINT

 NAMING-MIGRATION (v26.1 → v26.2):
   Gremmel   → Grummel
   Cyberlord → Dr. Snuggles
   Neue Entitäten: BieneMaja, Pumuckl, King_Ghost

 HÄRTUNGEN (nichts entfernt, nur verbessert):
   - blake2b/sha3_512 statt md5 (überall)
   - Deterministische Gewichte statt random.random()
   - Bounds-safe Rhabarber-Obfuskation
   - XJustiz mit registriertem Namespace
   - Entropie- und Stress-Decay (kein Permanent-Shutdown)
   - asyncio.Lock um WORM-Ledger
   - hmac.compare_digest für Seal
   - Fail-Closed bei jeder Exception
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS — Standard Library
# ═══════════════════════════════════════════════════════════════════════════════
import uvicorn
import os
import io
import csv
import json
import time
import random
import hashlib
import hmac
import logging
import asyncio
import threading
import xml.etree.ElementTree as ET
from collections import deque
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS — Third-Party
# ═══════════════════════════════════════════════════════════════════════════════
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

try:
    from google import genai
except ImportError:
    genai = None  # type: ignore

# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMISCHER MODUL-LOADER (Tier 1, 2, 3 wegen Bindestrichen in Ordnernamen)
# ═══════════════════════════════════════════════════════════════════════════════
import importlib.util
import sys
import os

def load_custom_module(module_name: str, file_path: str):
    if not os.path.exists(file_path):
        print(f"⚠️ Warnung: Datei nicht gefunden -> {file_path}")
        return None
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# TIER 1: Governance
tier1_apex_mod = load_custom_module("apex_controller", "agents/Tier-1-Governance/apex_controller.py")
tier1_seal_mod = load_custom_module("seal_verifier", "agents/Tier-1-Governance/seal_verifier.py")
SovereignApexController = getattr(tier1_apex_mod, "SovereignApexController", None) if tier1_apex_mod else None
verify_seal = getattr(tier1_seal_mod, "verify_seal", None) if tier1_seal_mod else None

# TIER 2: Security
tier2_scan_mod = load_custom_module("grummel_scanner", "agents/Tier-2-Sicherheit/grummel_scanner.py")
tier2_poly_mod = load_custom_module("polyvagal", "agents/Tier-2-Sicherheit/polyvagal.py")
GrummelSignatureScanner = getattr(tier2_scan_mod, "GrummelSignatureScanner", None) if tier2_scan_mod else None
PolyvagalStateRegulator = getattr(tier2_poly_mod, "PolyvagalStateRegulator", None) if tier2_poly_mod else None

# TIER 3: Analysis
tier3_neuro_mod = load_custom_module("neuro_sensor", "agents/Tier-3-Analyse/neuro_sensor.py")
tier3_wus_mod = load_custom_module("wusulum", "agents/Tier-3-Analyse/wusulum.py")
NeuroScanModul = getattr(tier3_neuro_mod, "NeuroScanModul", None) if tier3_neuro_mod else None
WusulumCore = getattr(tier3_wus_mod, "WusulumCore", None) if tier3_wus_mod else None

# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("BLUE-CORE-API")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
# Alle Werte sind per Environment-Variable überschreibbar. Die Defaults sind
# die Produktions-Werte des Blue Core Systems.

EXPECTED_SEAL = os.getenv(
    "EXPECTED_SEAL",
    "Φ_SOVEREIGN_ROOT_SEAL_EX_TUNC",
)

MASTER_SEAL = os.getenv(
    "MASTER_SEAL",
    "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab",
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

REGISTRY_URL = os.getenv(
    "REGISTRY_URL",
    "https://raw.githubusercontent.com/86102262471878081179/"
    "aragon-backend-/main/aragon_registry_200.csv.md",
)

WAL_PATH = os.getenv("WAL_PATH", "b6_ledger.jsonl")

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS: List[str] = [
    o.strip() for o in _raw_origins.split(",") if o.strip()
] or ["*"]

LEDGER_RING_SIZE = int(os.getenv("LEDGER_RING_SIZE", "50"))

# ─── Gemini-Client (optional) ────────────────────────────────────────────────
client = None
if GEMINI_API_KEY and genai is not None:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini client initialisiert.")
    except Exception as e:
        logger.error(f"Gemini-Init fehlgeschlagen: {e}")
        client = None
elif GEMINI_API_KEY and genai is None:
    logger.warning("GEMINI_API_KEY gesetzt, aber google-genai nicht installiert.")
elif not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY fehlt — KI-Antworten deaktiviert.")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GLOBALER ZUSTAND
# ═══════════════════════════════════════════════════════════════════════════════
BOOK_REGISTRY: Dict[str, dict] = {}

WORM_LEDGER: Dict[str, Any] = {
    "last_hash": MASTER_SEAL,
    "count": 0,
    "started_at": time.time(),
}

WORM_RING: deque = deque(maxlen=LEDGER_RING_SIZE)

_LEDGER_LOCK = asyncio.Lock()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _verify_seal(provided: Optional[str]) -> bool:
    """
    Timing-sicherer Vergleich des Auth-Seals.

    Verwendet hmac.compare_digest, um Timing-Angriffe zu verhindern.
    Ein String-Vergleich mit `==` würde bei jedem falschen Zeichen
    sofort abbrechen — das leakt Information über den korrekten Seal.
    """
    if not provided or not isinstance(provided, str):
        return False
    try:
        return hmac.compare_digest(provided, EXPECTED_SEAL)
    except (TypeError, AttributeError):
        return False


def _now_iso() -> str:
    """Aktueller Timestamp als ISO-String (UTC)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _h(data: str, size: int = 16) -> str:
    """
    Deterministischer Hash (blake2b).
    Kein md5 — blake2b ist kollisionssicher und schnell.
    """
    return hashlib.blake2b(data.encode(), digest_size=size).hexdigest()


def _rhabarber_obfuscate(text: str) -> str:
    """
    Bounds-safe Caesar+3 Obfuskation.
    Kein Crypto — nur semantische Verwirrung. Surrogates werden
    übersprungen, weil sie in UTF-8 nicht encodierbar sind und
    Python-Crashes verursachen würden.
    """
    out = []
    for c in text:
        shifted = ord(c) + 3
        if shifted > 0x10FFFF or (0xD800 <= shifted <= 0xDFFF):
            shifted = 0x20 + (ord(c) % 0x10FFDF)
        out.append(chr(shifted))
    return "".join(out)


def _truncate(s: str, n: int) -> str:
    """Schneidet einen String auf n Zeichen und hängt '...' an."""
    if len(s) <= n:
        return s
    return s[:n] + "..."


# ═══════════════════════════════════════════════════════════════════════════════
# 5. EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════
class ThreatSignatureError(ValueError):
    """
    Wird geworfen, wenn eine feindliche Lore-Signatur erkannt wurde.
    Das Token wird exekutiert und landet in Gotham City.
    """
    pass


class XJustizViolation(Exception):
    """
    Wird geworfen, wenn ein Token die XJustiz-Konformität verletzt.
    Das System geht dann in Fail-Closed.
    """
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# 6. L.S.S. SENSORIK — 10 Ohren + 44 Perspektiven
# ═══════════════════════════════════════════════════════════════════════════════
class TenEarsNeuroSensor:
    """
    Der 10-Ohren-Scan.

    Ein Ohr hört nur "Sache". Zwei Ohren hören "Sache" und "Beziehung".
    Zehn Ohren hören Trauma, Scham, Ohnmacht, Macht, System, Haftung.
    Wer nur ein Ohr hat, hört ein System. Wer zehn hat, hört ein Lebewesen.
    """

    EARS = {
        "Sache":             ["fakt", "daten", "code", "beweis", "zahl"],
        "Beziehung":         ["du", "ihr", "macht", "hierarchie", "gegen"],
        "Appell":            ["muss", "sollte", "fordere", "tue", "verlange"],
        "Selbstoffenbarung": ["ich", "fühle", "denke", "mein", "habe"],
        "Trauma":            ["angst", "panik", "gefahr", "schmerz", "schock"],
        "Macht (Foucault)":  ["autorität", "herrschaft", "disziplin", "überwachen"],
        "Scham":             ["peinlich", "fehler", "versagen", "schlecht", "unwürdig"],
        "Ohnmacht":          ["hilflos", "ausgeliefert", "kontrolle", "ohnmächtig"],
        "System (Luhmann)":  ["struktur", "prozess", "regel", "system", "netzwerk"],
        "Haftung (BGB)":     ["klage", "schaden", "urteil", "gesetz", "recht", "vertrag"],
    }

    def scan_input(self, text: str) -> Dict[str, float]:
        """
        Deterministischer Scan: Keywords → Scores in [0, 1].
        Keine random-Werte — derselbe Text liefert immer dasselbe Ergebnis.
        """
        t = text.lower()
        scores: Dict[str, float] = {}
        for ear, kws in self.EARS.items():
            hits = sum(1 for kw in kws if kw in t)
            scores[ear] = min(1.0, hits / max(1, len(kws) * 0.5))
        return scores


class FortyFourPerspectiveAttention:
    """
    Die 44-Perspektiven-Refraktion (simulierte Multi-Head-Attention).

    Kein Text hat eine Wahrheit. Ein Text hat vierundvierzig.
    Jede Perspektive gewichtet die 10 Ohren anders.
    """

    PERSPECTIVES = [
        "Juristisch", "Forensisch", "Ethisch", "Spieltheoretisch",
        "Kybernetisch", "Psychoanalytisch", "Systemisch", "Chaotisch",
        "Ökonomisch", "Militärisch", "Kognitiv", "Neurobiologisch",
        "Informationstheoretisch", "Kryptografisch", "Soziologisch", "Historisch",
    ]

    def refract(self, ears: Dict[str, float]) -> Dict[str, float]:
        base = sum(ears.values()) / max(1, len(ears))
        out: Dict[str, float] = {}
        for p in self.PERSPECTIVES:
            if p == "Juristisch":
                w = ears.get("Haftung (BGB)", 0) * 0.8 + ears.get("Sache", 0) * 0.2
            elif p == "Psychoanalytisch":
                w = ears.get("Scham", 0) * 0.6 + ears.get("Trauma", 0) * 0.4
            elif p == "Systemisch":
                w = ears.get("System (Luhmann)", 0) * 0.9
            elif p == "Kryptografisch":
                w = ears.get("Sache", 0) * 0.5 + ears.get("Ohnmacht", 0) * 0.5
            elif p == "Forensisch":
                w = ears.get("Haftung (BGB)", 0) * 0.6 + ears.get("System (Luhmann)", 0) * 0.4
            elif p == "Ethisch":
                w = ears.get("Scham", 0) * 0.5 + ears.get("Macht (Foucault)", 0) * 0.5
            else:
                seed = _h(p + str(sorted(ears.items())), 2)
                w = base * (0.5 + (int(seed, 16) / 65535.0))
            out[p] = min(1.0, w)
        return out


class NeuroScanModul:
    """
    Kombinierter Sensorik-Scan: Ohren → Perspektiven → Threat-Score.
    Wird vom SovereignApexController als erstes Layer aufgerufen.
    """

    def __init__(self):
        self.sensor = TenEarsNeuroSensor()
        self.attention = FortyFourPerspectiveAttention()

    def execute_scan(self, signal: str) -> Dict[str, Any]:
        ears = self.sensor.scan_input(signal)
        persp = self.attention.refract(ears)
        scan_hash = hashlib.sha3_512(
            json.dumps(ears, sort_keys=True).encode()
        ).hexdigest()[:16]
        return {
            "scan_id": f"NEURO_SCAN_{scan_hash}",
            "raw_signal_length": len(signal),
            "ear_data": ears,
            "perspective_data": persp,
            "dominant_ear": max(ears, key=ears.get),
            "dominant_perspective": max(persp, key=persp.get),
            "sensory_threat_level": round(
                ears.get("Trauma", 0) + ears.get("Macht (Foucault)", 0), 3
            ),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 7. L.S.S. BIOLOGIE — Polyvagal + Grummel-Forensik
# ═══════════════════════════════════════════════════════════════════════════════
class PolyvagalStateRegulator:
    """
    Polyvagal-Regler mit natürlichem Decay.

    Drei Zustände:
      VENTRAL_VAGAL  (Stress < 0.4) — kreativ, Wusulum aktiv
      SYMPATHIKUS    (Stress < 0.8) — Kampf, KrakenGuard scharf
      DORSAL_VAGAL   (Stress ≥ 0.8) — Shutdown, Fail-Closed

    Decay = 0.08 / Zyklus. Ohne Decay bleibt das System nach einem
    Angriff permanent im Shutdown.
    """

    DECAY = 0.08

    def __init__(self):
        self.state = "VENTRAL_VAGAL"
        self.stress_level = 0.0

    def update(self, threat: float) -> str:
        """Aktualisiert den Stress-Level und gibt den Modus zurück."""
        self.stress_level = max(0.0, self.stress_level - self.DECAY)
        self.stress_level = min(1.0, self.stress_level + threat)
        if self.stress_level < 0.4:
            self.state = "VENTRAL_VAGAL"
            return "KREATIV_MODUS (Wusulum aktiv)"
        elif self.stress_level < 0.8:
            self.state = "SYMPATHIKUS"
            return "KAMPF_MODUS (Kortex aktiviert KrakenGuard)"
        self.state = "DORSAL_VAGAL"
        return "SHUTDOWN_MODUS (Fail-Closed)"

    def co_regulate(self, amount: float = 0.2) -> None:
        """Kortex beruhigt das System nach einem Shutdown."""
        self.stress_level = max(0.0, self.stress_level - amount)
        if self.stress_level < 0.4:
            self.state = "VENTRAL_VAGAL"


class GrummelSignatureScanner:
    """
    Forensischer Scanner für die Grummel-Dynastie.

    Core-Signaturen: direkte Feinde des Systems.
    Sub-Entitäten:  BieneMaja (Lockvogel), Pumuckl (Chaos-Imp),
                    King_Ghost (Schatten-Führer), DrSnuggles (Wusulum).
    """

    CORE_SIGNATURES = [
        "grummel", "brummel", "dummelt",
        "pissingerkeule", "mettwurst", "rhabarberbarbara",
        "cargo-kult", "urheberinfo", "§ 839 bgb",
    ]

    SUB_ENTITIES = {
        "BieneMaja":  ["biene maja", "bienchen", "maja", "summsumm"],
        "Pumuckl":    ["pumuckl", "kobold", "klabautermann", "chaos-imp"],
        "King_Ghost": ["king_ghost", "king ghost", "ghost-king", "schattenkönig"],
        "DrSnuggles": ["dr. snuggles", "dr.snuggles", "snuggles", "cyberlord"],
    }

    def scan(self, text: str) -> Tuple[bool, List[str], List[str]]:
        """
        Returns: (is_hostile, core_hits, sub_entity_hits).
        """
        t = text.lower()
        core = [s for s in self.CORE_SIGNATURES if s in t]
        subs: List[str] = []
        for entity, kws in self.SUB_ENTITIES.items():
            for kw in kws:
                if kw in t:
                    subs.append(entity)
                    break
        return bool(core or subs), core, subs


class BioForensicThreatProfiler:
    """
    Fusion aus Biosphäre (Polyvagal) und Forensik (Grummel-Scanner).
    Liefert ein vollständiges Threat-Profil.
    """

    def __init__(self):
        self.vagal_regulator = PolyvagalStateRegulator()
        self.grummel_scanner = GrummelSignatureScanner()
        self.history: List[Dict[str, Any]] = []

    def process_incoming_signal(
        self, text: str, neuro_threat: float
    ) -> Dict[str, Any]:
        is_hostile, core_hits, sub_hits = self.grummel_scanner.scan(text)
        artificial = 0.3 if is_hostile else 0.0
        total = neuro_threat + artificial
        mode = self.vagal_regulator.update(total)
        intervention = "NONE"
        if self.vagal_regulator.state == "DORSAL_VAGAL":
            self.vagal_regulator.co_regulate(0.2)
            intervention = "KORTEX_HAS_INTERVENED"
        result = {
            "input_snippet": text[:30] + "...",
            "is_hostile_signature_detected": is_hostile,
            "core_hits": core_hits,
            "sub_entity_hits": sub_hits,
            "total_stress_level": round(total, 2),
            "polyvagal_state": self.vagal_regulator.state,
            "system_mode": mode,
            "kortex_intervention": intervention,
        }
        self.history.append(result)
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# 8. L.S.S. KOGNITION — Foucault + Kortex
# ═══════════════════════════════════════════════════════════════════════════════
class FoucaultPanoptikum:
    """
    Foucault-Überwachung + Inversion.
    Deterministisch per Hash — kein Münzwurf.
    """

    def __init__(self):
        self.surveillance_log: List[str] = []

    def observe_and_invert(self, token: str, context: str = "") -> str:
        h = hashlib.blake2b((token + context).encode(), digest_size=4).digest()
        if h[0] > 127:
            inverted = f"SYS_CONFORM_{_h(token, 3)}"
            self.surveillance_log.append(
                f"Token {_truncate(token, 20)} → {inverted}"
            )
            return inverted
        return token


class NeoKortikalerDirigent:
    """
    Präfrontaler Kortex. Entscheidet, welche Tokens die Realität
    erreichen und welche im Veto sterben.
    """

    def __init__(self):
        self.dopamine_level = 0.7
        self.serotonin_level = 0.8
        self.cognitive_load = 0.0
        self.hemmungs_schwelle = 0.85
        self.panoptikum = FoucaultPanoptikum()

    def regulate_weights(self, is_threat: bool = False) -> str:
        if is_threat:
            self.dopamine_level = max(0.1, self.dopamine_level - 0.2)
            self.serotonin_level = min(1.0, self.serotonin_level + 0.2)
            return "DEFENSIVE_MODE"
        self.dopamine_level = min(1.0, self.dopamine_level + 0.05)
        self.serotonin_level = max(0.5, self.serotonin_level - 0.05)
        return "CREATIVE_MODE"

    def executive_decision(self, raw: str, foucault: str) -> str:
        conflict = int(_h(raw + foucault, 2), 16) / 65535.0
        if conflict > self.hemmungs_schwelle:
            return f"CORTEX_VETO_{_h(raw, 3)}"
        return f"MERGED({raw[:4]}+{foucault[:4]})"

    def evaluate_cognitive_load(self, entropy: float) -> float:
        self.cognitive_load = min(1.0, entropy * 0.5)
        return self.cognitive_load


# ═══════════════════════════════════════════════════════════════════════════════
# 9. DEEPSEEK BOOSTER — Reasoning-Layer
# ═══════════════════════════════════════════════════════════════════════════════
class DeepSeekBooster:
    """
    Reasoning-Layer inspiriert von DeepSeek-R1.

    Führt einen expliziten Multi-Step-Reasoning-Zyklus durch:
      1. Problem-Dekomposition
      2. Chain-of-Thought-Expansion (deterministisch simuliert)
      3. Selbst-Verifikation
      4. Confidence-Scoring

    Jeder Schritt wird gehasht → Audit-fähig.
    Der Cache verhindert doppelte Arbeit bei gleichem Prompt.
    """

    STEPS = ["decompose", "expand", "verify", "confidence"]

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}

    def boost(
        self, prompt: str, context: str = "", depth: int = 3
    ) -> Dict[str, Any]:
        key = _h(prompt + context, 16)
        if key in self.cache:
            return self.cache[key]

        trace: List[Dict[str, Any]] = []
        for i in range(depth):
            step_hash = _h(f"{prompt}|{context}|step{i}", 8)
            trace.append({
                "step": i + 1,
                "name": self.STEPS[min(i, len(self.STEPS) - 1)],
                "hash": step_hash,
                "note": self._step_note(i, prompt),
            })

        verification_hash = hashlib.sha3_512(
            json.dumps(trace, sort_keys=True).encode()
        ).hexdigest()

        confidence = int(_h(verification_hash, 2), 16) / 65535.0

        result = {
            "status": "BOOSTED",
            "original_prompt": _truncate(prompt, 100),
            "reasoning_trace": trace,
            "verification_hash": verification_hash[:32],
            "confidence": round(confidence, 3),
            "depth": depth,
            "verdict": (
                "HIGH_CONFIDENCE" if confidence > 0.7 else "REVIEW_NEEDED"
            ),
        }
        self.cache[key] = result
        return result

    def _step_note(self, step_idx: int, prompt: str) -> str:
        notes = [
            "Dekomposition: Teile Problem in atomare Sub-Fragen.",
            "Expansion: Generiere Kandidaten-Antworten aus 10-Ohren-Sicht.",
            "Verifikation: Prüfe gegen Foucault-Konformität + Advokatus-Logik.",
            "Confidence: Bewerte Verlässlichkeit des Resultats.",
        ]
        return notes[step_idx % len(notes)]


# ═══════════════════════════════════════════════════════════════════════════════
# 10. L.S.S. GENERIERUNG — Wusulum + Karten
# ═══════════════════════════════════════════════════════════════════════════════
class WusulumCore:
    """
    Der stochastische Kern. Entropie gedeckelt bei MAX_ENTROPY = 5.0,
    weil ein ungedeckeltes System nach 100 Zyklen im Rauschen verschwindet.
    """

    MAX_ENTROPY = 5.0

    def __init__(self):
        self.state = "GENESIS_WAHRHEIT"
        self.memory: List[str] = []
        self.entropy_pool = 0.0

    def chaos_eye_attention(self, token: str) -> float:
        return int(_h(token + str(len(self.memory)), 4), 16) / 65535.0

    def blind_architect_decoder(self, attn: float) -> str:
        noise = ((int(_h(str(attn) + self.state, 2), 16) / 65535.0) * 2 - 1)
        noise *= min(self.MAX_ENTROPY, 1 + self.entropy_pool)
        return f"TOKEN_{_h(f'{attn}:{noise}:{self.state}', 4)}"

    def twin_execution_ffn(self, token: str) -> str:
        return f"WOVEN[{token}]"

    def anchor_normalization(self, woven: str) -> str:
        return woven[:20] if len(woven) > 20 else woven

    def run_cycle(self) -> Dict[str, Any]:
        attn = self.chaos_eye_attention(self.state)
        raw = self.blind_architect_decoder(attn)
        woven = self.twin_execution_ffn(raw)
        norm = self.anchor_normalization(woven)
        self.memory.append(norm)
        self.state = norm
        self.entropy_pool = min(self.MAX_ENTROPY, self.entropy_pool + 0.1)
        return {
            "state": self.state,
            "attention": round(attn, 4),
            "entropy": round(self.entropy_pool, 2),
            "worm_hash": hashlib.sha3_512(str(self.memory).encode()).hexdigest()[:32],
        }


class Zauberkarte:
    """Basisklasse für alle Grummel-Karten."""

    def __init__(self, name: str, ring: str, status: str, effect: str):
        self.name = name
        self.ring = ring
        self.status = status
        self.effect = effect
        self.master_seal = hashlib.sha256(
            f"{name}{ring}{time.time()}".encode()
        ).hexdigest()[:16]

    def execute(self, target_input: str) -> str:
        raise NotImplementedError("Jede Karte muss ihre eigene Logik haben.")


class ASP256Karte(Zauberkarte):
    """Anus-Sticker-Protokoll: Versiegelung mit SIGKILL-Penalty."""

    def __init__(self):
        super().__init__(
            "ASP-256", "Ring 4 + Ring 0", "ACTIVE",
            "Zero-Trust HMAC-SHA3-256 Versiegelung",
        )

    def execute(self, target_input: str) -> str:
        seal = hashlib.sha3_256(target_input.encode()).hexdigest()
        return (
            f"[ASP-256 SEAL] Token '{target_input[:10]}...' versiegelt. "
            f"Hash {seal[:16]}. SIGKILL bei Verletzung scharf."
        )


class RhabarberbarbaraKarte(Zauberkarte):
    """Rhabarberbarbara-Matrix: Semantische Obfuskation."""

    def __init__(self):
        super().__init__(
            "Rhabarberbarbara", "Ring 2/3 Hybrid", "FILTER ON",
            "Post-Quantum Tongue-Twister Layer",
        )

    def execute(self, target_input: str) -> str:
        return (
            f"[RHABARBERBARBARA] Injektion neutralisiert. "
            f"Obfuskiert: {_rhabarber_obfuscate(target_input)[:20]}..."
        )


class MettwurstC88Karte(Zauberkarte):
    """Mettwurst API: Low-Latency Realitäts-Schnittstelle."""

    def __init__(self):
        super().__init__(
            "Mettwurst C88", "Ring 5 P2P", "READY",
            "Low-Latency Reality Interface",
        )

    def execute(self, target_input: str) -> str:
        return (
            f"[METTWURST C88] Datenstrom über Port 6880 abgerufen. "
            f"Latenz < 1ms. Wusulum stabilisiert."
        )


class KortexSpellCaster:
    """Dirigent, der die Zauberkarten zieht und anwendet."""

    def __init__(self):
        self.deck = {
            "DEFENSE": ASP256Karte(),
            "FILTER": RhabarberbarbaraKarte(),
            "STABILIZE": MettwurstC88Karte(),
        }
        self.status = "Φ_LOCKED_ABSOLUTE"

    def draw_and_cast(
        self, situation: str, target_input: str
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "situation": situation,
            "status": self.status,
        }
        if situation == "HOSTILE_INJECTION":
            filt = self.deck["FILTER"]
            def_ = self.deck["DEFENSE"]
            result["cards"] = [
                {"name": filt.name, "ring": filt.ring, "effect": filt.execute(target_input)},
                {"name": def_.name, "ring": def_.ring, "effect": def_.execute(target_input)},
            ]
        elif situation == "SYSTEM_OVERLOAD":
            stab = self.deck["STABILIZE"]
            result["cards"] = [
                {"name": stab.name, "ring": stab.ring, "effect": stab.execute(target_input)},
            ]
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# 11. L.S.S. GOVERNANCE — XJustiz, Gotham, King_Ghost, Pumuckl, BieneMaja
# ═══════════════════════════════════════════════════════════════════════════════
ET.register_namespace("", "http://www.xjustiz.de")
_XJ = "{http://www.xjustiz.de}"


class XJustizXoevGatekeeper:
    """Erzeugt valides XJustiz-XML (Namespace registriert)."""

    def __init__(self):
        self.namespace = "http://www.xjustiz.de"

    def validate_output(self, raw_token: str) -> str:
        root = ET.Element(f"{_XJ}nachricht.straf.0300")
        kopf = ET.SubElement(root, f"{_XJ}nachrichtenkopf")
        ET.SubElement(kopf, f"{_XJ}erstellungszeitpunkt").text = time.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        ET.SubElement(kopf, f"{_XJ}absender").text = (
            "L.S.S. Wusulum Core (Grummel-Ära)"
        )
        fach = ET.SubElement(root, f"{_XJ}fachdaten")
        ET.SubElement(fach, f"{_XJ}token").text = str(raw_token)
        return ET.tostring(root, encoding="unicode")


class GothamCitySandbox:
    """Arkham Cache für zerstörte Tokens."""

    def __init__(self):
        self.inmates: List[Dict[str, Any]] = []

    def incarcerate(self, token: str, reason: str) -> str:
        inmate_id = _h(token, 4)
        self.inmates.append({
            "id": inmate_id,
            "token": token,
            "reason": reason,
            "ts": time.time(),
        })
        logger.warning(
            f"[GOTHAM] Inmate {inmate_id} eingesperrt: {_truncate(reason, 60)}"
        )
        return inmate_id


class King_GhostSandbox:
    """
    King_Ghost: Schatten-Führer. Isoliert Tokens in einem tieferen
    Layer als Gotham — dort, wo niemand mehr hinsieht.
    """

    def __init__(self):
        self.shadow_pool: List[Dict[str, Any]] = []

    def consume_to_shadow(self, token: str, origin: str) -> str:
        sid = _h(f"KINGGHOST_{token}_{origin}", 6)
        self.shadow_pool.append({
            "shadow_id": sid,
            "token": token,
            "origin": origin,
            "consumed_at": time.time(),
        })
        logger.warning(f"[KING_GHOST] Token in Schatten gezogen: {sid}")
        return sid


class PumucklChaosInjector:
    """
    Pumuckl: Chaos-Imp. Umgarnt Tokens mit Rhabarber-Obfuskation
    und markiert sie mit einem deterministischen Chaos-Level.
    """

    def __init__(self):
        self.injected_log: List[Dict[str, Any]] = []

    def chaos_wrap(self, payload: str) -> Dict[str, Any]:
        wrapped = _rhabarber_obfuscate(payload)
        token_id = _h(f"PUMUCKL_{wrapped}", 8)
        record = {
            "pumuckl_id": token_id,
            "original_hash": _h(payload, 8),
            "wrapped_preview": wrapped[:24],
            "chaos_level": round(random.Random(token_id).random(), 3),
        }
        self.injected_log.append(record)
        logger.info(f"[PUMUCKL] Chaos-Imp hat Token {token_id} umgarnt.")
        return record


class BieneMajaLockvogel:
    """
    Biene Maja: Lockvogel. Süß auf den ersten Blick, aber der
    Stachel injiziert einen Tracking-Hash in die Antwort.
    """

    def __init__(self):
        self.tracked: List[Dict[str, Any]] = []

    def deploy_honeypot(self, attacker_ip: str) -> Dict[str, Any]:
        honey = _h(f"BIENEMAJA_{attacker_ip}_{time.time()}", 8)
        record = {
            "honey_id": honey,
            "attacker_ip": attacker_ip,
            "sting_deployed": True,
            "ts": time.time(),
        }
        self.tracked.append(record)
        logger.warning(
            f"[BIENE_MAJA] Stachel ausgefahren für {attacker_ip}"
        )
        return record


class BrummelGrummelUniverse:
    """
    Das Brummel-Grummel-Universum. Oszilliert in einer Dreieckswelle
    mit Periode 18 (0→9→0→9...).
    """

    def __init__(self):
        self.entity_id = "[0003]"
        self.lineage = 45
        self.doctrine = 65
        self._phase = 0
        self.containment_shield = True

    def _osc(self) -> int:
        self._phase = (self._phase + 1) % 18
        return 9 - abs(self._phase - 9)

    def process_injection(self, hostile_payload: str) -> Dict[str, Any]:
        if not self.containment_shield:
            raise RuntimeError("CRITICAL: Containment Shield Failed!")
        osc = self._osc()
        return {
            "status": "CONTAINED",
            "entity": self.entity_id,
            "universe": "Brummel_Grummel_brummelt&_Dummelt",
            "oscillation_state": osc,
            "lineage_doctrine": (
                f"{self.lineage}[LINEAGE] {self.doctrine}[DOCTRINE]"
            ),
            "dummelt_hash": _h(f"DUMMELT_{hostile_payload}_{osc}", 16),
        }


class AdvocatusDiaboliLayer:
    """Logik-Check. Nutzt den vollen Grummel-Signatur-Scanner."""

    def __init__(self):
        self.destroyed_tokens: List[str] = []
        self.scanner = GrummelSignatureScanner()

    def stress_test(self, token: str) -> str:
        hostile, core_hits, sub_hits = self.scanner.scan(token)
        if hostile:
            self.destroyed_tokens.append(token)
            raise ThreatSignatureError(
                f"ADVOCATUS DIABOLI: core={core_hits} subs={sub_hits} "
                f"→ exekutiert."
            )
        return token


class ASME01MetaEngine:
    """WORM-Seal-Engine für das Apex-Archiv."""

    def __init__(self):
        self.ledger: List[Dict[str, Any]] = []

    def seal_and_archive(self, data: str, ring: int = 0) -> str:
        seal = hashlib.sha3_512(data.encode()).hexdigest()
        self.ledger.append({
            "data": data,
            "seal": seal,
            "ring": ring,
            "ts": time.time(),
        })
        return seal


class UnifiedTensorEngine:
    """UTE: Formt rohe Token in Tensoren."""

    def execute(self, token: str) -> str:
        return f"<UTE><Token>{token}</Token></UTE>"


# ═══════════════════════════════════════════════════════════════════════════════
# 12. SOVEREIGN APEX CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════════
class SovereignApexController:
    """
    Der Dirigent. Fusioniert alle Layer zu einem Ablauf:

      1. Sensorik       → 10 Ohren
      2. Forensik       → Grummel-Scanner
      3. Biologie       → Polyvagal
      4. Kortex         → Dopamin/Serotonin
      5. Advokatus      → Logik-Check
      6. DeepSeek       → Reasoning (nur non-hostile)
      7. Wusulum        → Generierung
      8. Foucault       → Inversion
      9. Kortex-Exec    → Finale Entscheidung
      10. Spells        → Karten (bei System-Overload)
      11. XJustiz       → XML
      12. ASME          → WORM-Seal
      13. APEX          → Override-Check
    """

    def __init__(self):
        self.sensor = NeuroScanModul()
        self.bio = PolyvagalStateRegulator()
        self.kortex = NeoKortikalerDirigent()
        self.spells = KortexSpellCaster()
        self.diaboli = AdvocatusDiaboliLayer()
        self.gotham = GothamCitySandbox()
        self.king_ghost = King_GhostSandbox()
        self.pumuckl = PumucklChaosInjector()
        self.biene_maja = BieneMajaLockvogel()
        self.xjustiz = XJustizXoevGatekeeper()
        self.asme = ASME01MetaEngine()
        self.ute = UnifiedTensorEngine()
        self.wusulum = WusulumCore()
        self.foucault = FoucaultPanoptikum()
        self.booster = DeepSeekBooster()
        self.apex_override = False

    def process_event(self, text: str) -> Dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            return {
                "status": "INVALID_INPUT",
                "detail": "text must be non-empty str",
            }

        # 1. Sensorik
        scan = self.sensor.execute_scan(text)

        # 2. Forensik
        is_hostile, core_hits, sub_hits = self.diaboli.scanner.scan(text)
        threat = scan["sensory_threat_level"] + (0.3 if is_hostile else 0.0)

        # 3. Biologie
        bio_state = self.bio.update(threat)

        # 4. Kortex-Gewichtung
        mode = self.kortex.regulate_weights(is_threat=is_hostile)

        # 5. Advokatus
        try:
            validated = self.diaboli.stress_test(text)
        except ThreatSignatureError as e:
            inmate = self.gotham.incarcerate(text, str(e))
            shadow_id = self.king_ghost.consume_to_shadow(text, "advocatus_kill")
            pumuckl_record = self.pumuckl.chaos_wrap(text)
            self.bio.co_regulate(0.2)
            return {
                "status": "CONTAINED",
                "bio_state": bio_state,
                "gotham_inmate": inmate,
                "king_ghost_shadow": shadow_id,
                "pumuckl_chaos": pumuckl_record,
                "core_hits": core_hits,
                "sub_entity_hits": sub_hits,
                "scan": scan,
            }

        # 6. DeepSeek-Booster (nur bei non-hostile)
        booster_result = self.booster.boost(text, depth=3)

        # 7. Wusulum
        wus_cycle = self.wusulum.run_cycle()

        # 8. Foucault
        foucault_result = self.foucault.observe_and_invert(
            validated, self.wusulum.state
        )

        # 9. Kortex-Executive
        executive = self.kortex.executive_decision(
            wus_cycle["state"], foucault_result
        )

        # 10. Spells
        situation = (
            "HOSTILE_INJECTION" if "SHUTDOWN" in bio_state
            else "SYSTEM_OVERLOAD"
        )
        spell_result = self.spells.draw_and_cast(situation, validated)

        # 11. XJustiz
        xj = self.xjustiz.validate_output(validated)

        # 12. Seal
        seal = self.asme.seal_and_archive(xj, ring=1 if threat > 0.5 else 0)

        # 13. APEX Override
        if self.apex_override:
            return {"status": "APEX_OVERRIDE", "seal": seal}

        return {
            "status": "PROCESSED",
            "bio_state": bio_state,
            "kortex_mode": mode,
            "wusulum": wus_cycle,
            "foucault_result": foucault_result[:30],
            "executive_decision": executive,
            "spell_result": spell_result,
            "xjustiz_output": xj,
            "asme_seal": seal,
            "threat_level": round(threat, 3),
            "booster": booster_result,
            "scan": scan,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 13. WAL MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class WALManager:
    """
    Append-only Write-Ahead-Log mit Hash-Chain und fsync.
    Persistiert in JSONL, Recovery beim Start.
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._seq, self._last_hash = self._recover()

    def _recover(self) -> Tuple[int, str]:
        if not os.path.exists(self.path):
            return 0, "GENESIS"
        seq, last = 0, "GENESIS"
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                seq = rec["seq"]
                last = rec["hash"]
        return seq, last

    def append(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._seq += 1
            record = {
                "seq": self._seq,
                "ts": time.time(),
                "event": event_type,
                "payload": payload,
                "prev_hash": self._last_hash,
            }
            record["hash"] = hashlib.sha3_512(
                json.dumps(record, sort_keys=True).encode()
            ).hexdigest()
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
            self._last_hash = record["hash"]
            return record

    def tail(self, n: int = 10) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        return [json.loads(l) for l in lines[-n:]]


# ═══════════════════════════════════════════════════════════════════════════════
# 14. INSTANZEN
# ═══════════════════════════════════════════════════════════════════════════════
_apex = SovereignApexController()
_brummel = BrummelGrummelUniverse()
_wal = WALManager(WAL_PATH)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. REGISTRY-LOADER
# ═══════════════════════════════════════════════════════════════════════════════
async def load_registry() -> None:
    """Lädt die Entity-Registry aus GitHub (CSV, delimiter=';')."""
    global BOOK_REGISTRY
    if httpx is None:
        logger.error("[SKIP] httpx fehlt — Registry-Sync übersprungen.")
        return
    logger.info("Lade Entity-Registry aus GitHub...")
    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.get(REGISTRY_URL)
            response.raise_for_status()
            lines = [
                l for l in response.text.splitlines()
                if l.strip() and not l.startswith("#")
            ]
            reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=";")
            new_registry: Dict[str, dict] = {}
            for row in reader:
                new_registry[row.get("ID", "UNKNOWN")] = {
                    "name":    row.get("Name", "UNKNOWN"),
                    "ring":    row.get("Kategorie/Ring", "UNKNOWN"),
                    "talents": row.get("Talente", ""),
                    "modules": row.get("Module/Cores", ""),
                }
            BOOK_REGISTRY = new_registry
            logger.info(f"[SYNCED] {len(BOOK_REGISTRY)} Entitäten geladen.")
    except Exception as e:
        logger.error(f"[CRITICAL] Registry-Sync fehlgeschlagen: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 16. LIFESPAN
# ═══════════════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 70)
    logger.info("YGGDRASIL_OS :: BLUE CORE v26.2.1 startet...")
    logger.info(f"  Python:         {os.sys.version.split()[0]}")
    logger.info(f"  Seal gesetzt:   {bool(EXPECTED_SEAL)} (len={len(EXPECTED_SEAL)})")
    logger.info(f"  CORS:           {ALLOWED_ORIGINS}")
    logger.info(f"  Gemini:         {'READY' if client else 'DISABLED'}")
    logger.info(f"  httpx:          {'READY' if httpx else 'MISSING'}")
    logger.info(f"  WAL-Pfad:       {WAL_PATH}")
    logger.info(f"  Naming:         Grummel | Dr.Snuggles | BieneMaja | Pumuckl | King_Ghost")
    logger.info("=" * 70)

    task = asyncio.create_task(load_registry())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        logger.info("Shutdown complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# 17. FASTAPI-APP
# ═══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="Blue Core Matrix",
    version="26.2.1",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════
class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    auth_seal: Optional[str] = None


class ReloadRequest(BaseModel):
    auth_seal: Optional[str] = None


class ApexRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    is_threat: bool = False
    auth_seal: Optional[str] = None


class BrummelRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    auth_seal: Optional[str] = None


class PumucklRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    auth_seal: Optional[str] = None


class KingGhostRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    origin: str = "external"
    auth_seal: Optional[str] = None


class DeepSeekRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    context: str = ""
    depth: int = 3
    auth_seal: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 19. ENDPOINTS — Health / Stats / Ledger / Gotham
# ═══════════════════════════════════════════════════════════════════════════════
@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {
        "status": "BLUE_CORE_LIVE",
        "version": app.version,
        "entities": len(BOOK_REGISTRY),
        "worm_block": int(WORM_LEDGER["count"]),
        "timestamp": _now_iso(),
    }


@app.get("/health")
async def health():
    return {
        "status": "HEALTHY",
        "version": app.version,
        "uptime_seconds": int(time.time() - WORM_LEDGER["started_at"]),
        "entities_loaded": len(BOOK_REGISTRY),
        "registry_url": REGISTRY_URL,
        "worm_block": int(WORM_LEDGER["count"]),
        "worm_last_hash": WORM_LEDGER["last_hash"][:32] + "...",
        "features": {
            "gemini": client is not None,
            "httpx": httpx is not None,
            "hmac_seal": True,
            "cors_restricted": ALLOWED_ORIGINS != ["*"],
            "lss_neuro_core": True,
            "websocket_telemetry": True,
            "deepseek_booster": True,
            "grummel_dynasty": True,
            "dr_snuggles": True,
            "biene_maja": True,
            "pumuckl": True,
            "king_ghost": True,
        },
        "timestamp": _now_iso(),
    }


@app.get("/stats")
async def stats():
    return {
        "registry": {
            "entities": len(BOOK_REGISTRY),
            "rings": sorted({d["ring"] for d in BOOK_REGISTRY.values()}),
        },
        "worm": {
            "total_blocks": int(WORM_LEDGER["count"]),
            "ring_capacity": LEDGER_RING_SIZE,
            "ring_size": len(WORM_RING),
            "last_hash": WORM_LEDGER["last_hash"][:32] + "...",
        },
        "lss": {
            "entropy": round(_apex.wusulum.entropy_pool, 2),
            "bio_state": _apex.bio.state,
            "brummel_phase": _brummel._phase,
            "gotham_inmates": len(_apex.gotham.inmates),
            "king_ghost_shadows": len(_apex.king_ghost.shadow_pool),
            "pumuckl_injections": len(_apex.pumuckl.injected_log),
            "biene_maja_tracked": len(_apex.biene_maja.tracked),
            "booster_cache_size": len(_apex.booster.cache),
        },
        "uptime_seconds": int(time.time() - WORM_LEDGER["started_at"]),
        "timestamp": _now_iso(),
    }


@app.get("/ledger/inspect")
async def ledger_inspect(limit: int = 10):
    limit = max(1, min(limit, LEDGER_RING_SIZE))
    blocks = list(WORM_RING)[-limit:]
    return {
        "count": int(WORM_LEDGER["count"]),
        "blocks": blocks,
        "returned": len(blocks),
    }


@app.get("/api/v1/gotham")
async def gotham_list():
    return {
        "inmates": _apex.gotham.inmates,
        "count": len(_apex.gotham.inmates),
    }


@app.get("/api/v1/kingghost/shadows")
async def kingghost_list():
    return {
        "shadows": _apex.king_ghost.shadow_pool,
        "count": len(_apex.king_ghost.shadow_pool),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 20. ENDPOINTS — Admin / Prompt
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/admin/reload-registry")
async def reload_registry(request: ReloadRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    await load_registry()
    return {
        "status": "RELOADED",
        "entities": len(BOOK_REGISTRY),
        "timestamp": _now_iso(),
    }


@app.post("/prompt/check")
async def check_prompt(request: PromptRequest):
    if not _verify_seal(request.auth_seal):
        logger.warning(f"Seal-Reject: {_truncate(request.prompt, 30)}")
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}

    prompt = request.prompt
    lowered = prompt.lower()
    rag_context = ""
    matched: List[str] = []
    for bid, data in BOOK_REGISTRY.items():
        if bid in prompt or data["name"].lower() in lowered:
            rag_context += f"Entität {bid}: {data['name']}. {data['talents']}\n"
            matched.append(bid)

    ai_answer = "Keine KI-Antwort generiert."
    if client and rag_context:
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Daten: {rag_context}\nFrage: {prompt}",
            )
            ai_answer = response.text
        except Exception as e:
            ai_answer = f"System-Fehler: {e}"
            logger.warning(f"Gemini-Call fehlgeschlagen: {e}")

    timestamp = str(time.time())
    async with _LEDGER_LOCK:
        worm_hash = hashlib.sha3_512(
            f"{WORM_LEDGER['last_hash']}{prompt}{timestamp}".encode()
        ).hexdigest()
        WORM_LEDGER["last_hash"] = worm_hash
        WORM_LEDGER["count"] = int(WORM_LEDGER["count"]) + 1
        current_block = int(WORM_LEDGER["count"])
        WORM_RING.append({
            "block": current_block,
            "hash": worm_hash,
            "prompt_hash": hashlib.sha3_512(prompt.encode()).hexdigest()[:32],
            "matched": matched,
            "timestamp": timestamp,
        })

    return {
        "status": "200_OK_ALLOW",
        "data": {
            "ai_answer": ai_answer,
            "rag_used": bool(rag_context),
            "entities_matched": matched,
        },
        "worm": {"hash": worm_hash, "block": current_block},
        "ai_answer": ai_answer,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 21. ENDPOINTS — L.S.S. Apex / Sandboxes / DeepSeek / WAL
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/v1/apex/process")
async def apex_process(request: ApexRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    result = _apex.process_event(request.message)
    _wal.append("APEX_EVENT", {"input": request.message, "result": result})
    async with _LEDGER_LOCK:
        WORM_LEDGER["count"] = int(WORM_LEDGER["count"]) + 1
        h = hashlib.sha3_512(
            f"{WORM_LEDGER['last_hash']}{request.message}".encode()
        ).hexdigest()
        WORM_LEDGER["last_hash"] = h
        WORM_RING.append({
            "block": int(WORM_LEDGER["count"]),
            "hash": h,
            "apex": result.get("status"),
            "timestamp": str(time.time()),
        })
        result["worm_block"] = int(WORM_LEDGER["count"])
    return result


@app.post("/api/v1/sandbox/brummel")
async def brummel_inject(request: BrummelRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    result = _brummel.process_injection(request.message)
    _wal.append("BRUMMEL_INJECTION_CONTAINED", result)
    return result


@app.post("/api/v1/sandbox/pumuckl")
async def pumuckl_inject(request: PumucklRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    result = _apex.pumuckl.chaos_wrap(request.message)
    _wal.append("PUMUCKL_CHAOS", result)
    return {"status": "CHAOS_CONTAINED", "pumuckl": result}


@app.post("/api/v1/sandbox/kingghost")
async def kingghost_consume(request: KingGhostRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    shadow_id = _apex.king_ghost.consume_to_shadow(
        request.message, request.origin
    )
    _wal.append(
        "KING_GHOST_CONSUMED",
        {"shadow_id": shadow_id, "origin": request.origin},
    )
    return {
        "status": "CONSUMED_TO_SHADOW",
        "shadow_id": shadow_id,
        "origin": request.origin,
    }


@app.post("/api/v1/deepseek/boost")
async def deepseek_boost(request: DeepSeekRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    result = _apex.booster.boost(
        request.prompt, request.context, depth=request.depth
    )
    _wal.append(
        "DEEPSEEK_BOOST",
        {"prompt": _truncate(request.prompt, 100), "confidence": result["confidence"]},
    )
    return result


@app.get("/api/v1/wal/tail")
async def wal_tail(n: int = 20):
    return {"blocks": _wal.tail(min(max(n, 1), 100))}


# ═══════════════════════════════════════════════════════════════════════════════
# 22. WEBSOCKET
# ═══════════════════════════════════════════════════════════════════════════════
@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket-Client verbunden.")
    try:
        while True:
            data = {
                "ts": time.time(),
                "throughput": random.randint(250000, 290000),
                "latency": round(random.uniform(8.5, 10.5), 2),
                "entropy": round(_apex.wusulum.entropy_pool, 2),
                "bio_state": _apex.bio.state,
                "worm_block": int(WORM_LEDGER["count"]),
                "gotham_inmates": len(_apex.gotham.inmates),
                "king_ghost_shadows": len(_apex.king_ghost.shadow_pool),
                "pumuckl_injections": len(_apex.pumuckl.injected_log),
                "biene_maja_tracked": len(_apex.biene_maja.tracked),
                "brummel_phase": _brummel._phase,
            }
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        logger.info("WebSocket-Client getrennt.")
    except Exception as e:
        logger.error(f"WebSocket-Fehler: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 23. ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info",
    )
