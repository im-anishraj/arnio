import re
import sys


def slugify(heading):
    slug = heading.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def extract_defined_anchors(content):
    anchors = set()
    for m in re.finditer(r"^#{1,6}\s+(.+)$", content, re.MULTILINE):
        anchors.add(slugify(m.group(1)))
    for m in re.finditer(r'<a\s+name=["\']([^"\']+)["\']', content):
        anchors.add(m.group(1).lower())
    return anchors


def extract_used_anchors(content):
    return set(re.findall(r"\(#([^)]+)\)", content))


filepath = sys.argv[1] if len(sys.argv) > 1 else "API_REFERENCE.md"
with open(filepath, encoding="utf-8") as f:
    content = f.read()

defined = extract_defined_anchors(content)
used = extract_used_anchors(content)
broken = used - defined

if broken:
    print(f"BROKEN anchors in {filepath}:")
    for a in sorted(broken):
        print(f"  #{a}")
    sys.exit(1)
else:
    print(f"All {len(used)} anchor links resolve correctly.")
