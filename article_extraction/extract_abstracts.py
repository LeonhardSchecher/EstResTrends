import re
import json
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader
from pypdf.errors import DependencyError, PdfReadError

# python3.11 -m pip install bs4 lxml pypdf python-docx cryptography

MAX_PDF_PAGES = 3          # how many pages to scan from each PDF
FALLBACK_WORDS = 400       # if no clear abstract/intro, take this many words
INPUT_EXTS = {".pdf", ".docx", ".html", ".htm"}
INPUT_DIR = r"C:\Users\ekkeg\data"      
OUTPUT_DIR = r"C:\Users\ekkeg\SA_Projekt\EstResTrends\article_output"  
JSONL_NAME = "articles_reduced.jsonl"           

def extract_abstract_or_intro(text: str) -> str:
    """
    Try to grab the abstract; if not, grab the introduction; otherwise
    return the first FALLBACK_WORDS words.
    """
    if not text:
        return ""

    # Normalize line breaks
    t = text.replace("\r", "\n")

    # Collapse multiple newlines to help regex
    t = re.sub(r"\n{2,}", "\n\n", t)

    # 1. Try ABSTRACT section
    abstract_pattern = re.compile(
        r"\babstract\b[:.]?\s*(.+?)(?:\n\s*\n|\bintroduction\b)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    m = abstract_pattern.search(t)
    if m:
        return m.group(1).strip()

    # 2. Try INTRODUCTION section 
    intro_pattern = re.compile(
        r"\bintroduction\b[:.]?\s*(.+?)(?:\n\s*\n|\bmethods\b|\bmaterials and methods\b|\bresults\b|\bbackground\b)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    m = intro_pattern.search(t)
    if m:
        return m.group(1).strip()

    # 3. Fallback: first N words
    words = t.split()
    return " ".join(words[:FALLBACK_WORDS]).strip()


def extract_from_pdf(path: Path) -> str:
    # Try to open the PDF at all
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        print(f"[PDF ERROR] {path}: {e}")
        return ""

    # Try to get number of pages
    try:
        num_pages = len(reader.pages)
    except (PdfReadError, DependencyError, Exception) as e:
        print(f"[PDF PAGES ERROR] {path}: {e}")
        return ""

    # Decide how many pages to read
    pages_to_read = min(num_pages, MAX_PDF_PAGES)

    text_parts = []
    for i in range(pages_to_read):
        try:
            page = reader.pages[i]
            page_text = page.extract_text() or ""
        except (PdfReadError, DependencyError, Exception) as e:
            print(f"[PDF PAGE ERROR] {path} page {i}: {e}")
            continue  
        text_parts.append(page_text)

    raw_text = "\n".join(text_parts)
    return extract_abstract_or_intro(raw_text)



def extract_from_docx(path: Path) -> str:
    try:
        doc = Document(str(path))
    except Exception as e:
        print(f"[DOCX ERROR] {path}: {e}")
        return ""

    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    raw_text = "\n".join(paragraphs)
    return extract_abstract_or_intro(raw_text)


def extract_from_html(path: Path) -> str:
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[HTML READ ERROR] {path}: {e}")
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Try meta tags
    meta_abstract = soup.find("meta", attrs={"name": "description"})
    if meta_abstract and meta_abstract.get("content"):
        return meta_abstract["content"].strip()

    meta_abstract = soup.find("meta", attrs={"name": "citation_abstract"})
    if meta_abstract and meta_abstract.get("content"):
        return meta_abstract["content"].strip()

    # Otherwise, just get page text
    # Remove script/style
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    return extract_abstract_or_intro(text)


def process_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_from_pdf(path)
    elif ext == ".docx":
        return extract_from_docx(path)
    elif ext in {".html", ".htm"}:
        return extract_from_html(path)
    else:
        return ""


def main(input_dir: str, output_dir: str, jsonl_name: str = "articles_reduced.jsonl"):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_path / jsonl_name

    count = 0
    with jsonl_path.open("w", encoding="utf-8") as jf:
        for file_path in input_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in INPUT_EXTS:
                continue

            print(f"Processing: {file_path}")
            reduced_text = process_file(file_path)
            if not reduced_text:
                print(f"  -> no text extracted")
                continue

            rel = file_path.relative_to(input_path)

            record = {
                "id": Path(str(rel)).stem, 
                "text": reduced_text,
            }
            jf.write(json.dumps(record, ensure_ascii=False) + "\n")

            count += 1

    print(f"Done. Processed {count} files.")
    print(f"JSONL written to: {jsonl_path}")


if __name__ == "__main__":
    main(INPUT_DIR, OUTPUT_DIR, JSONL_NAME)
