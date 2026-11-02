#!/usr/bin/env python3
"""Generate an ignored manifest using a sibling engine checkout for offline local builds."""
import os
from pathlib import Path
import re
root = Path(__file__).resolve().parent.parent
engine = Path(os.environ.get('FLIGHTCRAFT_ENGINE', root.parent / 'flightcraft')).resolve()
manifest = (root / 'Cargo.toml').read_text()
for crate in ['aero', 'sim', 'world', 'control', 'ui', 'render']:
    name = 'flightcraft-' + crate
    replacement = name + ' = { path = "' + (engine / 'crates' / crate).as_posix() + '" }'
    manifest = re.sub(r'^' + name + r' = \{ git = [^\n]+$', lambda _: replacement, manifest, flags=re.M)
manifest = manifest.replace('path = "src/', 'path = "../src/').replace('path = "tests/', 'path = "../tests/')
out = root / '.local-harness'
out.mkdir(exist_ok=True)
(out / 'Cargo.toml').write_text(manifest)
print('Local harness manifest prepared.')
