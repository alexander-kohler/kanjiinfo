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
top_n_words = config.get("number_of_example_vocab", 5)
max_word_frequency = config.get("example_vocab_frequency_cutoff", 100000)
expressionFieldName = config.get("field_to_process", "Expression")
destinationFieldName = config.get("destination_field_name", "KanjiInfo")
deckToProcess = config.get("deck_to_process", "Mining")


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
    csv_path = os.path.join(addon_dir, "data", "kanji_summary_stories.csv")
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
                "keyword": row.get("keyword", "").strip(),
                "story1": row.get("story1", "").strip(),
                "story2": row.get("story2", "").strip(),
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

def format_story(label: str, content: str, story_id: str) -> str:
    return f"""
    <div class='story-container'>
        <div class='story-header' onclick="toggleStory('{story_id}')">
            <span class='story-toggle' id='toggle-{story_id}'>[+]</span>
        </div>
        <div id='{story_id}' class='story-body hidden'>{content}</div>
    </div>
    """
#  <span class='story-label'>{label}</span>


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

        lines.append(f"""<h2 onclick="showLargePopup(this, '{kanji}')">{kanji}</h2>""")
        lines.append(f"""<div id="stroke-order-popup-{kanji}" class="stroke-order-popup" onclick="this.style.display='none'"></div>""")


        if summary:
            lines.append("<table>")

            def appendRow(label, val):
                lines.append(f"<tr><td class='label'>{label}</td><td class='value'>{val}</td></tr>")

            # NEW ORDER: Meaning → Onyomi → Kunyomi → JLPT → Frequency

            if summary.get("keyword"):
                keyword = summary["keyword"]
                appendRow("Keyword", f"<span class='meaning-primary'>{keyword.strip()}</span>")

            if summary.get("meaning"):
                appendRow("Meaning" , summary["meaning"])

            if summary.get("onyomi"):
                appendRow("Onyomi", ", ".join(summary["onyomi"].split()))

            if summary.get("kunyomi"):
                appendRow("Kunyomi", ", ".join(summary["kunyomi"].split()))

            if summary.get("jlpt"):
                appendRow("JLPT", summary["jlpt"])

            if summary.get("frequency"):
                appendRow("Frequency", summary["frequency"])

            if summary.get("story1"):
                appendRow("Story 1", format_story("Story 1", summary["story1"], f"story1-{kanji}"))

            if summary.get("story2"):
                appendRow("Story 2", format_story("Story 2", summary["story2"], f"story2-{kanji}"))



            lines.append("</table>")


        if matching_entries:
            lines.append("<hr class='word-separator'><ul>")
            
            for i, entry in enumerate(matching_entries):
                term = entry["term"]
                ruby = build_ruby(term, entry.get("reading", ""))
                freq = entry.get("frequency", "N/A")
                defs = entry.get("definitions", "").strip()
                definition_html = f"<span class='kanji-popup-definition'>{defs}</span>" if defs else ""

                # Extract kanji from term and add their meanings
                term_kanji = [k for k in term if KANJI_RE.match(k)]
                kanji_meaning_lines = []

                for k in term_kanji:
                    summary = kanji_summary.get(k)
                    if summary:
                        meaning = summary.get("meaning", "").strip()
                        keyword = summary.get("keyword", "").strip()
                        if keyword:
                            kanji_meaning_lines.append(f"""<li><strong>{k}</strong> {keyword}<span class="kanji-details-meaning">; {meaning}</span></li>""")

                kanji_details_html = ""
                if kanji_meaning_lines:
                    details_id = f"details-{term}-{i}"
                    kanji_details_html = f"""
                    <span class="kanji-details-toggle" id="toggle-{details_id}" onclick="toggleKanjiDetails('{details_id}')">[+]</span>
                    <div id="{details_id}" class="kanji-details hidden">
                        <ul>
                            {''.join(kanji_meaning_lines)}
                        </ul>
                    </div>
                    """

                # Now insert the [+] AFTER the frequency
                lines.append(f"""<li>{ruby} {definition_html}<small>({freq})</small> {kanji_details_html}</li>""")

            
            lines.append("</ul>")

        lines.append("</div>")  # end popup-scroll
        lines.append("<div class='popup-footer'><button class='popup-close' onclick='hideKanjiPopup()'>Close</button></div>")

        lines.append("</div>")

        popup_data.append("".join(lines))

    return "\n".join(popup_data)




def process_japanese_deck():
    deck_name = deckToProcess
    field_expression = expressionFieldName
    field_kanji_info = destinationFieldName

    frequency_data = load_frequency_data()
    kanji_summary = load_kanji_summary()
    kanji_index = build_kanji_index(frequency_data)

    col = mw.col
    deck = col.decks.by_name(deck_name)

    if not deck:
        showInfo(f"Deck '{deck_name}' not found.")
        return

    nids = col.find_notes(f'deck:"{deck_name}"')
    total = len(nids)
    updated_count = 0

    progress = ProgressManager(mw)
    progress.start(label="Updating Kanji Info...", max=total)

    try:
        for i, nid in enumerate(nids):
            progress.update(value=i)
            note = col.get_note(nid)

            expr = note[field_expression] if field_expression in note else ""
            kanji_chars = KANJI_RE.findall(expr)
            if not kanji_chars:
                continue

            highlighted_expr = ""
            for char in expr:
                if KANJI_RE.match(char):
                    highlighted_expr += f"<span class='kanji-click' onclick='showKanjiPopup(\"{char}\")'>{char}</span>"
                else:
                    highlighted_expr += char

            popup_html = generate_kanji_details(
                kanji_chars, kanji_index, kanji_summary, top_n_words, max_word_frequency
            )

            if field_kanji_info in note:
                note[field_kanji_info] = f"""
                <div class='kanji-popup'>
                <div class='expression'>{highlighted_expr}</div>
                <div class='kanji-popups'>{popup_html}</div>
                </div>
                """
                col.update_note(note)
                updated_count += 1
    finally:
        progress.finish()

    showInfo(f"Updated {updated_count} notes with kanji popup info.")



# Add menu item
action = QAction("Add Kanji Popup Info", mw)
action.triggered.connect(process_japanese_deck)
mw.form.menuTools.addAction(action)
