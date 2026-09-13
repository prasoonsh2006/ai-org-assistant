# AI Data Assistant — Two-Mode Platform

A website with **two modes**:

1. **🌐 Public / General Use** — a free ChatGPT/Gemini-style assistant. Sign
   in with Google or continue as a guest. Chat, **generate images from text**,
   analyze uploaded images, summarize or ask questions about any uploaded
   PDF/DOCX/TXT.
2. **🏢 Organization Portal** — organizations register, an **admin must
   approve** them, then they can upload documents/spreadsheets **or connect
   their own live database** and run AI-powered chat, summaries, and
   natural-language analytics — including **plain-English data updates**
   (e.g. *"update Rahul's marks to 30"*), with a mandatory preview-and-confirm
   step before anything is actually changed.

Built with Python + SQL, entirely on free-tier tools.

---

## Architecture

```
Home.py                              <- landing page (choose a mode)
pages/
  1_Public_Assistant.py              <- Google/guest login, chat, image & doc analysis
  2_Organization_Login.py            <- org register (-> pending) / login
  3_Organization_Dashboard.py        <- upload files / connect DB, RAG chat, summarize, analytics
  4_Admin_Panel.py                   <- approve/reject pending organizations

database.py        SQLite schema: organizations (with approval status),
                    users, public_users, documents, datasets, db_connections, chat_history
auth.py             org registration/login + approval gate, guest & Google public login
google_auth.py      real Google Sign-In wrapper (falls back to guest if unconfigured)
ingestion.py        PDF/DOCX/TXT/CSV -> text -> chunks
rag.py              sentence-transformers embeddings + ChromaDB (org-isolated)
llm.py              Gemini/Groq calls: general chat, image generation, image analysis,
                    RAG answers, summaries, text-to-SQL (read AND write)
text_to_sql.py       uploaded CSV/Excel -> SQLite table -> safe NL-to-SQL (read + write)
external_db.py       connect to an org's OWN Postgres/MySQL/SQLite DB -> safe NL-to-SQL (read + write)
ui.py                shared CSS/styling for a clean, consistent look
```

### Key design points (good for your report/viva)

- **Two isolated identity systems**: `public_users` (Google/guest, no
  password, no approval — open access) vs `organizations` + `users`
  (password-based, gated by an approval workflow). This mirrors how real
  platforms separate a free consumer tier from a vetted business tier.
- **Approval workflow**: every new organization starts `status='pending'`.
  `auth.login()` explicitly blocks login for anything not `'approved'`. Only
  the Admin Panel (password-gated) can change that status.
- **Multi-tenancy**: every document, embedding, dataset, and DB connection is
  tagged with `org_id` and filtered by it — Organization A can never see
  Organization B's data.
- **Two ways to bring analytics data**: upload a file (goes into a private
  SQLite table) **or** connect a live external database via SQLAlchemy —
  showing you understand both static and live data integration.
- **RAG vs. general chat**: the org dashboard grounds answers strictly in
  the org's own documents (and says so when it can't find something); the
  public assistant is open-domain, like ChatGPT/Gemini.
- **Natural-language data updates, done safely**: the "✏️ Update Data" page
  (org admins only) is a three-step flow, never a one-click action:
  1. The LLM converts your instruction into a single `UPDATE` or `INSERT`
     statement (never `DELETE`/`DROP`/`ALTER`/`TRUNCATE` — blocked both in
     the prompt AND again by a hardcoded check at execution time).
  2. Before anything runs, the app shows you the **exact rows that will
     change** (by re-running the same `WHERE` clause as a `SELECT`).
  3. Only after you click **"✅ Confirm and Apply Change"** does it execute.
  An `UPDATE` with no `WHERE` clause is refused outright, so a vague
  instruction can never silently overwrite an entire table.
- **Image generation vs. image understanding are separate LLM calls** —
  `llm.generate_image()` (text → picture) and `llm.analyze_image()`
  (picture → text) use the same Gemini image model but in opposite
  directions; keeping them as separate functions makes each easy to reason
  about and swap out independently.

---

## Setup

### 1. Install dependencies

```bash
cd ai-org-assistant
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

> If `pandas` fails to build from source on Windows, you likely have a very
> new Python version without prebuilt wheels yet — either wait for pip to
> retry with the loosened `>=` version (already set in requirements.txt), or
> install Python 3.12 side-by-side and recreate the venv with `py -3.12 -m venv venv`.

### 2. Set up your `.env` file

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Open `.env` and fill in:
```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_from_https://aistudio.google.com/apikey
ADMIN_PASSWORD=pick_any_password_here
```

`ADMIN_PASSWORD` is what you'll type into the Admin Panel to approve
organizations — pick anything, it's just for your own local demo/grading.

### 3. (Optional) Set up real Google Sign-In for the public mode

If you skip this, the public mode still works fully via **"Continue as
Guest"** — this step is only needed if you want the actual Google login
button.

1. Go to https://console.cloud.google.com/ → create a project.
2. **APIs & Services → OAuth consent screen** → set it up as "External",
   fill required fields, add your own email as a test user.
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   → Application type: **Web application**.
4. Under "Authorized redirect URIs" add:
   ```
   http://localhost:8501
   ```
5. Download the JSON, rename it to `google_credentials.json`, and place it
   in the `ai-org-assistant` folder (same level as `Home.py`).
6. Restart the app — the Google login button will now appear automatically
   on the Public Assistant page.

### 4. Run the app

```bash
streamlit run Home.py
```

Opens at `http://localhost:8501`. Note it's `Home.py` now (not `app.py`) —
Streamlit automatically detects the `pages/` folder and builds the sidebar
navigation for you.

---

## Using the app

### As a general/public user
1. From the landing page, click **"Go to Public Assistant"**.
2. Sign in with Google, or type a name and click **Continue as Guest**.
3. Use the **Chat**, **Generate Image**, **Analyze Image**, or
   **Analyze Document** tabs.

### As an organization
1. From the landing page, click **"Go to Organization Portal"**.
2. Register a new organization (you become its admin) — status is
   **pending**.
3. Tell your admin (yourself, in this demo) to open the **Admin Panel**
   page from the sidebar, log in with `ADMIN_PASSWORD`, and click
   **✅ Approve** next to your organization.
4. Go back to the Organization Portal and log in normally.
5. In the dashboard: **Upload Data** (documents/spreadsheets) or
   **Connect Database** (point at your own Postgres/MySQL/SQLite).
6. Use **Chat**, **Summarize**, or **Analytics** (read-only questions) as
   before.
7. Use **✏️ Update Data** (admins only — visible in the sidebar) to make
   actual changes in plain English:
   - Example: type *"update Rahul's marks to 30"* → it generates
     `UPDATE students SET marks = 30 WHERE name = 'Rahul'` → shows you
     exactly which row(s) match → you click **Confirm and Apply Change**
     to actually run it. Nothing is written until you confirm.
   - Works the same way whether the data came from an uploaded file or a
     connected database.

---

## Security notes to mention in your report

- Passwords are salted SHA-256 (fine for a demo; use bcrypt/argon2 via
  `passlib` for production).
- External DB connection strings are stored in plain text in SQLite for
  simplicity — a production version would encrypt them at rest and enforce
  a read-only DB user.
- Read-only analytics only ever executes `SELECT` statements and blocks
  dangerous keywords before running anything.
- Write access ("Update Data") is restricted to org **admins** only
  (checked via `user["role"]`), generates only `UPDATE`/`INSERT` (never
  `DELETE`/`DROP`/`ALTER`/`TRUNCATE`), refuses any `UPDATE` without a
  `WHERE` clause, and always requires a human to review a preview and click
  confirm before anything is committed.
- The Admin Panel is gated by a single shared password — a real product
  would use per-admin accounts with proper auth.
- Image generation calls a **preview/experimental** Gemini model — it can
  occasionally decline a prompt or return text instead of an image; the UI
  surfaces that as an error message rather than crashing.

## Possible extensions

- Per-document access control within an organization (not just per-org).
- Email notification to an org when its registration is approved/rejected.
- Multiple admins with an `is_admin` flag on the `users` table instead of a
  shared password.
- Swap SQLite → PostgreSQL for the app's own metadata store to show
  awareness of production-scale choices.
