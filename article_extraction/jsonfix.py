import json
from pathlib import Path


input  = r"C:\Users\ekkeg\SA_Projekt\EstResTrends\articles_reduced.jsonl"
ouput = r"C:\Users\ekkeg\SA_Projekt\EstResTrends\articles_reduced_clean.jsonl"

min_words = 4  


def main():
    in_path = Path(input)
    out_path = Path(ouput)

    kept = 0
    skipped_short = 0
    skipped_missing = 0

    with in_path.open("r", encoding="utf-8") as f_in, \
         out_path.open("w", encoding="utf-8") as f_out:

        for line in f_in:
            line = line.strip()
            if not line:
                continue

            obj = json.loads(line)
            obj.pop("source_path", None)
            if "id" in obj:
                obj["id"] = Path(str(obj["id"])).stem
            text = obj.get("text", "")
            if not text:
                skipped_missing += 1
                continue

            words = text.strip().split()
            if len(words) < min_words:
                skipped_short += 1
                continue

            # If it passed the filter, write it out
            f_out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            kept += 1

    print(f"Done.")
    print(f"Kept records         : {kept}")
    print(f"Skipped (no text)    : {skipped_missing}")
    print(f"Skipped (<=3 words)  : {skipped_short}")
    print(f"Output written to    : {out_path}")


if __name__ == "__main__":
    main()
