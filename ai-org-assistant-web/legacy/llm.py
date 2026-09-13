"""
Thin wrapper around the LLM provider(s).

Text (Gemini path): uses the modern `google-genai` SDK.
Text (Groq path): OpenAI-compatible chat completions, no vision/image-gen.
Image understanding + image GENERATION always use Gemini
(model: gemini-2.5-flash-image), regardless of which provider is set for
plain text - so set GEMINI_API_KEY even if LLM_PROVIDER=groq, if you want
those two features.
"""

import io
from config import LLM_PROVIDER, GEMINI_API_KEY, GROQ_API_KEY

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set. See config.py / README.md.")
        from google import genai
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def _call_gemini(prompt: str, max_tokens: int = 1024) -> str:
    from google.genai import types
    client = _get_gemini_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=max_tokens, temperature=0.4),
    )
    return (response.text or "").strip()


def _call_groq(prompt: str, max_tokens: int = 1024) -> str:
    from groq import Groq
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set. See config.py / README.md.")
    client = Groq(api_key=GROQ_API_KEY)
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.4,
    )
    return (resp.choices[0].message.content or "").strip()


def call_llm(prompt: str, max_tokens: int = 1024) -> str:
    if LLM_PROVIDER == "groq":
        return _call_groq(prompt, max_tokens)
    return _call_gemini(prompt, max_tokens)


# --------------------------------------------------------- general chat ----
def general_chat(message: str, history: list[dict] | None = None) -> str:
    history = history or []
    convo = ""
    for turn in history[-6:]:
        convo += f"User: {turn['question']}\nAssistant: {turn['answer']}\n"
    prompt = f"""You are a friendly, knowledgeable general-purpose AI assistant
(similar to ChatGPT/Gemini). Continue the conversation naturally.

{convo}User: {message}
Assistant:"""
    return call_llm(prompt, max_tokens=1024)


# ------------------------------------------------------- image analysis ----
def analyze_image(image_bytes: bytes, question: str = "Describe this image in detail.") -> str:
    """Vision understanding - always uses Gemini."""
    from PIL import Image
    client = _get_gemini_client()
    image = Image.open(io.BytesIO(image_bytes))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[question, image],
    )
    return (response.text or "").strip()


# ------------------------------------------------------ image generation ----
def generate_image(prompt: str) -> bytes:
    """Text-to-image generation using Gemini 2.5 Flash Image ('Nano Banana').
    Returns raw PNG bytes, or raises if no image came back."""
    from google.genai import types
    client = _get_gemini_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt],
        config=types.GenerateContentConfig(response_modalities=["Text", "Image"]),
    )
    for part in response.candidates[0].content.parts:
        if getattr(part, "inline_data", None) is not None:
            return part.inline_data.data
    raise RuntimeError("The model did not return an image for this prompt. Try rephrasing it.")


# --------------------------------------------------------------- RAG ----
def generate_rag_answer(question: str, context_chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks) if context_chunks else "(no relevant context found)"
    prompt = f"""You are a helpful assistant for an organization's internal knowledge base.
Answer the question using ONLY the context below. If the answer isn't in the
context, say clearly: "I could not find this in the uploaded documents."
Do not make anything up.

Context:
{context}

Question: {question}

Answer (clear, concise):"""
    return call_llm(prompt)


def summarize_text(text: str, style: str = "concise") -> str:
    max_chars = 15000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated for length]..."
    prompt = f"""Summarize the following document in a {style} way.
First give 5-8 bullet points with the key facts/ideas, then a short
2-3 sentence overview paragraph.

Document:
{text}

Summary:"""
    return call_llm(prompt, max_tokens=800)


# ------------------------------------------------------- text-to-SQL (read) ----
def nl_to_sql(question: str, table_name: str, columns: list[str]) -> str:
    col_list = ", ".join(columns)
    prompt = f"""You are a SQL expert. Convert the natural language question
into a single valid SQL SELECT query.

Table name: {table_name}
Columns: {col_list}

Rules:
- Output ONLY the raw SQL query. No explanation, no markdown, no backticks.
- Only ever generate a SELECT statement. Never INSERT/UPDATE/DELETE/DROP/ALTER.
- Use exactly the table and column names given above.

Question: {question}

SQL Query:"""
    sql = call_llm(prompt, max_tokens=300)
    return _strip_fences(sql)


# ------------------------------------------------------ text-to-SQL (write) ----
def nl_to_write_sql(instruction: str, table_name: str, columns: list[str]) -> str:
    """Converts an instruction like 'update John's marks to 30' into a single
    UPDATE or INSERT statement. Never generates DELETE/DROP/ALTER/TRUNCATE -
    those are also blocked again at execution time as a second layer of defense."""
    col_list = ", ".join(columns)
    prompt = f"""You are a SQL expert. Convert the instruction below into a
single valid SQL UPDATE or INSERT statement (whichever fits the instruction).

Table name: {table_name}
Columns: {col_list}

Rules:
- Output ONLY the raw SQL statement. No explanation, no markdown, no backticks.
- Only ever generate UPDATE or INSERT. NEVER DELETE, DROP, ALTER, or TRUNCATE.
- An UPDATE must always include a WHERE clause that identifies the specific
  row(s) as precisely as possible (e.g. by name or ID mentioned in the instruction).
- Use exactly the table and column names given above.
- If the instruction is ambiguous or could affect many rows unintentionally,
  make the WHERE clause as specific as possible using the details given.

Instruction: {instruction}

SQL Statement:"""
    sql = call_llm(prompt, max_tokens=300)
    return _strip_fences(sql)


def _strip_fences(sql: str) -> str:
    sql = sql.strip()
    for fence in ("```sql", "```SQL", "```"):
        sql = sql.replace(fence, "")
    return sql.strip().rstrip(";")
