import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY missing from .env")

llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0,
)

response = llm.invoke(
    "Explain customer complaint management in one sentence."
)

print(response.content)