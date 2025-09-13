#!/usr/bin/env python3
import os
import sys
import fnmatch
import subprocess

ROOT = os.path.dirname(os.path.dirname(__file__))

def load_allowlist():
    path = os.path.join(ROOT, '.allowed_markdown.txt')
    patterns = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            patterns.append(s)
    return patterns

def is_allowed(relpath: str, patterns) -> bool:
    p = relpath.replace('\\', '/')
    for pat in patterns:
        if fnmatch.fnmatch(p, pat):
            return True
    return False

def get_staged_files():
    try:
        out = subprocess.check_output(['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'], cwd=ROOT)
        files = out.decode('utf-8').splitlines()
        return [f for f in files if f.lower().endswith('.md')]
    except Exception:
        md_files = []
        for r, _, files in os.walk(ROOT):
            for f in files:
                if f.lower().endswith('.md'):
                    rel = os.path.relpath(os.path.join(r, f), ROOT)
                    md_files.append(rel)
        return md_files

def main():
    allow = load_allowlist()
    md_files = get_staged_files()
    violations = []
    for rel in md_files:
        if not is_allowed(rel, allow):
            violations.append(rel)
    if violations:
        print('Markdown policy violation: the following .md files are not allowed by .allowed_markdown.txt:')
        for v in violations:
            print(f'  - {v}')
        print('\nAdd them under docs/ or whitelist them in .allowed_markdown.txt if needed.')
        return 1
    print('Markdown policy check passed.')
    return 0

if __name__ == '__main__':
    sys.exit(main())

