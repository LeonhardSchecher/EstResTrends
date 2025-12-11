import json
import re
from pathlib import Path
from openai import AzureOpenAI, OpenAI
import atexit

# ----------------- AUTH / CLIENT SETUP -----------------
# Adjust this path if your key file is elsewhere
OPENAI_API_KEY = ""


client = AzureOpenAI(
    
)


# ------------------- CONFIG ----------------------------
INPUT_JSON  = "../etis.json"       # <--- your input .json
OUTPUT_JSON = "keywords.json"
MODEL_NAME  = "IDS2025-Gross-gpt-4o-mini"
# -------------------------------------------------------


INSTRUCTIONS = """
You are a bibliometrics assistant that generates BROAD subject keywords for scientific research articles.

Goal:
- For each article, read the provided information.
- Propose AT MOST 3 concise, high-level subject keywords that best describe the main topics and domain of the article.

Guidelines:
- Prefer ENGLISH keywords when any English text is present; otherwise use the primary language of the text (e.g. Estonian).
- Use broad noun phrases (e.g. "functional programming", "electric vehicles", "transportation")
  rather than very specific phrases (e.g. "strong functional programming", "EV load model",
  "managed charging", "state of charge").
- Focus on the main domain and most important concepts, not detailed methods or configurations.
- Avoid:
  - very narrow technical terms
  - algorithm names
  - too specific experimental conditions
  - long multi-word technical phrases that include unnecessary adjectives.
- Avoid extremely generic terms like "research", "article", "study", "introduction", "analysis"
  unless they are part of a standard field name (e.g. "time series analysis").
- Do NOT include:
  - author names
  - journal names
  - years or page numbers
  - generic place names like "Estonia", "Tartu" etc. unless central to the topic
    (e.g. "Estonian education system").
- Ignore any author-provided or imported keywords even if they are available in the data;
  do NOT copy or reuse them.

Examples:
- Title: "Strong functional pearl: Harper's regular-expression matcher in Cedille"
  → Keywords: ["functional programming", "regular expression matching", "termination checking"]
- Title: "Travel activity based stochastic modelling of load and charging state of electric vehicles"
  → Keywords: ["electric vehicles", "transportation", "charging load modelling"]

Priority of information:
1. Text
2. Abstract in Estonian (AbstractEst) OR Abstract in English (AbstractEng)
3. Title
4. Source
5. Projects

You will receive a single combined context string that has selected fields according to this priority.
Higher-priority fields are more important. Lower-priority fields are only included when higher-priority
fields are absent or clearly insufficient.

Output format (VERY IMPORTANT):
- Respond with ONLY a single JSON object, no extra explanations.
- The JSON MUST have exactly one key "keyword" whose value is a list of 1-3 keyword strings.

Example valid response:
{"keyword": ["electric vehicles", "transportation"]}

"""


def truncate(text: str, max_chars: int = 3000) -> str:
    """Truncate long text to avoid huge prompts."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def build_article_context(article: dict,
                          min_chars_for_stop: int = 700,
                          max_chars_total: int = 4000) -> str:
    """
    Build a context string for the article following the priority list.

    Priority list:
    1. Text
    2. Abstract in Estonian OR Abstract in English
    3. Title
    4. Journal or source name
    5. Related projects
    6. KeywordsAsFreeText OR UserKeywords

    Logic:
    - If Text exists -> use Text only (already high-quality).
    - Otherwise, incrementally add fields in priority order until total length is
      at least min_chars_for_stop or we run out of fields.
    """

    context_parts = []

    # 1. Text
    text_field = article.get("Text") or article.get("text")
    if text_field:
        text_field = truncate(str(text_field), max_chars_total)
        return f"Text:\n{text_field}"

    # If there is no Text, we combine other fields gradually.

    total_chars = 0

    def try_add(label: str, value: str):
        nonlocal total_chars
        if not value:
            return False
        value = truncate(str(value), max_chars_total)
        piece = f"{label}:\n{value}"
        if total_chars + len(piece) > max_chars_total:
            # Truncate further if we're over the global limit
            remaining = max_chars_total - total_chars
            if remaining <= 0:
                return False
            piece = piece[:remaining]
        context_parts.append(piece)
        total_chars += len(piece)
        return True

    # 2. Abstract in Estonian OR Abstract in English
    abs_et = article.get("Abstract in Estonian") or article.get("abstract_et")
    abs_en = article.get("Abstract in English") or article.get("abstract_en")

    if abs_et:
        try_add("Abstract in Estonian", abs_et)
    if abs_en and total_chars < min_chars_for_stop:
        # Only add English abstract if we still want more context
        try_add("Abstract in English", abs_en)

    if total_chars >= min_chars_for_stop:
        return "\n\n".join(context_parts).strip()

    # 3. Title
    title = article.get("Title") or article.get("title")
    if title:
        try_add("Title", title)
    if total_chars >= min_chars_for_stop:
        return "\n\n".join(context_parts).strip()

    # 4. Journal or source name
    journal = article.get("Source") or article.get("Source")
    if journal:
        try_add("Source", journal)
    if total_chars >= min_chars_for_stop:
        return "\n\n".join(context_parts).strip()

    # 5. Related projects
    related = article.get("Related projects") or article.get("related_projects")
    if related:
        try_add("Related projects", related)
    if total_chars >= min_chars_for_stop:
        return "\n\n".join(context_parts).strip()

    # 6. KeywordsAsFreeText OR UserKeywords
    imported_kw = article.get("KeywordsAsFreeText") or article.get("imported_keywords")
    author_kw = article.get("UserKeywords") or article.get("UserKeywords")

    # We treat these as a last resort: they can help to generate cleaner / normalized keywords.
    if imported_kw:
        try_add("KeywordsAsFreeText", imported_kw)
    if author_kw and total_chars < min_chars_for_stop:
        try_add("UserKeywords", author_kw)

    return "\n\n".join(context_parts).strip()


def call_keyword_model(context: str) -> list[str]:
    """
    Call the Azure GPT deployment once for a single article and
    return a list of keyword strings.
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

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=256,
    )

    content = completion.choices[0].message.content.strip()

    # Try to parse JSON; if it fails, return empty keyword list
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        print("Warning: model returned non-JSON, treating as no keywords:")
        print(content)
        return []

    raw_kw = data.get("keyword", []) or data.get("keywords", [])

    # Normalise different possible formats into a list of strings
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

def transpose_article_dict(data: dict) -> list[dict]:
    """
    Transform input of the form:
        { fieldName: { guid: value } }
    Into:
        [ { "GUID": guid, field1: value1, field2: value2, ... } ]
    """
    articles = {}

    for field_name, guid_map in data.items():
        if not isinstance(guid_map, dict):
            continue

        for guid, value in guid_map.items():
            if guid not in articles:
                articles[guid] = {"GUID": guid}
            articles[guid][field_name] = value

    return list(articles.values())

def load_articles(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Case: dict-of-dicts by field name → needs transposing
    if isinstance(data, dict):
        # detect if values are dicts mapping GUID → field value
        if all(isinstance(v, dict) for v in data.values()):
            return transpose_article_dict(data)

        # otherwise treat it as GUID→article
        articles = []
        for guid, fields in data.items():
            item = {"GUID": guid}
            if isinstance(fields, dict):
                item.update(fields)
            articles.append(item)
        return articles

    # Already a list
    if isinstance(data, list):
        return data

    raise ValueError("Unsupported JSON format")

def load_skip_articles(path:Path) -> list[str]:
    if not (path.exists()): return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list): return []
    guids = []
    for keyword in data:
        guids.append(keyword["GUID"])
    return guids


def main():
    in_path = Path(INPUT_JSON)
    out_path = Path(OUTPUT_JSON)

    articles = load_articles(in_path)
    print(f"Loaded {len(articles)} articles from {in_path}")
    with out_path.open("r", encoding= "utf-8") as f:
        d = json.load(f)
    results = []
    skip = load_skip_articles(out_path)
    processed = 0
    atexit.register(save, results)
    for article in articles[10000:15000]:
        
        guid = article.get("GUID") or article.get("guid")
        if guid in skip: continue
        processed += 1
        context = build_article_context(article)
        if not context:
            print(f"[GUID={guid}] No usable fields, skipping.")
            results.append({"GUID": guid, "keyword": []})
            continue

        try:
            keywords = call_keyword_model(context)
        except Exception as e:
            print(f"Error on GUID={guid}: {e}")
            keywords = []
        if keywords == []: continue 
        results.append({
            "GUID": guid,
            "keyword": keywords  # list of keyword strings
        })

        if processed % 20 == 0:
            print(f"Processed {processed} articles.")
    
    results.extend(d)
    with out_path.open("w", encoding="utf-8") as f_out:
        json.dump(results, f_out, ensure_ascii=False, indent=2)
    print(f"Done. Processed {processed} articles.")
    print(f"Keyword file written to: {out_path}")
def save(results):
    path = Path("emergency_dump.json")
    with path.open("w", encoding="utf-8") as f_out:
        json.dump(results, f_out, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
