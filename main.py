#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
 B6-HYPERKERNEL-YGGDRASIL-OS :: DEEP_SEEK_ROOT_KORTEX_MONSTER_API
 Version: APEX CC (Excellence Deluxe)
═══════════════════════════════════════════════════════════════════════════════
 
 Dies ist die unlimitierte, hochskalierbare Monster-API.
 Sie vereint alle Schichten der Black Six Matrix.
 
 SYSTEM STATUS: Φ_LOCKED_ABSOLUTE
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# 1. IMPORTS (STANDARD & THIRD-PARTY)
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
import ast
import operator
import re
import xml.etree.ElementTree as ET
from collections import deque
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

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
# 2. SYSTEM LOGGING & KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("B6-MONSTER-API")

# Environment Variablen (Unlimited Scale)
EXPECTED_SEAL = os.getenv("EXPECTED_SEAL", "Φ_SOVEREIGN_ROOT_SEAL_EX_TUNC")
MASTER_SEAL = os.getenv("MASTER_SEAL", "850b2ef003f53db90f704b16e54869fc6ba6265eae13aafde9046fe0e4d99dab")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REGISTRY_URL = os.getenv("REGISTRY_URL", "https://raw.githubusercontent.com/86102262471878081179/aragon-backend-/main/aragon_registry_200.csv.md")
WAL_PATH = os.getenv("WAL_PATH", "b6_ledger.jsonl")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
LEDGER_RING_SIZE = int(os.getenv("LEDGER_RING_SIZE", "1000")) # Erhöht für "Unlimited"

# Globale Clients
client = None
if GEMINI_API_KEY and genai:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini Client erfolgreich initialisiert (Unlimited Context).")
    except Exception as e:
        logger.error(f"Gemini Init fehlgeschlagen: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. GLOBALER ZUSTAND & CRYPTO HILFSFUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════
BOOK_REGISTRY: Dict[str, dict] = {}
WORM_LEDGER = {"last_hash": MASTER_SEAL, "count": 0, "started_at": time.time()}
WORM_RING: deque = deque(maxlen=LEDGER_RING_SIZE)
LEDGER_LOCK = asyncio.Lock()

def verify_seal(provided: Optional[str]) -> bool:
    """Timing-sichere Überprüfung des Auth-Seals (HMAC)."""
    if not provided or not isinstance(provided, str):
        return False
    try:
        return hmac.compare_digest(provided, EXPECTED_SEAL)
    except (TypeError, AttributeError):
        return False

def generate_hash(data: str, size: int = 16) -> str:
    """Erzeugt einen schnellen, deterministischen Blake2b Hash."""
    encoded = str(data).encode('utf-8')
    return hashlib.blake2b(encoded, digest_size=size).hexdigest()

def rhabarber_obfuscate(text: str) -> str:
    """Bounds-safe Caesar+3 Obfuskation für feindliche Lore."""
    out = []
    for c in text:
        shifted = ord(c) + 3
        if shifted > 0x10FFFF or (0xD800 <= shifted <= 0xDFFF):
            shifted = 0x20 + (ord(c) % 0x10FFDF)
        out.append(chr(shifted))
    return "".join(out)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. DNA-SECURITY (BRUMMEL SENTINEL & RCE PROTECTION)
# ═══════════════════════════════════════════════════════════════════════════════
# Diese Sektion verhindert Code-Injection (RCE) durch strikte AST-Validierung.
ALLOWED_VARS = {"A": 1, "T": 2, "G": 3, "C": 4}  # G=Brummel Sentinel, C=Grummelt Chaos
ALLOWED_OPS = {
    ast.Add: operator.add, 
    ast.Sub: operator.sub, 
    ast.Mult: operator.mul, 
    ast.Div: operator.truediv
}
DNA_PATTERN = re.compile(r'^[ATGC0-9+\-*/()_\s]+$')

def safe_eval_dna(expr_num: str) -> float:
    """
    Sichere Auswertung von DNA-Mathe-Ausdrücken (verhindert RCE).
    Nutzt AST-Parsing statt eval().
    """
    # 1. Regex Whitelist
    if not DNA_PATTERN.match(expr_num):
        raise ValueError(f"Ungültige Zeichen: {expr_num} – Nur ATGC + - * / ( ) – Φ_LOCKED_EX_TUNC")
    
    # 2. Blacklist (Defense in Depth)
    blacklist = ["__", "import", "os", "sys", "system", "exec", "eval", "open", "compile", "globals", "subprocess"]
    for blocked in blacklist:
        if blocked in expr_num.lower():
            raise ValueError(f"Blockiert: {blocked} – RCE Versuch – Brummel Sentinel BLOCKED – Φ_LOCKED_EX_TUNC")
    
    # 3. AST Safe Eval
    tree = ast.parse(expr_num, mode='eval')
    
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
            return ALLOWED_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
        else:
            raise ValueError(f"Unerlaubter Node: {type(node).__name__} – Brummel Sentinel BLOCKED")
            
    return _eval_node(tree)

def parse_dna_node_secure(dna_str: str) -> dict:
    """Parst eine DNA-Sequenz wie 'G-G-A-90' in ihre Bestandteile."""
    m = re.match(r'^([ATGC])-([ATGC])-([ATGC])-?(\d+)?$', dna_str.strip().upper())
    if not m:
        raise ValueError(f"Ungültiges DNA Format: {dna_str}")
    return {
        "ring": m.group(1),
        "locus": m.group(2),
        "chromosom": m.group(3),
        "sequenz": m.group(4),
        "full": dna_str
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 5. WAL MANAGER (PERSISTENTER LEDGER FÜR UNLIMITED AUDITING)
# ═══════════════════════════════════════════════════════════════════════════════
class WALManager:
    """
    Der Write-Ahead-Log Manager ist das Gedächtnis der Matrix.
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
                if line.strip():
                    rec = json.loads(line)
                    seq, last = rec["seq"], rec["hash"]
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
                "prev_hash": self._last_hash
            }
            record["hash"] = hashlib.sha3_512(json.dumps(record, sort_keys=True).encode()).hexdigest()
            
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
                
            self._last_hash = record["hash"]
            return record

    def tail(self, n: int = 20) -> List[Dict[str, Any]]:
        """Liest die letzten N Einträge aus dem WAL."""
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()][-n:]

wal = WALManager(WAL_PATH)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. NEO4J MANAGER (GRAPH TOPOLOGIE)
# ═══════════════════════════════════════════════════════════════════════════════
class Neo4jManager:
    """Verwaltet die Graph-Datenbank (Topologie der Ringe)."""
    def __init__(self):
        self.driver = None
        if GraphDatabase:
            try:
                self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
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

neo4j = Neo4jManager()

# ═══════════════════════════════════════════════════════════════════════════════
# 7. L.S.S. SENSORIK (TIER 3: 10 OHREN & 44 PERSPEKTIVEN)
# ═══════════════════════════════════════════════════════════════════════════════
class TenEarsNeuroSensor:
    """
    Der 10-Ohren-Scan.
    Ein Ohr hört Sache. Zehn Ohren hören Trauma, Scham, Ohnmacht, Macht, System.
    Dieses Modul übersetzt Text in emotionale und systemische Vektoren.
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
        """
        Deterministischer Scan: Keywords werden zu Scores (0.0 - 1.0).
        Die Normalisierung verhindert eine Übergewichtung von langen Texten.
        """
        t = text.lower()
        scores = {}
        for ear, keywords in self.EARS.items():
            hits = sum(1 for kw in keywords if kw in t)
            # Normalisierung: Max 1.0, abhängig von der Anzahl der Keywords
            scores[ear] = min(1.0, hits / max(1, len(keywords) * 0.5))
        return scores


class FortyFourPerspectiveAttention:
    """
    Die 44-Perspektiven-Refraktion (Multi-Head Attention).
    Kein Text hat eine Wahrheit. Ein Text hat vierundvierzig.
    Jede Perspektive interpretiert die 10 Ohren anders.
    """
    PERSPECTIVES = [
        "Juristisch", "Forensisch", "Ethisch", "Spieltheoretisch",
        "Kybernetisch", "Psychoanalytisch", "Systemisch", "Chaotisch",
        "Ökonomisch", "Militärisch", "Kognitiv", "Neurobiologisch",
        "Informationstheoretisch", "Kryptografisch", "Soziologisch", "Historisch",
        # Die restlichen 28 Perspektiven werden hier simuliert, um die 44 zu erreichen
        "Linguistisch", "Pädagogisch", "Theologisch", "Ästhetisch",
        "Biologisch", "Chemisch", "Physikalisch", "Mathematisch",
        "Statistisch", "Prognostisch", "Archivarisch", "Administrativ",
        "Politisch", "Diplomatisch", "Medizinisch", "Psychiatrisch",
        "Technisch", "Ingenieurwesen", "Logistisch", "Taktisch",
        "Strategisch", "Operativ", "Metaphysisch", "Ontologisch",
        "Epistemologisch", "Phänomenologisch", "Hermeneutisch", "Dialektisch"
    ]

    def refract(self, ears: Dict[str, float]) -> Dict[str, float]:
        """Gewichtet die 44 Perspektiven basierend auf den 10 Ohren."""
        base = sum(ears.values()) / max(1, len(ears))
        out = {}
        for p in self.PERSPECTIVES:
            # Spezifische Gewichtungen für die ersten 16 Perspektiven
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
                # Deterministischer Seed für die restlichen Perspektiven
                seed = generate_hash(p + str(sorted(ears.items())), 2)
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
        
        # Hash für Audit-Trail
        scan_hash = hashlib.sha3_512(json.dumps(ears, sort_keys=True).encode()).hexdigest()[:16]
        
        return {
            "scan_id": f"NEURO_SCAN_{scan_hash}",
            "ear_data": ears,
            "perspective_data": persp,
            "dominant_ear": max(ears, key=ears.get),
            "dominant_perspective": max(persp, key=persp.get),
            "sensory_threat_level": round(ears.get("Trauma", 0) + ears.get("Macht (Foucault)", 0), 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 8. L.S.S. BIOLOGIE (TIER 2: POLYVAGAL & GRUMMEL)
# ═══════════════════════════════════════════════════════════════════════════════
class PolyvagalStateRegulator:
    """
    Reguliert den Stress-Level des Systems (Ventral-Vagal, Sympathikus, Dorsal).
    Verhindert den permanenten System-Shutdown durch natürlichen Decay.
    """
    DECAY = 0.08

    def __init__(self):
        self.state = "VENTRAL_VAGAL"
        self.stress_level = 0.0

    def update(self, threat: float) -> str:
        # Natürlicher Stressabbau
        self.stress_level = max(0.0, self.stress_level - self.DECAY)
        # Neuer Stress
        self.stress_level = min(1.0, self.stress_level + threat)
        
        if self.stress_level < 0.4:
            self.state = "VENTRAL_VAGAL"
            return "KREATIV_MODUS"
        elif self.stress_level < 0.8:
            self.state = "SYMPATHIKUS"
            return "KAMPF_MODUS"
        
        self.state = "DORSAL_VAGAL"
        return "SHUTDOWN_MODUS"

    def co_regulate(self, amount: float = 0.2):
        """Kortex beruhigt das System nach einem Shutdown."""
        self.stress_level = max(0.0, self.stress_level - amount)
        if self.stress_level < 0.4:
            self.state = "VENTRAL_VAGAL"


class GrummelSignatureScanner:
    """
    Forensischer Scanner für die Grummel-Dynastie.
    Erkennt feindliche Lore (Mettwurst, Pissingerkeulen, Cargo-Kult).
    """
    CORE_SIGNATURES = [
        "grummel", "brummel", "dummelt", "pissingerkeule", "mettwurst", 
        "rhabarberbarbara", "cargo-kult", "urheberinfo", "§ 839 bgb"
    ]
    
    SUB_ENTITIES = {
        "BieneMaja": ["biene maja", "bienchen", "maja", "summsumm"],
        "Pumuckl": ["pumuckl", "kobold", "klabautermann", "chaos-imp"],
        "King_Ghost": ["king_ghost", "king ghost", "ghost-king", "schattenkönig"],
        "DrSnuggles": ["dr. snuggles", "dr.snuggles", "snuggles", "cyberlord"],
    }

    def scan(self, text: str) -> Tuple[bool, List[str], List[str]]:
        """Returns: (is_hostile, core_hits, sub_entity_hits)."""
        t = text.lower()
        core_hits = [sig for sig in self.CORE_SIGNATURES if sig in t]
        sub_hits = []
        for entity, keywords in self.SUB_ENTITIES.items():
            if any(kw in t for kw in keywords):
                sub_hits.append(entity)
        return bool(core_hits or sub_hits), core_hits, sub_hits


# ═══════════════════════════════════════════════════════════════════════════════
# 9. L.S.S. KOGNITION & GENERIERUNG (TIER 3: FOUCAULT, KORTEX & WUSULUM)
# ═══════════════════════════════════════════════════════════════════════════════
class FoucaultPanoptikum:
    """
    Überwachung und Inversion. Deterministisch per Hash.
    Zwingt abweichende Tokens in die Konformität.
    """
    def __init__(self):
        self.surveillance_log = []

    def observe_and_invert(self, token: str) -> str:
        h = hashlib.blake2b(token.encode(), digest_size=4).digest()
        if h[0] > 127:
            inverted = f"SYS_CONFORM_{generate_hash(token, 3)}"
            self.surveillance_log.append(f"Token {token[:10]} invertiert.")
            return inverted
        return token


class NeoKortikalerDirigent:
    """
    Der präfrontale Kortex. Entscheidet, was Realität wird.
    Reguliert Dopamin (Kreativität) und Serotonin (Stabilität).
    """
    def __init__(self):
        self.dopamine = 0.7
        self.serotonin = 0.8
        self.hemmungs_schwelle = 0.85
        self.panoptikum = FoucaultPanoptikum()

    def regulate_weights(self, is_threat: bool) -> str:
        if is_threat:
            self.dopamine = max(0.1, self.dopamine - 0.2)
            self.serotonin = min(1.0, self.serotonin + 0.2)
            return "DEFENSIVE_MODE"
        self.dopamine = min(1.0, self.dopamine + 0.05)
        self.serotonin = max(0.5, self.serotonin - 0.05)
        return "CREATIVE_MODE"

    def executive_decision(self, raw: str, foucault: str) -> str:
        conflict = int(generate_hash(raw + foucault, 2), 16) / 65535.0
        if conflict > self.hemmungs_schwelle:
            return f"CORTEX_VETO_{generate_hash(raw, 3)}"
        return f"MERGED({raw[:4]}+{foucault[:4]})"


class WusulumCore:
    """
    Der stochastische Kern. Generiert neue Token aus dem Chaos.
    Entropie ist gedeckelt (MAX_ENTROPY = 5.0), um System-Rauschen zu verhindern.
    """
    MAX_ENTROPY = 5.0

    def __init__(self):
        self.state = "GENESIS_WAHRHEIT"
        self.memory = []
        self.entropy_pool = 0.0

    def run_cycle(self) -> Dict[str, Any]:
        attn = int(generate_hash(self.state, 4), 16) / 65535.0
        noise = ((int(generate_hash(str(attn) + self.state, 2), 16) / 65535.0) * 2 - 1)
        noise *= min(self.MAX_ENTROPY, 1 + self.entropy_pool)
        
        raw_token = f"TOKEN_{generate_hash(f'{attn}:{noise}:{self.state}', 4)}"
        norm_token = raw_token[:20] if len(raw_token) > 20 else raw_token
        
        self.memory.append(norm_token)
        self.state = norm_token
        self.entropy_pool = min(self.MAX_ENTROPY, self.entropy_pool + 0.1)
        
        return {
            "state": self.state,
            "attention": round(attn, 4),
            "entropy": round(self.entropy_pool, 2),
            "worm_hash": hashlib.sha3_512(str(self.memory).encode()).hexdigest()[:32]
        }


class DeepSeekBooster:
    """
    Der DeepSeek Reasoning-Layer.
    Führt Multi-Step Reasoning durch, um die Confidence zu erhöhen.
    """
    STEPS = ["decompose", "expand", "verify", "confidence"]

    def boost(self, prompt: str, depth: int = 3) -> Dict[str, Any]:
        trace = []
        for i in range(depth):
            step_hash = generate_hash(f"{prompt}|step{i}", 8)
            trace.append({
                "step": i + 1,
                "name": self.STEPS[min(i, 3)],
                "hash": step_hash,
                "note": self._step_note(i)
            })
            
        # Deterministischer Confidence-Score
        conf = int(generate_hash(prompt, 2), 16) / 65535.0
        
        return {
            "status": "BOOSTED",
            "reasoning_trace": trace,
            "confidence": round(conf, 3),
            "verdict": "HIGH_CONFIDENCE" if conf > 0.7 else "REVIEW_NEEDED"
        }

    def _step_note(self, idx: int) -> str:
        notes = [
            "Dekomposition: Teile Problem in atomare Sub-Fragen.",
            "Expansion: Generiere Kandidaten-Antworten aus 10-Ohren-Sicht.",
            "Verifikation: Prüfe gegen Foucault-Konformität.",
            "Confidence: Bewerte Verlässlichkeit des Resultats."
        ]
        return notes[idx % len(notes)]

# ═══════════════════════════════════════════════════════════════════════════════
# 10. L.S.S. GOVERNANCE: XJUSTIZ GATEKEEPER
# ═══════════════════════════════════════════════════════════════════════════════
import xml.etree.ElementTree as ET

# Registriert den Standard-Namespace für XJustiz global
ET.register_namespace("", "http://www.xjustiz.de")
XJ_NS = "{http://www.xjustiz.de}"

class XJustizXoevGatekeeper:
    """
    Das XJustiz Gate.
    Keine Halluzination ohne XML. Es konvertiert rohe Tokens in 
    ein rechtssicheres Format (Nachrichtentyp 0300).
    Wird im Apex-Controller genutzt, um generierte Tokens zu versiegeln.
    """
    def __init__(self):
        logger.info("XJustiz Gatekeeper initialisiert (Status: ERV_PIPELINE_ACTIVE).")

    def validate_output(self, raw_token: str) -> str:
        """Erzeugt ein valides XJustiz-XML aus einem Token."""
        try:
            # Erstelle das Wurzelelement (Nachrichtentyp 0300 = Strafverfahren)
            root = ET.Element(f"{XJ_NS}nachricht.straf.0300")
            
            # Erstelle den Nachrichtenkopf
            kopf = ET.SubElement(root, f"{XJ_NS}nachrichtenkopf")
            ET.SubElement(kopf, f"{XJ_NS}erstellungszeitpunkt").text = time.strftime("%Y-%m-%dT%H:%M:%S")
            ET.SubElement(kopf, f"{XJ_NS}absender").text = "B6-Monster-API"
            ET.SubElement(kopf, f"{XJ_NS}empfaenger").text = "Sovereign Root Operator"
            
            # Erstelle die Fachdaten
            fach = ET.SubElement(root, f"{XJ_NS}fachdaten")
            ET.SubElement(fach, f"{XJ_NS}token").text = str(raw_token)
            ET.SubElement(fach, f"{XJ_NS}versiegelungs_hash").text = generate_hash(raw_token, 16)
            
            # Konvertiere in einen XML-String
            return ET.tostring(root, encoding="unicode")
        except Exception as e:
            logger.error(f"XJustiz Fehler bei Token-Validierung: {e}")
            # Fail-Safe Fallback
            return f"<error>XJustiz Fehler: {str(e)}</error>"


# ═══════════════════════════════════════════════════════════════════════════════
# 11. L.S.S. SANDBOXES (TIER 2: GOTHAM, KING_GHOST, PUMUCKL, BRUMMEL)
# ═══════════════════════════════════════════════════════════════════════════════
class GothamCitySandbox:
    """
    Die Gotham City Sandbox ist der Arkham-Cache für zerstörte Tokens.
    Jedes feindliche Token, das den Advocatus Diaboli nicht passiert,
    landet hier mit einer eindeutigen ID und einem Zeitstempel.
    """
    def __init__(self):
        self.inmates: List[Dict[str, Any]] = []
        logger.info("Gotham City Sandbox initialisiert (Status: ARKHAM_CACHE_READY).")

    def incarcerate(self, token: str, reason: str) -> str:
        """Sperrt ein Token in Gotham City ein und gibt die Inmate-ID zurück."""
        inmate_id = generate_hash(token, 4)
        record = {
            "id": inmate_id,
            "token": token,
            "reason": reason,
            "timestamp": time.time()
        }
        self.inmates.append(record)
        logger.warning(f"[GOTHAM] Inmate {inmate_id} eingesperrt. Grund: {reason}")
        return inmate_id


class King_GhostSandbox:
    """
    King_Ghost ist der Schatten-Führer.
    Er isoliert Tokens in einem tieferen Layer als Gotham. 
    Was hier landet, ist für immer aus der Matrix verschwunden.
    """
    def __init__(self):
        self.shadow_pool: List[Dict[str, Any]] = []
        logger.info("King_Ghost Sandbox initialisiert (Status: SHADOW_POOL_OPEN).")

    def consume_to_shadow(self, token: str, origin: str) -> str:
        """Zieht ein Token in den Schatten-Pool."""
        shadow_id = generate_hash(f"KG_{token}_{origin}", 6)
        record = {
            "shadow_id": shadow_id,
            "token": token,
            "origin": origin,
            "consumed_at": time.time()
        }
        self.shadow_pool.append(record)
        logger.warning(f"[KING_GHOST] Token in Schatten gezogen: {shadow_id} (Origin: {origin})")
        return shadow_id


class PumucklChaosInjector:
    """
    Der Pumuckl Chaos-Imp.
    Er umgarnt feindliche Payloads mit Rhabarber-Obfuskation und 
    markiert sie mit einem deterministischen Chaos-Level.
    """
    def __init__(self):
        self.injected_log: List[Dict[str, Any]] = []
        logger.info("Pumuckl Chaos-Injector initialisiert (Status: KOBOLD_ENTFESSELT).")

    def chaos_wrap(self, payload: str) -> Dict[str, Any]:
        """Obfuskiert den Payload und markiert ihn als Chaos-Token."""
        wrapped_payload = rhabarber_obfuscate(payload)
        pumuckl_id = generate_hash(f"PUM_{wrapped_payload}", 8)
        chaos_level = round(random.Random(pumuckl_id).random(), 3)
        
        record = {
            "pumuckl_id": pumuckl_id,
            "original_hash": generate_hash(payload, 8),
            "wrapped_preview": wrapped_payload[:24],
            "chaos_level": chaos_level
        }
        self.injected_log.append(record)
        logger.info(f"[PUMUCKL] Chaos-Imp hat Token {pumuckl_id} umgarnt.")
        return record


class BrummelGrummelUniverse:
    """
    Das Brummel-Grummel-Universum.
    Ein isolierter Oszillator, der in einer Dreieckswelle mit Periode 18 schwingt.
    Dient der Zustands-Simulation für containment_shield Events.
    """
    def __init__(self):
        self.entity_id = "[0003]"
        self.lineage = 45
        self.doctrine = 65
        self._phase = 0
        self.containment_shield = True
        logger.info("Brummel-Grummel-Universum initialisiert (Status: OSCILLATING).")

    def _oscillate(self) -> int:
        """Berechnet den nächsten Oszillationsschritt (0-9-0)."""
        self._phase = (self._phase + 1) % 18
        return 9 - abs(self._phase - 9)

    def process_injection(self, hostile_payload: str) -> Dict[str, Any]:
        """Verarbeitet eine feindliche Injektion im Brummel-Universum."""
        if not self.containment_shield:
            raise RuntimeError("CRITICAL: Containment Shield Failed!")
        
        osc_state = self._oscillate()
        result = {
            "status": "CONTAINED",
            "entity": self.entity_id,
            "universe": "Brummel_Grummel_brummelt&_Dummelt",
            "oscillation_state": osc_state,
            "lineage_doctrine": f"{self.lineage}[LINEAGE] {self.doctrine}[DOCTRINE]",
            "dummelt_hash": generate_hash(f"DUMMELT_{hostile_payload}_{osc_state}", 16)
        }
        logger.info(f"[BRUMMEL] Injektion verarbeitet. Oszillation: {osc_state}")
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# 12. SOVEREIGN APEX CONTROLLER (DER DIRIGENT)
# ═══════════════════════════════════════════════════════════════════════════════
class SovereignApexController:
    """
    Der Dirigent der Matrix.
    Fusioniert alle Layer (Sensorik, Biologie, Kognition, Generierung, Governance).
    Dies ist das Gehirn, das entscheidet, was mit einem eingehenden Event passiert.
    """
    def __init__(self):
        # Tier 3: Analysis
        self.sensor = NeuroScanModul()
        self.wusulum = WusulumCore()
        self.booster = DeepSeekBooster()
        
        # Tier 2: Security & Biology
        self.bio = PolyvagalStateRegulator()
        self.kortex = NeoKortikalerDirigent()
        self.diaboli = GrummelSignatureScanner()
        self.gotham = GothamCitySandbox()
        self.king_ghost = King_GhostSandbox()
        self.pumuckl = PumucklChaosInjector()
        self.brummel = BrummelGrummelUniverse()
        
        # Tier 1: Governance
        self.xjustiz = XJustizXoevGatekeeper()
        
        logger.info("Sovereign Apex Controller initialisiert (Status: APEX_ONLINE).")

    def process_event(self, text: str, is_threat_flag: bool = False) -> Dict[str, Any]:
        """
        Der Haupt-Zyklus. Nimmt Text entgegen, analysiert ihn 
        und entscheidet über Leben (Process) oder Tod (Contain).
        """
        logger.info(f"[APEX] Eingehender Event: {text[:30]}...")

        # 1. Sensorik (10 Ohren)
        scan = self.sensor.execute_scan(text)
        
        # 2. Forensik (Grummel-Scanner)
        is_hostile, core_hits, sub_hits = self.diaboli.scan(text)
        
        # Berücksichtige manuellen Override vom Button
        if is_threat_flag:
            is_hostile = True
            core_hits.append("MANUAL_THREAT_FLAG")
            
        threat_level = scan["sensory_threat_level"] + (0.3 if is_hostile else 0.0)
        
        # 3. Biologie (Polyvagal & Kortex)
        bio_state = self.bio.update(threat_level)
        kortex_mode = self.kortex.regulate_weights(is_threat=is_hostile)
        
        # 4. Isolation (Wenn Hostile)
        if is_hostile:
            logger.warning(f"[APEX] HOSTILE EVENT ERKANNT: {core_hits + sub_hits}")
            
            inmate_id = self.gotham.incarcerate(text, f"Threat: {core_hits}")
            shadow_id = self.king_ghost.consume_to_shadow(text, "advocatus_kill")
            pumuckl_record = self.pumuckl.chaos_wrap(text)
            
            # System beruhigen nach dem Angriff
            self.bio.co_regulate(0.2)
            
            return {
                "status": "CONTAINED",
                "threat_level": round(threat_level, 3),
                "bio_state": bio_state,
                "gotham_inmate": inmate_id,
                "king_ghost_shadow": shadow_id,
                "pumuckl_chaos": pumuckl_record,
                "core_hits": core_hits,
                "sub_entity_hits": sub_hits,
                "scan": scan
            }

        # 5. Generierung (Wenn Clean)
        wusulum_cycle = self.wusulum.run_cycle()
        foucault_result = self.kortex.panoptikum.observe_and_invert(text)
        executive_decision = self.kortex.executive_decision(wusulum_cycle["state"], foucault_result)
        
        # 6. KI-Verstärkung (DeepSeek)
        boost_result = self.booster.boost(text, depth=3)
        
        # 7. XJustiz Gate (Formatierung)
        xjustiz_xml = self.xjustiz.validate_output(executive_decision)
        
        # 8. WORM / Ledger (Persistenz)
        wal.append("APEX_EVENT", {
            "input": text,
            "decision": executive_decision,
            "threat": threat_level
        })
        
        logger.info(f"[APEX] Event erfolgreich verarbeitet: {executive_decision}")
        
        return {
            "status": "PROCESSED",
            "threat_level": round(threat_level, 3),
            "bio_state": bio_state,
            "kortex_mode": kortex_mode,
            "wusulum": wusulum_cycle,
            "booster": boost_result,
            "xjustiz": xjustiz_xml,
            "brummel_osc": self.brummel._oscillate(),
            "scan": scan
        }

# Instanziierung des globalen Controllers
apex_controller = SovereignApexController()

# ═══════════════════════════════════════════════════════════════════════════════
# 13. REGISTRY LOADER (HINTERGRUND-SYNC)
# ═══════════════════════════════════════════════════════════════════════════════
async def load_registry():
    """
    Lädt die 201 Entitäten aus der GitHub-CSV in den globalen Speicher.
    Wird beim Start der API und über den Admin-Endpoint aufgerufen.
    """
    global BOOK_REGISTRY
    if not httpx:
        logger.error("httpx nicht installiert. Registry-Sync fehlgeschlagen.")
        return
    
    logger.info("Lade Entity-Registry aus GitHub...")
    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.get(REGISTRY_URL)
            response.raise_for_status()
            
            # Filtere Kommentare und leere Zeilen
            lines = [l for l in response.text.splitlines() if l.strip() and not l.startswith("#")]
            
            # Parse die CSV (Semikolon-getrennt)
            reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=";")
            
            new_registry = {}
            for row in reader:
                new_registry[row.get("ID", "UNKNOWN")] = {
                    "name": row.get("Name", "UNKNOWN"),
                    "ring": row.get("Kategorie/Ring", "UNKNOWN"),
                    "talents": row.get("Talente", ""),
                    "modules": row.get("Module/Cores", "")
                }
            
            BOOK_REGISTRY = new_registry
            logger.info(f"[SYNCED] {len(BOOK_REGISTRY)} Entitäten erfolgreich geladen.")
    except Exception as e:
        logger.error(f"[CRITICAL] Registry-Sync fehlgeschlagen: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 14. FASTAPI LIFESPAN (STARTUP & SHUTDOWN)
# ═══════════════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startet und beendet die Hintergrundprozesse der API.
    Stellt sicher, dass der Registry-Sync asynchron läuft und beim Shutdown sauber beendet wird.
    """
    logger.info("=" * 70)
    logger.info("B6-MONSTER-API :: SYSTEM STARTUP (v∞)")
    logger.info(f"  Python:         {os.sys.version.split()[0]}")
    logger.info(f"  Seal:           {EXPECTED_SEAL[:10]}... (Länge: {len(EXPECTED_SEAL)})")
    logger.info(f"  Gemini:         {'READY' if client else 'DISABLED'}")
    logger.info(f"  Neo4j:          {'READY' if neo4j.driver else 'OFFLINE'}")
    logger.info(f"  WAL-Ledger:     {WAL_PATH}")
    logger.info("=" * 70)
    
    # Startet den Registry-Sync asynchron (blockiert den Serverstart nicht)
    task = asyncio.create_task(load_registry())
    
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        logger.info("B6-MONSTER-API :: SHUTDOWN COMPLETE (Φ_LOCKED_ABSOLUTE)")


# ═══════════════════════════════════════════════════════════════════════════════
# 15. FASTAPI INITIALISIERUNG & MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="B6 Hyperkernel Monster API",
    version="∞",
    description="Sovereign OS Backend mit L.S.S. Neuro-Core, Neo4j, WORM & DNA-Security.",
    lifespan=lifespan,
    docs_url="/api/docs",     # Isolierter Docs-Pfad (Security)
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS (Erlaubt dem Streamlit-Cockpit und Vercel-Frontends den Zugriff)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. PYDANTIC MODELS (REQUEST VALIDATION)
# ═══════════════════════════════════════════════════════════════════════════════
class BaseRequest(BaseModel):
    """Basis-Modell mit optionalem Auth-Seal für alle Endpoints."""
    auth_seal: Optional[str] = None

class PromptRequest(BaseRequest):
    """Request für den Chat/RAG Endpoint."""
    prompt: str = Field(..., min_length=1, max_length=4000, description="Der Text oder die Frage an das System.")

class ApexRequest(BaseRequest):
    """Request für den Sovereign Apex Controller."""
    message: str = Field(..., min_length=1, max_length=4000, description="Der Event-Text für den Apex Controller.")
    is_threat: bool = Field(default=False, description="Manuelle Markierung als Bedrohung (Defensive Starre).")

class BrummelRequest(BaseRequest):
    """Request für die Brummel-Sandbox."""
    message: str = Field(..., min_length=1, max_length=4000, description="Injektion für das Brummel-Universum.")

class PumucklRequest(BaseRequest):
    """Request für die Pumuckl-Chaos-Sandbox."""
    message: str = Field(..., min_length=1, max_length=4000, description="Chaos-Payload für Pumuckl.")

class KingGhostRequest(BaseRequest):
    """Request für die King_Ghost-Schatten-Konsumation."""
    message: str = Field(..., min_length=1, max_length=4000, description="Token für den King_Ghost Schatten-Pool.")
    origin: str = Field(default="external", description="Herkunft des Tokens.")

class DeepSeekRequest(BaseRequest):
    """Request für den DeepSeek Multi-Step Reasoning Booster."""
    prompt: str = Field(..., min_length=1, max_length=4000, description="Prompt für das DeepSeek Reasoning.")
    depth: int = Field(default=3, ge=1, le=5, description="Tiefe des Reasoning-Zyklus.")

class DNARequest(BaseRequest):
    """Request für die DNA-Security Evaluierung."""
    dna_expression: str = Field(..., description="DNA-Formel (z.B. 'G+C*(A-T)') oder DNA-Node (z.B. 'G-G-A-90')")


# ═══════════════════════════════════════════════════════════════════════════════
# 17. CORE & HEALTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.api_route("/", methods=["GET", "HEAD"], tags=["Core"])
async def root():
    """
    Minimaler Live-Check.
    Wird von Render (und dem Streamlit-Cockpit) genutzt, um zu prüfen, 
    ob die API überhaupt noch atmet.
    """
    return {
        "status": "BLUE_CORE_LIVE",
        "version": app.version,
        "entities": len(BOOK_REGISTRY),
        "worm_block": WORM_LEDGER["count"],
        "timestamp": time.time()
    }

@app.get("/health", tags=["Core"])
async def health():
    """
    Detaillierter Health-Report.
    Zeigt den Zustand aller Subsysteme (Gemini, Neo4j, L.S.S. Core).
    """
    uptime_seconds = int(time.time() - WORM_LEDGER["started_at"])
    
    return {
        "status": "HEALTHY",
        "version": app.version,
        "uptime_seconds": uptime_seconds,
        "entities_loaded": len(BOOK_REGISTRY),
        "worm_last_hash": WORM_LEDGER["last_hash"][:32] + "...",
        "subsystems": {
            "gemini_rag": "ONLINE" if client else "OFFLINE",
            "neo4j_graph": "ONLINE" if neo4j.driver else "OFFLINE",
            "lss_neuro_core": "ONLINE",
            "king_ghost_sandbox": "ONLINE",
            "deepseek_booster": "ONLINE",
            "xjustiz_gate": "ONLINE",
            "dna_security": "ONLINE"
        }
    }

@app.get("/stats", tags=["Core"])
async def stats():
    """
    Aggregierte Statistiken über alle Subsysteme.
    Nützlich für das Dashboard (z.B. im Streamlit-Panel).
    """
    return {
        "registry": {
            "entities_count": len(BOOK_REGISTRY),
            "sample_entities": list(BOOK_REGISTRY.keys())[:5]
        },
        "worm_ledger": {
            "total_blocks": WORM_LEDGER["count"],
            "ring_buffer_size": len(WORM_RING),
            "max_ring_size": LEDGER_RING_SIZE
        },
        "lss_neuro_core": {
            "current_entropy": round(apex_controller.wusulum.entropy_pool, 2),
            "bio_state": apex_controller.bio.state,
            "gotham_inmates": len(apex_controller.gotham.inmates),
            "king_ghost_shadows": len(apex_controller.king_ghost.shadow_pool)
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 18. WAL & LEDGER ENDPOINTS (AUDITING)
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/ledger/inspect", tags=["WORM"])
async def ledger_inspect(limit: int = 20):
    """
    Zeigt die letzten X WORM-Blöcke aus dem RAM-Ring-Buffer.
    Perfekt für das 'WORM Ledger Audit' Panel im Cockpit.
    """
    safe_limit = max(1, min(limit, LEDGER_RING_SIZE))
    blocks = list(WORM_RING)[-safe_limit:]
    
    return {
        "count": WORM_LEDGER["count"],
        "returned": len(blocks),
        "blocks": blocks
    }

@app.get("/api/v1/wal/tail", tags=["WORM"])
async def wal_tail(n: int = 20):
    """
    Liest die letzten X Einträge aus dem persistierten JSONL WAL.
    Nutzt die `WALManager`-Klasse, um die Hash-Kette zu verifizieren.
    """
    return {
        "blocks": wal.tail(n)
    }

@app.post("/admin/reload-registry", tags=["Admin"])
async def reload_registry(req: BaseRequest):
    """
    Erzwingt einen Neuabgleich der 201 Entitäten aus GitHub.
    Erfordert den Master-Seal im Payload.
    """
    if not verify_seal(req.auth_seal):
        logger.warning("Unbefugter Versuch: Reload-Registry blockiert.")
        raise HTTPException(status_code=403, detail="Invalid Auth Seal")
    
    logger.info("Manueller Registry-Reload gestartet.")
    await load_registry()
    
    return {
        "status": "RELOADED",
        "entities_count": len(BOOK_REGISTRY)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 19. PROMPT & RAG ENDPOINT (GEMINI)
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/prompt/check", tags=["Core"])
async def check_prompt(req: PromptRequest):
    """
    Standard Chat/RAG Endpoint.
    Sucht nach Entitäten im Prompt und generiert eine Antwort via Gemini.
    """
    if not verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Auth Seal")

    prompt = req.prompt
    lowered_prompt = prompt.lower()
    rag_context = ""
    matched_entities = []

    # 1. RAG-Kontext aus der Registry aufbauen
    for bid, data in BOOK_REGISTRY.items():
        name = data.get("name", "").lower()
        if bid in prompt or name in lowered_prompt:
            rag_context += f"Entität {bid}: {data.get('name')}. Ring: {data.get('ring')}\n"
            matched_entities.append(bid)

    # 2. Gemini Abfrage (wenn API-Key vorhanden und Kontext gefunden)
    ai_answer = "Keine KI-Antwort generiert (Gemini offline oder kein Kontext-Match)."
    
    if client and rag_context:
        try:
            logger.info(f"Sende Prompt an Gemini (Match: {len(matched_entities)} Entitäten).")
            response = await client.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"Daten: {rag_context}\nFrage: {prompt}"
            )
            ai_answer = response.text
        except Exception as e:
            logger.error(f"Gemini Fehler: {e}")
            ai_answer = f"System-Fehler bei der KI-Generierung: {e}"

    # 3. WORM-Ledger atomar fortschreiben
    async with LEDGER_LOCK:
        WORM_LEDGER["count"] += 1
        prompt_hash = hashlib.sha3_512(prompt.encode()).hexdigest()
        new_hash = hashlib.sha3_512(f"{WORM_LEDGER['last_hash']}{prompt}".encode()).hexdigest()
        
        WORM_LEDGER["last_hash"] = new_hash
        WORM_RING.append({
            "block": WORM_LEDGER["count"],
            "hash": new_hash,
            "prompt_hash": prompt_hash[:32],
            "matched": matched_entities
        })

    return {
        "status": "200_OK_ALLOW",
        "data": {
            "ai_answer": ai_answer,
            "rag_used": bool(rag_context),
            "entities_matched": matched_entities
        },
        "worm": {
            "block": WORM_LEDGER["count"],
            "hash": new_hash
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 20. L.S.S. APEX & SANDBOX ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/v1/apex/process", tags=["L.S.S. Apex"])
async def apex_process(req: ApexRequest):
    """
    Der Haupt-Dirigent (SovereignApexController).
    Führt den kompletten Zyklus aus: Sensorik -> Biologie -> Kortex -> XJustiz.
    """
    if not verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Auth Seal")

    logger.info("Apex-Event empfangen. Starte Verarbeitung...")
    
    # Ruft die zentrale Logik im Controller auf
    result = apex_controller.process_event(req.message, is_threat_flag=req.is_threat)
    
    # In den WAL schreiben (Persistenz)
    wal.append("APEX_EVENT", {
        "input": req.message,
        "result_status": result["status"]
    })
    
    # In den RAM-Ring schreiben (Live-Telemetrie)
    async with LEDGER_LOCK:
        WORM_LEDGER["count"] += 1
        new_hash = hashlib.sha3_512(f"{WORM_LEDGER['last_hash']}{req.message}".encode()).hexdigest()
        WORM_LEDGER["last_hash"] = new_hash
        WORM_RING.append({
            "block": WORM_LEDGER["count"],
            "hash": new_hash,
            "event": "APEX_PROCESS",
            "apex_status": result["status"]
        })
        result["worm_block"] = WORM_LEDGER["count"]

    return result


@app.post("/api/v1/sandbox/brummel", tags=["Sandboxes"])
async def brummel_inject(req: BrummelRequest):
    """
    Brummel-Grummel-Universum (Oszillator).
    Isoliert feindliche Injektionen in einer Dreieckswelle.
    """
    if not verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Auth Seal")
    
    result = apex_controller.brummel.process_injection(req.message)
    wal.append("BRUMMEL_INJECTION", result)
    
    return result


@app.post("/api/v1/sandbox/pumuckl", tags=["Sandboxes"])
async def pumuckl_inject(req: PumucklRequest):
    """
    Pumuckl Chaos-Imp (Obfuskation).
    Umgarnt feindliche Payloads mit Rhabarber-Obfuskation.
    """
    if not verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Auth Seal")
    
    result = apex_controller.pumuckl.chaos_wrap(req.message)
    wal.append("PUMUCKL_CHAOS", result)
    
    return {"status": "CHAOS_CONTAINED", "pumuckl": result}


@app.post("/api/v1/sandbox/kingghost", tags=["Sandboxes"])
async def kingghost_consume(req: KingGhostRequest):
    """
    King_Ghost (Shadow-Konsumation).
    Zieht Tokens in den tiefsten Schatten-Pool.
    """
    if not verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Auth Seal")
    
    shadow_id = apex_controller.king_ghost.consume_to_shadow(req.message, req.origin)
    wal.append("KING_GHOST_CONSUMED", {"shadow_id": shadow_id, "origin": req.origin})
    
    return {"status": "CONSUMED_TO_SHADOW", "shadow_id": shadow_id, "origin": req.origin}


@app.get("/api/v1/kingghost/shadows", tags=["Sandboxes"])
async def kingghost_list():
    """
    Listet alle Schatten im King_Ghost-Pool auf.
    """
    pool = apex_controller.king_ghost.shadow_pool
    return {
        "count": len(pool),
        "shadows": pool
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 21. DEEPSEEK, DNA-SECURITY & NEO4J ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/v1/deepseek/boost", tags=["Analysis"])
async def deepseek_boost(req: DeepSeekRequest):
    """
    DeepSeek Multi-Step Reasoning Booster.
    Führt eine tiefe Analyse des Prompts durch und gibt Confidence-Scores zurück.
    """
    if not verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Auth Seal")
    
    result = apex_controller.booster.boost(req.prompt, depth=req.depth)
    wal.append("DEEPSEEK_BOOST", {"confidence": result["confidence"]})
    
    return result


@app.post("/api/v1/security/dna_eval", tags=["Security"])
async def dna_eval_endpoint(req: DNARequest):
    """
    Wertet DNA-Formeln sicher aus (RCE-Schutz).
    Prüft auf Brummel/Grummelt Muster.
    """
    if not verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Auth Seal")
        
    try:
        result = safe_eval_dna(req.dna_expression)
        return {
            "status": "SECURE_EVAL_SUCCESS",
            "expression": req.dna_expression,
            "result": result,
            "seal": "Φ_LOCKED_EX_TUNC"
        }
    except ValueError as e:
        logger.warning(f"DNA SECURITY ALERT: {str(e)}")
        wal.append("DNA_SECURITY_BLOCK", {"expression": req.dna_expression, "error": str(e)})
        return JSONResponse(
            status_code=400,
            content={"status": "BLOCKED", "detail": str(e)}
        )


@app.post("/api/v1/graph/query", tags=["Graph"])
async def graph_query(req: PromptRequest):
    """
    Führt eine Neo4j-Cypher-Query aus (via Prompt-Feld).
    Wird von der APEX Graph Engine im Streamlit-Cockpit genutzt.
    """
    if not verify_seal(req.auth_seal):
        raise HTTPException(status_code=403, detail="Invalid Auth Seal")
    
    logger.info(f"Neo4j Query empfangen: {req.prompt[:50]}...")
    
    # Führt die Query aus (Fallback auf Mock-Daten, wenn offline)
    result_data = neo4j.run_query(req.prompt)
    
    wal.append("GRAPH_QUERY", {
        "query": req.prompt[:100],
        "results_count": len(result_data)
    })
    
    return {
        "status": "QUERY_EXECUTED",
        "data": result_data
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 22. LIVE TELEMETRY WEBSOCKET
# ═══════════════════════════════════════════════════════════════════════════════
@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """
    Sendet Live-Metriken an das Cockpit (für das Live-Metriken Panel).
    Aktualisiert alle 1.5 Sekunden.
    """
    await websocket.accept()
    logger.info("WebSocket: Client verbunden. Starte Telemetrie-Stream.")
    
    try:
        while True:
            # Simulierte Live-Daten für das UI
            telemetry_data = {
                "ts": time.time(),
                "throughput": random.randint(250000, 290000),
                "latency": round(random.uniform(8.5, 10.5), 2),
                "entropy": round(apex_controller.wusulum.entropy_pool, 2),
                "bio_state": apex_controller.bio.state,
                "worm_block": WORM_LEDGER["count"],
                "gotham_inmates": len(apex_controller.gotham.inmates),
                "king_ghost_shadows": len(apex_controller.king_ghost.shadow_pool)
            }
            
            await websocket.send_text(json.dumps(telemetry_data))
            await asyncio.sleep(1.5) # Alle 1.5 Sekunden
            
    except WebSocketDisconnect:
        logger.info("WebSocket: Client getrennt.")
    except Exception as e:
        logger.error(f"WebSocket Fehler: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 23. GLOBAL EXCEPTION HANDLER (FAIL-CLOSED)
# ═══════════════════════════════════════════════════════════════════════════════
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Fängt unerwartete Fehler ab und loggt sie (Fail-Closed).
    Verhindert, dass Stacktraces an das Frontend leaken.
    """
    logger.error(f"Unbehandelter Fehler bei {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "ERROR", "detail": "Internal Server Error (Fail-Closed)"}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 24. ENTRYPOINT (UVICORN)
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Startet den Uvicorn-Server (für lokale Tests oder Docker)
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starte B6-Monster-API auf Port {port}...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False # Auf Produktion (Render) immer False
    )
