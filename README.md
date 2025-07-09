# Kanji Info Popup

[Features](#features)
[Setup](#Setup)
[Usage](#usage)

## Features

<img src="/readme_images/IMG_6671%202.PNG" width=50%>

## Setup

- Add the contents from [CSS](styles.css) to the styles template.
- Add the contents from [Script](script.html) to the back card template.
- Add KanjiInfo Field.
- Add {{KanjiInfo}} to Back Card Template.

Change settings in config (Tools -> Add-ons -> kanjiinfo -> Config)

- "number_of_example_vocab": Number of example Vocab shown for each Kanji.
- "example_vocab_frequency_cutoff": The Frequency up to which example Vocab is included.
- "field_to_process": The field with the Kanji for which to generate the popup.
- "destination_field_name": The field where the popup HTML is written. Default: KanjiInfo.
- "deck_to_process": The Name of the Deck to generate popups for.

Restart Anki.

## Usage

Tools -> Add Kanji Popup Info
