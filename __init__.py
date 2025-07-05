from collections import defaultdict
from typing import TypedDict, Optional, Dict, List
import csv
import os
import re

from aqt import mw
from aqt.qt import QAction
from aqt.utils import showInfo
from anki.notes import Note
from aqt.progress import ProgressManager

config = mw.addonManager.getConfig(__name__)
top_n_words = config.get("number_of_examples", 5)
max_word_frequency = config.get("example_frequency_cutoff", 100000)

class FrequencyEntry(TypedDict):
    term: str
    reading: str
    frequency: int
    kana_frequency: Optional[int]
    definitions: Optional[str]

FrequencyData = Dict[str, List[FrequencyEntry]]

KANJI_RE = re.compile(r'[\u4e00-\u9faf]')

def load_frequency_data() -> FrequencyData:
    addon_dir = os.path.dirname(__file__)
    csv_path = os.path.join(addon_dir, "data", "term_frequencies_with_definitions.csv")

    frequency_data = defaultdict(list)

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "term" not in row:
                continue
            try:
                row["frequency"] = int(row["frequency"])
                row["kana_frequency"] = int(row["kana_frequency"]) if row["kana_frequency"] else None
                row["definitions"] = row.get("definitions", "").strip()
            except ValueError:
                continue

            term = row["term"]
            frequency_data[term].append(row)

    return frequency_data


def load_kanji_summary() -> Dict[str, dict]:
    addon_dir = os.path.dirname(__file__)
    csv_path = os.path.join(addon_dir, "data", "kanji_summary.csv")
    kanji_info = {}

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            char = row.get("character", "")
            if not char:
                continue
            kanji_info[char] = {
                "onyomi": row.get("onyomi", "").strip(),
                "kunyomi": row.get("kunyomi", "").strip(),
                "jlpt": row.get("jlpt", "").strip(),
                "meaning": row.get("meaning", "").strip(),
                "frequency": row.get("frequency", "").strip(),
            }

    return kanji_info


def build_kanji_index(frequency_data: FrequencyData) -> Dict[str, List[FrequencyEntry]]:
    kanji_index = defaultdict(list)
    for term_entries in frequency_data.values():
        for entry in term_entries:
            for kanji in set(KANJI_RE.findall(entry["term"])):
                kanji_index[kanji].append(entry)

    for k in kanji_index:
        kanji_index[k].sort(key=lambda x: x["frequency"])

    return kanji_index


def build_ruby(term: str, reading: str) -> str:
    if not term or not reading:
        return f"{term} <span class='reading-fallback'>[{reading}]</span>"
    return f"<ruby>{term}<rt>{reading}</rt></ruby>"

def generate_kanji_details(
    kanji_chars,
    kanji_index,
    kanji_summary,
    top_n_words: int,
    max_word_freq: int
) -> str:
    popup_data = []

    for kanji in sorted(set(kanji_chars)):

        # if kanji == "県":
        #     print("✅ Found kanji '県'")
        #     for entry in kanji_index.get(kanji, []):
        #         print(entry["term"], entry["frequency"])


        summary = kanji_summary.get(kanji, {})

        all_matches = kanji_index.get(kanji, [])
        filtered = [
            entry for entry in all_matches
            if entry.get("frequency", float("inf")) <= max_word_freq
        ]

        matching_entries = sorted(filtered, key=lambda x: x.get("frequency", float("inf")))[:top_n_words]

        lines = []

        lines.append(f"<div class='kanji-popup-content' id='popup-{kanji}' style='display:none;'>")
        lines.append("<div class='popup-scroll'>")  # start scroll container

        lines.append(f"<h2>{kanji}</h2>")

        if summary:
            lines.append("<table>")

            def row(label, val):
                lines.append(f"<tr><td class='label'>{label}</td><td class='value'>{val}</td></tr>")

            # NEW ORDER: Meaning → Onyomi → Kunyomi → JLPT → Frequency
            if summary.get("meaning"):
                meanings = summary["meaning"].split(";")
                if meanings:
                    first = f"<span class='meaning-primary'>{meanings[0].strip()}</span>"
                    others = "; ".join(m.strip() for m in meanings[1:])
                    if others:
                        rest = f"<span class='meaning-secondary'>; {others}</span>"
                    else:
                        rest = ""
                    row("Meaning", first + rest)

            if summary.get("onyomi"):
                row("Onyomi", ", ".join(summary["onyomi"].split()))

            if summary.get("kunyomi"):
                row("Kunyomi", ", ".join(summary["kunyomi"].split()))

            if summary.get("jlpt"):
                row("JLPT", summary["jlpt"])

            if summary.get("frequency"):
                row("Frequency", summary["frequency"])

            lines.append("</table>")


        if matching_entries:
            lines.append("<hr class='word-separator'><ul>")
            
            for entry in matching_entries:
                term = entry["term"]
                ruby = build_ruby(term, entry.get("reading", ""))
                freq = entry.get("frequency", "N/A")
                defs = entry.get("definitions", "").strip()
                definition_html = f"<div class='definition'>{defs}</div>" if defs else ""

                # Extract kanji from term and add their meanings
                term_kanji = [k for k in term if KANJI_RE.match(k)]
                kanji_meaning_lines = []

                for k in term_kanji:
                    summary = kanji_summary.get(k)
                    if summary:
                        meaning = summary.get("meaning", "").strip()
                        if meaning:
                            kanji_meaning_lines.append(f"<li><strong>{k}</strong>: {meaning}</li>")

                kanji_details_html = ""
                if kanji_meaning_lines:
                    kanji_details_html = f"""
                    <details>
                        <summary>Kanji meanings</summary>
                        <ul>
                            {''.join(kanji_meaning_lines)}
                        </ul>
                    </details>
                    """

                lines.append(f"<li>{ruby} <small>({freq})</small>{definition_html}{kanji_details_html}</li>")
            
            lines.append("</ul>")

        lines.append("</div>")  # end popup-scroll
        lines.append("<div class='popup-footer'><button class='popup-close' onclick='hideKanjiPopup()'>Close</button></div>")

        lines.append("</div>")

        popup_data.append("".join(lines))

    return "\n".join(popup_data)




def process_japanese_deck():
    deck_name = "Mining"
    field_expression = "Expression"
    field_kanji_info = "KanjiInfo"

    mw.progress.start(label="Updating Kanji Info...", immediate=True)

    try:
        col = mw.col
        deck = col.decks.by_name(deck_name)

        if not deck:
            showInfo(f"Deck '{deck_name}' not found.")
            return

        frequency_data = load_frequency_data()
        kanji_summary = load_kanji_summary()
        kanji_index = build_kanji_index(frequency_data)

        nids = col.find_notes(f'deck:"{deck_name}"')
        total = len(nids)
        updated_count = 0

        for i, nid in enumerate(nids):
            mw.progress.update(value=i, max=total)
            note = col.get_note(nid)

            expr = note[field_expression] if field_expression in note else ""
            kanji_chars = KANJI_RE.findall(expr)
            if not kanji_chars:
                continue

            # Generate clickable kanji version of expression
            highlighted_expr = ""
            for char in expr:
                if KANJI_RE.match(char):
                    highlighted_expr += f"<span class='kanji-click' onclick='showKanjiPopup(\"{char}\")'>{char}</span>"
                else:
                    highlighted_expr += char

            # Generate kanji info popup blocks
            popup_html = generate_kanji_details(
                kanji_chars, kanji_index, kanji_summary, top_n_words, max_word_frequency
            )

            # Combine expression + hidden popups
            if field_kanji_info in note:
                note[field_kanji_info] = f"""
                <div class='kanji-popup'>
                <div class='expression'>{highlighted_expr}</div>
                <div class='kanji-popups'>{popup_html}</div>
                </div>
                """
                col.update_note(note)
                updated_count += 1


        showInfo(f"Updated {updated_count} notes with kanji frequency info.")
    finally:
        mw.progress.finish()



# Add menu item
action = QAction("Add Kanji Frequency Info", mw)
action.triggered.connect(process_japanese_deck)
mw.form.menuTools.addAction(action)
