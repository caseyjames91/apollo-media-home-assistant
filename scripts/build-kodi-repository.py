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

# Kodi 21 requires a SHA-256 sidecar when a package hash cannot be
# obtained from the HTTP response. Generate one for every repository ZIP.
def write_sha256_sidecars(repository_root):
    import hashlib
    from pathlib import Path

    root = Path(repository_root)
    for zip_path in root.rglob("*.zip"):
        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        sidecar = zip_path.with_name(zip_path.name + ".sha256")
        sidecar.write_text(digest + "\n", encoding="utf-8")
        print(f"SHA256: {sidecar}")

if __name__ == "__main__":
    write_sha256_sidecars("kodi-repository")
