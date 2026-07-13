"""Turn raw resume text into structured JSON via Groq, then normalize it."""

import json
import re
from typing import Any, Dict

from .groq_client import GroqClient

SCHEMA_EXAMPLE = {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+1 555 123 4567",
    "location": "Mumbai, India",
    "links": [
        {"label": "LinkedIn", "url": "https://linkedin.com/in/janedoe"},
        {"label": "GitHub", "url": "https://github.com/janedoe"},
    ],
    "summary": "One or two sentence professional summary, or empty string.",
    "education": [
        {
            "institution": "Some University",
            "location": "City, Country",
            "degree": "B.Tech in Computer Engineering; CGPA: 9.1/10",
            "dates": "Aug 2022 -- May 2026",
        }
    ],
    "experience": [
        {
            "title": "Software Engineering Intern",
            "company": "Acme Corp",
            "location": "Remote",
            "dates": "Jun 2025 -- Aug 2025",
            "bullets": [
                "Achievement-oriented bullet starting with a strong verb, with metrics where available"
            ],
        }
    ],
    "projects": [
        {
            "name": "Project Name",
            "tech": "Python, FastAPI, PostgreSQL",
            "dates": "2025",
            "bullets": ["What it does and the measurable impact"],
        }
    ],
    "skills": [
        {"category": "Languages", "items": ["Python", "C++", "SQL"]},
        {"category": "Frameworks & Tools", "items": ["FastAPI", "Docker", "Git"]},
    ],
    "certifications": ["AWS Certified Cloud Practitioner (2025)"],
    "achievements": ["Winner, XYZ Hackathon 2024 (200+ teams)"],
}

SYSTEM_PROMPT = f"""You are a resume-parsing engine. You receive the raw text of a resume \
(or informal notes about someone's background) and must return ONLY a JSON object with \
exactly this structure:

{json.dumps(SCHEMA_EXAMPLE, indent=2)}

Rules:
- Use only information present in the input. Never invent employers, dates, degrees, or metrics.
- If a field is unknown, use "" for strings and [] for lists. Omit nothing; keep every key.
- Rewrite experience/project bullets to be concise, achievement-oriented, and to start with a \
strong action verb. Keep each bullet under ~25 words. Preserve all real numbers/metrics.
- Do not drop information when rewriting bullets: keep the technologies used (e.g. "in Python \
and SQL"), and when the input gives a before/after comparison (e.g. "from 2 days to 1 hour", \
"from 45% to 85%") keep BOTH numbers. Every distinct accomplishment in the input must appear \
in some bullet.
- Use canonical capitalization for technology names: LaTeX, PostgreSQL, JavaScript, FastAPI, \
GitHub, etc.
- PDF extraction often deletes spaces ("KJSomaiyaCollegeofEngineering") and separators \
("NERVE—AutonomousOutreachEngine"). Reconstruct proper spacing, apostrophes, and keep \
separator dashes: that project name is "NERVE — Autonomous Outreach Engine".
- Format certifications as "Name — Issuer (Year)" when the issuer/year is known.
- Keep the resume single-page worthy: at most 4 bullets per experience entry, 3 per project, \
and drop trivial or redundant items if the input is very long.
- Dates: use the format "Mon YYYY -- Mon YYYY" or "Mon YYYY -- Present" when known.
- links: include LinkedIn/GitHub/portfolio URLs found in the input; label them sensibly.
- Plain text only in values: no markdown, no LaTeX commands, no HTML.
Return ONLY the JSON object, nothing else."""

REQUIRED_KEYS: Dict[str, Any] = {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "links": [],
    "summary": "",
    "education": [],
    "experience": [],
    "projects": [],
    "skills": [],
    "certifications": [],
    "achievements": [],
}


def parse_resume(raw_text: str, client: GroqClient) -> Dict[str, Any]:
    content = client.chat(SYSTEM_PROMPT, raw_text, json_mode=True)
    data = _loads_lenient(content)
    return normalize(data)


def _loads_lenient(content: str) -> Dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # model occasionally wraps JSON in code fences or prose
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Model did not return valid JSON:\n{content[:500]}")


def normalize(data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarantee every key exists with the right shape so the template never breaks."""
    out = dict(REQUIRED_KEYS)
    out.update({k: v for k, v in data.items() if k in REQUIRED_KEYS and v is not None})

    for key in ("links", "education", "experience", "projects", "skills"):
        if not isinstance(out[key], list):
            out[key] = []

    out["links"] = [l for l in out["links"] if isinstance(l, dict) and l.get("url")]
    for link in out["links"]:
        link.setdefault("label", link["url"])

    for entry in out["experience"]:
        entry.setdefault("bullets", [])
        entry["bullets"] = [b for b in entry["bullets"] if isinstance(b, str) and b.strip()]
    for entry in out["projects"]:
        entry.setdefault("bullets", [])
        entry["bullets"] = [b for b in entry["bullets"] if isinstance(b, str) and b.strip()]

    out["skills"] = [
        s for s in out["skills"]
        if isinstance(s, dict) and s.get("category") and s.get("items")
    ]
    out["certifications"] = [c for c in out["certifications"] if isinstance(c, str) and c.strip()]
    out["achievements"] = [a for a in out["achievements"] if isinstance(a, str) and a.strip()]

    if not out["name"].strip():
        raise ValueError("Could not find a name in the input — is this actually a resume?")
    return out
