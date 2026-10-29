# eselsbruecke.py
"""
Die Eselsbrücken-Registry.
Verbindet alte Hashes mit Mnemonics und Payload-Code.
Die KI nutzt diese Brücken, um Wissen zu navigieren.
"""
import csv
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

REGISTRY_PATH = Path(__file__).parent / "eselsbruecken_registry.csv"

class Eselsbruecke:
    """Eine einzelne Eselsbrücke (ein Safe Point)."""
    def __init__(self, row: dict):
        self.id = row.get("ID", "")
        self.alter_hash = row.get("Alter_Hash", "")
        self.mnemonic = row.get("Mnemonic_Key", "")
        self.payload_type = row.get("Payload_Type", "")
        self.payload_code = row.get("Payload_Code", "")
        self.txt_output = row.get("TXT_Output", "")
        self.farbcode = row.get("Farbcode", "#FFFFFF")
        self.ring = row.get("Ring", "Ring 0")
        self.postmortem = row.get("Postmortem_Hash", "-")

    def to_dict(self) -> dict:
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
        """Lädt die CSV. Gibt die Anzahl der geladenen Eselsbrücken zurück."""
        if not REGISTRY_PATH.exists():
            return 0

        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                bruecke = Eselsbruecke(row)
                if bruecke.alter_hash:
                    self.bruecken[bruecke.alter_hash] = bruecke
                if bruecke.mnemonic:
                    self.by_mnemonic[bruecke.mnemonic] = bruecke

        return len(self.bruecken)

    def finde_hash(self, hash_prefix: str) -> Optional[Eselsbruecke]:
        """Findet eine Eselsbrücke über den Hash (auch Teiltreffer)."""
        for h, bruecke in self.bruecken.items():
            if h.startswith(hash_prefix) or h == hash_prefix:
                return bruecke
        return None

    def finde_mnemonic(self, mnemonic: str) -> Optional[Eselsbruecke]:
        """Findet eine Eselsbrücke über den Mnemonic-Key."""
        return self.by_mnemonic.get(mnemonic)

    def alle(self) -> list:
        """Gibt alle Eselsbrücken zurück."""
        return [b.to_dict() for b in self.bruecken.values()]


# Singleton für den Import in main.py
register = EselsbrueckenRegister()
