#!/usr/bin/env python3
"""Install an already reviewed V8 Blender output, preserving the legacy procedural generator."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent.parent
    source=args.output.resolve()
    spec=importlib.util.spec_from_file_location('generator',root/'scripts/blender-exterior.py')
    generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
    receipt=json.loads((source/'validation.json').read_text())
    assert receipt['registration']==generator.REGISTRATION_TEXT
    assert receipt.get('geometry_revision')==generator.GEOMETRY_REVISION, 'requires the V8 wing-root and gear revision'
    assert receipt.get('coordinate_conversion')=='proper rotation: x,-y,-z; no reflection'
    containment=json.loads((source/'interior-checks.json').read_text())
    assert set(containment)=={'LOD0','LOD1','LOD2'}
    assert all(not value['violations'] for value in containment.values())
    names=['exterior.glb','exterior-lod1.glb','exterior-lod2.glb']
    # Idempotent name normalization preserves the format-2 motion bindings.
    staged=tempfile.TemporaryDirectory(prefix='fc-plane-pack-')
    normalized=Path(staged.name)
    for name in names:(normalized/name).write_bytes(generator.normalize_node_names((source/name).read_bytes()))
    reports=[generator.validate_glb(normalized/name,lod) for lod,name in enumerate(names)]
    for report in reports[1:]:generator.validate_lod_bounds(reports[0],report)
    for name in names:
        data=(source/name).read_bytes();size=struct.unpack_from('<I',data,12)[0]
        doc=json.loads(data[20:20+size]);nodes={n['name'] for n in doc['nodes']}
        assert not any(n.startswith('brake_line_') for n in nodes), 'requires V6 without brake lines'
        assert 'step_left_support' in nodes, 'requires V6-final with the rigid boarding platform'
    for camera in list(generator.VIEWS)+list(generator.ORTHO_VIEWS):
        assert (source/('cycles-'+camera+'.png')).is_file()
    for name in ['basecolor','metallic-roughness','normal','ao','emissive','curvature']:
        data=(source/(name+'.png')).read_bytes()
        assert data[:8]==b'\x89PNG\r\n\x1a\n'
        assert struct.unpack_from('>II',data,16)==(generator.TEXTURE_SIZE,generator.TEXTURE_SIZE)
    cameras=json.loads((source/'cameras.json').read_text())
    assert set(cameras)==set(generator.VIEWS)|set(generator.ORTHO_VIEWS)
    assert cameras==receipt['cameras']
    assert (source/'orthographic-dimensions.json').is_file()
    definition=json.loads((root/'exterior.json').read_text())
    definition['lod2']='exterior-lod2.glb'
    definition['registration']['text']=generator.REGISTRATION_TEXT
    definition['registration']['surface']={
        'node':'airframe','x_m':[-4.68,-3.17],'z_m':[-.23,.10],'height_m':.30,
        'background':list(generator.WHITE[:3]),'color':list(generator.NAVY[:3]),
    }
    manifest=json.loads((root/'pack.json').read_text())
    entries=[i for i,value in enumerate(manifest['exterior']) if value['aircraft']==definition['aircraft']]
    assert len(entries)==1
    manifest['exterior'][entries[0]]=definition
    # All acceptance checks finish before any installed asset is replaced.
    for name in names:shutil.copyfile(normalized/name,root/name)
    textures=root/'textures/exterior';textures.mkdir(parents=True,exist_ok=True)
    for name in ['basecolor','metallic-roughness','normal','ao','emissive','curvature']:
        shutil.copyfile(source/(name+'.png'),textures/(name+'.png'))
    (root/'exterior.json').write_text(json.dumps(definition,indent=2)+'\n')
    (root/'pack.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (root/'docs/exterior-blender-validation.json').write_text(json.dumps(dict(
        geometry_revision=receipt['geometry_revision'],blender=receipt['blender'],
        source_script='scripts/blender-exterior.py',
        source_sha256=hashlib.sha256((root/'scripts/blender-exterior.py').read_bytes()).hexdigest(),
        registration=generator.REGISTRATION_TEXT,lods=reports,blender_lods=receipt['lods'],
        node_name_mapping=generator.PACK_NODE_NAMES,containment=containment),indent=2)+'\n')
    shutil.copyfile(source/'cameras.json',root/'docs/exterior-cameras.json')
    print(json.dumps(dict(installed=[r['file'] for r in reports],triangles=[r['triangles'] for r in reports],registration=generator.REGISTRATION_TEXT),indent=2))


if __name__=='__main__':main()
