# Deployment Notes

Local command:

```bash
cp .env.example .env
docker compose up --build
```

Image-based PDF parsing requires the backend image built from
`backend/Dockerfile`, because that image installs the system `tesseract-ocr`
engine used by pytesseract. Rebuild the backend container after OCR dependency
changes:

```bash
docker compose build backend
docker compose up backend
```

Later deployment can use Vercel for frontend and Render/Railway/Fly.io for backend and PostgreSQL.
