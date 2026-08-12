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
