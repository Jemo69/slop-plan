import re
import yaml


def parse_frontmatter(html: str) -> tuple[dict, str]:
    pattern = r"^---\n(.*?)\n---\n(.*)$"
    match = re.match(pattern, html, re.DOTALL)
    
    if not match:
        return {}, html
    
    frontmatter = yaml.safe_load(match.group(1))
    content = match.group(2)
    
    return frontmatter or {}, content


def add_frontmatter(html: str, metadata: dict) -> str:
    frontmatter_yaml = yaml.dump(metadata, default_flow_style=False)
    return f"---\n{frontmatter_yaml}---\n{html}"
