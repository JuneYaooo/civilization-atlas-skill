#!/usr/bin/env python3
"""Install a portable skill payload; never overwrite an existing installation."""
import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = 'civilization-atlas'
PAYLOAD = ('SKILL.md', 'agents/openai.yaml', 'references', 'scripts/casebook.py', 'LICENSE')


def copy_payload(source, target):
    allowed = set(json.loads((source / 'PUBLIC_FILES.json').read_text())['files'])
    for relative in PAYLOAD:
        candidate = source / relative
        entries = [candidate] + (list(candidate.rglob('*')) if candidate.is_dir() else [])
        for entry in entries:
            if entry.is_symlink():
                raise ValueError('Refusing symlink in payload')
            if entry.is_file() and entry.relative_to(source).as_posix() not in allowed:
                raise ValueError('Refusing payload file outside public manifest')
    for relative in PAYLOAD:
        src, dst = source / relative, target / relative
        if not src.exists():
            raise FileNotFoundError(f'payload missing: {relative}')
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
        else:
            shutil.copy2(src, dst)



def install(source, parent):
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / NAME
    if target.exists() or target.is_symlink():
        raise FileExistsError(f'{target} already exists; preserve it and review updates explicitly')
    with tempfile.TemporaryDirectory(prefix='.civilization-atlas-', dir=parent) as temp:
        staging = Path(temp) / NAME
        staging.mkdir()
        copy_payload(source, staging)
        if target.exists() or target.is_symlink():
            raise FileExistsError(f'{target} appeared while installing')
        staging.rename(target)
    return target


def package(source, archive):
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        staging = Path(temp) / NAME
        staging.mkdir()
        copy_payload(source, staging)
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(staging.rglob('*')):
                if path.is_file():
                    z.write(path, path.relative_to(staging.parent))
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dest', type=Path, help='parent skills directory; defaults to CODEX_HOME/skills')
    parser.add_argument('--zip', type=Path, help='create portable archive instead of installing; must not exist')
    args = parser.parse_args()
    if args.zip and args.dest:
        parser.error('choose --zip or --dest')
    try:
        if args.zip:
            result = package(ROOT, args.zip.expanduser().resolve())
        else:
            codex_dir = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
            result = install(ROOT, (args.dest or codex_dir / 'skills').expanduser().resolve())
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == '__main__':
    sys.exit(main())
