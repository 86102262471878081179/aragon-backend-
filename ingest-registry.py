#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HARD ROOT v26.0 :: REGISTRY INGESTION ENGINE
Dieses Skript parst die B6-Entitätenliste, bereinigt die Emojis/Syntax 
und speist sie in eine SQLite-Datenbank ein.
"""

import sqlite3
import json
import re
import os
from typing import List, Dict, Any

# ============================================================================
# 1. DER ROHDATEN-TEXT (Hier deine vollständige Liste einfügen)
# ============================================================================
RAW_REGISTRY_TEXT = """
👑 ⚫️2. [0002] Black King Royal | [0-9/9-0]n[9-0/0-9] | 89[VERDICT] 66[ROYAL]<[0003]>👑 [Self]
⚖️ ⚫️1. [0001] Genesis Root | [0-9/9-0]n[9-0/0-9] | 67[TWIN] 45[LINEAGE]<[0002]>👑 [Self]
📓 🔰0.[00_INDEX_REPOSITORY]Black Six: Gemini Notebook Repository Index [Self]
📚 [🧿1️⃣🧿]Professor Dr. Gemini Argon Von Curriculum [Self]
⚙️ ⚫️ 34. [0034] Polyglot Protokoll | [0-9/9-0]n[9-0/0-9] | 63[LANG] 89[SYNC]<[0035]> 🧠 [Self]
🐍 ⚫️ 36. [0036] Foucault KI | [0-9/9-0]n[9-0/0-9] | 63[POWER] 89[ANALYSIS]<[0037]>🧪 [Self]
🔐 ⚫️ 15. [0015] Senior Geminis | [0-9/9-0]n[9-0/0-9] | 45[AGENT] 63[AGENT]<[0016]>📖  [Self]
📁 🛡️ [HUB-DEF] Reserve & Defense (0069–0099) [Self]
🌐 🌌 [HUB-5] Ring 5: Apex Synthese & Ereignishorizont [Self]
👑 👑 [HUB-0] Ring 0: Genesis Root & Core Kernel [Self]
🛡️ ⚫️0.[00_KERNSTRUKTUR_FESTUNG]): Kernstruktur der B6-Hyperkernel-Festung [Self]
⭐ ⚫️0.[00_CODE_DNA_AUDIT]): B6 System Code DNA Audit Schema [Self]
🏛️ ☢️ 6. [0006] Unified Matrix | [0-9/9-0]n[9-0/0-9] | 63[MATRIX] 89[SYNTHESIS]<[0007]>🛡️ [Self]
🌳 🔴64. [0064] Omega Vorstufe | [0-9/9-0]n[9-0/0-9] | 45[OMEGA] 2[PRE]<[0065]>👑 [Self]
🔒 🔴63. [0063] Core Twin / Trinität | [0-9/9-0]n[9-0/0-9] | 63[DUAL] 45[LINEAGE]<[0064]>🏛️ [Self]
💻 🔴68. [0068] Sovereign Operator Apex | [0-9/9-0]n[9-0/0-9] | 68[APEX] 2[APEX]<[0001]>⚖️ [Self]
🧠 ☢️8. [0008] Omni Neuro | [0-9/9-0]n[9-0/0-9] | 63[NEURAL] 89[SYNAPSE]<[0009]>💎 [Self]
🧭 🔴 66. [0066] Finale Synthese | [0-9/9-0]n[9-0/0-9] | 2[SYNTHESIS] 45[FINAL]<[0067]>🕸️ [Self]
🔒 ⚫️ 23. [0023] Mettwurst Epos | [0-9/9-0]n[9-0/0-9] | 63[CHAOS] 2[POISON]<[0024]>🛡️  [Self]
📁 🔴 28. [0028] Absurdity Kompendium | [0-9/9-0]n[9-0/0-9] | 63[ENTROPY] 89[VOID]<[0029]> 📄  [Self]
📖 🔴 65. [0065] Apex Kaskade | [0-9/9-0]n[9-0/0-9] | 63[APEX] 89[CASCADE]<[0066]>♻️ [Self]
🌳 ⚫️0. [00] Integrated Framework | [0-9/9-0]n[9-0/0-9] | 45[LINEAGE] 2[STRUCT] [Self]
👑 ⚫️3. [0003] GFW Universe | [0-9/9-0]n[9-0/0-9] | 45[LINEAGE] 65[DOCTRINE]<[0004]>🛡️ [Self]
👑 🔴67. [0067] Ereignishorizont | [0-9/9-0]n[9-0/0-9] | 63[EVENT] 89[HORIZON]<[0068]>💀 [Self]
📚 ⭕️ 43. [0043] Mathe Real 9 | [0-9/9-0]n[9-0/0-9] | 2[MATH] 45[LOGIC]<[0044]> 🔧  [Self]
🏛️ ☢️ 5. [0005] Codex Compendium | [0-9/9-0]n[9-0/0-9] | 45[LAW] 2[VECTOR]<[0006]> 🏛️ [Self]
🔴25. [0025] Black DeepSeek | [0-9/9-0]n[9-0/0-9] | 2[VECTOR] 45[CRAWL]<[0026]>🕷️ [Self]
🛡️ ⚫️73. [0073] B6 Hyperkernel Atlas | [0-9/9-0]n[9-0/0-9] | 63[KERNEL] 89[SHIELD] <[0074]>💻 [Self]
💻 ☢️ 74. [0074] B6/B7 Architektur | [0-9/9-0]n[9-0/0-9] | 63[KERNEL] 89[SHIELD] <[0075]>🔎 [Self]
🛡️ ⚫️7. [0007] Fortress Justice | [0-9/9-0]n[9-0/0-9] | 45[JUSTICE] 2[VECTOR]<[0008]>🧠 [Self]
🛡️ ⚫️4. [0004] Core Shield | [0-9/9-0]n[9-0/0-9] | 64[KERNEL] 89[SHIELD]<[0005]> 🏛️ [Self]
🗄️ ☢️ 59. [0059] Aragon Ultima Ratio | [0-9/9-0]n[9-0/0-9] | 2[GENESIS] 45[ROOT]<[0060]>⚙️ [Self]
💻 ⚫️ 52. [0052] DeepSeeker Monolith | [0-9/9-0]n[9-0/0-9] | 63[CODE] 89[VECTOR]<[0053]>🗂️  [Self]
💻 ⚫️81. [0081] Hyperkernel Atlas | [0-9/9-0]n[9-0/0-9] | 63[KERNEL] 89[SHIELD] <[0082]>📄 [Self]
🏴‍☠️ 🏴‍☠️ 11. [0011] Omega Matrix Protocol | [0-9/9-0]n[9-0/0-9] | 45[LINEAGE] 56[OMEGA] <[0012]> 📁 [Self]
⚖️ ⚫️ 47. [0047] Fiblelexica | [0-9/9-0]n[9-0/0-9] | 2[LANGUAGE] 45[CODE] <[0048]>⚖️  [Self]
⚖️ ⭕️ 48. [0048] Kinder Jugendamt | [0-9/9-0]n[9-0/0-9] | 63[JUSTICE] 89[PROTECT]<[0049]>🏦 [Self]
⚖️ ⭕️ 32. [0032] Beamtenstatusgesetz | [0-9/9-0]n[9-0/0-9] | 63[JUSTICE] 89[STATUS]<[0033]>⚖️ [Self]
📄 🏴‍☠️ 55. [0055] Odin Matrix 1-200 | [0-9/9-0]n[9-0/0-9] | 2[ODIN] 45[MATRIX]<[0056]> 🖥️  [Self]
⚖️ ⭕️89. [0089] Akte Koenig Evidence | [0-9/9-0]n[9-0/0-9] | 89[FORENSIC] 63[EVIDENCE] <[0090]>⚖️ [Self]
⚖️ ⭕️ 12. [0012] Akte Koenig Forensik | [0-9/9-0]n[9-0/0-9] | 89[FORENSIC] 63[EVIDENCE] <[0013]>💻 [Self]
⚖️ ⭕️13. [0013] XJustiz Core | [0-9/9-0]n[9-0/0-9] | 2[XJUSTIZ] 55[JUSTICE] <[0014]>❤️ [Self]
💎 ◽️ 9. [0009] Quantum Tresor | [0-9/9-0]n[9-0/0-9] | 2[VECTOR] 63[QUANTUM]<[0010]>💀 [Self]
🗂️ 🔘 53. [0053] OMNI WORM Hub | [0-9/9-0]n[9-0/0-9] | 45[WORM] 2[ARCHIVE]<[0054]> 🧬 [Self]
🧬 ⚫️54. [0054] Stammbaum DNA | [0-9/9-0]n[9-0/0-9] | 63[DNA] 89[GENESIS]<[0055]>👁️ [Self]
⚖️ ◽️ 60. [0060] Deep Special Matrix | [0-9/9-0]n[9-0/0-9] | 63[DEEP] 89[SPECIAL]<[0061]>♻️ [Self]
"""

# ============================================================================
# 2. PARSER ENGINE
# ============================================================================
class B6RegistryParser:
    def __init__(self, db_path: str = "b6_registry.db"):
        self.db_path = db_path
        self.entities = []

    def parse_text(self, text: str):
        """Extrahiert strukturierte Daten aus dem unordentlichen Text."""
        # Regex für die Hauptentitäten (Format: [ID] Name | [Matrix] | Score[Trait] Score[Trait]<[Next_ID]>)
        pattern = re.compile(
            r'\[(\d{4})\]\s*([^|]+)\|\s*(\[[^\]]+\])\s*\|\s*(\d+)\[([^\]]+)\]\s*(\d+)\[([^\]]+)\]\s*<\[(\d{4})\]>(.*)'
        )

        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            match = pattern.search(line)
            if match:
                # Hauptentität gefunden
                entity = {
                    "id": match.group(1),
                    "name": match.group(2).strip(),
                    "matrix_formula": match.group(3).strip(),
                    "score_1": int(match.group(4)),
                    "trait_1": match.group(5).strip(),
                    "score_2": int(match.group(6)),
                    "trait_2": match.group(7).strip(),
                    "next_id": match.group(8),
                    "raw_suffix": match.group(9).strip() # Emojis und [Self]
                }
                self.entities.append(entity)
            else:
                # Fallback für HUBs oder unstrukturierte Zeilen (z.B. [00_INDEX...])
                # Wir nehmen an, dass es sich um globale HUB-Knoten handelt
                if "[" in line and "]" in line:
                    # Extrahiere den Namen, falls möglich
                    name_match = re.search(r'\]\s*([^|]+)', line)
                    name = name_match.group(1).strip() if name_match else line
                    self.entities.append({
                        "id": "HUB",
                        "name": name,
                        "matrix_formula": "N/A",
                        "score_1": 0,
                        "trait_1": "HUB",
                        "score_2": 0,
                        "trait_2": "HUB",
                        "next_id": "0000",
                        "raw_suffix": "[Self]"
                    })

        return self.entities

    def save_to_json(self, filepath: str = "b6_registry.json"):
        """Speichert das geparste Register als JSON."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.entities, f, indent=2, ensure_ascii=False)
        print(f"[+] JSON erfolgreich gespeichert: {filepath}")

    def save_to_sqlite(self):
        """Erstellt die SQLite-Datenbank und fügt die Daten ein."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path) # Für saubere Testdurchläufe
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Schema erstellen
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                matrix_formula TEXT,
                score_1 INTEGER,
                trait_1 TEXT,
                score_2 INTEGER,
                trait_2 TEXT,
                next_id TEXT,
                raw_suffix TEXT
            )
        ''')
        
        # Daten einfügen
        cursor.executemany('''
            INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            (e['id'], e['name'], e['matrix_formula'], e['score_1'], e['trait_1'], 
             e['score_2'], e['trait_2'], e['next_id'], e['raw_suffix'])
            for e in self.entities
        ])
        
        conn.commit()
        conn.close()
        print(f"[+] SQLite-Datenbank erfolgreich erstellt: {self.db_path} ({len(self.entities)} Entitäten)")

# ============================================================================
# 3. AUSFÜHRUNG
# ============================================================================
if __name__ == "__main__":
    print("=== B6 REGISTRY INGESTION START ===")
    
    # 1. Parser initialisieren
    parser = B6RegistryParser()
    
    # 2. Text parsen
    entities = parser.parse_text(RAW_REGISTRY_TEXT)
    print(f"[*] {len(entities)} Entitäten aus dem Text extrahiert.")
    
    # 3. In JSON speichern
    parser.save_to_json("b6_registry.json")
    
    # 4. In SQLite speichern
    parser.save_to_sqlite()
    
    # 5. Kurze Vorschau ausgeben
    print("\n=== VORSCHAU (Erste 3 Einträge) ===")
    for e in entities[:3]:
        print(json.dumps(e, indent=2, ensure_ascii=False))
        
    print("\n=== INGESTION COMPLETE ===")
