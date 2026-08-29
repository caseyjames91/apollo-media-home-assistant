#!/usr/bin/env python3
from pathlib import Path
import hashlib, re, shutil, tempfile, zipfile, xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'kodi' / 'plugin.video.apollomedia'
REPO = ROOT / 'kodi-repository'
manifest = (SRC / 'addon.xml').read_text(encoding='utf-8')
version = ET.fromstring(manifest).attrib['version']
outdir=REPO/'plugin.video.apollomedia'; outdir.mkdir(parents=True, exist_ok=True)
zip_path=outdir/f'plugin.video.apollomedia-{version}.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for p in SRC.rglob('*'):
        if not p.is_file() or 'tests' in p.parts or p.name.startswith('PATCH_NOTES_') or p.name.endswith('.pyc') or '__pycache__' in p.parts: continue
        z.write(p, Path('plugin.video.apollomedia')/p.relative_to(SRC))
(outdir/'addon.xml').write_text(manifest,encoding='utf-8')
repo_manifest=(REPO/'repository.apollomedia'/'addon.xml').read_text(encoding='utf-8')
def strip_decl(s): return '\n'.join(x for x in s.splitlines() if not x.lstrip().startswith('<?xml'))
addons='<?xml version="1.0" encoding="UTF-8"?>\n<addons>\n'+strip_decl(manifest.strip())+'\n'+strip_decl(repo_manifest.strip())+'\n</addons>\n'
ET.fromstring(addons)
(REPO/'addons.xml').write_text(addons,encoding='utf-8')
(REPO/'addons.xml.md5').write_text(hashlib.md5(addons.encode()).hexdigest(),encoding='ascii')
print(f'PASS: built Kodi repository for Apollo Media {version}')
