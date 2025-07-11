# Kanji Info Popup

- [Features](#features)
- [Setup](#Setup)
- [Usage](#usage)

## Features

- RTK Keyword
- Other meanings
- On- & kun-yomi
- JLPT lvl
- Kanji Frequency
- two top kanji koohii stories
- example words with frequency aswell as respective kanji keyword and meaning
- Kanji stroke order

<img src="https://github.com/alexander-kohler/kanjiinfo/blob/main/readme_gif.gif?raw=true" width=40%>

## Setup

- Add the contents from [CSS](https://github.com/alexander-kohler/kanjiinfo/blob/main/styles.css) to the styles template.
- Add the contents from [Script](https://github.com/alexander-kohler/kanjiinfo/blob/main/script.html) to the back card template.
- Add KanjiInfo Field.
- Add {{KanjiInfo}} to Back Card Template.
- To get the stroke order you need to have the Kanji Stroke Order Font in your collection.media

Change settings in config (Tools -> Add-ons -> kanjiinfo -> Config)

- "number_of_example_vocab": Number of example Vocab shown for each Kanji.
- "example_vocab_frequency_cutoff": The Frequency up to which example Vocab is included.
- "field_to_process": The field with the Kanji for which to generate the popup.
- "destination_field_name": The field where the popup HTML is written. Default: KanjiInfo.
- "deck_to_process": The Name of the Deck to generate popups for.

Restart Anki.

## Usage

Tools -> Add Kanji Popup Info
