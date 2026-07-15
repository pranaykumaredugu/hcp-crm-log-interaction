import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Primary conversational / orchestration model (fast + cheap, good for
# tool-calling in the agent loop).
chat_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2,
    groq_api_key=GROQ_API_KEY,
)

# Used inside tools for structured JSON extraction (log_interaction / edit_interaction).
extraction_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    groq_api_key=GROQ_API_KEY,
)

# Used for longer-context reasoning / summarization + follow-up suggestions,
# where a larger model gives better quality suggestions.
summarizer_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    groq_api_key=GROQ_API_KEY,
)