import re
import yaml


def parse_frontmatter(html: str) -> tuple[dict, str]:
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, html, re.DOTALL)

    if not match:
        pattern2 = r"^---\s*\n(.*?)\n---\s*$(.*)"
        m2 = re.match(pattern2, html, re.DOTALL)
        if not m2:
            return {}, html
        front_raw = m2.group(1)
        content = m2.group(2).lstrip("\n")
        try:
            fm = yaml.safe_load(front_raw)
            return fm or {}, content
        except Exception:
            return {}, html

    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, html

    content = match.group(2)

    return frontmatter or {}, content


def add_frontmatter(html: str, metadata: dict) -> str:
    frontmatter_yaml = yaml.dump(metadata, default_flow_style=False)
    return f"---\n{frontmatter_yaml}---\n{html}"
