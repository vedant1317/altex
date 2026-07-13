# LaTeX Resume Builder

Feed it your existing resume (PDF) or plain-text notes about your background, and it
produces a **single-page, ATS-ready LaTeX resume** you can upload straight to Overleaf
and compile with pdfLaTeX.

How it works:

1. **Extract** — pulls text out of your PDF (`pdfplumber`) or reads your `.txt`/`.md` file
2. **Parse** — sends the text to Groq (`llama-3.3-70b-versatile`), which returns clean,
   structured JSON (name, education, experience, projects, skills, ...) and rewrites
   bullets to be concise and achievement-oriented — without inventing anything
3. **Render** — fills a compact single-column LaTeX template (Jake's-resume style) with
   proper escaping of LaTeX special characters

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Groq API keys (free at https://console.groq.com/keys)

One key:

```bash
export GROQ_API_KEY=gsk_...
```

Multiple keys — automatically rotated when one hits its rate limit:

```bash
export GROQ_API_KEYS=gsk_key1,gsk_key2,gsk_key3
```

Or keep them in a file (one per line, `#` comments allowed) and pass `--keys-file keys.txt`.
`keys.txt` is already in `.gitignore`.

## Usage

```bash
# from an existing PDF resume
resume-build old_resume.pdf

# from plain-text notes
resume-build samples/sample_input.txt -o resume.tex

# save the parsed JSON too, so you can hand-edit it and re-render without the LLM
resume-build old_resume.pdf --json-out parsed.json
# ...edit parsed.json...
resume-build parsed.json --from-json -o resume.tex

# see what text was extracted from your PDF
resume-build old_resume.pdf --show-text
```

Then upload `resume.tex` to Overleaf (**New Project → Upload Project**, or paste into a
blank project) and compile. The Overleaf default pdfLaTeX compiler works as-is.

If you have [tectonic](https://tectonic-typesetting.github.io) or `pdflatex` installed
locally, you can also compile without Overleaf: `tectonic resume.tex`.

## Why it's ATS-friendly

- Single column, standard section names (Education, Experience, Projects, Skills)
- Real selectable text — no images, icons, text boxes, or multi-column tricks
- `\pdfgentounicode=1` so ligatures copy out as normal characters
- Machine-readable fonts and standard PDF metadata

## Project layout

```
resume_builder/
├── cli.py           # resume-build entry point
├── extract.py       # PDF/text extraction
├── groq_client.py   # Groq API client with key rotation
├── parse.py         # LLM prompt + JSON schema + normalization
├── render.py        # Jinja2 env with LaTeX-safe delimiters & escaping
└── templates/
    └── resume.tex.j2
samples/             # sample input, parsed JSON, and generated output
```

See [samples/sample_resume.pdf](samples/sample_resume.pdf) for what the output looks like.

## License

MIT

