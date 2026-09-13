import sys
from pathlib import Path
# Reuse the original AI logic during migration.
LEGACY = Path(__file__).resolve().parents[3] / "legacy"
sys.path.insert(0, str(LEGACY))
from llm import general_chat, analyze_image, generate_image, generate_rag_answer, summarize_text
