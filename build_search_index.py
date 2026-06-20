from pathlib import Path
from html import unescape
from urllib.parse import quote
import re
import json

ROOT = Path(".")
SKIP_DIRS = {".git", "pagefind", "node_modules"}
STOPWORDS = set("""
و در به از که را با برای این آن یک است می ها های شد شده می‌شود دارد
the and of to in a is for on with as by from this that
""".split())

def normalize(s):
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = re.sub(r"[\u064B-\u065F\u0670]", "", s)
    s = s.lower()
    return s

def strip_html(html):
    html = re.sub(r"(?is)<script.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?</style>", " ", html)
    html = re.sub(r"(?is)<noscript.*?</noscript>", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = unescape(html)
    html = re.sub(r"\s+", " ", html).strip()
    return html

def get_title(html, fallback):
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    if m:
        t = strip_html(m.group(1))
        if t:
            return t[:180]
    h = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", html)
    if h:
        t = strip_html(h.group(1))
        if t:
            return t[:180]
    return fallback

docs = []
terms = {}

files = list(ROOT.rglob("*.html"))
print(f"Scanning {len(files)} html files...")

for p in files:
    rel = p.relative_to(ROOT).as_posix()

    if any(part in SKIP_DIRS for part in p.parts):
        continue
    if rel in {"search.html"}:
        continue
    if "backend" in rel:
        continue

    raw = p.read_text(errors="ignore")
    if "<html" not in raw.lower():
        continue

    text = strip_html(raw)
    if len(text) < 80:
        continue

    title = get_title(raw, rel)
    snippet = text[:320]

    url = quote(rel, safe="/%#")
    doc_id = len(docs)

    docs.append({
        "u": url,
        "t": title,
        "s": snippet
    })

    searchable = normalize(title + " " + text)
    toks = re.findall(r"[a-z0-9\u0600-\u06FF]{2,}", searchable)

    seen = set()
    for tok in toks:
        if tok in STOPWORDS or tok.isdigit():
            continue
        seen.add(tok)
        if len(seen) >= 900:
            break

    for tok in seen:
        arr = terms.setdefault(tok, [])
        if len(arr) < 5000:
            arr.append(doc_id)

out = {
    "docs": docs,
    "terms": terms
}

Path("search-index.json").write_text(
    json.dumps(out, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8"
)

print(f"Indexed docs: {len(docs)}")
print(f"Indexed terms: {len(terms)}")
print("Wrote search-index.json")
