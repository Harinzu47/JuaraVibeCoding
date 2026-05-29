import os
import re

# The order matters. Replace longer matches first.
REPLACEMENTS = [
    (re.compile(r"AturModal", re.IGNORECASE), "AturModal"),
    (re.compile(r"Atur Modal", re.IGNORECASE), "Atur Modal"),
    (re.compile(r"AturModal", re.IGNORECASE), "AturModal"),
    (re.compile(r"aturmodal", re.IGNORECASE), "aturmodal"),
    (re.compile(r"atur-modal", re.IGNORECASE), "atur-modal"),
    (re.compile(r"ATURMODAL", re.IGNORECASE), "ATURMODAL"),
]

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return

    original = content
    for pattern, replacement in REPLACEMENTS:
        # We use re.sub with ignorecase for some, but actually the patterns
        # handle case variations if we don't strictly use IGNORECASE where it changes meaning.
        # But wait, AturModal -> AturModal (exact case) is better.
        pass

    # A simpler exact replacement approach to preserve casing
    replacements_exact = {
        "AturModal": "AturModal",
        "AturModal": "AturModal",
        "aturmodal": "aturmodal",
        "Atur Modal": "Atur Modal",
        "atur-modal": "atur-modal",
        "ATURMODAL": "ATURMODAL",
    }
    
    for old, new in replacements_exact.items():
        content = content.replace(old, new)
        
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")

def main():
    skip_dirs = {'.git', 'node_modules', '.venv', '__pycache__', 'dist', 'build', '.pytest_cache'}
    skip_exts = {'.png', '.jpg', '.jpeg', '.pdf', '.pyc', '.ico'}
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in skip_exts:
                continue
            filepath = os.path.join(root, file)
            process_file(filepath)

if __name__ == '__main__':
    main()
