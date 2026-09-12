import re
import uuid


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    slug = re.sub(r"[\s_-]+", "-", cleaned)
    if not slug:
        slug = f"project-{uuid.uuid4().hex[:6]}"
    return slug[:80]
