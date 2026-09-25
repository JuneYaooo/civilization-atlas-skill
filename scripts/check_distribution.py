#!/usr/bin/env python3
"""Check the explicit public-file boundary and common accidental disclosures.

This is a bounded release check, not proof that every conceivable secret is absent.
Manual semantic review remains necessary before expanding the manifest.
"""
import json
import gzip
import hashlib
import zipfile
import tempfile
import sqlite3
import shutil
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def check():
    manifest = json.loads((ROOT / 'PUBLIC_FILES.json').read_text())
    allowed = set(manifest['files'])
    problems = []
    actual = set()
    for path in ROOT.rglob('*'):
        rel = path.relative_to(ROOT)
        if any(part in ('.git', 'dist', '__pycache__') for part in rel.parts):
            continue
        if path.is_symlink():
            problems.append(f'Symlink not allowed: {rel}')
        elif path.is_file():
            actual.add(rel.as_posix())
    for rel in sorted(actual ^ allowed):
        problems.append(f'File outside manifest or missing: {rel}')
    git = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True)
    if git.returncode == 0:
        for rel in git.stdout.decode().split('\0'):
            if rel and rel not in allowed:
                problems.append(f'Tracked file outside manifest: {rel}')
    checks = {
        'private key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'access token': r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',
        'personal absolute path': r'(?:/Users/|/home/)[A-Za-z0-9_.-]+/',
        'email': r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        'URL credentials': r'https?://[^\s/:]+:[^\s/@]+@',
    }
    for rel in sorted(actual & allowed):
        try:
            path = ROOT / rel
            if rel in manifest.get('binary_files', {}):
                expected = manifest['binary_files'][rel]
                if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    problems.append(f'Binary checksum mismatch: {rel}')
                if path.suffix == '.gz':
                    with tempfile.TemporaryDirectory() as temp:
                        unpacked = Path(temp) / 'inspection.sqlite'
                        with gzip.open(path, 'rb') as content, unpacked.open('wb') as out:
                            shutil.copyfileobj(content, out)
                        with sqlite3.connect(unpacked.as_uri() + '?mode=ro', uri=True) as db:
                            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                                problems.append(f'Invalid SQLite database: {rel}')
                            text = '\n'.join(db.iterdump())
                elif path.suffix == '.xlsx':
                    with zipfile.ZipFile(path) as archive:
                        text = '\n'.join(archive.read(n).decode('utf-8') for n in archive.namelist() if n.endswith('.xml'))
                elif path.suffix in ('.png', '.jpg', '.gif'):
                    # Screenshots require visual review; hashes bind that review to exact bytes.
                    signatures = {'.jpg': (b'\xff\xd8\xff',), '.png': (b'\x89PNG\r\n\x1a\n',), '.gif': (b'GIF87a', b'GIF89a')}
                    if not path.read_bytes().startswith(signatures[path.suffix]):
                        problems.append(f'Invalid image signature: {rel}')
                    continue
                else:
                    problems.append(f'Unsupported binary type: {rel}')
                    continue
            else:
                text = path.read_text()
        except UnicodeError:
            problems.append(f'Unexpected binary file: {rel}')
            continue
        for label, pattern in checks.items():
            inspected = re.sub(r'https?://[^\s\"<>]+', '', text) if label == 'personal absolute path' else text
            if re.search(pattern, inspected):
                problems.append(f'{label} pattern found in {rel}')
        if (ROOT / rel).suffix == '.md':
            for target in re.findall(r'\]\(([^)]+)\)', text):
                if not target.startswith(('https://', 'http://', '#')):
                    resolved = (ROOT / rel).parent / target.split('#')[0]
                    if not resolved.exists():
                        problems.append(f'Broken local link in {rel}')
    return problems


if __name__ == '__main__':
    errors = check()
    if errors:
        print('\n'.join(errors))
        raise SystemExit(1)
    print('Public manifest, local links and common disclosure-pattern checks passed.')
