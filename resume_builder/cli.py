"""resume-build: PDF/text resume in, Overleaf-ready single-page LaTeX out.

Examples:
    resume-build old_resume.pdf
    resume-build notes.txt -o resume.tex --json-out parsed.json
    resume-build parsed.json --from-json          # skip the LLM, just render
    resume-build old_resume.pdf --keys-file keys.txt --model llama-3.3-70b-versatile
"""

import argparse
import json
import sys
from pathlib import Path

from .extract import extract_text
from .groq_client import DEFAULT_MODEL, GroqClient, load_keys
from .parse import normalize, parse_resume
from .render import render_resume


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="resume-build",
        description="Build a single-page, ATS-ready LaTeX resume from a PDF or text file.",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("input", help="input file: .pdf, .txt, .md — or .json with --from-json")
    ap.add_argument("-o", "--output", default="resume.tex", help="output .tex path (default: resume.tex)")
    ap.add_argument("--json-out", metavar="PATH", help="also save the parsed data as JSON (edit it, then re-run with --from-json)")
    ap.add_argument("--from-json", action="store_true", help="input is already-parsed JSON; skip the Groq call")
    ap.add_argument("--keys-file", metavar="PATH", help="file with one Groq API key per line (rotated on rate limits)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Groq model id (default: {DEFAULT_MODEL})")
    ap.add_argument("--show-text", action="store_true", help="print the text extracted from the input and exit")
    args = ap.parse_args()

    try:
        run(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


def run(args: argparse.Namespace) -> None:
    if args.from_json:
        data = normalize(json.loads(Path(args.input).read_text(encoding="utf-8")))
    else:
        raw = extract_text(args.input)
        if args.show_text:
            print(raw)
            return
        print(f"Extracted {len(raw)} characters from {args.input}")

        keys = load_keys(args.keys_file)
        client = GroqClient(keys, model=args.model)
        print(f"Parsing with Groq ({args.model}, {len(keys)} key(s) available)...")
        data = parse_resume(raw, client)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Parsed data saved to {args.json_out}")

    tex = render_resume(data)
    out = Path(args.output)
    out.write_text(tex, encoding="utf-8")

    sections = [s for s in ("summary", "education", "experience", "projects", "skills",
                            "certifications", "achievements") if data.get(s)]
    print(f"\nWrote {out} for {data['name']}  (sections: {', '.join(sections)})")
    print("Next: upload it to Overleaf (New Project -> Upload Project) and compile with pdfLaTeX.")


if __name__ == "__main__":
    main()
