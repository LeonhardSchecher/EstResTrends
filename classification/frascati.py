from labeler import build_article_context, load_articles, save
import json

from pathlib import Path
from openai import OpenAI, AzureOpenAI
import atexit


INPUT_JSON = "" # data file from s
OUTPUT_JSON = ""

OPENAI_API_KEY = ""

client = OpenAI(api_key=OPENAI_API_KEY)



MODEL_NAME  = "gpt-4o-mini"



INSTRUCTIONS = """
            You are an expert classifier trained to assign research publications to the correct Frascati category
            Frascati Fields of Science and Technology (FOS) category.
            Task Requirements

Input: You will receive any combination of:

Title
Abstract
Keywords
Article body text
Author-assigned classifications
Journal scope

Output the the categorization number only, no text or other outputs is allowed.

Rules:
Choose one code only — the most dominant field.
If multiple fields appear, select the field most central to the research question or methodology.
If uncertain, choose the closest higher-level match rather than guessing.
Never invent codes beyond the official FOS list.
Do not output explanations unless explicitly asked.
Behavior:
    - Be strict, consistent, and deterministic.
    - Resolve ambiguity in favor of the methodological or disciplinary core.
    - Ignore journal marketing language; rely on article content.
            Frascati categorization list:
            1. Natural Sciences
                1.1 Mathematics
                1.2 Computer and information sciences
                1.3 Physical sciences
                1.4 Chemical sciences
                1.5 Earth and related environmental sciences
                1.6 Biological sciences
                1.7 Other natural sciences
            2. Engineering and technology 
                2.1 Civil engineering
                2.2 Electrical engineering, electronic engineering, information engineering
                2.3 Mechanical engineering
                2.4 Chemical engineering
                2.5 Materials engineering
                2.6 Medical engineering
                2.7 Environmental engineering
                2.8 Environmental biotechnology
                2.9 Industrial biotechnology
                2.10 Nano-technology
                2.11 Other engineering and technologies
            3. Medical and health sciences 
                3.1 Basic medicine
                3.2 Clinical medicine
                3.3 Health sciences
                3.4 Medical biotechnology
                3.5 Other medical science
            4. Agricultural and veterinary sciences 
                4.1 Agriculture, forestry, and fisheries
                4.2 Animal and dairy science
                4.3 Veterinary science
                4.4 Agricultural biotechnology
                4.5 Other agricultural sciences
            5. Social Sciences
                5.1 Psychology and cognitive sciences
                5.2 Economics and business
                5.3 Education
                5.4 Sociology
                5.5 Law
                5.6 Political science
                5.7 Social and economic geography
                5.8 Media and communications
                5.9 Other social sciences
            6. Humanities and the arts 
                6.1 History and archaeology
                6.2 Languages and literature
                6.3 Philosophy, ethics and religion
                6.4 Arts (arts, history of arts, performing arts, music)
                6.5 Other humanities
"""
CODES = [
    "1.1","1.2",
    "1.3", "1.4", "1.5", "1.6", "1.7",
    "2.1", "2.2","2.3","2.4","2.5","2.6","2.7","2.8","2.9",
    "2.10","4.1", "4.2", "4.3", "4.4", "4.5",
    "2.11","3.1","3.3","3.2","3.5","3.4",
    "5.1","5.2","5.3","5.4","5.5",
    "5.6","5.7","5.8","5.9","6.1",
    "6.2","6.3","6.4","6.5"
]


def add_to_old(old:dict, new:dict):
    old_keys = set(old.keys())
    new_keys = set(new.keys())
    diff_guids = new_keys.difference(old_keys) 
    for guid in diff_guids:
        old[guid] = new[guid]
    return old




def call_frascati_model(context: str) -> str:
    if not context:
        return ""

    prompt = context

    # Using Responses API instead of chat.completions
    response = client.responses.create(
        model=MODEL_NAME,
        input=[
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_output_tokens=256,
    )

    # Concatenate all text output into a single string
    content = response.output_text
    if content not in CODES: return ""
    return content


def main():
    in_path = Path(INPUT_JSON)
    out_path = Path(OUTPUT_JSON)

    articles = load_articles(in_path)
    print(f"Loaded {len(articles)} articles from {in_path}")

    results = {}
    skip = []
    processed = 0
    atexit.register(save, results)
    for article in articles:

        guid = article.get("GUID") or article.get("guid")
        if guid in skip:
            continue
        processed += 1
        context = build_article_context(article)
        if not context:
            print(f"[GUID={guid}] No usable fields, skipping.")
            continue
        try:
            frascati = call_frascati_model(context)
        except Exception as e:
            print(f"Error on GUID={guid}: {e}")
            frascati
            frascati = ""
        if frascati == "": continue
        results[guid] = frascati

        if processed % 20 == 0:
            print(f"Processed {processed} articles.")
    if out_path.exists():
        with out_path.open("r", encoding="utf-8") as f:
            d = json.load(f)
        results = add_to_old(d, results)
    with out_path.open("w", encoding="utf-8") as f_out:
        json.dump(results, f_out, ensure_ascii=False, indent=2)

    print(f"Done. Processed {processed} articles.")
    print(f"Frascati file written to: {out_path}")


def save(results):
    path = Path("./emergency_dump_f.json")
    with path.open("w", encoding="utf-8") as f_out:
        json.dump(results, f_out, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()