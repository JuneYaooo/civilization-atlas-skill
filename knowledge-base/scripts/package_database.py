#!/usr/bin/env python3
"""Compress a locally built database and bind its exact bytes to bundle metadata."""
from pathlib import Path
import gzip,hashlib,json,os,shutil,sqlite3,tempfile
ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def main():
    db=ROOT/'data/history.sqlite'
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as conn:
        if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or conn.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Invalid database')
        count=conn.execute('SELECT count(*) FROM records').fetchone()[0]
    archive=ROOT/'data/history.sqlite.gz'
    fd,name=tempfile.mkstemp(dir=archive.parent,suffix='.tmp')
    try:
        with os.fdopen(fd,'wb') as out,db.open('rb') as source:
            with gzip.GzipFile(filename='',fileobj=out,mode='wb',mtime=0) as z:shutil.copyfileobj(source,z)
        os.replace(name,archive)
    finally:
        if Path(name).exists():Path(name).unlink()
    meta=dict(archive=archive.name,archive_sha256=digest(archive),database_sha256=digest(db),database_bytes=db.stat().st_size,record_count=count)
    (ROOT/'data/bundle.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps(meta))

if __name__=='__main__':main()
