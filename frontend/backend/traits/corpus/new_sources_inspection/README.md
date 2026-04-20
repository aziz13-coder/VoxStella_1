# Text Inspection Corpus

This directory contains cleaned Markdown books and chunked excerpts built from the raw extracted text corpus.

## Layout

- `normalized_books/`: full-book cleaned Markdown with page and heading anchors
- `guides/`: per-book scan guides with heading indexes and keyword anchors
- `chunks/`: per-book chunk files sized for agent inspection
- `catalog.json`: machine-readable summary of books and chunk coverage
- `chunk_index.jsonl`: one line per chunk for simple retrieval/search tooling

## Search

Use the helper script to query the chunk index:

`python scripts/search_text_inspection_corpus.py "ascendant ruler" --index "C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\new_sources_inspection\chunk_index.jsonl" --limit 5`

## Books

| Title | Source | Chunks | Characters | Guide | Notes |
| --- | --- | ---: | ---: | --- | --- |
| Ancient Astrology in Theory and Practice A Manual of -- Demetra George -- Auckland, New Zealand, 2022 -- Rubedo Press -- 9780473445393 -- cc0bd94229290713bff61ef3968b9c28 -- Anna's Archive | Ancient Astrology in Theory and Practice_ A Manual of -- Demetra George -- Auckland, New Zealand, 2022 -- Rubedo Press -- 9780473445393 -- cc0bd94229290713bff61ef3968b9c28 -- Anna's Archive.pdf | 224 | 1353935 | C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\new_sources_inspection\guides\Ancient_Astrology_in_Theory_and_Practice_A_Manual_of_--_Demetra_George_--_Auckland_Ne_d7110c0cb5.md |  |
| Compendium of Astrology (Rose Lineman, Jan Popelka) (z-library.sk, 1lib.sk, z-lib.sk) | Compendium of Astrology (Rose Lineman, Jan Popelka) (z-library.sk, 1lib.sk, z-lib.sk).pdf | 136 | 1006439 | C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\new_sources_inspection\guides\Compendium_of_Astrology_Rose_Lineman_Jan_Popelka_z-library.sk_1lib.sk_z-lib.sk.md |  |
| Person Centered Astrology (Dane Rudhyar) (z-library.sk, 1lib.sk, z-lib.sk) | Person Centered Astrology (Dane Rudhyar) (z-library.sk, 1lib.sk, z-lib.sk).pdf | 92 | 534696 | C:\Users\sabaa\Downloads\codexhorary\extracted_text_docs\new_sources_inspection\guides\Person_Centered_Astrology_Dane_Rudhyar_z-library.sk_1lib.sk_z-lib.sk.md |  |
