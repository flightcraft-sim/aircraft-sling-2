#!/usr/bin/env python3
"""Install an already reviewed V11 Blender output, preserving the legacy procedural generator."""
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
    assert receipt.get('geometry_revision')==generator.GEOMETRY_REVISION, 'requires the V11 pilot-seat interior revision'
    source_sha256=hashlib.sha256((root/'scripts/blender-exterior.py').read_bytes()).hexdigest()
    assert receipt.get('source_sha256')==source_sha256, 'output must match the current queued V11 source exactly'
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
    required_interior={'glareshield','panel_silhouette','throttle_grip','center_console','baggage_bulkhead'}
    required_interior.update(prefix+str(side) for side in [-1,1] for prefix in [
        'seat_back_','seat_cushion_','control_stick_','stick_grip_','side_panel_','armrest_','rudder_pedal_'])
    assert all(reports[0]['mesh_triangles'].get(name,0)>0 for name in required_interior), 'missing visible V11 cabin fittings'
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
    assert set(cameras)==set(generator.VIEWS)|set(generator.ORTHO_VIEWS)|{'beauty-open','elevation-side-open'}
    for label in ('beauty-open','elevation-side-open'):assert (source/('cycles-'+label+'.png')).is_file()
    assert cameras==receipt['cameras']
    pilot_cameras=json.loads((source/'pilot-cameras.json').read_text())
    assert set(pilot_cameras)==set(generator.PILOT_LOOKS)
    for label,(yaw,pitch,fraction) in generator.PILOT_LOOKS.items():
        assert (source/('cycles-'+label+'.png')).is_file()
        assert pilot_cameras[label]['eye_body_m']==list(generator.PILOT_EYE_M)
        assert pilot_cameras[label]['canopy_open_fraction']==fraction
    assert (source/'orthographic-dimensions.json').is_file()
    definition=json.loads((root/'exterior.json').read_text())
    definition['moving_parts']=[p for p in definition['moving_parts'] if p['node']!='canopy_slide']
    definition['moving_parts'].append(dict(node='canopy_slide',motion='slide',axis=[-1,0,0],travel_m=generator.CANOPY_TRAVEL_M))
    definition['lod2']='exterior-lod2.glb'
    definition['interior']={'pilot_eye_m':list(generator.PILOT_EYE_M)}
    definition['registration']['text']=generator.REGISTRATION_TEXT
    definition['registration']['surface']={
        'node':'airframe','x_m':[-4.68,-3.17],'z_m':[-.23,.10],'height_m':.30,
        'background':list(generator.WHITE[:3]),'color':list(generator.NAVY[:3]),
    }
    manifest=json.loads((root/'pack.json').read_text())
    entries=[i for i,value in enumerate(manifest['exterior']) if value['aircraft']==definition['aircraft']]
    assert len(entries)==1
    manifest['format_version']=3
    manifest['version']='0.4.0'
    manifest['exterior'][entries[0]]=definition
    systems=json.loads((root/'systems.json').read_text())
    systems['definition']['sliding_canopy']=True
    # Losslessly externalize identical PNGs once, including the exporter-packed AO/MR map.
    share_spec=importlib.util.spec_from_file_location('share',root/'scripts/share-exterior-textures.py')
    share=importlib.util.module_from_spec(share_spec);share_spec.loader.exec_module(share)
    models,shared=share.prepare(normalized)
    definition['textures']=sorted(shared)
    manifest['exterior'][entries[0]]=definition
    # All acceptance checks finish before any installed asset is replaced.
    for name,data in models.items():(root/name).write_bytes(data)
    textures=root/'textures/exterior';textures.mkdir(parents=True,exist_ok=True)
    for name,data in shared.items():(root/name).write_bytes(data)
    for path in textures.glob('*.png'):
        if path.relative_to(root).as_posix() not in shared:path.unlink()
    share.write_embedded_assets(root, [*models, *sorted(shared)])
    (root/'exterior.json').write_text(json.dumps(definition,indent=2)+'\n')
    (root/'systems.json').write_text(json.dumps(systems,indent=2)+'\n')
    (root/'pack.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (root/'docs/exterior-blender-validation.json').write_text(json.dumps(dict(
        geometry_revision=receipt['geometry_revision'],blender=receipt['blender'],
        source_script='scripts/blender-exterior.py',
        source_sha256=hashlib.sha256((root/'scripts/blender-exterior.py').read_bytes()).hexdigest(),
        registration=generator.REGISTRATION_TEXT,lods=reports,blender_lods=receipt['lods'],
        node_name_mapping=generator.PACK_NODE_NAMES,containment=containment,
        installed_bytes={name:len(data) for name,data in models.items()},
        installed_sha256={name:hashlib.sha256(data).hexdigest() for name,data in models.items()},
        shared_textures={name:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in shared.items()},
        canopy=receipt['canopy'],cameras=receipt['cameras']),indent=2)+'\n')
    (root/'docs/exterior-storage.json').write_text(json.dumps(dict(
        before_glb_bytes=sum(r['bytes'] for r in reports),
        models={name:len(data) for name,data in models.items()},
        textures={name:len(data) for name,data in shared.items()},
        after_download_bytes=sum(map(len,models.values()))+sum(map(len,shared.values())),
        geometry_and_image_bytes_identical_to=receipt['source_sha256'],
        geometry_revision=generator.GEOMETRY_REVISION,
        model_sha256={name:hashlib.sha256(data).hexdigest() for name,data in models.items()},
        texture_sha256={name:hashlib.sha256(data).hexdigest() for name,data in shared.items()},
    ),indent=2)+'\n')
    shutil.copyfile(source/'cameras.json',root/'docs/exterior-cameras.json')
    shutil.copyfile(source/'pilot-cameras.json',root/'docs/interior-cameras.json')
    print(json.dumps(dict(installed=[r['file'] for r in reports],triangles=[r['triangles'] for r in reports],registration=generator.REGISTRATION_TEXT),indent=2))


if __name__=='__main__':main()
