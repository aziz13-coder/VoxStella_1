# Kazuko Hosoki Sources - English Acquisition Guide

Date: 2026-05-02

The Hosoki books are Japanese-language books. I did not find a local full-text source during the initial search. The practical path is to place scans/PDFs/e-books in a local folder and run the same private extraction pipeline used for the I Ching PDFs.

## Titles To Look For

### 1. 運命を読む六星占術入門

English working title: *Introduction to Six-Star Divination for Reading Destiny*

Author: 細木数子 / Kazuko Hosoki

Key metadata:

- Publisher: ごま書房
- Date: 1985-08
- Pages: 226
- ISBN: 4341030531

Useful links:

- CiNii: https://ci.nii.ac.jp/ncid/BN16011136
- Rakuten Books: https://books.rakuten.co.jp/rb/192618/

### 2. 六星占術による運命の読み方

English working title: *How to Read Destiny through Six-Star Divination*

Author: 細木数子 / Kazuko Hosoki

Key metadata:

- Publisher: ベストセラーズ
- Date: 1985-02
- Pages: 249
- ISBN: 9784584300572 / 4-584-30057-7

Useful links:

- NDL Search: https://ndlsearch.ndl.go.jp/books/R100000002-I000001733358
- Books.or.jp: https://www.books.or.jp/book-details/9784584300572
- Used-book listing: https://www.kosho.or.jp/products/catalog_detail.php?nh_id=1604350

### 3. 六星占術によるあなたの運命

English working title: *Your Destiny According to Six-Star Divination*

This is a series title with many yearly and star-type editions. Confirm the exact edition before adding it to the corpus.

Useful starting points:

- 2019 boxed set record: https://www.asukashinsha.co.jp/bookinfo/9784864106344.php
- 2020 renewed series example: https://www.asukashinsha.co.jp/bookinfo/9784864107068.php
- 2024 boxed set record: https://www.hanmoto.com/bd/isbn/9784069497070

### 4. 六星占術による相性運入門

English working title: *Introduction to Compatibility Fortune through Six-Star Divination*

Author: 細木数子 / Kazuko Hosoki

Key metadata:

- Publisher: ごま書房
- Date: 1982-10
- Pages: 234
- ISBN: 9784341030209

Useful links:

- NDL Search: https://ndlsearch.ndl.go.jp/books/R100000002-I000001590886
- Rakuten Books: https://books.rakuten.co.jp/rb/97110/

## Japanese Terms

- 六星占術: Six-Star Divination
- 運命: destiny / fate
- 運命星: destiny star
- 大殺界: major bad-luck period / great killing-boundary period
- 相性: compatibility
- 相性運: compatibility fortune / compatibility timing
- 入門: introduction / beginner guide
- 読み方: method of reading / how to read

## Local Processing Workflow

Once a Japanese PDF or scan is available:

1. Put it under a local folder such as:
   `C:/Users/sabaa/Desktop/astrolgy books/iching/hosoki/`
2. Run:
   `python tools/iching_corpus/extract_private_pdf_text.py --out output/iching_private_corpus "PATH_TO_HOSOKI_PDF"`
3. If the PDF is image-only, run:
   `python tools/iching_corpus/ocr_image_only_pdf_text.py "PATH_TO_HOSOKI_PDF"`
4. After extraction/OCR, create English summaries and implementation notes rather than committing full translated book text into source directories.
