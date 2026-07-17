# Chinese Astrology Source Audit

Date: 2026-05-11

Scope: compared the local source folder `C:/Users/sabaa/Desktop/astrolgy books/iching` with the repository's private converted corpus notes. Large extracted and OCR outputs remain under gitignored `output/` folders.

## Corpus Comparison

| Source | Format | External file | Native private corpus | OCR private corpus | Feature relevance |
|---|---:|---:|---:|---:|---|
| I Ching, Kerson Huang and Rosemary Huang | PDF | Present | 202 / 210 pages with text | Not needed | I Ching casting terminology, hexagram reading structure |
| Legacy of the Luoshu, Frank J. Swetz | PDF | Present | 215 / 229 pages with text | Not needed | Luoshu, magic-square, and nine-palace background |
| Beginners Guide to Reading Their Destiny Code, Joey Yap | PDF | Present | 0 / 58 pages with text | 58 / 58 pages OCR, avg confidence 0.866 | Introductory BaZi / Destiny Code workflow |
| Ba Zi - The Four Pillars of Destiny, Serge Augier | PDF | Present | 85 / 87 pages with text | Not needed | BaZi fundamentals and Four Pillars framing |
| Bazi - The Destiny Code Book 1, Joey Yap | PDF | Present | 312 / 316 pages with text | Not needed | Strongest first-pass BaZi workflow source |
| BaZi - The Destiny Code Revealed Book 2, Joey Yap | PDF | Present | 328 / 332 pages with text | Not needed | Advanced BaZi relationships, interactions, and luck-cycle topics |
| Chinese Astrology, Kay Tom | EPUB | Present | 20 / 20 sections with text | Not applicable | Plain-English Chinese astrology framing and zodiac UX |
| The Chinese Fortune Telling System: BaZi Method, G L Golding | PDF | Present | 0 / 82 pages with text | 82 / 82 pages OCR, avg confidence 0.848 | Compact BaZi method cross-check |

No additional files were found in the local `iching` folder beyond the eight sources already represented in `source_manifest.yml`.

## Conversion Work

The existing native text corpus at `output/iching_private_corpus/` already covered the five text-layer PDFs and the Kay Tom EPUB. Two image-only PDFs had placeholder outputs only:

- `Beginners Guide to Reading Their Destiny Code`
- `The Chinese Fortune Telling System: BaZi Method`

I added `tools/iching_corpus/ocr_image_only_pdf_text.py` and ran it against the local folder. It skipped PDFs with native text layers and wrote OCR output only for the two image-only PDFs under `output/iching_private_corpus_ocr/`.

The OCR output should be treated as research-grade only. It is useful for searching and feature planning, but any important interpretation should be checked against the page image or a cleaner source before becoming product copy.

## Topic Coverage Counts

These are keyword-hit counts over the private corpora, used only to orient feature planning:

| Source file | I Ching terms | BaZi/Four Pillars terms | Five Elements/Luoshu terms | Zodiac/general terms |
|---|---:|---:|---:|---:|
| bazi-the-destiny-code-revealed...md | 2193 | 1523 | 20 | 1940 |
| bazi-the-destiny-code-your-guide...md | 1173 | 576 | 81 | 942 |
| ba-zi-the-four-pillars-of-destiny.md | 525 | 286 | 28 | 412 |
| beginners-guide-to-reading-their-destiny-code.ocr.md | 53 | 21 | 2 | 33 |
| chinese-astrology.md | 107 | 23 | 13 | 630 |
| i-ching.md | 586 | 71 | 4 | 240 |
| legacy-of-the-luoshu...md | 395 | 81 | 1472 | 320 |
| the-chinese-fortune-telling-system-bazi-method.ocr.md | 74 | 120 | 8 | 85 |

Counts are broad because terms like yin, yang, line, branch, and zodiac animals occur in multiple systems. The useful signal is the relative concentration: Huang anchors I Ching, Swetz anchors Luoshu, and the Joey Yap plus Augier/Golding sources anchor BaZi.

## Product Implications

Do not combine I Ching and BaZi into one first feature. They share Chinese metaphysical vocabulary, but the workflows are different enough that a combined MVP would be harder to explain and test.

Recommended first slice: standalone I Ching Oracle.

- User enters or saves a question.
- App supports manual line entry and coin-toss simulation.
- Six lines are stored bottom-to-top.
- App derives primary hexagram, changing lines, and resulting hexagram.
- Interpretation text should be handled as a separate content-source decision.

Recommended second slice: BaZi research-preview module.

- User enters birth date/time/place.
- Backend derives Four Pillars with explicit timezone handling.
- UI shows Day Master, stems, branches, hidden stems, five elements, Ten Gods, interactions, and luck pillars.
- Keep this separate from I Ching until calculation rules and test fixtures are stable.

Recommended later slice: Luoshu / nine-palace education.

- Use Swetz as private orientation for a visual explainer or reference surface.
- Treat it as background/educational content, not required by the I Ching oracle MVP.

## Remaining Source Gaps

Kazuko Hosoki / Six-Star Divination remains bibliographic only. No local full-text source is present in the compared folder, so there is nothing to convert yet. If scans are added later, run native extraction first and then the OCR script for image-only PDFs.
