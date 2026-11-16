import re
import math
from concurrent.futures import ThreadPoolExecutor
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
    "Flask", "FastAPI", "Pandas", "NumPy", "PyTorch", "TensorFlow", "Scikit-learn",
    "Jupyter", "R Programming", "Statistics", "Data Engineering", "Data Cleaning",
    "Data Modeling", "ETL", "BigQuery", "Snowflake", "Apache Spark", "Looker",
    "SQLite", "SQL Server", "Oracle Database", "Redis", "Elasticsearch",
    "Spring Boot", "ASP.NET", "Laravel", "Symfony", "Ruby on Rails", "Express.js",
    "GraphQL", "REST API Development", "WebSockets", "Microservices", "API Testing",
    "Vue.js", "Angular", "Next.js", "Svelte", "Bootstrap", "Tailwind CSS",
    "Responsive Design", "Accessibility", "Web Design", "Prototyping", "Wireframing",
    "Design Systems", "User Research", "Usability Testing", "Product Design",
    "DevOps", "CI/CD", "Kubernetes", "Terraform", "Jenkins", "GitHub Actions",
    "Nginx", "Apache", "Networking", "System Administration", "Information Security",
    "Penetration Testing", "OWASP", "Incident Response", "Linux Administration",
    "Android Development", "iOS Development", "Flutter", "React Native", "SwiftUI",
    "Business Analysis", "Requirements Analysis", "Product Management", "Scrum",
    "Jira", "Project Coordination", "Technical Writing", "Documentation",
    "Search Engine Optimization", "SEO", "Social Media Marketing", "Content Marketing",
    "Google Analytics", "Email Marketing", "Copywriting", "Graphic Design",
    "Adobe Photoshop", "Adobe Illustrator", "Video Editing", "Public Relations",
    "Financial Analysis", "Financial Modeling", "Bookkeeping", "Tax Preparation",
    "Payroll", "QuickBooks", "Budgeting", "Auditing", "Human Resources",
    "Talent Acquisition", "Interviewing", "Applicant Tracking Systems", "Recruitment",
    "Customer Support", "Customer Success", "Technical Support", "Salesforce",
    "CRM", "Lead Generation", "Negotiation", "Presentation Skills", "Teamwork",
    "Time Management", "Problem Solving", "Critical Thinking", "Attention to Detail",
    "Written Communication", "Verbal Communication", "Conflict Resolution",
)
ALIASES = {
    "js": "javascript", "nodejs": "node.js", "node js": "node.js",
    "postgres": "postgresql", "powerbi": "power bi", "power-bi": "power bi",
    "ml": "machine learning", "natural language processing": "nlp",
    "qa": "quality assurance", "ux": "ux design", "ui": "ui design",
    "restful api": "rest api", "rest apis": "rest api", "restful services": "rest api", "rest api development": "rest api",
    "reactjs": "react", "react js": "react", "ts": "typescript",
}

RELATED_SKILLS = {
    "Python": ("Django", "Flask", "FastAPI", "Pandas", "NumPy", "PyTorch", "TensorFlow", "Scikit-learn", "Jupyter"),
    "JavaScript": ("TypeScript", "React", "Node.js", "Vue.js", "Angular", "Next.js", "Express.js", "HTML", "CSS"),
    "SQL": ("PostgreSQL", "MySQL", "SQLite", "SQL Server", "Oracle Database", "Data Modeling", "Query Optimization"),
    "Data Analysis": ("Excel", "Power BI", "Tableau", "Looker", "Statistics", "Python", "SQL", "Data Visualization"),
    "Design": ("UX Design", "UI Design", "Product Design", "Figma", "User Research", "Prototyping", "Wireframing", "Design Systems"),
    "Cloud": ("AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Terraform", "CI/CD", "DevOps"),
    "Cybersecurity": ("Information Security", "Penetration Testing", "OWASP", "Incident Response", "Network Security", "Security Auditing"),
    "Marketing": ("SEO", "Content Marketing", "Social Media Marketing", "Email Marketing", "Google Analytics", "Copywriting", "Lead Generation"),
    "Finance": ("Accounting", "Bookkeeping", "Financial Analysis", "Financial Modeling", "Auditing", "Tax Preparation", "Payroll", "Budgeting"),
    "Recruitment": ("Human Resources", "Talent Acquisition", "Interviewing", "Applicant Tracking Systems", "Communication", "Scheduling"),
    "Project Management": ("Agile", "Scrum", "Jira", "Project Coordination", "Requirements Analysis", "Communication", "Leadership"),
    "Customer Service": ("Customer Support", "Customer Success", "Technical Support", "Communication", "Conflict Resolution", "CRM"),
}


def suggest_skills(prefix, limit=18):
    """Return prefix matches first, then related skills from the same area."""
    query = normalize_skill(prefix)
    if len(query) < 2:
        return []

    def matches_prefix(skill):
        words = re.findall(r"[a-z0-9+#.]+", normalize_skill(skill))
        return any(word.startswith(query) for word in words)

    direct = [skill for skill in SKILL_CATALOG if matches_prefix(skill)]
    related = []
    for group_name, group_skills in RELATED_SKILLS.items():
        if matches_prefix(group_name) or any(skill in direct for skill in group_skills):
            related.extend(group_skills)
    direct_set = {normalize_skill(skill) for skill in direct}
    ordered = direct + [skill for skill in related if normalize_skill(skill) not in direct_set]
    seen = set()
    suggestions = []
    for skill in ordered:
        normalized = normalize_skill(skill)
        if normalized not in seen:
            suggestions.append(skill)
            seen.add(normalized)
        if len(suggestions) == limit:
            break
    return suggestions


class ResumeParseError(ValueError):
    pass


def normalize_skill(value):
    value = re.sub(r"[^a-z0-9+#. ]+", " ", str(value or "").casefold())
    value = re.sub(r"\s+", " ", value).strip()
    return ALIASES.get(value, value)


SKILL_RELATIONSHIP_EDGES = (
    ("sql", "postgresql", 0.82), ("sql", "mysql", 0.82), ("sql", "sqlite", 0.78),
    ("sql", "sql server", 0.78), ("postgresql", "mysql", 0.68),
    ("javascript", "typescript", 0.84), ("react", "react native", 0.70),
    ("django", "flask", 0.66), ("django", "fastapi", 0.66), ("flask", "fastapi", 0.66),
    ("aws", "azure", 0.72), ("aws", "google cloud", 0.72), ("azure", "google cloud", 0.72),
    ("power bi", "tableau", 0.82), ("power bi", "looker", 0.74), ("tableau", "looker", 0.74),
    ("ux design", "ui design", 0.72), ("ux design", "product design", 0.76),
    ("selenium", "software testing", 0.78), ("api testing", "software testing", 0.78),
    ("excel", "google sheets", 0.76), ("project management", "project coordination", 0.72),
    ("recruitment", "talent acquisition", 0.82), ("customer service", "customer support", 0.86),
    ("machine learning", "scikit-learn", 0.75), ("machine learning", "pytorch", 0.68),
    ("machine learning", "tensorflow", 0.68), ("data analysis", "data visualization", 0.72),
    ("html", "css", 0.55), ("docker", "kubernetes", 0.60),
)


def _skill_graph():
    graph = {}
    for left, right, weight in SKILL_RELATIONSHIP_EDGES:
        left, right = normalize_skill(left), normalize_skill(right)
        graph.setdefault(left, {})[right] = weight
        graph.setdefault(right, {})[left] = weight
    return graph


SKILL_GRAPH = _skill_graph()


def _best_skill_evidence(required, candidate_skills):
    """Find exact, alias-equivalent, or up to two weighted relationship hops."""
    required_key = normalize_skill(required)
    candidates = [(normalize_skill(label), label) for label in candidate_skills]
    exact = next(((1.0, label) for key, label in candidates if key == required_key), None)
    if exact:
        return exact

    best = (0.0, "")
    direct = SKILL_GRAPH.get(required_key, {})
    for candidate_key, label in candidates:
        if candidate_key in direct and direct[candidate_key] > best[0]:
            best = (direct[candidate_key], label)
        for middle, first_weight in direct.items():
            second_weight = SKILL_GRAPH.get(middle, {}).get(candidate_key, 0)
            score = first_weight * second_weight * 0.85
            if candidate_key != required_key and score > best[0]:
                best = (score, label)
    return best


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


def extract_resume_facts(text):
    """Heuristically detect education level and stated years of experience."""
    text = str(text or "")[:150_000]
    education_patterns = (
        ("doctorate", r"\b(?:ph\.?d\.?|doctorate|doctoral degree)\b"),
        ("master", r"\b(?:master(?:'s)?|m\.s\.?|m\.a\.?|mba)\b"),
        ("bachelor", r"\b(?:bachelor(?:'s)?|b\.s\.?|b\.a\.?|b\.sc\.?)\b"),
        ("intermediate", r"\b(?:intermediate|a[ -]?levels?)\b"),
        ("secondary", r"\b(?:matric(?:ulation)?|secondary school|high school)\b"),
    )
    education_level = next((level for level, pattern in education_patterns if re.search(pattern, text, re.IGNORECASE)), "")
    experience = re.search(r"\b(\d{1,2}(?:\.\d)?)\s*\+?\s+years?\s+(?:of\s+)?(?:relevant\s+|professional\s+)?experience\b", text, re.IGNORECASE)
    experience_years = float(experience.group(1)) if experience else None
    return {"education_level": education_level, "experience_years": experience_years}


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
    preferred = split_skills(job.preferred_skills)
    evidence = _profile_evidence(profile, resume_text)
    found = extract_skills(evidence, extra_skills=required + preferred)
    # Preserve manually entered skill phrases, including job-specific names.
    candidate_labels = list(dict.fromkeys(found + split_skills(profile.skills)))
    matched, missing = [], []
    related_matches = []
    required_strengths = []
    for skill in required:
        strength, evidence_skill = _best_skill_evidence(skill, candidate_labels)
        required_strengths.append(strength)
        if strength >= 0.999:
            matched.append(skill)
        elif strength > 0:
            related_matches.append(f"{evidence_skill} → {skill} ({round(strength * 100)}% related credit)")
        else:
            missing.append(skill)

    preferred_strengths = []
    matched_preferred = []
    for skill in preferred:
        strength, evidence_skill = _best_skill_evidence(skill, candidate_labels)
        preferred_strengths.append(strength)
        if strength >= 0.999:
            matched_preferred.append(skill)
        elif strength > 0:
            related_matches.append(f"{evidence_skill} → preferred: {skill} ({round(strength * 100)}% related credit)")

    if required and preferred:
        required_weight, preferred_weight = 40, 10
    elif required:
        required_weight, preferred_weight = 50, 0
    elif preferred:
        required_weight, preferred_weight = 0, 50
    else:
        required_weight, preferred_weight = 50, 0
    required_score = required_weight * sum(required_strengths) / len(required) if required else required_weight
    preferred_score = preferred_weight * sum(preferred_strengths) / len(preferred) if preferred else preferred_weight

    required_experience = float(job.experience_years or 0)
    candidate_experience = float(profile.experience_years or 0)
    if required_experience <= 0:
        experience_score = 20
    else:
        experience_score = 20 * min(candidate_experience / required_experience, 1) if profile.experience_years is not None else 0

    education_ranks = {"secondary": 1, "intermediate": 2, "bachelor": 3, "master": 4, "doctorate": 5}
    required_education = job.minimum_education or ""
    candidate_education = profile.education_level or ""
    if not required_education:
        education_score = 10
    elif candidate_education and education_ranks.get(candidate_education, 0) >= education_ranks.get(required_education, 99):
        education_score = 10
    else:
        education_score = 0

    # Transparent token-vector similarity keeps the score explainable and works offline.
    stop_words = {"and", "the", "for", "with", "from", "this", "that", "have", "has", "will", "you", "your", "our", "are", "job", "role", "work", "years", "year", "experience", "required", "preferred", "skills", "team", "candidate"}
    token_pattern = re.compile(r"[a-z][a-z0-9+#.]{1,}")
    candidate_text = " ".join((evidence, candidate_education))
    job_text = " ".join((job.title, job.description, job.required_skills, job.preferred_skills))
    candidate_counts = {}
    job_counts = {}
    for token in token_pattern.findall(candidate_text.casefold()):
        if token not in stop_words:
            candidate_counts[token] = candidate_counts.get(token, 0) + 1
    for token in token_pattern.findall(job_text.casefold()):
        if token not in stop_words:
            job_counts[token] = job_counts.get(token, 0) + 1
    common_tokens = candidate_counts.keys() & job_counts.keys()
    dot = sum(candidate_counts[token] * job_counts[token] for token in common_tokens)
    candidate_norm = math.sqrt(sum(value * value for value in candidate_counts.values()))
    job_norm = math.sqrt(sum(value * value for value in job_counts.values()))
    text_similarity = dot / (candidate_norm * job_norm) if candidate_norm and job_norm else 0
    text_score = 20 * text_similarity

    breakdown = {
        "required_skills": round(required_score), "preferred_skills": round(preferred_score),
        "experience": round(experience_score), "education": round(education_score),
        "text_similarity": round(text_score),
    }
    score = max(0, min(100, round(sum(breakdown.values()))))
    explanation = (
        f"Required skills {breakdown['required_skills']}/{required_weight}; preferred skills {breakdown['preferred_skills']}/{preferred_weight}; "
        f"experience {breakdown['experience']}/20; education {breakdown['education']}/10; "
        f"job text relevance {breakdown['text_similarity']}/20."
    )
    if related_matches:
        explanation += " Related skill credit: " + "; ".join(related_matches) + "."
    return {
        "score": score, "matched": matched, "missing": missing, "related": related_matches,
        "matched_preferred": matched_preferred,
        "candidate_skills": found, "breakdown": breakdown, "explanation": explanation,
    }


def calculate_match_batch(job_profile_pairs, max_workers=4):
    """Calculate independent job/profile matches concurrently, without ORM work in workers."""
    pairs = list(job_profile_pairs)
    if not pairs:
        return []
    if len(pairs) == 1:
        job, profile = pairs[0]
        return [calculate_match(job, profile)]

    worker_count = max(1, min(max_workers, len(pairs)))
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="smarthire-match") as pool:
        return list(pool.map(_calculate_match_pair, pairs))


def _calculate_match_pair(pair):
    job, profile = pair
    return calculate_match(job, profile)
