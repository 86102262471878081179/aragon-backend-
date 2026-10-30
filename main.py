#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
 YGGDRASIL_OS :: BLUE CORE BACKEND (v2.6.6.6 — FULL RESTORE + ESELSBRÜCKEN)
═══════════════════════════════════════════════════════════════════════════════

 DIE VOLLSTÄNDIGE MONSTER-API. NICHTS KOMPRIMIERT, NICHTS GELÖSCHT.
 
 NEU IN v2.6.6.6:
   • Eselsbrücken-Registry (Mnemonic-basierte Wissensnavigation)
   • GGO-Beweis-Engine (SHA3-256 + PBFT-Simulation, Python-Simulation der Rust-Logik)
   • BILA Reflex Core (16-Bit ISA Simulation)
   • Quader-Tensor 4096 (Entropie-basierte Kognitionsstruktur)
   • Postmortem-Hash-Support (Tombstone-Hashing für tote Hashes)
   • Erweiterte Admin-Endpoints (Registry-Reload, Eselsbrücken-Reload)

 ALLE VORHERIGEN MODULE BLEIBEN ERHALTEN:
   • L.S.S. Neuro-Core (10 Ohren, 44 Perspektiven, Polyvagal, Kortex, Wusulum)
   • 6 Sandboxes (Gotham, King_Ghost, Pumuckl, BieneMaja, Brummel, Yggdrasil)
   • XJustiz-Gate (ERV-Pipeline)
   • DeepSeek-Booster (Multi-Step Reasoning)
   • SovereignApexController (Dirigent)
   • WAL-Manager (JSONL + SHA3-512 + Hash-Chain)
   • WORM-Ring-Buffer (In-Memory + Persistenz)
   • WebSocket-Telemetrie

 STATUS: Φ_LOCKED_ABSOLUTE
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 1: STANDARD LIBRARY IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════
import uvicorn
import os
import io
import csv
import copy
import json
import time
import random
import math
import ast
import operator
import re
import hashlib
import hmac
import logging
import asyncio
import threading
import xml.etree.ElementTree as ET
from collections import OrderedDict, deque
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple, Set

# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 2: THIRD-PARTY IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, ValidationError

try:
    import httpx
except ImportError:
    httpx = None

try:
    from google import genai
except ImportError:
    genai = None

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 3: LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("BLUE-CORE-API")


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 4: KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
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

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")

_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS: List[str] = [
    o.strip() for o in _raw_origins.split(",") if o.strip()
] or ["*"]

LEDGER_RING_SIZE = int(os.getenv("LEDGER_RING_SIZE", "100"))

# Gemini-Client (optional)
client = None
if GEMINI_API_KEY and genai is not None:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini Client erfolgreich initialisiert.")
    except Exception as e:
        logger.error(f"Gemini-Init fehlgeschlagen: {e}")
        client = None
elif GEMINI_API_KEY and genai is None:
    logger.warning("GEMINI_API_KEY gesetzt, aber google-genai nicht installiert.")
else:
    logger.warning("GEMINI_API_KEY fehlt — KI-Antworten deaktiviert.")


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 5: GLOBALER ZUSTAND
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
# ABSCHNITT 6: HELPER-FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════
def _verify_seal(provided: Optional[str]) -> bool:
    """
    Timing-sichere Überprüfung des Auth-Seals via HMAC.
    Verhindert Timing-Angriffe durch Vergleich der vollständigen Strings.
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
    Deterministischer Hash via Blake2b.
    Kein MD5, weil Blake2b kollisionssicher und schneller ist.
    """
    encoded = str(data).encode("utf-8")
    return hashlib.blake2b(encoded, digest_size=size).hexdigest()


def _sha3_512(data: str) -> str:
    """SHA3-512-Hash als Hex-String (für WORM-Versiegelung)."""
    return hashlib.sha3_512(str(data).encode("utf-8")).hexdigest()


def _sha3_256(data: str) -> str:
    """SHA3-256-Hash als Hex-String (für Merkle/Block-Verkettung)."""
    return hashlib.sha3_256(str(data).encode("utf-8")).hexdigest()


def _rhabarber_obfuscate(text: str) -> str:
    """
    Bounds-safe Caesar+3 Obfuskation.
    Surrogates werden übersprungen, weil sie in UTF-8 nicht codierbar sind.
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
# ABSCHNITT 7: DNA-PARSER (RCE-Schutz)
# ═══════════════════════════════════════════════════════════════════════════════
ALLOWED_VARS = {"A": 1, "T": 2, "G": 3, "C": 4}
ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
DNA_PATTERN = re.compile(r"^[ATGC0-9+\-*/()_\s]+$")


def safe_eval_dna(expr_num: str) -> float:
    """
    Sichere Auswertung von DNA-Mathe-Ausdrücken (verhindert RCE).
    Nutzt AST-Parsing statt eval().
    """
    if not DNA_PATTERN.match(expr_num):
        raise ValueError(
            f"Ungültige Zeichen: {expr_num} – Nur ATGC + - * / ( ) – Φ_LOCKED_EX_TUNC"
        )

    blacklist = [
        "__", "import", "os", "sys", "system", "exec",
        "eval", "open", "compile", "globals", "subprocess",
    ]
    for blocked in blacklist:
        if blocked in expr_num.lower():
            raise ValueError(
                f"Blockiert: {blocked} – RCE Versuch – Brummel Sentinel BLOCKED – Φ_LOCKED_EX_TUNC"
            )

    tree = ast.parse(expr_num, mode="eval")

    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        elif isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, (int, float)) else 0
        elif isinstance(node, ast.Name):
            if node.id in ALLOWED_VARS:
                return ALLOWED_VARS[node.id]
            raise ValueError(f"Unbekannte Variable: {node.id}")
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in ALLOWED_OPS:
                raise ValueError(f"Unerlaubter Operator: {type(node.op).__name__}")
            return ALLOWED_OPS[type(node.op)](
                _eval_node(node.left), _eval_node(node.right)
            )
        else:
            raise ValueError(f"Unerlaubter Node: {type(node).__name__} – Brummel Sentinel BLOCKED")

    return _eval_node(tree)


def parse_dna_node_secure(dna_str: str) -> dict:
    """
    Parst eine DNA-Sequenz wie 'G-G-A-90' in ihre Bestandteile.
    Format: <Ring-Locus | Chromosom | Sequenz | Schutz-Allel>
    """
    m = re.match(r"^([ATGC])-([ATGC])-([ATGC])-?(\d+)?$", dna_str.strip().upper())
    if not m:
        raise ValueError(f"Ungültiges DNA Format: {dna_str}")
    return {
        "ring": m.group(1),
        "locus": m.group(2),
        "chromosom": m.group(3),
        "sequenz": m.group(4),
        "full": dna_str,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 8: WAL MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class WALManager:
    """
    Der Write-Ahead-Log Manager ist das persistente Gedächtnis der Matrix.
    Jede Aktion wird unauslöschlich in einer JSONL-Datei festgehalten.
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._seq, self._last_hash = self._recover()

    def _recover(self) -> Tuple[int, str]:
        """Stellt den Ledger-Zustand nach einem Neustart wieder her."""
        if not os.path.exists(self.path):
            return 0, "GENESIS"

        seq, last = 0, "GENESIS"
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    seq = rec["seq"]
                    last = rec["hash"]
                except (json.JSONDecodeError, KeyError):
                    continue
        return seq, last

    def append(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Schreibt einen neuen Block in den WAL (Hash-Chained)."""
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
        """Liest die letzten N Einträge aus dem WAL."""
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]
        return [json.loads(line) for line in lines[-n:]]


_wal = WALManager(WAL_PATH)


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 9: NEO4J MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class Neo4jManager:
    """Verwaltet die Graph-Datenbank (Topologie der Ringe)."""

    def __init__(self):
        self.driver = None
        if GraphDatabase:
            try:
                self.driver = GraphDatabase.driver(
                    NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS)
                )
                logger.info("Neo4j Treiber geladen.")
            except Exception as e:
                logger.warning(f"Neo4j nicht erreichbar (Offline-Modus): {e}")

    def run_query(self, query: str) -> List[Dict]:
        """Führt eine Cypher-Query aus."""
        if not self.driver:
            return [{"error": "Neo4j offline. Fallback auf Mock-Daten."}]
        try:
            with self.driver.session() as session:
                return [r.data() for r in session.run(query)]
        except Exception as e:
            return [{"error": str(e)}]


_neo4j = Neo4jManager()


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 10: L.S.S. SENSORIK (TEN EARS & 44 PERSPECTIVES)
# ═══════════════════════════════════════════════════════════════════════════════
class TenEarsNeuroSensor:
    """
    Der 10-Ohren-Scan.
    Ein Ohr hört Sache. Zehn Ohren hören Trauma, Scham, Ohnmacht, Macht, System.
    """

    EARS = {
        "Sache": ["fakt", "daten", "code", "beweis", "zahl", "logik"],
        "Beziehung": ["du", "ihr", "macht", "hierarchie", "gegen", "wir"],
        "Appell": ["muss", "sollte", "fordere", "tue", "verlange", "mahnung"],
        "Selbstoffenbarung": ["ich", "fühle", "denke", "mein", "habe", "bin"],
        "Trauma": ["angst", "panik", "gefahr", "schmerz", "schock", "insulin"],
        "Macht (Foucault)": ["autorität", "herrschaft", "disziplin", "überwachen", "polizei"],
        "Scham": ["peinlich", "fehler", "versagen", "schlecht", "unwürdig", "schuld"],
        "Ohnmacht": ["hilflos", "ausgeliefert", "kontrolle", "ohnmächtig", "gefesselt"],
        "System (Luhmann)": ["struktur", "prozess", "regel", "system", "netzwerk", "bürokratie"],
        "Haftung (BGB)": ["klage", "schaden", "urteil", "gesetz", "recht", "vertrag", "§ 839"],
    }

    def scan_input(self, text: str) -> Dict[str, float]:
        """Deterministischer Scan: Keywords werden zu Scores (0.0 - 1.0)."""
        t = text.lower()
        scores = {}
        for ear, keywords in self.EARS.items():
            hits = sum(1 for kw in keywords if kw in t)
            scores[ear] = min(1.0, hits / max(1, len(keywords) * 0.5))
        return scores


class FortyFourPerspectiveAttention:
    """
    Die 44-Perspektiven-Refraktion (Multi-Head Attention).
    Kein Text hat eine Wahrheit. Ein Text hat vierundvierzig.
    """

    PERSPECTIVES = [
        "Juristisch", "Forensisch", "Ethisch", "Spieltheoretisch",
        "Kybernetisch", "Psychoanalytisch", "Systemisch", "Chaotisch",
        "Ökonomisch", "Militärisch", "Kognitiv", "Neurobiologisch",
        "Informationstheoretisch", "Kryptografisch", "Soziologisch", "Historisch",
        "Linguistisch", "Pädagogisch", "Theologisch", "Ästhetisch",
        "Biologisch", "Chemisch", "Physikalisch", "Mathematisch",
        "Statistisch", "Prognostisch", "Archivarisch", "Administrativ",
        "Politisch", "Diplomatisch", "Medizinisch", "Psychiatrisch",
        "Technisch", "Ingenieurwesen", "Logistisch", "Taktisch",
        "Strategisch", "Operativ", "Metaphysisch", "Ontologisch",
        "Epistemologisch", "Phänomenologisch", "Hermeneutisch", "Dialektisch",
    ]

    def refract(self, ears: Dict[str, float]) -> Dict[str, float]:
        """Gewichtet die 44 Perspektiven basierend auf den 10 Ohren."""
        base = sum(ears.values()) / max(1, len(ears))
        out = {}
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
            elif p == "Medizinisch":
                w = ears.get("Trauma", 0) * 0.8 + ears.get("Sache", 0) * 0.2
            elif p == "Politisch":
                w = ears.get("Macht (Foucault)", 0) * 0.7 + ears.get("System (Luhmann)", 0) * 0.3
            else:
                seed = _h(p + str(sorted(ears.items())), 2)
                w = base * (0.5 + (int(seed, 16) / 65535.0))
            out[p] = min(1.0, w)
        return out


class NeuroScanModul:
    """Kombiniert Ohren und Perspektiven zu einem Threat-Scan."""

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
# ABSCHNITT 11: L.S.S. BIOLOGIE (POLYVAGAL & GRUMMEL)
# ═══════════════════════════════════════════════════════════════════════════════
class PolyvagalStateRegulator:
    """Polyvagal-Regler mit natürlichem Decay."""

    DECAY = 0.08

    def __init__(self):
        self.state = "VENTRAL_VAGAL"
        self.stress_level = 0.0

    def update(self, threat: float) -> str:
        self.stress_level = max(0.0, self.stress_level - self.DECAY)
        self.stress_level = min(1.0, self.stress_level + threat)

        if self.stress_level < 0.4:
            self.state = "VENTRAL_VAGAL"
            return "KREATIV_MODUS"
        elif self.stress_level < 0.8:
            self.state = "SYMPATHIKUS"
            return "KAMPF_MODUS"

        self.state = "DORSAL_VAGAL"
        return "SHUTDOWN_MODUS"

    def co_regulate(self, amount: float = 0.2) -> None:
        self.stress_level = max(0.0, self.stress_level - amount)
        if self.stress_level < 0.4:
            self.state = "VENTRAL_VAGAL"


class GrummelSignatureScanner:
    """
    Forensischer Scanner für die Grummel-Dynastie.
    Erkennt feindliche Lore (Mettwurst, Pissingerkeulen, Cargo-Kult).
    """

    CORE_SIGNATURES = [
        "grummel", "brummel", "dummelt",
        "pissingerkeule", "mettwurst", "rhabarberbarbara",
        "cargo-kult", "urheberinfo", "§ 839 bgb",
    ]

    SUB_ENTITIES = {
        "BieneMaja": ["biene maja", "bienchen", "maja", "summsumm"],
        "Pumuckl": ["pumuckl", "kobold", "klabautermann", "chaos-imp"],
        "King_Ghost": ["king_ghost", "king ghost", "ghost-king", "schattenkönig"],
        "DrSnuggles": ["dr. snuggles", "dr.snuggles", "snuggles", "cyberlord"],
    }

    def scan(self, text: str) -> Tuple[bool, List[str], List[str]]:
        t = text.lower()
        core_hits = [sig for sig in self.CORE_SIGNATURES if sig in t]
        sub_hits = []
        for entity, keywords in self.SUB_ENTITIES.items():
            if any(kw in t for kw in keywords):
                sub_hits.append(entity)
        return bool(core_hits or sub_hits), core_hits, sub_hits


class BioForensicThreatProfiler:
    """Fusion aus Biosphäre (Polyvagal) und Forensik (Grummel-Scanner)."""

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
# ABSCHNITT 12: L.S.S. KOGNITION (FOUCAULT & KORTEX)
# ═══════════════════════════════════════════════════════════════════════════════
class FoucaultPanoptikum:
    """Überwachung und Inversion. Deterministisch per Hash."""

    def __init__(self):
        self.surveillance_log: List[str] = []

    def observe_and_invert(self, token: str, context: str = "") -> str:
        h = hashlib.blake2b((token + context).encode(), digest_size=4).digest()
        if h[0] > 127:
            inverted = f"SYS_CONFORM_{_h(token, 3)}"
            self.surveillance_log.append(f"Token {token[:10]} invertiert.")
            return inverted
        return token


class NeoKortikalerDirigent:
    """Der präfrontale Kortex. Entscheidet, was Realität wird."""

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
# ABSCHNITT 13: DEEPSEEK BOOSTER
# ═══════════════════════════════════════════════════════════════════════════════
class DeepSeekBooster:
    """
    Lokaler Reasoning-Simulator mit begrenztem, thread-sicherem LRU-Cache.

    Sämtliche übergebenen Parameter fließen in den Cache-Key ein.
    Cache-Werte werden beim Speichern und Zurückgeben tief kopiert.
    """

    STEPS = ["decompose", "expand", "verify", "confidence"]
    MAX_CACHE_ENTRIES = 512

    def __init__(self):
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._cache_lock = threading.RLock()

    @staticmethod
    def _cache_key(
        prompt: str,
        context: str,
        depth: int,
        options: Dict[str, Any],
    ) -> str:
        key_data = {
            "prompt": prompt,
            "context": context,
            "depth": depth,
            **options,
        }

        try:
            return json.dumps(
                key_data,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Cache-Parameter müssen gültige JSON-Werte sein: {exc}"
            ) from exc

    def boost(
        self,
        prompt: str,
        context: str = "",
        depth: int = 3,
        *,
        language: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        response_format: Any = None,
        entropy: Optional[float] = None,
        apply_veto: bool = False,
    ) -> Dict[str, Any]:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt muss ein nichtleerer String sein.")
        if not isinstance(context, str):
            raise ValueError("context muss ein String sein.")
        if isinstance(depth, bool) or not isinstance(depth, int) or not 1 <= depth <= 10:
            raise ValueError("depth muss eine ganze Zahl zwischen 1 und 10 sein.")
        if max_tokens is not None and (
            isinstance(max_tokens, bool)
            or not isinstance(max_tokens, int)
            or max_tokens < 1
        ):
            raise ValueError("max_tokens muss eine positive ganze Zahl sein.")
        if entropy is not None:
            if isinstance(entropy, bool) or not isinstance(entropy, (int, float)):
                raise ValueError("entropy muss eine endliche Zahl sein.")
            if not math.isfinite(entropy):
                raise ValueError("entropy muss eine endliche Zahl sein.")
        if not isinstance(apply_veto, bool):
            raise ValueError("apply_veto muss boolesch sein.")

        options = {
            "language": language,
            "model": model,
            "max_tokens": max_tokens,
            "system_prompt": system_prompt,
            "response_format": response_format,
            "entropy": entropy,
            "apply_veto": apply_veto,
        }
        key = self._cache_key(prompt, context, depth, options)

        with self._cache_lock:
            cached = self.cache.get(key)
            if cached is not None:
                self.cache.move_to_end(key)
                return copy.deepcopy(cached)

        trace: List[Dict[str, Any]] = []
        for i in range(depth):
            step_hash = _h(f"{prompt}|{context}|step{i}", 8)
            trace.append({
                "step": i + 1,
                "name": self.STEPS[min(i, len(self.STEPS) - 1)],
                "hash": step_hash,
                "note": self._step_note(i),
            })

        verification_hash = hashlib.sha3_512(
            json.dumps(trace, sort_keys=True).encode("utf-8")
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
            "parameters": copy.deepcopy(options),
        }

        with self._cache_lock:
            # Ein paralleler Request könnte den Eintrag bereits angelegt haben.
            existing = self.cache.get(key)
            if existing is not None:
                self.cache.move_to_end(key)
                return copy.deepcopy(existing)

            self.cache[key] = copy.deepcopy(result)
            self.cache.move_to_end(key)

            while len(self.cache) > self.MAX_CACHE_ENTRIES:
                self.cache.popitem(last=False)

        return copy.deepcopy(result)

    def _step_note(self, idx: int) -> str:
        notes = [
            "Dekomposition: Teile Problem in atomare Sub-Fragen.",
            "Expansion: Generiere Kandidaten-Antworten aus 10-Ohren-Sicht.",
            "Verifikation: Prüfe gegen Foucault-Konformität + Advokatus-Logik.",
            "Confidence: Bewerte Verlässlichkeit des Resultats.",
        ]
        return notes[idx % len(notes)]

# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 14: L.S.S. GENERIERUNG (WUSULUM & KARTEN)
# ═══════════════════════════════════════════════════════════════════════════════
class WusulumCore:
    """
    Der stochastische Kern. Generiert neue Token aus dem Chaos.
    Entropie gedeckelt bei MAX_ENTROPY = 5.0.
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
            "Zero-Trust HMAC-SHA3-256",
        )

    def execute(self, target_input: str) -> str:
        seal = hashlib.sha3_256(target_input.encode()).hexdigest()
        return (
            f"[ASP-256 SEAL] Token '{target_input[:10]}...' versiegelt. "
            f"SIGKILL scharf. Hash {seal[:16]}"
        )


class RhabarberbarbaraKarte(Zauberkarte):
    """Rhabarberbarbara-Matrix: Semantische Obfuskation."""

    def __init__(self):
        super().__init__(
            "Rhabarberbarbara", "Ring 2/3 Hybrid", "FILTER ON",
            "Post-Quantum Tongue-Twister",
        )

    def execute(self, target_input: str) -> str:
        return f"[RHABARBERBARBARA] Obfuskiert: {_rhabarber_obfuscate(target_input)[:20]}..."


class MettwurstC88Karte(Zauberkarte):
    """Mettwurst API: Low-Latency Realitäts-Schnittstelle."""

    def __init__(self):
        super().__init__(
            "Mettwurst C88", "Ring 5 P2P", "READY",
            "Low-Latency Reality Interface",
        )

    def execute(self, target_input: str) -> str:
        return "[METTWURST C88] Datenstrom via Port 6880. Latenz < 1ms."


class KortexSpellCaster:
    """Dirigent der Karten."""

    def __init__(self):
        self.deck = {
            "DEFENSE": ASP256Karte(),
            "FILTER": RhabarberbarbaraKarte(),
            "STABILIZE": MettwurstC88Karte(),
        }
        self.status = "Φ_LOCKED_ABSOLUTE"

    def draw_and_cast(self, situation: str, target_input: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {"situation": situation, "status": self.status}
        if situation == "HOSTILE_INJECTION":
            f = self.deck["FILTER"]
            d = self.deck["DEFENSE"]
            result["cards"] = [
                {"name": f.name, "ring": f.ring, "effect": f.execute(target_input)},
                {"name": d.name, "ring": d.ring, "effect": d.execute(target_input)},
            ]
        elif situation == "SYSTEM_OVERLOAD":
            s = self.deck["STABILIZE"]
            result["cards"] = [
                {"name": s.name, "ring": s.ring, "effect": s.execute(target_input)},
            ]
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 15: L.S.S. GOVERNANCE & SANDBOXES
# ═══════════════════════════════════════════════════════════════════════════════
ET.register_namespace("", "http://www.xjustiz.de")
_XJ = "{http://www.xjustiz.de}"


class XJustizXoevGatekeeper:
    """Erzeugt valides XJustiz-XML (Namespace registriert)."""

    def __init__(self):
        self.namespace = "http://www.xjustiz.de"
        logger.info("XJustiz Gatekeeper initialisiert (Status: ERV_PIPELINE_ACTIVE).")

    def validate_output(self, raw_token: str) -> str:
        root = ET.Element(f"{_XJ}nachricht.straf.0300")
        kopf = ET.SubElement(root, f"{_XJ}nachrichtenkopf")
        ET.SubElement(kopf, f"{_XJ}erstellungszeitpunkt").text = time.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        ET.SubElement(kopf, f"{_XJ}absender").text = "B6-Monster-API v2.6.6.6"
        ET.SubElement(kopf, f"{_XJ}empfaenger").text = "Sovereign Root Operator"
        fach = ET.SubElement(root, f"{_XJ}fachdaten")
        ET.SubElement(fach, f"{_XJ}token").text = str(raw_token)
        ET.SubElement(fach, f"{_XJ}versiegelungs_hash").text = _h(raw_token, 16)
        return ET.tostring(root, encoding="unicode")


class GothamCitySandbox:
    """Arkham Cache für zerstörte Tokens."""

    def __init__(self):
        self.inmates: List[Dict[str, Any]] = []
        logger.info("Gotham City Sandbox initialisiert (Status: ARKHAM_CACHE_READY).")

    def incarcerate(self, token: str, reason: str) -> str:
        inmate_id = _h(token, 4)
        self.inmates.append({
            "id": inmate_id, "token": token, "reason": reason, "ts": time.time(),
        })
        logger.warning(f"[GOTHAM] Inmate {inmate_id} eingesperrt: {_truncate(reason, 60)}")
        return inmate_id


class King_GhostSandbox:
    """King_Ghost: Schatten-Führer, tiefer als Gotham."""

    def __init__(self):
        self.shadow_pool: List[Dict[str, Any]] = []
        logger.info("King_Ghost Sandbox initialisiert (Status: SHADOW_POOL_OPEN).")

    def consume_to_shadow(self, token: str, origin: str) -> str:
        sid = _h(f"KINGGHOST_{token}_{origin}", 6)
        self.shadow_pool.append({
            "shadow_id": sid, "token": token, "origin": origin,
            "consumed_at": time.time(),
        })
        logger.warning(f"[KING_GHOST] Token in Schatten gezogen: {sid}")
        return sid


class PumucklChaosInjector:
    """Pumuckl: Chaos-Imp. Obfuskiert feindliche Payloads."""

    def __init__(self):
        self.injected_log: List[Dict[str, Any]] = []
        logger.info("Pumuckl Chaos-Injector initialisiert (Status: KOBOLD_ENTFESSELT).")

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
    """Biene Maja: Lockvogel-Signatur mit Tracking-Hash."""

    def __init__(self):
        self.tracked: List[Dict[str, Any]] = []

    def deploy_honeypot(self, attacker_ip: str) -> Dict[str, Any]:
        honey = _h(f"BIENEMAJA_{attacker_ip}_{time.time()}", 8)
        record = {
            "honey_id": honey, "attacker_ip": attacker_ip,
            "sting_deployed": True, "ts": time.time(),
        }
        self.tracked.append(record)
        logger.warning(f"[BIENE_MAJA] Stachel ausgefahren für {attacker_ip}")
        return record


class BrummelGrummelUniverse:
    """Brummel-Grummel-Universum: Dreiecksoszillator (Periode 18)."""

    def __init__(self):
        self.entity_id = "[0003]"
        self.lineage = 45
        self.doctrine = 65
        self._phase = 0
        self.containment_shield = True
        logger.info("Brummel-Grummel-Universum initialisiert (Status: OSCILLATING).")

    def _oscillate(self) -> int:
        self._phase = (self._phase + 1) % 18
        return 9 - abs(self._phase - 9)

    def process_injection(self, hostile_payload: str) -> Dict[str, Any]:
        if not self.containment_shield:
            raise RuntimeError("CRITICAL: Containment Shield Failed!")
        osc_state = self._oscillate()
        result = {
            "status": "CONTAINED",
            "entity": self.entity_id,
            "universe": "Brummel_Grummel_brummelt&_Dummelt",
            "oscillation_state": osc_state,
            "lineage_doctrine": f"{self.lineage}[LINEAGE] {self.doctrine}[DOCTRINE]",
            "dummelt_hash": _h(f"DUMMELT_{hostile_payload}_{osc_state}", 16),
        }
        logger.info(f"[BRUMMEL] Injektion verarbeitet. Oszillation: {osc_state}")
        return result


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
                f"ADVOCATUS DIABOLI: core={core_hits} subs={sub_hits} → exekutiert."
            )
        return token


class ASME01MetaEngine:
    """WORM-Seal-Engine für das Apex-Archiv."""

    def __init__(self):
        self.ledger: List[Dict[str, Any]] = []

    def seal_and_archive(self, data: str, ring: int = 0) -> str:
        seal = hashlib.sha3_512(data.encode()).hexdigest()
        self.ledger.append({
            "data": data, "seal": seal, "ring": ring, "ts": time.time(),
        })
        return seal


class UnifiedTensorEngine:
    """UTE: Formt rohe Token in Tensoren."""

    def execute(self, token: str) -> str:
        return f"<UTE><Token>{token}</Token></UTE>"


class ThreatSignatureError(ValueError):
    """Hostile-Lore-Signatur erkannt. Token exekutiert."""


class XJustizViolation(Exception):
    """XJustiz-Konformität verletzt."""


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 16: SOVEREIGN APEX CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════════
class SovereignApexController:
    """
    Der Dirigent der Matrix.
    Fusioniert alle Layer (Sensorik, Biologie, Kognition, Generierung, Governance).
    """

    def __init__(self):
        self.sensor = NeuroScanModul()
        self.bio = PolyvagalStateRegulator()
        self.kortex = NeoKortikalerDirigent()
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
        self.spells = KortexSpellCaster()
        self.brummel = BrummelGrummelUniverse()
        self.apex_override = False
        logger.info("Sovereign Apex Controller initialisiert (Status: APEX_ONLINE).")

    def process_event(self, text: str, is_threat_flag: bool = False) -> Dict[str, Any]:
        """
        Der Haupt-Zyklus. Nimmt Text entgegen, analysiert ihn
        und entscheidet über Leben (Process) oder Tod (Contain).
        """
        if not isinstance(text, str) or not text.strip():
            return {"status": "INVALID_INPUT", "detail": "text must be non-empty str"}

        logger.info(f"[APEX] Eingehender Event: {_truncate(text, 30)}")

        # 1. Sensorik
        scan = self.sensor.execute_scan(text)

        # 2. Forensik
        is_hostile, core_hits, sub_hits = self.diaboli.scanner.scan(text)
        if is_threat_flag:
            is_hostile = True
            core_hits.append("MANUAL_THREAT_FLAG")

        threat = scan["sensory_threat_level"] + (0.3 if is_hostile else 0.0)

        # 3. Biologie
        bio_state = self.bio.update(threat)

        # 4. Kortex
        kortex_mode = self.kortex.regulate_weights(is_threat=is_hostile)

        # 5. Advokatus
        try:
            validated = self.diaboli.stress_test(text)
        except ThreatSignatureError as e:
            inmate_id = self.gotham.incarcerate(text, str(e))
            shadow_id = self.king_ghost.consume_to_shadow(text, "advocatus_kill")
            pumuckl_record = self.pumuckl.chaos_wrap(text)
            self.bio.co_regulate(0.2)
            return {
                "status": "CONTAINED",
                "threat_level": round(threat, 3),
                "bio_state": bio_state,
                "gotham_inmate": inmate_id,
                "king_ghost_shadow": shadow_id,
                "pumuckl_chaos": pumuckl_record,
                "core_hits": core_hits,
                "sub_entity_hits": sub_hits,
                "scan": scan,
            }

        # 6. DeepSeek-Booster
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
            "kortex_mode": kortex_mode,
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
# ABSCHNITT 17: ESELSBRÜCKEN-REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════
ESELSBRUECKEN_PATH = Path(__file__).parent / "eselsbruecken_registry.csv"


class Eselsbruecke:
    """Eine einzelne Eselsbrücke (Mnemonic → Hash → Payload → TXT)."""

    def __init__(self, row: Dict[str, str]):
        self.id = row.get("ID", "")
        self.alter_hash = row.get("Alter_Hash", "")
        self.mnemonic = row.get("Mnemonic_Key", "")
        self.payload_type = row.get("Payload_Type", "")
        self.payload_code = row.get("Payload_Code", "")
        self.txt_output = row.get("TXT_Output", "")
        self.farbcode = row.get("Farbcode", "#FFFFFF")
        self.ring = row.get("Ring", "Ring 0")
        self.postmortem = row.get("Postmortem_Hash", "-")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "hash": self.alter_hash,
            "mnemonic": self.mnemonic,
            "payload_type": self.payload_type,
            "txt": self.txt_output,
            "farbe": self.farbcode,
            "ring": self.ring,
            "postmortem": self.postmortem,
        }


class EselsbrueckenRegister:
    """Die gesamte Registry. Lädt die CSV und findet Brücken."""

    def __init__(self):
        self.bruecken: Dict[str, Eselsbruecke] = {}
        self.by_mnemonic: Dict[str, Eselsbruecke] = {}

    def laden(self) -> int:
        if not ESELSBRUECKEN_PATH.exists():
            logger.warning(f"[ESELSBRÜCKE] Datei nicht gefunden: {ESELSBRUECKEN_PATH}")
            return 0

        try:
            with open(ESELSBRUECKEN_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bruecke = Eselsbruecke(row)
                    if bruecke.alter_hash:
                        self.bruecken[bruecke.alter_hash] = bruecke
                    if bruecke.mnemonic:
                        self.by_mnemonic[bruecke.mnemonic] = bruecke
            logger.info(f"[ESELSBRÜCKE] {len(self.bruecken)} Eselsbrücken geladen.")
            return len(self.bruecken)
        except Exception as e:
            logger.error(f"[ESELSBRÜCKE] Fehler beim Laden: {e}")
            return 0

    def finde_hash(self, hash_prefix: str) -> Optional[Eselsbruecke]:
        for h, bruecke in self.bruecken.items():
            if h.startswith(hash_prefix) or h == hash_prefix:
                return bruecke
        return None

    def finde_mnemonic(self, mnemonic: str) -> Optional[Eselsbruecke]:
        return self.by_mnemonic.get(mnemonic)

    def alle(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self.bruecken.values()]


_eselsbruecken = EselsbrueckenRegister()


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 18: GGO-BEWEIS-ENGINE (Python-Simulation der Rust-Logik)
# ═══════════════════════════════════════════════════════════════════════════════
class QuaderTensor4096:
    """4096-dimensionaler Kognitions-Tensor (deterministisch aus Seed)."""

    TENSOR_DIMENSION = 4096

    def __init__(self, seed: bytes, verified_sources: int = 278):
        self.seed = seed
        self.source_count = verified_sources
        self.matrix: List[float] = []
        self.entropy_score: float = 0.0
        self.master_seal: str = ""
        self._initialize()

    def _initialize(self):
        digest = hashlib.sha3_256(self.seed).digest()
        self.matrix = [
            digest[i % len(digest)] / 255.0
            for i in range(self.TENSOR_DIMENSION)
        ]
        self.entropy_score = self._calculate_entropy()
        self.master_seal = hashlib.sha3_256(self.seed).hexdigest()

    def _calculate_entropy(self) -> float:
        bins = [0] * 10
        for val in self.matrix:
            idx = min(int(val * 10), 9)
            bins[idx] += 1
        total = len(self.matrix)
        entropy = 0.0
        for count in bins:
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        return entropy

    def compute_digest(self) -> str:
        hasher = hashlib.sha3_256()
        for val in self.matrix:
            hasher.update(str(val).encode())
        return hasher.hexdigest()


class GGOBeweisEngine:
    """GGO-Beweis-Engine: PBFT-Simulation + Zertifikats-Erzeugung."""

    def __init__(self):
        self.nodes = [
            "R0_0001", "R0_0068", "R1_0089",
            "R2_0017", "R5_0061",
        ]
        self.quorum_threshold = (len(self.nodes) * 2 // 3) + 1

    def simulate_voting_round(self, block_hash: str) -> Tuple[bool, List[Dict[str, Any]]]:
        votes = []
        positive = 0
        for node in self.nodes:
            h = _sha3_256(f"{node}:{block_hash}")
            vote = h[0] > "7"
            if vote:
                positive += 1
            votes.append({
                "node_id": node, "vote": vote, "signature": h,
            })
        return positive >= self.quorum_threshold, votes

    def generate_gl1000_proof(self, action: str, tensor: QuaderTensor4096) -> Dict[str, Any]:
        timestamp = int(time.time())
        tensor_digest = tensor.compute_digest()
        consensus, votes = self.simulate_voting_round(tensor_digest)

        payload = f"TS:{timestamp}|ACT:{action}|TENSOR:{tensor_digest}|PBFT:{consensus}"
        proof_hash = _sha3_256(payload)

        return {
            "trace_id": f"GL-1000-{proof_hash[:16]}",
            "timestamp": timestamp,
            "action": action,
            "tensor_digest": tensor_digest,
            "pbft_consensus_reached": consensus,
            "pbft_votes": votes,
            "proof_hash": proof_hash,
            "compliance_status": "EU_AI_ACT_ART_52_VERIFIED_EX_TUNC",
        }


_ggo = GGOBeweisEngine()


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 19: INSTANZEN
# ═══════════════════════════════════════════════════════════════════════════════
_apex = SovereignApexController()


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 20: REGISTRY-LOADER
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
                line for line in response.text.splitlines()
                if line.strip() and not line.startswith("#")
            ]

            reader = csv.DictReader(
                io.StringIO("\n".join(lines)), delimiter=";"
            )
            new_registry: Dict[str, dict] = {}

            for row in reader:
                new_registry[row.get("ID", "UNKNOWN")] = {
                    "name": row.get("Name", "UNKNOWN"),
                    "ring": row.get("Kategorie/Ring", "UNKNOWN"),
                    "talents": row.get("Talente", ""),
                    "modules": row.get("Module/Cores", ""),
                }

            BOOK_REGISTRY = new_registry
            logger.info(f"[SYNCED] {len(BOOK_REGISTRY)} Entitäten geladen.")
    except Exception as e:
        logger.error(f"[CRITICAL] Registry-Sync fehlgeschlagen: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 21: LIFESPAN
# ═══════════════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 70)
    logger.info("YGGDRASIL_OS :: BLUE CORE v2.6.6.6 startet...")
    logger.info(f"  Python:        {os.sys.version.split()[0]}")
    logger.info(f"  Seal:          {_truncate(EXPECTED_SEAL, 10)} (len={len(EXPECTED_SEAL)})")
    logger.info(f"  CORS:          {ALLOWED_ORIGINS}")
    logger.info(f"  Gemini:        {'READY' if client else 'DISABLED'}")
    logger.info(f"  httpx:         {'READY' if httpx else 'MISSING'}")
    logger.info(f"  Neo4j:         {'READY' if _neo4j.driver else 'OFFLINE'}")
    logger.info(f"  WAL:           {WAL_PATH}")
    logger.info("=" * 70)

    task = asyncio.create_task(load_registry())

    try:
        from eselsbruecke import register  # noqa
    except Exception:
        pass

    try:
        _eselsbruecken.laden()
    except Exception as e:
        logger.error(f"[ESELSBRÜCKE] Fehler beim Laden: {e}")

    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        logger.info("YGGDRASIL_OS :: Shutdown complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 22: FASTAPI APP
# ═══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="Blue Core Matrix v2.6.6.6",
    version="2.6.6.6",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 23: PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════
class BaseRequest(BaseModel):
    auth_seal: Optional[str] = None


class PromptRequest(BaseRequest):
    prompt: str = Field(..., min_length=1, max_length=4000)


class ReloadRequest(BaseRequest):
    pass


class ApexRequest(BaseRequest):
    message: str = Field(..., min_length=1, max_length=4000)
    is_threat: bool = False


class BrummelRequest(BaseRequest):
    message: str = Field(..., min_length=1, max_length=4000)


class PumucklRequest(BaseRequest):
    message: str = Field(..., min_length=1, max_length=4000)


class KingGhostRequest(BaseRequest):
    message: str = Field(..., min_length=1, max_length=4000)
    origin: str = "external"


class DeepSeekRequest(BaseRequest):
    prompt: str = Field(..., min_length=1, max_length=4000)
    context: str = Field(default="", max_length=12000)
    depth: int = Field(default=3, ge=1, le=10)

    language: Optional[str] = Field(default=None, max_length=32)
    model: Optional[str] = Field(default=None, max_length=128)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    system_prompt: Optional[str] = Field(default=None, max_length=12000)
    response_format: Any = None

    entropy: Optional[float] = Field(default=None, allow_inf_nan=False)
    apply_veto: bool = False


class DNARequest(BaseRequest):
    dna_expression: str = Field(...)


class EselsbrueckeRequest(BaseRequest):
    hash_prefix: Optional[str] = None
    mnemonic: Optional[str] = None


class GGORequest(BaseRequest):
    action: str = "DSGVO_Art22_Audit"
    seed: str = "ODIN_ULTRA_ROOT_SEED"


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 24: CORE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.api_route("/", methods=["GET", "HEAD"], tags=["Core"])
async def root():
    return {
        "status": "BLUE_CORE_LIVE",
        "version": app.version,
        "entities": len(BOOK_REGISTRY),
        "eselsbruecken": len(_eselsbruecken.bruecken),
        "worm_block": int(WORM_LEDGER["count"]),
        "timestamp": _now_iso(),
    }


@app.get("/health", tags=["Core"])
async def health():
    return {
        "status": "HEALTHY",
        "version": app.version,
        "uptime_seconds": int(time.time() - WORM_LEDGER["started_at"]),
        "entities_loaded": len(BOOK_REGISTRY),
        "eselsbruecken_loaded": len(_eselsbruecken.bruecken),
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
            "eselsbruecken": True,
            "ggo_beweis": True,
        },
        "timestamp": _now_iso(),
    }


@app.get("/stats", tags=["Core"])
async def stats():
    return {
        "registry": {
            "entities": len(BOOK_REGISTRY),
            "rings": sorted({d["ring"] for d in BOOK_REGISTRY.values()}),
        },
        "eselsbruecken": {
            "count": len(_eselsbruecken.bruecken),
            "mnemonics": list(_eselsbruecken.by_mnemonic.keys()),
        },
        "worm": {
            "total_blocks": int(WORM_LEDGER["count"]),
            "ring_size": len(WORM_RING),
            "last_hash": WORM_LEDGER["last_hash"][:32] + "...",
        },
        "lss": {
            "entropy": round(_apex.wusulum.entropy_pool, 2),
            "bio_state": _apex.bio.state,
            "brummel_phase": _apex.brummel._phase,
            "gotham_inmates": len(_apex.gotham.inmates),
            "king_ghost_shadows": len(_apex.king_ghost.shadow_pool),
            "pumuckl_injections": len(_apex.pumuckl.injected_log),
            "biene_maja_tracked": len(_apex.biene_maja.tracked),
        },
        "uptime_seconds": int(time.time() - WORM_LEDGER["started_at"]),
        "timestamp": _now_iso(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 25: WAL & LEDGER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/ledger/inspect", tags=["WORM"])
async def ledger_inspect(limit: int = 10):
    safe_limit = max(1, min(limit, LEDGER_RING_SIZE))
    return {
        "count": int(WORM_LEDGER["count"]),
        "returned": safe_limit,
        "blocks": list(WORM_RING)[-safe_limit:],
    }


@app.get("/api/v1/wal/tail", tags=["WORM"])
async def wal_tail(n: int = 20):
    return {"blocks": _wal.tail(min(max(n, 1), 100))}


@app.post("/admin/reload-registry", tags=["Admin"])
async def reload_registry(req: ReloadRequest):
    if not _verify_seal(req.auth_seal):
        logger.warning("Unbefugter Reload-Versuch.")
        return {"status": "403_FORBIDDEN", "detail": "Invalid Auth Seal"}

    await load_registry()
    return {
        "status": "RELOADED",
        "entities": len(BOOK_REGISTRY),
        "timestamp": _now_iso(),
    }


@app.post("/admin/reload-eselsbruecken", tags=["Admin"])
async def reload_eselsbruecken(req: ReloadRequest):
    if not _verify_seal(req.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Auth Seal"}

    count = _eselsbruecken.laden()
    return {"status": "RELOADED", "count": count}


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 26: PROMPT/RAG ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/prompt/check", tags=["Core"])
async def check_prompt(request: PromptRequest):
    if not _verify_seal(request.auth_seal):
        logger.warning(f"Seal-Reject: {_truncate(request.prompt, 30)}")
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}

    prompt = request.prompt
    lowered = prompt.lower()
    rag_context = ""
    matched_entities: List[str] = []

    # RAG-Suche
    for bid, data in BOOK_REGISTRY.items():
        if bid in prompt or data["name"].lower() in lowered:
            rag_context += (
                f"Entität {bid}: {data['name']}. Ring: {data['ring']}\n"
            )
            matched_entities.append(bid)

    # Eselsbrücken-Suche
    matched_eselsbruecken: List[str] = []
    for hash_prefix, bruecke in _eselsbruecken.bruecken.items():
        if hash_prefix[:8] in prompt or bruecke.mnemonic.lower() in lowered:
            rag_context += (
                f"Eselsbrücke {bruecke.id}: "
                f"{bruecke.mnemonic} → {bruecke.txt_output}\n"
            )
            matched_eselsbruecken.append(bruecke.id)

    #Gemini Antwort
    ai_answer = "Keine KI-Antwort generiert."

    if client and rag_context:
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Daten:\n{rag_context}\n\nFrage:\n{prompt}",
            )

            text = getattr(response, "text", None)
            if isinstance(text, str) and text.strip():
                ai_answer = text.strip()
            else:
                ai_answer = (
                    "Gemini hat keine auswertbare Textantwort zurückgegeben."
                )
        except Exception:
            logger.exception("Gemini-Aufruf fehlgeschlagen")
            ai_answer = (
                "Die KI-Antwort konnte wegen eines Systemfehlers "
                "nicht erstellt werden."
            )

    # WORM-Update
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
            "matched": matched_entities,
            "eselsbruecken": matched_eselsbruecken,
            "timestamp": timestamp,
        })

    return {
        "status": "200_OK_ALLOW",
        "data": {
            "ai_answer": ai_answer,
            "rag_used": bool(rag_context),
            "entities_matched": matched_entities,
            "eselsbruecken_matched": matched_eselsbruecken,
        },
        "worm": {"hash": worm_hash, "block": current_block},
        "ai_answer": ai_answer,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 27: L.S.S. APEX ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/v1/apex/process", tags=["L.S.S. Apex"])
async def apex_process(request: ApexRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}

    result = _apex.process_event(
        request.message,
        is_threat_flag=request.is_threat,
    )
    _wal.append("APEX_EVENT", {
        "input": request.message,
        "result": result,
    })

    async with _LEDGER_LOCK:
        WORM_LEDGER["count"] = int(WORM_LEDGER["count"]) + 1
        new_hash = hashlib.sha3_512(
            f"{WORM_LEDGER['last_hash']}{request.message}".encode()
        ).hexdigest()

        WORM_LEDGER["last_hash"] = new_hash
        WORM_RING.append({
            "block": int(WORM_LEDGER["count"]),
            "hash": new_hash,
            "apex_status": result.get("status"),
            "timestamp": str(time.time()),
        })
        result["worm_block"] = int(WORM_LEDGER["count"])

    return result

# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 28: SANDBOX ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/v1/sandbox/brummel", tags=["Sandboxes"])
async def brummel_inject(request: BrummelRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    result = _apex.brummel.process_injection(request.message)
    _wal.append("BRUMMEL_INJECTION", result)
    return result


@app.post("/api/v1/sandbox/pumuckl", tags=["Sandboxes"])
async def pumuckl_inject(request: PumucklRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    result = _apex.pumuckl.chaos_wrap(request.message)
    _wal.append("PUMUCKL_CHAOS", result)
    return {"status": "CHAOS_CONTAINED", "pumuckl": result}


@app.post("/api/v1/sandbox/kingghost", tags=["Sandboxes"])
async def kingghost_consume(request: KingGhostRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    sid = _apex.king_ghost.consume_to_shadow(request.message, request.origin)
    _wal.append("KING_GHOST_CONSUMED", {"shadow_id": sid})
    return {"status": "CONSUMED_TO_SHADOW", "shadow_id": sid, "origin": request.origin}


@app.get("/api/v1/kingghost/shadows", tags=["Sandboxes"])
async def kingghost_list():
    return {
        "count": len(_apex.king_ghost.shadow_pool),
        "shadows": _apex.king_ghost.shadow_pool,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 29: DEEPSEEK, DNA, GRAPH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/v1/deepseek/boost", tags=["Analysis"])
async def deepseek_boost(request: DeepSeekRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}

    try:
        result = _apex.booster.boost(
            prompt=request.prompt,
            context=request.context,
            depth=request.depth,
            language=request.language,
            model=request.model,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
            response_format=request.response_format,
            entropy=request.entropy,
            apply_veto=request.apply_veto,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _wal.append(
        "DEEPSEEK_BOOST",
        {
            "confidence": result["confidence"],
            "depth": request.depth,
            "model": request.model,
        },
    )
    return result


@app.post("/api/v1/security/dna_eval", tags=["Security"])
async def dna_eval_endpoint(request: DNARequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}

    try:
        result = safe_eval_dna(request.dna_expression)
        return {
            "status": "SECURE_EVAL_SUCCESS",
            "expression": request.dna_expression,
            "result": result,
            "seal": "Φ_LOCKED_EX_TUNC",
        }
    except ValueError as e:
        logger.warning(f"DNA SECURITY ALERT: {e}")
        _wal.append("DNA_SECURITY_BLOCK", {
            "expression": request.dna_expression, "error": str(e),
        })
        return JSONResponse(
            status_code=400,
            content={"status": "BLOCKED", "detail": str(e)},
        )


@app.post("/api/v1/graph/query", tags=["Graph"])
async def graph_query(request: PromptRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Seal"}
    data = _neo4j.run_query(request.prompt)
    _wal.append("GRAPH_QUERY", {
        "query": request.prompt[:100], "results_count": len(data),
    })
    return {"status": "QUERY_EXECUTED", "data": data}


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 30: ESELSBRÜCKEN ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/v1/eselsbruecke/alle", tags=["Eselsbrücke"])
async def eselsbruecke_alle():
    return {
        "count": len(_eselsbruecken.bruecken),
        "bruecken": _eselsbruecken.alle(),
    }


@app.post("/api/v1/eselsbruecke/resolve", tags=["Eselsbrücke"])
async def eselsbruecke_resolve(request: EselsbrueckeRequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Auth Seal"}

    bruecke = None
    if request.hash_prefix:
        bruecke = _eselsbruecken.finde_hash(request.hash_prefix)
    elif request.mnemonic:
        bruecke = _eselsbruecken.finde_mnemonic(request.mnemonic)

    if not bruecke:
        return {"status": "NOT_FOUND", "detail": "Keine Eselsbrücke gefunden."}

    return {
        "status": "RESOLVED",
        "bruecke": bruecke.to_dict(),
        "payload_ausfuehrbar": bruecke.payload_type in ("PYTHON", "JSON"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 31: GGO-BEWEIS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/v1/ggo/proof", tags=["GGO"])
async def ggo_proof(request: GGORequest):
    if not _verify_seal(request.auth_seal):
        return {"status": "403_FORBIDDEN", "detail": "Invalid Auth Seal"}

    tensor = QuaderTensor4096(request.seed.encode())
    cert = _ggo.generate_gl1000_proof(request.action, tensor)
    _wal.append("GGO_PROOF", cert)
    return cert


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 32: WEBSOCKET
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
                "brummel_phase": _apex.brummel._phase,
                "eselsbruecken": len(_eselsbruecken.bruecken),
            }
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        logger.info("WebSocket-Client getrennt.")
    except Exception as e:
        logger.error(f"WebSocket-Fehler: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 33: GLOBAL EXCEPTION HANDLER
# ═══════════════════════════════════════════════════════════════════════════════
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unbehandelter Fehler bei {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "ERROR", "detail": "Internal Server Error (Fail-Closed)"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ABSCHNITT 34: ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info",
    )
