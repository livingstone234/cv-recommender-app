# 6. LangChain Service (Multimodal Extraction + Structured Output)

## `app/services/llm_service.py`

```python
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from app.schemas.cv_schema import ExtractedCV
from app.schemas.improvement_schema import ImprovementReport
from app.schemas.job_match_schema import JobMatchReport
from app.config import settings
import base64

def get_llm(provider: str = "openai"):
    if provider == "gemini":
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", api_key=settings.GEMINI_API_KEY)
    return ChatOpenAI(model="gpt-4o", api_key=settings.OPENAI_API_KEY, temperature=0)

def extract_cv_from_file(file_bytes: bytes, mime_type: str, provider: str = "openai") -> ExtractedCV:
    """Multimodal call: sends the raw CV (PDF page images or DOCX-rendered images) to the LLM
    and forces structured output validated against the ExtractedCV Pydantic schema."""
    llm = get_llm(provider).with_structured_output(ExtractedCV)
    b64 = base64.b64encode(file_bytes).decode()

    message = HumanMessage(content=[
        {"type": "text", "text": "Extract all candidate information from this CV into the structured schema."},
        {"type": "image_url", "image_url": f"data:{mime_type};base64,{b64}"},
    ])
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
```

## Breaking down the three calls

1. **`extract_cv_from_file`** — the *multimodal* call. Rather than running a
   separate text-extraction/OCR library on the PDF first, the raw page images are
   base64-encoded and sent directly in the message content as `image_url` blocks
   (both GPT-4o and Gemini 1.5 Pro accept this format). The LLM reads the CV
   visually — this correctly handles CVs with unusual layouts, tables, or columns
   that a naive text extractor would mangle. `temperature=0` on the OpenAI client
   is deliberate: for an extraction task, you want the most deterministic,
   least "creative" output possible.
2. **`generate_improvements`** — takes the *already-validated* `ExtractedCV`
   object (not the raw file) and asks a second, separate LLM call to critique it.
   Splitting extraction and critique into two calls (rather than one mega-prompt
   doing both) keeps each call's job narrow, which in practice makes structured
   output far more reliable — the model has one clear task and one clear schema
   per call.
3. **`match_jobs`** — same pattern, a third call, again working off the
   structured `ExtractedCV`, not the raw file. Both `generate_improvements` and
   `match_jobs` are independent of each other's LLM call and could, as an
   optimization, run concurrently (`asyncio.gather`) rather than sequentially —
   worth doing once the sync version works, since each is a separate network
   round-trip to the LLM provider.

## The `prompt | llm` syntax — LangChain Expression Language (LCEL)

`chain = prompt | llm` isn't Python's bitwise-or operator doing anything special
with ints — `ChatPromptTemplate` and the LLM client both implement `__or__` to
compose into a `Runnable` pipeline. `chain.invoke({...})` first formats the
prompt template with the given variables, then feeds the formatted messages into
the LLM. This is LangChain's "LCEL" (LangChain Expression Language) — the same
`|` composition pattern works for chaining in retrievers, output parsers, or
other chains later, which is the main reason to learn the pattern rather than
just calling `llm.invoke(prompt.format(...))` directly.

## The job-board link builder (deterministic, not LLM-generated)

`app/services/job_search_service.py`:

```python
from urllib.parse import quote_plus

def build_search_links(job_title: str, location: str = "") -> dict:
    q = quote_plus(job_title)
    loc = quote_plus(location)
    return {
        "linkedin": f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}",
        "indeed": f"https://www.indeed.com/jobs?q={q}&l={loc}",
        "weworkremotely": f"https://weworkremotely.com/remote-jobs/search?term={q}",
    }

def build_learning_link(skill: str) -> dict:
    q = quote_plus(skill)
    return {
        "coursera": f"https://www.coursera.org/search?query={q}",
        "freecodecamp": f"https://www.freecodecamp.org/news/search/?query={q}",
    }
```

This is plain, boring, testable Python — not a chain, not an LLM call. Whenever
a URL *must* be valid (as opposed to LLM prose, which just needs to be roughly
sensible), build it deterministically from a known-good template rather than
trusting a model to produce or copy a correct URL. `urllib.parse.quote_plus` is
what safely encodes the job title/skill into the query string (handles spaces,
special characters — e.g. `"C++ Developer"` needs escaping to be a valid URL).

See [16-concepts-glossary.md](16-concepts-glossary.md) for: LCEL/Runnable,
multimodal input, temperature, tool calling.
