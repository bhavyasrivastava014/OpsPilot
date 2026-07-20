# OpsPilot backend - TODO

- [ ] Add PyMuPDF extraction service (extract non-blank pages: page_number + text)
- [ ] Add new FastAPI route `POST /extract` that accepts multipart `files` and returns structured JSON
- [ ] Wire `/extract` router into `app/main.py`
- [ ] Add `pymupdf` dependency to `requirements.txt`
- [ ] Basic verification commands (curl) and quick sanity test

