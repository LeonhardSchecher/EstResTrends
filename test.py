import json
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from openai import AsyncOpenAI

# ----------------- AUTH / CLIENT SETUP -----------------
with open("../api.key", 'r', encoding="utf-8") as f:
    OPENAI_API_KEY = f.read().strip()

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY
)

# ------------------- CONFIG ----------------------------
INPUT_JSON  = "./etis.json"
OUTPUT_JSON = "test.json"
MODEL_NAME  = "gpt-4o-mini"

# Tweak this based on your rate limits & how fast you want to go
MAX_CONCURRENT_REQUESTS = 5
# -------------------------------------------------------


INSTRUCTIONS = """
You are a bibliometrics assistant that generates BROAD subject keywords for scientific research articles.
[... keep your long instructions exactly as before ...]
"""


def truncate(text: str, max_chars: int = 3000) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def build_article_context(article: Dict[str, Any],
                          min_chars_for_stop: int = 700,
                          max_chars_total: int = 4000) -> str:
    # <<< same as in your previous version, unchanged >>>
    context_parts = []

    text_field = article.get("Text") or article.get("text")
    if text_field:
        text_field = truncate(str(text_field), max_chars_total)
        return f"Text:\n{text_field}"

    total_chars = 0

    def try_add(label: str, value: str):
        nonlocal total_chars
        if not value:
            return False
        value = truncate(str(value), max_chars_total)
        piece = f"{label}:\n{value}"
        if total_chars + len(piece) > max_chars_total:
            remaining = max_chars_total - total_chars
            if remaining <= 0:
                return False
            piece = piece[:remaining]
        context_parts.append(piece)
        total_chars += len(piece)
        return True

    abs_et = article.get("Abstract in Estonian") or article.get("abstract_et")
    abs_en = article.get("Abstract in English") or article.get("abstract_en")

    if abs_et:
        try_add("Abstract in Estonian", abs_et)
    if abs_en and total_chars < min_chars_for_stop:
        try_add("Abstract in English", abs_en)

    if total_chars >= min_chars_for_stop:
        return "\n\n".join(context_parts).strip()

    title = article.get("Title") or article.get("title")
    if title:
        try_add("Title", title)
    if total_chars >= min_chars_for_stop:
        return "\n\n".join(context_parts).strip()

    journal = article.get("Source") or article.get("Source")
    if journal:
        try_add("Source", journal)
    if total_chars >= min_chars_for_stop:
        return "\n\n".join(context_parts).strip()

    related = article.get("Related projects") or article.get("related_projects")
    if related:
        try_add("Related projects", related)
    if total_chars >= min_chars_for_stop:
        return "\n\n".join(context_parts).strip()

    imported_kw = article.get("KeywordsAsFreeText") or article.get("imported_keywords")
    author_kw = article.get("UserKeywords") or article.get("UserKeywords")

    if imported_kw:
        try_add("KeywordsAsFreeText", imported_kw)
    if author_kw and total_chars < min_chars_for_stop:
        try_add("UserKeywords", author_kw)

    return "\n\n".join(context_parts).strip()


async def call_keyword_model_async(context: str) -> List[str]:
    """
    Async version: call the Responses API once for a single article.
    """
    if not context:
        return []

    prompt = f"""Below is information about a scientific article.
Use it to generate subject keywords following the instructions.

ARTICLE INFORMATION:
{context}

Remember: respond ONLY with a JSON object of the form:
{{"keyword": ["kw1", "kw2", "..."]}}
"""

    resp = await client.responses.create(
        model=MODEL_NAME,
        input=[
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_output_tokens=256,
    )

    content = resp.output_text.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        print("Warning: model returned non-JSON, treating as no keywords:")
        print(content[:300])
        return []

    raw_kw = data.get("keyword", []) or data.get("keywords", [])

    if isinstance(raw_kw, str):
        parts = [p.strip() for p in re.split(r"[;,]", raw_kw) if p.strip()]
        return parts

    if isinstance(raw_kw, list):
        cleaned = []
        for k in raw_kw:
            s = str(k).strip()
            if s:
                cleaned.append(s)
        return cleaned

    return []


def transpose_article_dict(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    articles: Dict[str, Dict[str, Any]] = {}

    for field_name, guid_map in data.items():
        if not isinstance(guid_map, dict):
            continue

        for guid, value in guid_map.items():
            if guid not in articles:
                articles[guid] = {"GUID": guid}
            articles[guid][field_name] = value

    return list(articles.values())


def load_articles(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        if all(isinstance(v, dict) for v in data.values()):
            return transpose_article_dict(data)

        articles = []
        for guid, fields in data.items():
            item = {"GUID": guid}
            if isinstance(fields, dict):
                item.update(fields)
            articles.append(item)
        return articles

    if isinstance(data, list):
        return data

    raise ValueError("Unsupported JSON format")


def load_existing_results(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return []
    return data


async def process_article(article: Dict[str, Any],
                          existing_guids: set,
                          sem: asyncio.Semaphore) -> Dict[str, Any] | None:
    guid = article.get("GUID") or article.get("guid")
    if not guid:
        return None
    if guid in existing_guids:
        # already processed in existing output file
        return None

    context = build_article_context(article)
    if not context:
        print(f"[GUID={guid}] No usable fields, skipping.")
        return {"GUID": guid, "keyword": []}

    async with sem:
        try:
            keywords = await call_keyword_model_async(context)
        except Exception as e:
            print(f"Error on GUID={guid}: {e}")
            keywords = []

    if keywords == []:
        # If you want to record empty too, return {"GUID": guid, "keyword": []}
        return None

    return {"GUID": guid, "keyword": keywords}


async def main_async():
    in_path = Path(INPUT_JSON)
    out_path = Path(OUTPUT_JSON)

    articles = load_articles(in_path)
    print(f"Loaded {len(articles)} articles from {in_path}")

    existing = load_existing_results(out_path)
    existing_guids = {row.get("GUID") for row in existing if isinstance(row, dict)}
    print(f"Loaded {len(existing)} existing results, will skip those GUIDs.")

    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    tasks = [
        process_article(article, existing_guids, sem)
        for article in articles[:500]  # or remove slicing if you want all
    ]

    results: List[Dict[str, Any]] = []
    processed = 0

    for coro_chunk_start in range(0, len(tasks), 50):
        # run in moderate chunks so we see progress
        chunk = tasks[coro_chunk_start:coro_chunk_start + 50]
        chunk_results = await asyncio.gather(*chunk)
        for r in chunk_results:
            if r is not None:
                results.append(r)
            processed += 1
        print(f"Processed {processed} articles so far...")

    all_results = existing + results

    with out_path.open("w", encoding="utf-8") as f_out:
        json.dump(all_results, f_out, ensure_ascii=False, indent=2)

    print(f"Done. New results: {len(results)}, total stored: {len(all_results)}.")
    print(f"Keyword file written to: {out_path}")


if __name__ == "__main__":
    asyncio.run(main_async())
