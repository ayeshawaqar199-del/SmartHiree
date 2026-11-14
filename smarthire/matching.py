import re
import zipfile
import xml.etree.ElementTree as ET


SKILL_CATALOG = (
    "Python", "Django", "Java", "JavaScript", "TypeScript", "React", "Node.js",
    "HTML", "CSS", "REST API", "SQL", "PostgreSQL", "MySQL", "MongoDB",
    "Git", "Docker", "AWS", "Azure", "Linux", "C++", "C#", "PHP", "Go",
    "Kotlin", "Swift", "Excel", "Power BI", "Tableau", "Data Analysis",
    "Machine Learning", "Natural Language Processing", "NLP", "Communication",
    "Project Management", "Leadership", "Customer Service", "Sales", "UX Design",
    "UI Design", "Figma", "Quality Assurance", "Testing", "Agile", "Cybersecurity",
    "Microsoft Office", "Accounting", "Recruiting", "Marketing", "Writing",
)
ALIASES = {
    "js": "javascript", "nodejs": "node.js", "node js": "node.js",
    "postgres": "postgresql", "powerbi": "power bi", "power-bi": "power bi",
    "ml": "machine learning", "natural language processing": "nlp",
    "qa": "quality assurance", "ux": "ux design", "ui": "ui design",
}


class ResumeParseError(ValueError):
    pass


def normalize_skill(value):
    value = re.sub(r"[^a-z0-9+#. ]+", " ", str(value or "").casefold())
    value = re.sub(r"\s+", " ", value).strip()
    return ALIASES.get(value, value)


def split_skills(value):
    return [part.strip() for part in re.split(r"[,;|\n]+", value or "") if part.strip()]


def _contains_skill(text, alias):
    alias = re.escape(alias.casefold()).replace(r"\ ", r"\s+")
    return re.search(r"(?<![a-z0-9])" + alias + r"(?![a-z0-9])", text, re.IGNORECASE) is not None


def extract_skills(text, extra_skills=()):
    """Extract catalog and job-specific skill phrases from plain CV text."""
    text = str(text or "")[:150_000]
    candidates = list(SKILL_CATALOG) + list(extra_skills)
    found = {}
    for label in candidates:
        canonical = normalize_skill(label)
        if not canonical:
            continue
        aliases = [str(label), canonical]
        aliases.extend(alias for alias, target in ALIASES.items() if target == canonical)
        if any(_contains_skill(text, alias) for alias in aliases):
            found.setdefault(canonical, str(label).strip())
    return list(found.values())


def extract_resume_text(upload):
    """Read text from text-based PDF and DOCX uploads. Scanned PDFs need OCR."""
    name = getattr(upload, "name", "").lower()
    try:
        upload.seek(0)
        if name.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(upload, strict=False)
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception as exc:
                    raise ResumeParseError("This PDF is password protected. Upload an unlocked copy.") from exc
            chunks = []
            for page in reader.pages[:20]:
                chunks.append(page.extract_text() or "")
            text = "\n".join(chunks)
        elif name.endswith(".docx"):
            with zipfile.ZipFile(upload) as archive:
                info = archive.getinfo("word/document.xml")
                if info.file_size > 5 * 1024 * 1024:
                    raise ResumeParseError("This Word document expands beyond the supported size.")
                root = ET.fromstring(archive.read("word/document.xml"))
            text = " ".join(node.text or "" for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
        else:
            raise ResumeParseError("Upload a PDF or DOCX file so SmartHire can read its skills.")
    except ResumeParseError:
        raise
    except Exception as exc:
        raise ResumeParseError("We couldn't read this CV. Try a text-based PDF or a valid DOCX file.") from exc
    upload.seek(0)
    if not text.strip():
        raise ResumeParseError("No selectable text was found. Scanned PDFs need OCR; upload a text-based PDF or DOCX.")
    return text[:150_000]


def _profile_evidence(profile, resume_text=""):
    pieces = [profile.skills, profile.resume_skills, profile.headline, profile.bio, resume_text]
    return "\n".join(piece for piece in pieces if piece)


def calculate_match(job, profile, resume_text=""):
    required = split_skills(job.required_skills)
    evidence = _profile_evidence(profile, resume_text)
    found = extract_skills(evidence, extra_skills=required)
    found_keys = {normalize_skill(skill) for skill in found}
    # Preserve manually entered skill phrases, including job-specific names.
    found_keys.update(normalize_skill(skill) for skill in split_skills(profile.skills))
    matched, missing = [], []
    for skill in required:
        (matched if normalize_skill(skill) in found_keys else missing).append(skill)
    score = round(100 * len(matched) / len(required)) if required else 0
    return {"score": score, "matched": matched, "missing": missing, "candidate_skills": found}
