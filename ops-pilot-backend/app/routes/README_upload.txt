POST /upload

Accepts multipart/form-data with field name `files`.

Example (curl):
curl -F "files=@./a.pdf" -F "files=@./b.pdf" http://localhost:8000/upload

Returns:
- 200: { ok: true, files: [ { filename, pages, size, saved: { path, uploaded_at } } ] }
- 400: { ok: false, errors: [ { filename, error } ] }

Notes:
- Rejects non-PDFs.
- Stores files under app/uploads/tmp temporarily.

