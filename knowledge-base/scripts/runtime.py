"""Verify and expand the bundled database into a content-addressed local cache."""
from pathlib import Path
import gzip,hashlib,json,os,tempfile
ROOT=Path(__file__).resolve().parents[1]
_cached=None

def file_hash(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def database_path():
 global _cached
 if _cached is not None:return _cached
 local=ROOT/'data/history.sqlite'
 if local.exists():return local
 meta=json.loads((ROOT/'data/bundle.json').read_text())
 archive=ROOT/'data'/meta['archive']
 if file_hash(archive)!=meta['archive_sha256']:raise ValueError('Bundled database checksum mismatch')
 parent=Path(os.environ.get('HISTORY_KB_CACHE',str(Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'civilization-atlas/knowledge'))).expanduser()
 parent.mkdir(parents=True,exist_ok=True);target=parent/(meta['database_sha256']+'.sqlite')
 if target.exists() and file_hash(target)==meta['database_sha256']:_cached=target;return target
 fd,name=tempfile.mkstemp(prefix='.expanding-',dir=parent);temp=Path(name)
 try:
  h=hashlib.sha256();size=0
  with os.fdopen(fd,'wb') as output,gzip.open(archive,'rb') as source:
   for block in iter(lambda:source.read(1024*1024),b''):
    size+=len(block)
    if size>meta['database_bytes']:raise ValueError('Unexpected database expansion size')
    output.write(block);h.update(block)
  if size!=meta['database_bytes'] or h.hexdigest()!=meta['database_sha256']:raise ValueError('Expanded database checksum mismatch')
  os.replace(temp,target);_cached=target;return target
 finally:
  if temp.exists():temp.unlink()
