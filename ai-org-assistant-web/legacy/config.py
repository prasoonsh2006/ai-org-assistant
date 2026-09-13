"""
Central configuration for the project.

API keys/settings are read from environment variables. The easiest way is to
create a file named `.env` in this folder (copy `.env.example`) - it is
loaded automatically below.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# "gemini" (Google, free tier) or "groq" (very fast, free tier, Llama models)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Password for the Admin Panel (approving/rejecting organizations)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# RAG settings
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
TOP_K_RESULTS = 4

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
