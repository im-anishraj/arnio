import os
import sys
import yaml

TEMPLATES_DIR = ".github/ISSUE_TEMPLATE"
LABELS_FILE = ".github/labels.yml"

def get_live_labels():
    with open(LABELS_FILE) as f:
        labels = yaml.safe_load(f)
    return {label["name"] for label in labels}

def get_template_labels():
    used = {}
    for fname in os.listdir(TEMPLATES_DIR):
        if not fname.endswith(".yml"):
            continue
        path = os.path.join(TEMPLATES_DIR, fname)
        with open(path) as f:
            data = yaml.safe_load(f)
        if isinstance(data.get("labels"), list):
            used[fname] = data["labels"]
    return used

def main():
    live = get_live_labels()
    templates = get_template_labels()
    errors = []

    for fname, labels in templates.items():
        for label in labels:
            if label not in live:
                errors.append(f"  [{fname}] unknown label: '{label}'")

    if errors:
        print("Label mismatch found:")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("All template labels match live taxonomy.")

if __name__ == "__main__":
    main()