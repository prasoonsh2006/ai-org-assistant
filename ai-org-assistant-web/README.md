# AI Organization Assistant — Web Conversion

This conversion separates the original Streamlit prototype into:

- `backend/` — FastAPI API and reusable Python AI services
- `frontend/` — React + Vite + Tailwind-style dashboard shell
- `legacy/` — the original uploaded Streamlit project, preserved while services are migrated

## Run backend
```bash
cd backend
python -m venv .venv
# activate it
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Run frontend
```bash
cd frontend
npm install
npm run dev
```

The frontend expects `http://localhost:8000`.


## Added developer features
- Multi Decoder: Base64, URL, HTML entities, Hex, Unicode escapes, ROT13 and JSON candidates
- Developer Tools hub
- JSON formatter/validator entry point
- Base64 tools entry point
- JWT inspector entry point
- Regex tester entry point
- Timestamp converter entry point
- Hash generator entry point
- AI code assistant entry point

The tool hub is intentionally modular so additional decoders and AI coding agents can be added without changing the main chat architecture.
