"""
Reads every URL written in .github/workflows/keep_alive.yml and writes them
as a table into README.md, between two invisible marker comments.
Run automatically by GitHub Actions (update_readme.yml) 
"""
import re                               # regular expressions: find URLs in text
from pathlib import Path                # easy file reading/writing
from urllib.parse import urlparse, quote

WORKFLOW = Path(".github/workflows/keep_alive.yml")   # where your URLs live
README = Path("README.md")
START = "<!-- APPS:START -->"           # HTML comments are invisible on GitHub,
END = "<!-- APPS:END -->"               # so readers never see these markers


def read_urls():
    """Return every http(s) URL in keep_alive.yml, in order, without duplicates.
    Lines that are commented out with # are ignored."""
    urls = []
    for line in WORKFLOW.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):          # whole line is a comment
            continue
        line = line.split(" #")[0]                 # drop a comment at the end of a line
        for url in re.findall(r"https?://[^\s'\",\]]+", line):
            url = url.rstrip("/")
            if url not in urls:
                urls.append(url)
    return urls


def app_name(url):
    """'https://webscrapingwiki.streamlit.app' -> 'Webscrapingwiki'"""
    subdomain = urlparse(url).netloc.split(".")[0]
    return subdomain.replace("-", " ").replace("_", " ").title()


KEEP_ALIVE_BADGE = ("[![Keep alive](https://github.com/Saavan-Dev/simple-streamlit-app/actions/"
                    "workflows/keep_alive.yml/badge.svg)](https://github.com/Saavan-Dev/"
                    "simple-streamlit-app/actions/workflows/keep_alive.yml)")
OPEN_BADGE = "https://static.streamlit.io/badges/streamlit_badge_black_white.svg"


def build_table(urls):
    rows = [KEEP_ALIVE_BADGE, "",                       # one status badge for all apps
            "| # | App | Link | Open |", "|---|---|---|---|"]
    for i, url in enumerate(urls, 1):
        rows.append(f"| {i} | {app_name(url)} | [{url}]({url}) | [![Open in Streamlit]({OPEN_BADGE})]({url}) |")
    if not urls:
        rows.append("| – | No apps listed yet | – | – |")
    return "\n".join(rows)

def main():
    urls = read_urls()
    block = f"{START}\n{build_table(urls)}\n{END}"

    if README.exists():
        text = README.read_text(encoding="utf-8")
    else:                                          # first run: create a README
        text = "# simple-streamlit-app\n\nStreamlit apps built while learning Python.\n"

    if START in text and END in text:
        # replace ONLY the part between the markers; the rest of README stays as you wrote it
        pattern = re.escape(START) + r".*?" + re.escape(END)
        text = re.sub(pattern, lambda m: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n## 🚀 Live apps\n\n" + block + "\n"

    README.write_text(text, encoding="utf-8")
    print(f"README.md updated with {len(urls)} app link(s).")


if __name__ == "__main__":
    main()
