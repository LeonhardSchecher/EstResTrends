import json
from pathlib import Path
from openai import AzureOpenAI

file = open(r"C:\Users\ekkeg\OneDrive - Tartu Ülikool\Dokumendid\OPENAI_API_KEY.txt", "r")
OPENAI_API_KEY = file.read().strip()

client = AzureOpenAI(
    api_key=OPENAI_API_KEY,
    api_version="2024-12-01-preview",  
    azure_endpoint="https://tu-openai-api-management.azure-api.net/oltatkull/openai/deployments/IDS2025-Gross-gpt-4o-mini/chat/completions?api-version=2024-12-01-preview"
)

# ---------- CONFIG ----------
INPUT_JSONL  = r"article_extraction\ar_clean_rest.jsonl"
OUTPUT_JSONL = r"article_extraction\articles_filtered.jsonl"
MODEL_NAME   = "IDS2025-Gross-gpt-4o-mini"
# ----------------------------

INSTRUCTIONS = """
You are a filter for scientific article snippets.

For each text:
- Return keep=true if it is a useful scientific abstract or introduction:
  - It clearly describes a research topic, study, or scientific problem.
  - It has at least a couple of full sentences with substance.
  - It is not mostly boilerplate (copyright, journal info, references, index, table of contents, etc.).

- Return keep=false if:
  - It is only metadata, headings, or references.
  - It is extremely short or meaningless.
  - It is clearly not part of a scientific article.

You MUST respond with ONLY a single JSON object, no extra text, in this form:
{
  "keep": boolean,
  "reason": string
}
"""

def classify_text(text: str) -> bool:
    """Call the Azure GPT deployment once for a single text and return keep=True/False."""
    prompt = f"""Here is the text:

{text}

Remember: respond ONLY with a JSON object like:
{{"keep": true, "reason": "..."}} or {{"keep": false, "reason": "..."}}
"""

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=64,
    )

    content = completion.choices[0].message.content.strip()

    # Try to parse JSON; if it fails, default to keep=False
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        print("Warning: model returned non-JSON, treating as keep=False:")
        print(content)
        return False

    keep = bool(data.get("keep", False))
    print("keep:", keep, "reason:", data.get("reason"))
    return keep


def main():
    in_path = Path(INPUT_JSONL)
    out_path = Path(OUTPUT_JSONL)

    kept = 0
    total = 0

    with in_path.open("r", encoding="utf-8") as f_in, \
         out_path.open("w", encoding="utf-8") as f_out:

        for line in f_in:
            line = line.strip()
            if not line:
                continue

            total += 1
            obj = json.loads(line)
            text = obj.get("text", "").strip()
            if not text:
                continue

            try:
                keep = classify_text(text)
            except Exception as e:
                print(f"Error on row {total}: {e}")
                continue

            if keep:
                f_out.write(json.dumps(obj, ensure_ascii=False) + "\n")
                kept += 1

            if total % 50 == 0:
                print(f"Processed {total} rows, kept {kept}")

    print(f"Done. Total rows: {total}, kept: {kept}")
    print(f"Filtered file written to: {out_path}")


if __name__ == "__main__":
    main()
