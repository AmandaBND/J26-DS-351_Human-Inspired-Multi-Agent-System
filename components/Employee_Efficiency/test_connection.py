"""Checks the OpenRouter LLM connection (optional - the agent also works offline)."""
from src.config import LLM_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

if not OPENROUTER_API_KEY:
    raise SystemExit("OPENROUTER_API_KEY is not set in .env - the agent will use template narration (offline mode).")

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model=LLM_MODEL, api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL, timeout=20)
print(llm.invoke("Reply with the single word: connected").content)
