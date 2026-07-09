from langchain_groq import ChatGroq
from app.config import settings

primary_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_model,          
    temperature=0.2,
)

context_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_context_model, 
    temperature=0.2,
)
