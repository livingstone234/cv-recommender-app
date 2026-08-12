from app.services.job_search_service import build_learning_link, build_search_links


def test_build_search_links_includes_all_platforms():
    links = build_search_links("Backend Engineer", "London")

    assert set(links.keys()) == {"linkedin", "indeed", "weworkremotely"}
    assert "Backend+Engineer" in links["linkedin"]
    assert "London" in links["linkedin"]


def test_build_search_links_encodes_special_characters():
    links = build_search_links("C++ Developer")

    assert "C%2B%2B" in links["linkedin"]
    assert "C%2B%2B" in links["indeed"]


def test_build_search_links_defaults_to_empty_location():
    links = build_search_links("Data Scientist")

    assert links["linkedin"].endswith("location=")


def test_build_learning_link_encodes_skill():
    links = build_learning_link("C# / .NET")

    assert set(links.keys()) == {"coursera", "freecodecamp"}
    assert "C%23" in links["coursera"]
