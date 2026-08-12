import base64

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import settings
from app.schemas.cv_schema import ExtractedCV
from app.schemas.improvement_schema import ImprovementReport
from app.schemas.job_match_schema import JobMatchReport


def get_llm(provider: str = "openai"):
    if provider == "openai":
        return ChatOpenAI(model="gpt-4o", api_key=settings.OPENAI_API_KEY, temperature=0)
    if provider == "gemini":
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", api_key=settings.GEMINI_API_KEY)
    raise ValueError(f"Unsupported LLM provider: {provider!r}")


def extract_cv_from_file(page_images: list[bytes], mime_type: str = "image/png", provider: str = "openai") -> ExtractedCV:
    """Multimodal call: sends the raw CV page images (one per page) to the LLM
    and forces structured output validated against the ExtractedCV Pydantic schema."""
    llm = get_llm(provider).with_structured_output(ExtractedCV)

    content: list[dict] = [
        {"type": "text", "text": "Extract all candidate information from this CV into the structured schema."}
    ]
    for image_bytes in page_images:
        b64 = base64.b64encode(image_bytes).decode()
        content.append({"type": "image_url", "image_url": f"data:{mime_type};base64,{b64}"})

    message = HumanMessage(content=content)
    return llm.invoke([message])


def generate_improvements(cv: ExtractedCV, provider: str = "openai") -> ImprovementReport:
    llm = get_llm(provider).with_structured_output(ImprovementReport)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a senior technical recruiter. Critique this CV honestly and "
                   "give concrete, actionable rewrite suggestions per section."),
        ("human", "{cv_json}"),
    ])
    chain = prompt | llm
    return chain.invoke({"cv_json": cv.model_dump_json()})


def match_jobs(cv: ExtractedCV, provider: str = "openai") -> JobMatchReport:
    llm = get_llm(provider).with_structured_output(JobMatchReport)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Given this candidate profile, suggest the 5 best-fit job titles. "
                   "For each, provide a match score, reasoning, 2-3 real job-board search "
                   "links (LinkedIn Jobs, Indeed, We Work Remotely — build a search-query URL, "
                   "do not invent a specific job posting), and skill gaps with a real learning "
                   "resource link (Coursera, freeCodeCamp, official docs) for each gap."),
        ("human", "{cv_json}"),
    ])
    chain = prompt | llm
    return chain.invoke({"cv_json": cv.model_dump_json()})
