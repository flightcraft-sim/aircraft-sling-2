#!/usr/bin/env python3
"""Export, registration, and cabin constraint tests without Blender or external assets."""
import importlib.util
import copy
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('exterior',Path(__file__).with_name('blender-exterior.py'))
exterior=importlib.util.module_from_spec(spec)
spec.loader.exec_module(exterior)


class AuthoringTests(unittest.TestCase):
    def test_crown_is_curved_and_tangent_is_continuous_at_split(self):
        lo=exterior.CANOPY_PROFILE[0][0];hi=exterior.CANOPY_SPLIT_X
        xs=[lo+(hi-lo)*i/100 for i in range(101)]
        heights=[exterior.canopy_section(x)[2] for x in xs]
        chord=[heights[0]+(heights[-1]-heights[0])*i/100 for i in range(101)]
        self.assertGreater(max(h-c for h,c in zip(heights,chord)),.15)
        self.assertEqual(sum(a<b and b>c for a,b,c in zip(heights,heights[1:],heights[2:])),1)
        e=1e-5;x=exterior.CANOPY_SPLIT_X
        for k in [1,2]:
            left=(exterior.canopy_section(x)[k]-exterior.canopy_section(x-e)[k])/e
            right=(exterior.canopy_section(x+e)[k]-exterior.canopy_section(x)[k])/e
            self.assertAlmostEqual(left,right,delta=.0001)
        self.assertEqual(exterior.CANOPY_TRAVEL_M,1.10)
        self.assertLess(hi-exterior.CANOPY_TRAVEL_M,-2.65)

    def test_every_hardware_vertex_is_checked_not_only_the_mounts(self):
        names=set(exterior.CANOPY_SURFACE_HARDWARE)
        moving=names|{'canopy_slide','canopy_glass','canopy_runner_left','canopy_runner_right'}
        points={n:[(0,0,-.001),(0.1,0,-.0025)] for n in names|set(exterior.WINDSHIELD_SURFACE_HARDWARE)}
        faces={n:[((-1,-1,0),(1,-1,0),(0,1,0))] for n in ['canopy_glass','windshield']}
        report=exterior.canopy_hardware_check(points,faces,moving)
        self.assertEqual(report['parts']['canopy_outside_latch']['vertices'],2)
        points['canopy_outside_latch'].append((0,0,-.006))
        with self.assertRaisesRegex(AssertionError,'floating canopy hardware'):
            exterior.canopy_hardware_check(points,faces,moving)
        points['canopy_outside_latch'][-1]=(0,0,.006)
        with self.assertRaisesRegex(AssertionError,'floating canopy hardware'):
            exterior.canopy_hardware_check(points,faces,moving)
        with self.assertRaisesRegex(AssertionError,'unchecked canopy hardware'):
            exterior.canopy_hardware_check(points,faces,moving|{'unregistered_handle'})

    def test_distance_handles_triangle_edges_and_degenerate_faces(self):
        face=((0,0,0),(1,0,0),(0,1,0))
        self.assertAlmostEqual(exterior.point_triangle_distance_sq((.2,.2,.003),face),.003**2)
        self.assertAlmostEqual(exterior.point_triangle_distance_sq((1,1,0),face),.5)
        self.assertAlmostEqual(exterior.point_triangle_distance_sq((0,0,.005),((0,0,0),)*3),.005**2)


    def test_canopy_continuous_clearance_rejects_intersection_at_intermediate_travel(self):
        moving={'canopy_glass'}
        points={'canopy_glass':[(-3.04,0,-.445),(-1.95,0,-.445)]}
        deck={'airframe':[((-4.2,-.5,-.40),(-1.9,.5,-.4),(-3.,0,.3))]}
        clearance,swept=exterior.canopy_clearance(points,deck,moving)
        self.assertAlmostEqual(clearance,.045)
        self.assertAlmostEqual(swept[0],-4.14)
        # Raised deck patch overlaps only the swept interval, not the closed rear edge.
        deck['airframe'].append(((-3.7,0,-.46),(-3.5,.1,-.46),(-3.5,-.1,-.46)))
        with self.assertRaisesRegex(AssertionError,'continuous sweep'):
            exterior.canopy_clearance(points,deck,moving)
        with self.assertRaisesRegex(AssertionError,'missing sliding'):
            exterior.canopy_clearance({},deck,moving)

    def test_registration_matches_pack_default(self):
        root=Path(__file__).resolve().parent.parent
        variant=json.loads((root/'variant.json').read_text())
        definition=json.loads((root/'exterior.json').read_text())
        self.assertEqual(exterior.REGISTRATION_TEXT,variant['identity']['registration'])
        self.assertEqual(exterior.REGISTRATION_TEXT,definition['registration']['text'])

    def test_cabin_rejects_protruding_panel_and_other_invalid_vertices(self):
        self.assertIsNone(exterior.interior_vertex_error((-1.70,.33,-.275),True))
        self.assertEqual(exterior.interior_vertex_error((-1.70,0,-.48),True),'above canopy rail')
        self.assertEqual(exterior.interior_vertex_error((-1.70,.58,-.20),True),'outside cockpit station limits')
        self.assertEqual(exterior.interior_vertex_error((-.90,0,-.20),True),'outside cockpit station limits')
        self.assertEqual(exterior.interior_vertex_error((-1.70,.33,-.275),False),'outside closed fuselage envelope')
        self.assertEqual(exterior.interior_vertex_error((float('nan'),0,0),True),'non-finite interior vertex')

    def test_seating_floor_ends_at_baggage_wall_and_rejects_v3_lod2_overrun(self):
        center=exterior.CABIN_FLOOR_CENTER;size=exterior.CABIN_FLOOR_SIZE
        self.assertAlmostEqual(center[0]-size[0]/2,-2.70)
        self.assertAlmostEqual(center[0]+size[0]/2,-1.45)
        self.assertIn('cabin_floor',exterior.PRESERVE_LOD_MESHES)
        for x in [center[0]-size[0]/2,center[0]+size[0]/2]:
            for y in [-size[1]/2,size[1]/2]:
                for z in [center[2]-size[2]/2,center[2]+size[2]/2]:
                    self.assertIsNone(exterior.interior_vertex_error((x,y,z),True,'cabin_floor'))
        self.assertEqual(exterior.interior_vertex_error((-2.80,0,.13),True,'cabin_floor'),'outside seating floor extent')
        self.assertEqual(exterior.interior_vertex_error((-3.0454545,0,.13),True,'cabin_floor'),'outside cockpit station limits')

    def test_vector_glyphs_have_uniform_stems_open_counters_and_antialiasing(self):
        width,height=120,180  # Isotropic: 2/3-height width, 1/6-height stroke = 30 pixels.
        probes={
            'N':[(.08,.5,255),(.333,.5,255),(.58,.5,255),(.40,.2,0)],
            '1':[(.333,.5,255),(.08,.5,0)],
            '3':[(.40,.5,255),(.58,.29,255),(.333,.083,255),(.333,.917,255),(.10,.03,0),(.30,.29,0),(.30,.71,0)],
            '7':[(.30,.083,255),(.36,.50,255),(.08,.50,0),(.55,.80,0)],
            'F':[(.08,.80,255),(.40,.083,255),(.40,.50,255),(.40,.28,0),(.40,.85,0)],
            'C':[(.08,.50,255),(.333,.083,255),(.333,.917,255),(.333,.50,0),(.58,.50,0)],
        }
        for glyph,points in probes.items():
            pixels=exterior.rasterize_glyph(glyph,width,height)
            for x,y,expected in points:
                with self.subTest(glyph=glyph,point=(x,y)):
                    self.assertEqual(pixels[int(y*height)*width+int(x*height)],expected)
            self.assertTrue(any(0<value<255 for value in pixels),glyph)
        n=exterior.rasterize_glyph('N',width,height)
        f=exterior.rasterize_glyph('F',width,height)
        for mask,y in [(n,height//2),(f,int(height*.80))]:
            row=mask[y*width:(y+1)*width]
            self.assertEqual(sum(v>=128 for v in row[:width//3]),30)
        self.assertAlmostEqual(exterior.REGISTRATION_STROKE,.05)
        self.assertAlmostEqual(exterior.REGISTRATION_HEIGHT,.30)
        c=exterior.rasterize_glyph('C',width,height)
        self.assertFalse(any(c[height//2*width+width//2:(height//2+1)*width]))

    def test_livery_has_no_background_box_keeps_stripe_and_reads_forward_both_sides(self):
        width,height=exterior.ART_SIZE
        navy=bytes(round(c*255) for c in exterior.NAVY)
        teal=bytes(round(c*255) for c in exterior.TEAL)
        # Ink and counter landmarks, expressed in height units, independent of rasterization.
        self.assertEqual(exterior.REGISTRATION_TEXT,'N371FC')
        probes=[('N',.333,.5,True),('3',.30,.29,False),('7',.36,.50,True),
                ('1',.333,.5,True),('F',.40,.50,True),('C',.58,.50,False)]
        for side in [-1,1]:
            pixels=exterior.livery_pixels(side)
            def sample(x,z):
                u=int((x+6)/6.675*width);v=int((.45-z)/.9*height)
                start=4*(v*width+u)
                return pixels[start:start+4]
            for index,(glyph,u,v,ink) in enumerate(probes):
                x=-4.65+index*.25+u*.30 if side>0 else -3.20-index*.25-u*.30
                z=-.215+v*.30
                with self.subTest(side=side,glyph=glyph):
                    value=sample(x,z)
                    self.assertEqual(value,navy if ink else bytes(4))
            self.assertEqual(sample(-4.69,-.17),bytes(4))  # Former grey sticker margin.
            self.assertEqual(sample(-4.60,.18),teal)       # Stripe continues under former box.
            self.assertEqual(sample(-4.425,-.05) if side>0 else sample(-3.425,-.05),bytes(4)) # Space between N and 3.

    def test_flat_deck_straight_tail_and_blunt_cowl_constraints(self):
        stations=exterior.FUSELAGE_SECTIONS
        deck=[p for p in stations if -3.05<=p[0]<=-1.12]
        self.assertTrue(all(p[2]==-.40 and p[3]==.36 for p in deck))
        # All aft intermediate tops and bottoms follow straight independent tapers.
        aft=[p for p in stations if -5.15<=p[0]<=-3.05]
        for a,b,c in zip(aft,aft[1:],aft[2:]):
            for axis in (2,3):
                first=(b[axis]-a[axis])/(b[0]-a[0]);second=(c[axis]-b[axis])/(c[0]-b[0])
                self.assertAlmostEqual(first,second,delta=.0007)
        cowl=[p for p in stations if p[0]>=-1.12]
        self.assertTrue(all(b[2]>=a[2] for a,b in zip(cowl,cowl[1:])))
        self.assertGreater(cowl[-1][3]-cowl[-1][2],.50)  # Remains blunt, not a cone.
        self.assertAlmostEqual((cowl[-1][2]+cowl[-1][3])/2,exterior.PROP_Z)
        self.assertLess(exterior.PROP_Z+exterior.FACTS['prop_diameter']/2,exterior.CONTACT_Z)
        for a,b,c in zip(cowl,cowl[1:],cowl[2:]):
            self.assertAlmostEqual((b[3]-a[3])/(b[0]-a[0]),(c[3]-b[3])/(c[0]-b[0]),delta=.0007)
        for angle in [math.pi/6,math.pi/4,math.pi/3]:
            y,z=exterior.superellipse_section(.5,.65,0,angle)
            self.assertAlmostEqual(abs(y/.5)**3.5+abs(z/.65)**3.5,1)
        y,z=exterior.superellipse_section(.5,.65,0,math.pi/4)
        self.assertGreater(y/.5,.80);self.assertGreater(z/.65,.80)
        self.assertEqual(exterior.body((1,2,3)),(1,-2,-3))
        self.assertEqual(exterior.body(exterior.body((1,2,3))),(1,2,3))

    def test_wing_area_and_seven_dimension_review_poses(self):
        root,tip=exterior.WING_ROOT_CHORD,exterior.WING_TIP_CHORD
        area=exterior.FACTS['span']*(.45*root+.55*(root+tip)/2)-2*.06*tip/11
        self.assertAlmostEqual(area,exterior.FACTS['area'])
        self.assertEqual(exterior.wing_chord(0),exterior.wing_chord(exterior.FACTS['span']*.45/2))
        self.assertAlmostEqual(exterior.wing_chord(exterior.FACTS['span']/2),tip)
        self.assertEqual(len(exterior.VIEWS)+len(exterior.ORTHO_VIEWS),7)
        side=exterior.ORTHO_VIEWS['elevation-side'];top=exterior.ORTHO_VIEWS['plan-top']
        self.assertEqual(side['eye'][0],side['target'][0]);self.assertEqual(side['eye'][2],side['target'][2])
        self.assertEqual(top['eye'][:2],top['target'][:2])
        self.assertGreater(side['scale'],exterior.FACTS['length'])
        self.assertGreater(top['scale'],exterior.FACTS['span'])
        self.assertGreater(top['scale']/1.6,exterior.FACTS['length'])

    def test_lod_retains_blur_fan_and_open_tubes_and_samples_round_boundaries(self):
        for lod in (1,2):
            for name in ('prop_blur','beacon','exhaust','step_left_support'):
                self.assertEqual(exterior.lod_ratio(name,lod),1.)
            for name in ('tire_0','tire_1','tire_2','wingtip_left','wingtip_right','gear_leg_0','wing_fillet_left'):
                self.assertEqual(exterior.lod_ratio(name,lod),.18)
        self.assertEqual(exterior.lod_ratio('airframe',2),.029)

    def test_neutral_flap_is_the_same_thin_airfoil_trailing_section(self):
        for distance in (.57,1.,2.8):
            chord=exterior.wing_chord(distance)
            for step in range(101):
                u=step/100;thickness,camber=exterior.foil_section(chord,u,True)
                top=exterior.wing_point(distance,u,upper=True)
                bottom=exterior.wing_point(distance,u,upper=False)
                self.assertAlmostEqual(bottom[2]-top[2],2*thickness)
                self.assertLessEqual(thickness/chord,.057)
                self.assertLessEqual(camber/chord,.01201)
                # Trailing surface has no separate vertical displacement or boxed bevel.
                if u>=.734:self.assertLess(top[2],bottom[2])
            self.assertAlmostEqual(exterior.foil_section(chord,1,True)[0],.00035)

    def test_main_fairings_are_broad_and_sweep_aft_to_the_pants(self):
        for side in (-1,1):
            y=side*exterior.FACTS['track']/2
            sections=exterior.gear_sections(0,-1.959,y,.66)
            self.assertAlmostEqual(sections[0][0]-sections[-1][0],.48)
            self.assertAlmostEqual(sections[-1][1],y)
            self.assertAlmostEqual(sections[-1][2],.605)
            self.assertAlmostEqual(sections[0][3],.34)
            self.assertAlmostEqual(sections[-1][3],.20)
            self.assertTrue(all(a[0]>b[0] and a[2]<b[2] for a,b in zip(sections,sections[1:])))
            self.assertTrue(all(p[3]/p[4]>3.5 for p in sections))


class ExportTests(unittest.TestCase):
    def fixture(self,path,triangles=1,mesh_node='airframe'):
        # Z-up fixture deliberately uses the real dimensional envelope.
        positions=[(-6,-4.5825,-1.04),(.675,4.5825,1.41),(-6,4.5825,1.41)]
        binary=bytearray()
        for p in positions: binary.extend(struct.pack('<3f',*p))
        binary.extend(struct.pack('<9f',*([0,0,1]*3)))
        binary.extend(struct.pack('<12f',*([1,0,0,1]*3)))
        binary.extend(struct.pack('<3I',0,1,2)*triangles)
        doc={'asset':{'version':'2.0'},'nodes':[dict(name=name,**({'mesh':0} if name==mesh_node else {})) for name in sorted(exterior.REQUIRED)],
             'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'TANGENT':2},'indices':3}]}],
             'buffers':[{'byteLength':len(binary)}],
             'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':36},{'buffer':0,'byteOffset':36,'byteLength':36},
                            {'buffer':0,'byteOffset':72,'byteLength':48},{'buffer':0,'byteOffset':120,'byteLength':12*triangles}],
             'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[-6,-4.5825,-1.04],'max':[.675,4.5825,1.41]},
                          {'bufferView':1,'componentType':5126,'count':3,'type':'VEC3'},
                          {'bufferView':2,'componentType':5126,'count':3,'type':'VEC4'},
                          {'bufferView':3,'componentType':5125,'count':3*triangles,'type':'SCALAR'}]}
        encoded=json.dumps(doc).encode(); encoded+=b' '*((-len(encoded))%4)
        path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(encoded)+len(binary))+
                         struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary)
    def test_rotation_preserves_bounds_winding_and_tangent_handedness(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.glb'; self.fixture(path); exterior.body_axes_glb(path)
            result=exterior.validate_glb(path,0,check_canopy=False)
            for actual,wanted in zip(result['dimensions_m'],[6.675,9.165,2.45]):
                self.assertAlmostEqual(actual,wanted,places=5)
            data=path.read_bytes(); size=struct.unpack_from('<I',data,12)[0]; binary=data[28+size:]
            self.assertEqual(struct.unpack_from('<3I',binary,120),(0,1,2))
            self.assertEqual(struct.unpack_from('<4f',binary,72),(1,0,0,1))
            self.assertEqual(struct.unpack_from('<3f',binary,36),(0,0,-1))
            self.assertAlmostEqual(struct.unpack_from('<3f',binary,0)[1],4.5825,places=5)
    def test_acceptance_rejects_missing_nodes_and_wrong_dimensions(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.glb'; self.fixture(path)
            data=path.read_bytes().replace(b'propeller',b'bad_node_'); path.write_bytes(data)
            with self.assertRaises(AssertionError): exterior.validate_glb(path,0,check_canopy=False)
            self.fixture(path)
            original=exterior.FACTS['length']; exterior.FACTS['length']=10
            try:
                with self.assertRaises(AssertionError): exterior.validate_glb(path,0,check_canopy=False)
            finally: exterior.FACTS['length']=original

    def test_extremum_gate_catches_translation_even_when_dimensions_match(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bounds.glb';self.fixture(path)
            original=exterior.validate_glb(path,0,check_canopy=False)
            self.assertEqual(original['bounds_nodes_body']['max'],['airframe']*3)
            # A translated LOD has unchanged overall dimensions but fails the new gate.
            moved=copy.deepcopy(original)
            for end in ('min','max'):moved['bounds_body_m'][end][2]+=.006
            with self.assertRaisesRegex(AssertionError,'airframe'):
                exterior.validate_lod_bounds(original,moved)
            for end in ('min','max'):moved['bounds_body_m'][end][2]-=.003
            exterior.validate_lod_bounds(original,moved)

    def test_v6_blur_disc_height_failure_identifies_extreme_node(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'blur.glb';self.fixture(path,mesh_node='prop_blur')
            data=bytearray(path.read_bytes());size=struct.unpack_from('<I',data,12)[0]
            # Move the fixture's lower z extremum to the actual V6 LOD2 blur edge.
            struct.pack_into('<f',data,28+size+8,-1.14428626)
            path.write_bytes(data)
            with self.assertRaisesRegex(AssertionError,'prop_blur'):
                exterior.validate_glb(path,2,check_canopy=False)
    def test_original_lod_caps_accept_boundary_and_reject_one_triangle_over(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'budget.glb'
            for lod,limit in enumerate((120000,25000,5000)):
                with self.subTest(lod=lod):
                    self.fixture(path,limit)
                    result=exterior.validate_glb(path,lod,check_canopy=False)
                    self.assertEqual(result['triangles'],limit)
                    self.assertEqual(sum(result['mesh_triangles'].values()),limit)
                    self.fixture(path,limit+1)
                    with self.assertRaises(AssertionError): exterior.validate_glb(path,lod,check_canopy=False)


if __name__=='__main__': unittest.main()
