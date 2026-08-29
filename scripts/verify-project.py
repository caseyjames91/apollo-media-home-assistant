#!/usr/bin/env python3
from pathlib import Path
import hashlib, re, sys, zipfile, xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[1]
addon=(R/'kodi/plugin.video.apollomedia/addon.xml').read_text(); v=ET.fromstring(addon).attrib['version']
ET.parse(R/'kodi-repository/addons.xml')
md5=hashlib.md5((R/'kodi-repository/addons.xml').read_bytes()).hexdigest()
assert md5==(R/'kodi-repository/addons.xml.md5').read_text().strip()
z=R/'kodi-repository/plugin.video.apollomedia'/f'plugin.video.apollomedia-{v}.zip'
with zipfile.ZipFile(z) as f: assert f.testzip() is None
assert (R/'dist/apollo-media-card.js').read_bytes()==(R/'card/apollo-media-card.js').read_bytes()==(R/'kodi/apollo-media-card.js').read_bytes()
print(f'PASS: Apollo project distribution verified (Kodi/Card {v})')
