#!/usr/bin/env python3
"""Assemble unchanged Cycles/engine PNGs into a self-contained side-by-side proof page."""
import argparse
import base64
import html
import json
from pathlib import Path
import struct


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cycles',type=Path); parser.add_argument('engine',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    cameras=json.loads((args.cycles/'cameras.json').read_text())
    engine_cameras=json.loads((args.engine/'cameras.json').read_text())
    if cameras!=engine_cameras:
        parser.error('Camera manifests differ; proof requires the same eyes, targets, up vectors, FOVs, and sizes.')
    rows=[]
    for name,camera in cameras.items():
        images=[]
        for folder,prefix,label in [(args.cycles,'cycles','Cycles'),(args.engine,'engine','FlightCraft')]:
            path=folder/(prefix+'-'+name+'.png')
            if path.stat().st_size>16*1024*1024: raise ValueError('Oversized preview: '+str(path))
            png=path.read_bytes()
            if png[:8]!=b'\x89PNG\r\n\x1a\n' or list(struct.unpack_from('>II',png,16))!=camera['size']:
                raise ValueError('Preview size does not match camera manifest: '+str(path))
            encoded=base64.b64encode(png).decode('ascii')
            images.append('<figure><figcaption>'+label+'</figcaption><img alt="'+label+' '+html.escape(name,quote=True)+'" src="data:image/png;base64,'+encoded+'"></figure>')
        rows.append('<section><h2>'+html.escape(name)+'</h2><div>'+''.join(images)+'</div></section>')
    document='''<!doctype html><meta charset="utf-8"><title>Sling 2 exterior proof</title>
<style>body{background:#17191d;color:#eee;font:16px system-ui;margin:2rem}section{margin:2rem 0}section div{display:grid;grid-template-columns:1fr 1fr;gap:1rem}figure{margin:0}img{width:100%;height:auto}figcaption{padding:.6rem}p{max-width:70rem}</style>
<h1>Sling 2 exterior proof</h1><p>Unmodified renders with identical recorded cameras. Lighting differs between Cycles and FlightCraft; compare shape, material response, glass, and visible interior. This page does not establish real-aircraft fidelity or replace visual review.</p>'''+''.join(rows)
    args.output.write_text(document)
    print(args.output)


if __name__=='__main__': main()
