#!/usr/bin/env python3
"""Original Sling 2 exterior; Blender 5.2 background job, no external assets/network.

blender -b --python blender-exterior.py -- /writable/output
Only the output folder is written. Sources: POH Rev 2.8 Section 1.4 numerical facts,
Section 7.7 sliding mechanism/latches, levelling reference and normal checklists.
All contours, travel, airfoils, lettering, and livery are independent modeling estimates.
The old generator is retained solely for reproducing the previous pack revision.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

# Independently transcribed SI values; do not substitute the inconsistent imperial column.
FACTS = dict(span=9.165, length=6.675, height=2.45, area=11.845, track=1.95,
             prop_diameter=1.79, blades=3, tail_span=2.825, vertical_span=1.47, dihedral=5.0, taper=1.375)
BUDGETS = (120000, 25000, 5000)
TEXTURE_SIZE = 4096
GEOMETRY_REVISION = 'v13-thin-wing-fillet'
PILOT_EYE_M = (-2.30, -.205, -.72)  # Original pilot-seat estimate, in body axes.
CANOPY_TRAVEL_M = 1.10  # Estimate: front edge clears the seat backs by about 0.45 m.
CANOPY_SPLIT_X = -1.95
CANOPY_BASE_Z = -.445  # 45 mm above skin deck: swept glass/frame clears turtledeck.
LOD_BOUNDS_TOLERANCE_M = .005
# LOD0 detail allocation: (Bezier samples per span, cross-section bevel resolution).
# Preserve the canopy rails/frames, fairings, and exterior silhouette settings below.
TUBE_DETAIL = {
    'seat_stitch_': (4, 0),
    'tiedown_': (6, 1),
    'belt_': (8, 1),
    'control_stick_': (8, 1),
    'throttle': (6, 1),
    'canopy_': (2, 1),
    'windshield_frame': (2, 1),
    'roll_over_bar': (2, 1),
}
TIRE_SEGMENTS = (32, 8)
# Exact body reference and pivots used by the existing pack. Blender uses z-up internally.
NOSE, TAIL, CONTACT_Z, PROP_Z = .675, -6.0, .85, -.06
WHITE, NAVY, TEAL = (.86, .89, .90, 1), (.015, .038, .067, 1), (.012, .32, .37, 1)
VIEWS = {
    'director-front': ((10, -10, -3.0), (-2.2, 0, -.15)),
    'director-rear': ((-13, 9, -3.6), (-2.2, 0, -.15)),
    'director-left': ((-2.2, -13.5, -1.7), (-2.2, 0, -.15)),
    'director-top': ((-2.2, 0, -19.5), (-2.2, 0, -.15)),
    'beauty': ((7.8, -10.5, -3.1), (-2.15, 0, -.1)),
}
PILOT_LOOKS = {
    'pilot-forward': (0.,0.,0.), 'pilot-left': (-1.25,-.08,0.),
    'pilot-right': (1.25,-.08,0.), 'pilot-down': (0.,-.65,0.),
    'pilot-right-down': (1.25,-.65,0.), 'pilot-rear-left': (-2.1,-.65,0.),
    'pilot-canopy-closed': (-.65,.32,0.), 'pilot-canopy-open': (-.65,.32,1.),
}
REQUIRED = {'airframe', 'canopy_slide', 'canopy_glass', 'windshield', 'roll_over_bar',
            'canopy_inside_latch', 'canopy_outside_latch', 'canopy_latch_spine', 'canopy_rail_left', 'canopy_rail_right', 'spinner', 'propeller', 'prop_blur', 'aileron_left',
            'aileron_right', 'flaps_left', 'flaps_right', 'elevator_left', 'elevator_right', 'rudder', 'steering',
            'oleo_0', 'oleo_1', 'oleo_2', 'wheel_0', 'wheel_1', 'wheel_2', 'nav_left',
            'nav_right', 'nav_tail', 'strobe_left', 'strobe_right', 'beacon', 'landing',
            'registration'}
PACK_NODE_NAMES = {'flap_left':'flaps_left','flap_right':'flaps_right',
                   'elevator_skin_left':'elevator_left','elevator_skin_right':'elevator_right'}


def normalize_node_names(data):
    """Preserve the existing format-2 animation bindings without changing mesh data or pivots."""
    size=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+size])
    for node in doc['nodes']:node['name']=PACK_NODE_NAMES.get(node.get('name'),node.get('name'))
    encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    remainder=data[20+size:]
    return struct.pack('<III',0x46546C67,2,20+len(encoded)+len(remainder))+struct.pack('<II',len(encoded),0x4E4F534A)+encoded+remainder


# Shape constraints from flight lead's written observations; stations are original estimates.
FUSELAGE_EXPONENT = 3.5
# x, half-width, top z, bottom z; body z increases downward.
FUSELAGE_SECTIONS = [
    (-6.00,.006,-.128,-.100),(-5.94,.016,-.131,-.091),
    (-5.15,.100,-.2045,.033),(-4.25,.205,-.2883,.173),
    (-3.40,.310,-.3674,.3055),(-3.05,.500,-.400,.360),
    (-2.70,.560,-.400,.360),(-1.40,.550,-.400,.360),
    (-1.12,.510,-.400,.360),(-.25,.400,-.365,.2688),
    (.18,.360,-.345,.22372414),(.30,.325,-.330,.21114483),(.33,.315,-.328,.208),
]
WING_INNER_FRACTION = .45
WING_TIP_RADIUS = .06
WING_TIP_PANEL = .18
WING_ROOT_Z = .27
WING_SWEEP = .018
WING_RATIO = 1/FACTS['taper']
WING_ROOT_CHORD = FACTS['area']/(FACTS['span']*(WING_INNER_FRACTION+(1-WING_INNER_FRACTION)*(1+WING_RATIO)/2)-2*WING_TIP_RADIUS*WING_RATIO/11)
WING_TIP_CHORD = WING_ROOT_CHORD*WING_RATIO
# One original Bezier meridian for both glazing pieces: x, half-width, crown height.
# Monotone x permits a unique inverse; no clamping or flat interpolation plateaus.
CANOPY_PROFILE = ((-3.04,.460,.400),(-2.82,.580,.860),(-1.48,.610,.820),(-1.12,.080,.008))
CANOPY_HARDWARE_TOLERANCE_M = .003
CANOPY_SURFACE_HARDWARE = ('canopy_bow_front','canopy_bow_rear','canopy_sill_left',
                           'canopy_sill_right','canopy_latch_spine','canopy_outside_latch')
WINDSHIELD_SURFACE_HARDWARE = ('windshield_frame',)


def canopy_section(x):
    """Continuous crown, width and tangent through the fixed/moving seam (body metres)."""
    assert CANOPY_PROFILE[0][0] <= x <= CANOPY_PROFILE[-1][0], x
    def evaluate(t):
        weights=((1-t)**3,3*(1-t)**2*t,3*(1-t)*t*t,t**3)
        return tuple(sum(w*p[k] for w,p in zip(weights,CANOPY_PROFILE)) for k in range(3))
    lo,hi=0.,1.
    for _ in range(60):
        mid=(lo+hi)/2
        if evaluate(mid)[0]<x:lo=mid
        else:hi=mid
    _,width,height=evaluate((lo+hi)/2)
    return x,width,height


def canopy_surface(x,angle):
    x,width,height=canopy_section(x)
    return x,width*math.cos(angle),CANOPY_BASE_Z-height*math.sin(angle)


CANOPY_SECTIONS = [canopy_section(CANOPY_PROFILE[0][0]+(CANOPY_PROFILE[-1][0]-CANOPY_PROFILE[0][0])*i/48) for i in range(49)]
ORTHO_VIEWS = {
    'elevation-side': dict(eye=(-2.6625,-20,-.375),target=(-2.6625,0,-.375),up=(0,0,-1),scale=8.0),
    'plan-top': dict(eye=(-2.6625,0,-20),target=(-2.6625,0,-.375),up=(1,0,0),scale=12.4),
}


def superellipse_section(ry,rz,z,angle,exponent=FUSELAGE_EXPONENT):
    def signed_power(value):return math.copysign(abs(value)**(2/exponent),value)
    return ry*signed_power(math.sin(angle)),z+rz*signed_power(math.cos(angle))


def wing_chord(distance):
    t=max(0,min(1,(distance/(FACTS['span']/2)-WING_INNER_FRACTION)/(1-WING_INNER_FRACTION)))
    return WING_ROOT_CHORD+(WING_TIP_CHORD-WING_ROOT_CHORD)*t


def foil_section(chord, u, wing=False):
    """Original analytic section shared by the fixed wing and neutral trailing surfaces."""
    if wing:
        # Rounded nose, thin finite trailing edge, no bevel across thin faces.
        return .105*chord*math.sqrt(u)*(1-u)*(1+.8*u)+.00035*u, .012*chord*math.sin(math.pi*u)
    return .06*chord*math.sin(math.pi*u)**.55, .018*chord*math.sin(math.pi*u)


def wing_point(distance, u, side=1, upper=True, tip=False):
    chord=wing_chord(distance);thickness,camber=foil_section(chord,u,True)
    x=-1.05-WING_SWEEP*distance-chord*u
    y=side*distance
    z=WING_ROOT_Z-distance*math.tan(math.radians(FACTS['dihedral']))-camber+(-thickness if upper else thickness)
    if tip:
        t=max(0,min(1,(distance-(FACTS['span']/2-WING_TIP_PANEL))/WING_TIP_PANEL))
        y-=side*WING_TIP_RADIUS*t*t*abs(2*u-1)**10;z-=.045*t*t
    return x,y,z


# Wing-to-fuselage fillet. v12 rose 55 mm above the wing and reached 190 mm out along nearly the
# whole chord, which read as a boxy block from the side. v13 is a thin saddle: 20 mm at its
# crest, 85 mm of reach, and a squared-sine taper so both ends feather out into the wing skin.
WING_FILLET_RISE = .020
WING_FILLET_REACH = .085
WING_FILLET_TAPER = 2.0
WING_FILLET_ROWS, WING_FILLET_COLS = 24, 8
WING_FILLET_U = (.012, .716)  # chord fractions covered, ending before the flap hinge
WING_FILLET_BASE_DISTANCE = .57  # span station where the fillet meets the wing at its feathered ends
WING_FILLET_TOLERANCE_M = (.004, .007, .007)  # per LOD: 1.5 mm skin thickness plus decimation


def wing_fillet_points(side, hull_hit, rows=WING_FILLET_ROWS, cols=WING_FILLET_COLS):
    """Body-frame saddle vertices from the fuselage side to the wing upper skin.

    hull_hit(x, z) returns the body point where the fuselage skin is met at that x and height
    (Blender ray cast), or None when the ray misses."""
    points=[]
    for i in range(rows+1):
        u=WING_FILLET_U[0]+(WING_FILLET_U[1]-WING_FILLET_U[0])*i/rows
        blend=math.sin(math.pi*i/rows)**WING_FILLET_TAPER
        xx,yy,zz=wing_point(.56,u,side)
        start_z=zz-WING_FILLET_RISE*blend
        inner=hull_hit(xx,start_z)
        if inner is None:raise RuntimeError('Wing fillet missed closed fuselage at '+str((xx,start_z)))
        end_distance=max(abs(inner[1])+.012,WING_FILLET_BASE_DISTANCE+WING_FILLET_REACH*blend)
        outer=wing_point(end_distance,u,side)
        for j in range(cols+1):
            angle=j*math.pi/(2*cols)
            points.append((inner[0]+(outer[0]-inner[0])*(1-math.cos(angle)),
                           inner[1]+(outer[1]-inner[1])*(1-math.cos(angle)),
                           inner[2]+(outer[2]-inner[2])*math.sin(angle)))
    return points


def wing_fillet_rise_allowance(distance):
    """Greatest height of the fillet above the wing upper skin at this span station. The crest is
    WING_FILLET_RISE above the skin at the 0.56 m station it is lofted from; inboard of that the
    skin itself is lower by the dihedral, and the fillet follows the fuselage side down to it."""
    return WING_FILLET_RISE+math.tan(math.radians(FACTS['dihedral']))*max(0.,.56-distance)


def wing_fillet_envelope_violations(points, side, tolerance=WING_FILLET_TOLERANCE_M[0]):
    """Vertices of a fillet that leave the wing/fuselage envelope it must stay inside.

    The envelope is the wing's own planform and section: chordwise within the fillet's chord
    fractions, spanwise on the correct side from the fuselage out to the fillet reach, and
    vertically between the wing upper skin and the rise allowance above it. A vertex below the
    upper skin would hide inside the wing; above the rise, or outside the planform or reach, it
    would stick out as a block. Body axes, z down."""
    bad=[]
    for x,y,z in points:
        distance=abs(y)
        if y*side<0:
            bad.append(((x,y,z),'wrong side of the aircraft'));continue
        chord=wing_chord(distance)
        u=(-1.05-WING_SWEEP*distance-x)/chord
        margin=tolerance/chord
        if not WING_FILLET_U[0]-margin<=u<=WING_FILLET_U[1]+margin:
            bad.append(((x,y,z),'outside the wing chord range'));continue
        if distance>WING_FILLET_BASE_DISTANCE+WING_FILLET_REACH+tolerance:
            bad.append(((x,y,z),'beyond the fillet reach'));continue
        upper=wing_point(distance,min(max(u,0.),1.),side)[2]
        if z>upper+tolerance:bad.append(((x,y,z),'below the wing upper skin'))
        elif z<upper-wing_fillet_rise_allowance(distance)-tolerance:bad.append(((x,y,z),'above the fillet rise'))
    return bad


def wing_fillet_check(mesh_points, lod):
    """Exported-GLB acceptance gate for the fillets (absent in synthetic test files)."""
    report={}
    for side,label in ((-1,'left'),(1,'right')):
        points=mesh_points.get('wing_fillet_'+label)
        if not points:continue
        bad=wing_fillet_envelope_violations(points,side,WING_FILLET_TOLERANCE_M[min(lod,2)])
        assert not bad, ('wing fillet leaves the wing/fuselage envelope','wing_fillet_'+label,len(bad),bad[:3])
        zs=[p[2]-wing_point(abs(p[1]),min(max((-1.05-WING_SWEEP*abs(p[1])-p[0])/wing_chord(abs(p[1])),0.),1.),side)[2] for p in points]
        report['wing_fillet_'+label]=dict(vertices=len(points),max_rise_above_wing_m=-min(zs),
                                          tolerance_m=WING_FILLET_TOLERANCE_M[min(lod,2)])
    return report


def gear_sections(index, x, y, z):
    """Wide tapered fairings; main legs sweep 48 cm aft into the unchanged wheel track."""
    main=index<2
    start=(x+.48,y*.38,.29) if main else (x+.11,0,.23)
    control=(x+.26,y*.69,.42) if main else (x+.05,0,.42)
    end=(x,y,z-.055)
    sections=[]
    for i in range(9):
        t=i/8
        point=tuple((1-t)**2*a+2*t*(1-t)*b+t*t*c for a,b,c in zip(start,control,end))
        chord=(.34*(1-t)+.20*t) if main else (.17*(1-t)+.115*t)
        width=(.085*(1-t)+.055*t) if main else (.070*(1-t)+.055*t)
        sections.append((*point,chord,width))
    return sections


# Original paint masks use body-coordinate X/Z projections, then bake into the game UVs.
ART_X = (-6.0, .675)
ART_Z = (-.45, .45)
ART_SIZE = (4096, 1024)
RAIL_Z = -.40
REGISTRATION_HEIGHT = .30
REGISTRATION_WIDTH = REGISTRATION_HEIGHT*2/3
REGISTRATION_STROKE = REGISTRATION_HEIGHT/6
REGISTRATION_GAP = .05
REGISTRATION_LEFT, REGISTRATION_TOP = -4.65, -.215
REGISTRATION_TEXT = 'N371FC'
REGISTRATION_RIGHT = REGISTRATION_LEFT+len(REGISTRATION_TEXT)*REGISTRATION_WIDTH+(len(REGISTRATION_TEXT)-1)*REGISTRATION_GAP
# Seat backs finish near -2.62 m. Terminate the seating floor at the front baggage wall,
# immediately behind them, consistent with POH 7.6/7.9's layout. Stations are modeling estimates.
CABIN_FLOOR_AFT, CABIN_FLOOR_FRONT = -2.70, -1.45
CABIN_FLOOR_CENTER = ((CABIN_FLOOR_AFT+CABIN_FLOOR_FRONT)/2,0,.13)
CABIN_FLOOR_SIZE = (CABIN_FLOOR_FRONT-CABIN_FLOOR_AFT,.86,.10)
# QEM is unsuitable for a coplanar triangle fan or these already tiny open tubes.
# V6 reduced the blur disc to one triangle, extending its lower edge by 21.6 cm;
# exhaust and boarding support collapsed to invalid meshes and vanished on export.
# Keep the small beacon too: it sets the authored upper extent with the fin tip.
PRESERVE_LOD_MESHES = ('cabin_floor','baggage_bulkhead','prop_blur','beacon',
                       'exhaust','step_left_support','canopy_rail_','canopy_runner_','canopy_inside_latch',*CANOPY_SURFACE_HARDWARE,*WINDSHIELD_SURFACE_HARDWARE)
# These boundary silhouettes need more than the general distant-LOD ratio.
SILHOUETTE_LOD_PREFIXES = ('tire_','wingtip_','gear_leg_','wing_fillet_','canopy_glass','canopy_sill_','canopy_bow_','windshield','roll_over_bar')
INTERIOR_PREFIXES = ('cabin_floor','seat_','belt_','control_stick_','stick_grip_',
                     'display_','panel_silhouette','glareshield','center_console','throttle','baggage_bulkhead',
                     'side_panel_','armrest_','rudder_pedal_')


def dashboard_geometry(glareshield=False):
    """Original curved dash/coaming; no cuboid slab or imported/photographed outline."""
    samples=24
    if not glareshield:
        # High, domed center, dropping to rounded shoulders beside the two displays.
        outline=[(-.40+.80*i/samples,-.352+.105*((-.40+.80*i/samples)/.40)**2) for i in range(samples+1)]
        outline += [(.40-.80*i/samples,.018+.035*(1-((.40-.80*i/samples)/.40)**2)) for i in range(samples+1)]
        count=len(outline)
        points=[(x,y,z) for x in [-1.82,-1.76] for y,z in outline]
        faces=[tuple(reversed(range(count))),tuple(count+i for i in range(count))]
        faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
        return points,faces
    # The pilot edge bows aft in plan; the top follows the domed panel shoulders.
    # A narrow rolled lip and smooth top replace the old flat rectangular box.
    points=[]
    for layer in range(2):
        for i in range(samples+1):
            y=-.42+.84*i/samples;s=(y/.42)**2
            for edge in range(2):
                x=-1.48 if edge==0 else -1.92+.12*s
                z=-.378+.10*s+layer*.022
                points.append((x,y,z))
    stride=2*(samples+1);faces=[]
    for i in range(samples):
        a=2*i
        faces += [(a,a+2,a+3,a+1),(a+stride+1,a+stride+3,a+stride+2,a+stride),
                  (a,a+stride,a+stride+2,a+2),(a+1,a+3,a+stride+3,a+stride+1)]
    faces += [(0,1,stride+1,stride),(stride-2,2*stride-2,2*stride-1,stride-1)]
    return points,faces


def side_panel_geometry(side):
    """Sloped cabin lining: turn inward under the rail, rather than crossing the outer skin."""
    profile=[(.34,-.37),(.424,-.25),(.424,.06),(.412,.06),(.412,-.25),(.328,-.37)]
    count=len(profile)
    points=[(x,side*y,z) for x in [-2.61,-1.67] for y,z in profile]
    faces=[tuple(reversed(range(count))),tuple(count+i for i in range(count))]
    faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    return points,faces


def interior_vertex_error(point, inside_shell, part_name=''):
    """Body z is down: every cabin fitting must be below the rail and inside the closed hull."""
    x, y, z = point
    if not all(math.isfinite(v) for v in point): return 'non-finite interior vertex'
    if z < RAIL_Z+.005: return 'above canopy rail'
    if not (-2.95 <= x <= -1.35) or abs(y) > .46: return 'outside cockpit station limits'
    if part_name.startswith('cabin_floor') and not (CABIN_FLOOR_AFT-.001 <= x <= CABIN_FLOOR_FRONT+.001):
        return 'outside seating floor extent'
    if not inside_shell: return 'outside closed fuselage envelope'
    return None


def vector_glyphs():
    """Original sans-serif outlines in height units: straight strokes and circular arcs.

    Height 1, width 2/3, uniform stroke 1/6. No font, bitmap grid, or traced outlines.
    Straight stroke ends are square; sampled arcs form smooth vector outline polygons.
    """
    stroke=REGISTRATION_STROKE/REGISTRATION_HEIGHT;r=stroke/2;w=REGISTRATION_WIDTH/REGISTRATION_HEIGHT
    def rectangle(x0,y0,x1,y1):return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
    def path(points,start_direction=None,end_direction=None):
        directions=[]
        for a,b in zip(points,points[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            directions.append((dx/length,dy/length))
        left=[];right=[]
        for i,(x,y) in enumerate(points):
            before=directions[max(0,i-1)];after=directions[min(i,len(directions)-1)]
            # Exact circle tangents weld the bowls to their straight bars without hairline gaps.
            if i==0 and start_direction is not None:before=after=start_direction
            if i==len(points)-1 and end_direction is not None:before=after=end_direction
            scale=r/(1+before[0]*after[0]+before[1]*after[1])
            ox=-(before[1]+after[1])*scale;oy=(before[0]+after[0])*scale
            left.append((x+ox,y+oy));right.append((x-ox,y-oy))
        return left+list(reversed(right))
    def arc(cx,cy,radius,start,end,y_radius=None):
        ry=radius if y_radius is None else y_radius
        return [(cx+radius*math.cos(start+(end-start)*i/64),cy+ry*math.sin(start+(end-start)*i/64)) for i in range(65)]
    # Matching rounded bowls, open on the left; no flat top/bottom bars to resemble a B.
    upper=path(arc(w/2,.25+r/2,w/2-r,-5*math.pi/6,math.pi/2,y_radius=(.5-r)/2))
    lower=path(arc(w/2,.75-r/2,w/2-r,-math.pi/2,5*math.pi/6,y_radius=(.5-r)/2))
    return {
        'N':[rectangle(0,0,stroke,1),rectangle(w-stroke,0,w,1),path([(r,r),(w-r,1-r)])],
        '1':[rectangle(w/2-r,0,w/2+r,1-r),path([(r,.29),(w/2,r)]),rectangle(r,1-stroke,w-r,1)],
        '3':[upper,lower],
        # The 7's diagonal runs through the baseline; raster clipping gives it a flat bottom.
        '7':[rectangle(0,0,w,stroke),path([(w-r,r),(r,1)])],
        'F':[rectangle(0,0,stroke,1),rectangle(0,0,w,stroke),rectangle(0,.5-r,w*.84,.5+r)],
        # A single 300-degree open elliptical arc: constant normal stroke width, no closing bar.
        'C':[path(arc(w/2,.5,w/2-r,math.pi/6,11*math.pi/6,y_radius=.5-r))],
    }


def rasterize_glyph(glyph, width, height, samples=4):
    """Scan-convert vector outline unions at 4x4 coverage, returning top-first alpha rows."""
    large_w,large_h=width*samples,height*samples
    coverage=bytearray(large_w*large_h)
    glyph_width=REGISTRATION_WIDTH/REGISTRATION_HEIGHT
    for polygon in vector_glyphs()[glyph]:
        points=[(x/glyph_width*large_w,y*large_h) for x,y in polygon]
        edges=list(zip(points,points[1:]+points[:1]))
        for row in range(max(0,math.floor(min(p[1] for p in points))),min(large_h,math.ceil(max(p[1] for p in points)))):
            y=row+.5;crossings=[]
            for (xa,ya),(xb,yb) in edges:
                if (ya<=y<yb) or (yb<=y<ya):crossings.append(xa+(y-ya)/(yb-ya)*(xb-xa))
            crossings.sort()
            for left,right in zip(crossings[::2],crossings[1::2]):
                start=max(0,math.ceil(left-.5));end=min(large_w,math.ceil(right-.5))
                if end>start:coverage[row*large_w+start:row*large_w+end]=b'\1'*(end-start)
    pixels=bytearray(width*height)
    for y in range(height):
        for x in range(width):
            count=sum(sum(coverage[(y*samples+j)*large_w+x*samples:(y*samples+j)*large_w+(x+1)*samples]) for j in range(samples))
            pixels[y*width+x]=round(count*255/(samples*samples))
    return pixels


def livery_pixels(side, size=ART_SIZE):
    """Original antialiased vector glyphs and ribbons; no font, tracing, or imported pixels.

    Rows are Blender image rows (bottom first). Colors are linear values, not sRGB.
    Only this source-art image is projected: the exported model uses a baked UV atlas.
    """
    width, height = size
    pixels = bytearray(width*height*4)
    def rgba(color): return bytes(round(c*255) for c in color)
    def px(x): return (x-ART_X[0])/(ART_X[1]-ART_X[0])*width
    def py(z): return (ART_Z[1]-z)/(ART_Z[1]-ART_Z[0])*height
    def ribbon(knots,half_width,color):
        slopes=[]
        for i in range(len(knots)):
            xa,za=knots[max(0,i-1)];xb,zb=knots[min(len(knots)-1,i+1)]
            slopes.append((zb-za)/(xb-xa))
        for i,((xa,za),(xb,zb)) in enumerate(zip(knots,knots[1:])):
            for x_pixel in range(max(0,round(px(xa))),min(width,round(px(xb))+1)):
                x=ART_X[0]+(x_pixel+.5)/width*(ART_X[1]-ART_X[0])
                t=min(1,max(0,(x-xa)/(xb-xa)))
                # C1-continuous cubic sweeps avoid angular joins in the original paint masks.
                z=(2*t**3-3*t*t+1)*za+(t**3-2*t*t+t)*(xb-xa)*slopes[i]+(-2*t**3+3*t*t)*zb+(t**3-t*t)*(xb-xa)*slopes[i+1]
                bottom=max(0,round(py(z+half_width)));top=min(height,round(py(z-half_width)))
                for y in range(bottom,top):pixels[(y*width+x_pixel)*4:(y*width+x_pixel+1)*4]=rgba(color)
    ribbon([(-5.85,.16),(.25,.16)],.033,TEAL)
    # Painted directly on the skin, ABOVE the sweeps (body Z is down). No background panel.
    glyph_w=round(REGISTRATION_WIDTH/(ART_X[1]-ART_X[0])*width)
    glyph_h=round(REGISTRATION_HEIGHT/(ART_Z[1]-ART_Z[0])*height)
    for index,glyph in enumerate(REGISTRATION_TEXT):
        mask=rasterize_glyph(glyph,glyph_w,glyph_h)
        advance=index*(REGISTRATION_WIDTH+REGISTRATION_GAP)
        left=round(px(REGISTRATION_LEFT+advance)) if side>0 else round(px(REGISTRATION_RIGHT-advance))-glyph_w
        top=round(py(REGISTRATION_TOP))
        for y in range(glyph_h):
            row=top-1-y
            if not 0<=row<height:continue
            for x in range(glyph_w):
                column=left+x if side>0 else left+glyph_w-1-x
                if not 0<=column<width:continue
                alpha=mask[y*glyph_w+x]
                if not alpha:continue
                offset=(row*width+column)*4
                # Linear straight-alpha source-over also preserves paint if masks ever overlap.
                a=alpha/255;old=pixels[offset+3]/255;out_alpha=a+old*(1-a)
                for c in range(3):pixels[offset+c]=round((NAVY[c]*255*a+pixels[offset+c]*old*(1-a))/out_alpha)
                pixels[offset+3]=round(out_alpha*255)
    return pixels


def body(p):
    """Proper 180-degree X rotation between right-handed body and Blender frames."""
    return (p[0], -p[1], -p[2])


def lod_ratio(name, lod):
    """Per-object reduction; preserve small extent markers and sample round silhouettes."""
    if lod == 0 or name.startswith(PRESERVE_LOD_MESHES): return 1.
    if lod == 2 and name in ('canopy_glass','windshield'): return .06
    if lod == 1 or name.startswith(SILHOUETTE_LOD_PREFIXES): return .18
    return .029


def validate_lod_bounds(reference, candidate):
    """Every exported extremum must remain within 5 mm of LOD0, without rescaling."""
    for end in ('min','max'):
        for axis,(wanted,actual) in enumerate(zip(reference['bounds_body_m'][end],candidate['bounds_body_m'][end])):
            assert abs(actual-wanted) <= LOD_BOUNDS_TOLERANCE_M, dict(
                file=candidate['file'],issue='LOD extremum moved',end=end,axis=axis,
                reference_m=wanted,actual_m=actual,tolerance_m=LOD_BOUNDS_TOLERANCE_M,
                node=candidate['bounds_nodes_body'][end][axis])


def canopy_clearance(mesh_points,mesh_faces,moving_names):
    # Continuous proof, not discrete pose sampling: translations never change z.
    # Use every fuselage triangle whose x interval overlaps the complete swept slider.
    moving=[p for name in moving_names for p in mesh_points.get(name,[])]
    assert moving, 'missing sliding canopy geometry'
    swept_x=(min(p[0] for p in moving)-CANOPY_TRAVEL_M,max(p[0] for p in moving))
    deck=[p for face in mesh_faces['airframe'] if min(p[0] for p in face)<=swept_x[1] and max(p[0] for p in face)>=swept_x[0] for p in face]
    clearance=min(p[2] for p in deck)-max(p[2] for p in moving)
    assert clearance>.003, ('canopy/turtledeck continuous sweep clearance',clearance)
    assert CANOPY_SPLIT_X-CANOPY_TRAVEL_M < -2.65, 'open front bow must clear seat backs'
    return clearance,swept_x


def point_triangle_distance_sq(p,face):
    """Distance to a closed triangle, including edges, using projection and barycentrics."""
    def sub(a,b):return tuple(x-y for x,y in zip(a,b))
    def dot(a,b):return sum(x*y for x,y in zip(a,b))
    a,b,c=face;ab=sub(b,a);ac=sub(c,a);ap=sub(p,a)
    aa=dot(ab,ab);cc=dot(ac,ac);cross=dot(ab,ac)
    determinant=aa*cc-cross*cross
    candidates=[]
    if determinant>1e-24:
        u=(dot(ap,ab)*cc-dot(ap,ac)*cross)/determinant
        v=(dot(ap,ac)*aa-dot(ap,ab)*cross)/determinant
        if u>=0 and v>=0 and u+v<=1:
            q=tuple(x+u*y+v*z for x,y,z in zip(a,ab,ac))
            candidates.append(dot(sub(p,q),sub(p,q)))
    for a,b in ((a,b),(b,c),(c,a)):
        edge=sub(b,a);length=dot(edge,edge)
        t=max(0.,min(1.,dot(sub(p,a),edge)/length)) if length>1e-24 else 0.
        delta=sub(p,tuple(x+t*y for x,y in zip(a,edge)))
        candidates.append(dot(delta,delta))
    return min(candidates)


def canopy_hardware_check(mesh_points,mesh_faces,moving_names):
    # Rails/runners belong to the slider mechanism; the fixed inside latch mounts
    # to the roll-over bar. Every OTHER moving mesh is checked against its glass.
    hardware=set(moving_names)-{'canopy_slide','canopy_glass','canopy_runner_left','canopy_runner_right'}
    assert hardware==set(CANOPY_SURFACE_HARDWARE), ('unchecked canopy hardware',hardware)
    report={}
    for names,surface in ((CANOPY_SURFACE_HARDWARE,'canopy_glass'),(WINDSHIELD_SURFACE_HARDWARE,'windshield')):
        faces=mesh_faces[surface];assert faces, ('missing mounting surface',surface)
        for name in names:
            points=mesh_points[name];assert points, ('missing canopy hardware',name)
            distances=[math.sqrt(min(point_triangle_distance_sq(p,f) for f in faces)) for p in points]
            worst=max(distances)
            assert worst <= CANOPY_HARDWARE_TOLERANCE_M, ('floating canopy hardware',name,worst,CANOPY_HARDWARE_TOLERANCE_M)
            report[name]=dict(surface=surface,vertices=len(points),maximum_distance_m=worst)
    return dict(tolerance_m=CANOPY_HARDWARE_TOLERANCE_M,parts=report)


def validate_glb(path, lod, check_canopy=True):
    """Independent binary-level acceptance gate; callable with CPython without Blender."""
    data = path.read_bytes()
    magic, version, length = struct.unpack_from('<III', data)
    assert (magic, version, length) == (0x46546C67, 2, len(data))
    size, tag = struct.unpack_from('<II', data, 12)
    assert tag == 0x4E4F534A
    doc = json.loads(data[20:20 + size])
    binary = data[28 + size:]
    assert len(doc['nodes']) <= 128
    names = {n.get('name') for n in doc['nodes']}
    assert REQUIRED <= names, sorted(REQUIRED - names)
    triangles = 0
    mesh_triangles = {}
    mesh_points = {}; mesh_faces = {}; moving_names = set()
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    bounds_nodes = dict(min=[None]*3,max=[None]*3)
    # Exporter applies all object scale/rotation before export; pivots use translations only.
    children = {i for n in doc['nodes'] for i in n.get('children', [])}
    def visit(i, translation, moving=False):
        nonlocal triangles
        n = doc['nodes'][i]
        moving = moving or n['name']=='canopy_slide'
        if moving:moving_names.add(n['name'])
        assert 'matrix' not in n and n.get('rotation',[0,0,0,1])==[0,0,0,1] and n.get('scale',[1,1,1])==[1,1,1], n['name']
        t = [a+b for a, b in zip(translation, n.get('translation', [0, 0, 0]))]
        if 'mesh' in n:
            for prim in doc['meshes'][n['mesh']]['primitives']:
                a = doc['accessors'][prim['attributes']['POSITION']]
                v = doc['bufferViews'][a['bufferView']]
                offset = v.get('byteOffset', 0) + a.get('byteOffset', 0)
                stride = v.get('byteStride', 12)
                positions=[]
                for j in range(a['count']):
                    p = struct.unpack_from('<3f', binary, offset + j*stride)
                    positions.append(tuple(p[k]+t[k] for k in range(3)))
                    for k in range(3):
                        value=p[k]+t[k]
                        if value<lo[k]:lo[k]=value;bounds_nodes['min'][k]=n['name']
                        if value>hi[k]:hi[k]=value;bounds_nodes['max'][k]=n['name']
                mesh_points.setdefault(n['name'],[]).extend(positions)
                ia=doc['accessors'][prim['indices']];iv=doc['bufferViews'][ia['bufferView']]
                io=iv.get('byteOffset',0)+ia.get('byteOffset',0)
                code={5121:'B',5123:'H',5125:'I'}[ia['componentType']]
                indices=struct.unpack_from('<'+code*ia['count'],binary,io)
                mesh_faces.setdefault(n['name'],[]).extend(tuple(positions[indices[k+j]] for j in range(3)) for k in range(0,len(indices),3))
                triangles += doc['accessors'][prim['indices']]['count']//3
                mesh_triangles[n['name']] = mesh_triangles.get(n['name'], 0) + doc['accessors'][prim['indices']]['count']//3
                material = doc.get('materials', [])[prim['material']] if 'material' in prim else {}
                if 'normalTexture' in material:
                    assert 'TANGENT' in prim['attributes'], ('missing normal-map tangents', n['name'])
                    assert 'TEXCOORD_0' in prim['attributes'], ('missing normal-map UVs', n['name'])
        for child in n.get('children', []):
            visit(child, t, moving)
    for i in set(range(len(doc['nodes']))) - children:
        visit(i, [0, 0, 0])
    clearance,swept_x=canopy_clearance(mesh_points,mesh_faces,moving_names) if check_canopy else (None,None)
    hardware=canopy_hardware_check(mesh_points,mesh_faces,moving_names) if check_canopy else None
    fillets=wing_fillet_check(mesh_points,lod)
    assert triangles <= BUDGETS[lod], (lod, triangles, BUDGETS[lod])
    dimensions = [hi[k]-lo[k] for k in range(3)]
    for actual, wanted in zip(dimensions, [FACTS['length'], FACTS['span'], FACTS['height']]):
        assert abs(actual/wanted-1) <= .01, dict(file=str(path),dimensions_m=dimensions,
                bounds_body_m=dict(min=lo,max=hi),bounds_nodes_body=bounds_nodes)
    images = doc.get('images', [])
    assert len(images) <= 8
    for image in images:
        assert image['mimeType'] == 'image/png'
        if 'uri' in image:
            uri=image['uri']
            assert uri.startswith('textures/exterior/shared-') and uri.endswith('.png') and '..' not in uri
            png=(path.parent/uri).read_bytes()
        else:
            view = doc['bufferViews'][image['bufferView']]
            start = view.get('byteOffset', 0)
            png = binary[start:start+view['byteLength']]
        assert png[:8] == b'\x89PNG\r\n\x1a\n'
        assert struct.unpack_from('>II', png, 16) == (TEXTURE_SIZE, TEXTURE_SIZE)
    assert len(data) <= 64*1024*1024
    return dict(file=path.name, wing_fillets=fillets, canopy_hardware=hardware, canopy_clearance_m=clearance, canopy_travel_m=CANOPY_TRAVEL_M, canopy_swept_x_m=swept_x, triangles=triangles, dimensions_m=dimensions,
                bounds_body_m=dict(min=lo,max=hi),bounds_nodes_body=bounds_nodes,
                nodes=len(names),images=len(images),bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                mesh_triangles=dict(sorted(mesh_triangles.items(), key=lambda row: (-row[1], row[0]))))


def body_axes_glb(path):
    """Rotate Blender to body axes by 180 degrees around X; preserve handedness.

    Both spaces are right-handed. A single-axis reflection mirrors the airframe/lettering
    relative to the renderer's real cameras. This proper rotation preserves winding and w.
    """
    data=path.read_bytes();size=struct.unpack_from('<I',data,12)[0]
    doc=json.loads(data[20:20+size]);binary=bytearray(data[28+size:]);done=set()
    def rotate(index,tangent=False):
        if index in done:return
        done.add(index);a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
        start=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',16 if tangent else 12)
        for j in range(a['count']):
            for axis in (1,2):
                offset=start+j*stride+axis*4
                struct.pack_into('<f',binary,offset,-struct.unpack_from('<f',binary,offset)[0])
        if 'min' in a:
            for axis in (1,2):a['min'][axis],a['max'][axis]=-a['max'][axis],-a['min'][axis]
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            for key in ['POSITION','NORMAL','TANGENT']:
                if key in primitive['attributes']:rotate(primitive['attributes'][key],key=='TANGENT')
    for node in doc['nodes']:
        if 'translation' in node:
            for axis in (1,2):node['translation'][axis]*=-1
    doc['asset']['generator']='FlightCraft original Blender exterior, body x-forward/y-right/z-down'
    encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    binary+=b'\0'*((-len(binary))%4)
    path.write_bytes(struct.pack('<III',0x46546C67,2,28+len(encoded)+len(binary))+
                     struct.pack('<II',len(encoded),0x4E4F534A)+encoded+
                     struct.pack('<II',len(binary),0x004E4942)+binary)
    path.write_bytes(normalize_node_names(path.read_bytes()))


def build(out):
    import bpy
    from array import array
    from mathutils import Vector, Matrix
    from mathutils.bvhtree import BVHTree
    from math import sin, cos, pi, sqrt
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'; scene.render.threads = 4
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 1600; scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    low = bpy.data.collections.new('FlightCraft LOD0'); scene.collection.children.link(low)
    high = bpy.data.collections.new('Bake high'); scene.collection.children.link(high)
    mats, parts = {}, {}
    def shader_tree(datablock):
        # 5.2 supplies node trees directly; only older versions need the legacy switch.
        # Blender 6 can remove use_nodes without affecting the normal path here.
        tree = datablock.node_tree
        if tree is None:
            datablock.use_nodes = True
            tree = datablock.node_tree
        if tree is None:
            raise RuntimeError('Shader node tree is unavailable: '+datablock.name)
        return tree
    # Validate the Blender 5.x procedural sky before any expensive modeling or bakes.
    world=bpy.data.worlds.new('Procedural outdoor sky');scene.world=world;nt=shader_tree(world)
    bg=nt.nodes.get('Background') or nt.nodes.new('ShaderNodeBackground')
    output=next((n for n in nt.nodes if n.type=='OUTPUT_WORLD'),None)
    if output is None:output=nt.nodes.new('ShaderNodeOutputWorld')
    sky=nt.nodes.new('ShaderNodeTexSky');sky.sky_type='MULTIPLE_SCATTERING';sky.sun_disc=False
    sky.sun_elevation=math.radians(28);sky.sun_rotation=math.radians(295)
    sky.sun_size=math.radians(.53);sky.sun_intensity=1
    sky.air_density=1;sky.aerosol_density=.35;sky.ozone_density=1
    nt.links.new(sky.outputs['Color'],bg.inputs['Color']);bg.inputs['Strength'].default_value=.32
    nt.links.new(bg.outputs['Background'],output.inputs['Surface'])
    def mat(name, color, metal=0, rough=.28, coat=0, emission=0, glass=False):
        m = bpy.data.materials.new(name)
        nt = shader_tree(m)
        m.diffuse_color = color
        bs = nt.nodes.get('Principled BSDF') or nt.nodes.new('ShaderNodeBsdfPrincipled')
        output = next((n for n in nt.nodes if n.type=='OUTPUT_MATERIAL'), None)
        if output is None: output = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(bs.outputs['BSDF'], output.inputs['Surface'])
        bs.inputs['Base Color'].default_value = color
        bs.inputs['Metallic'].default_value = metal; bs.inputs['Roughness'].default_value = rough
        bs.inputs['Coat Weight'].default_value = coat; bs.inputs['Coat Roughness'].default_value = .12
        bs.inputs['Emission Color'].default_value = color; bs.inputs['Emission Strength'].default_value = emission
        if glass:
            bs.inputs['Transmission Weight'].default_value = .92
            bs.inputs['IOR'].default_value = 1.47
            bs.inputs['Alpha'].default_value = color[3]
            m.surface_render_method = 'BLENDED'
            m.use_transparency_overlap = False
        noise = m.node_tree.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 180
        ramp = m.node_tree.nodes.new('ShaderNodeMapRange')
        ramp.inputs['To Min'].default_value = rough*.85; ramp.inputs['To Max'].default_value = rough*1.16
        m.node_tree.links.new(noise.outputs['Fac'], ramp.inputs['Value'])
        m.node_tree.links.new(ramp.outputs['Result'], bs.inputs['Roughness'])
        mats[name] = m
        return m
    paint = mat('Pearl enamel', WHITE, .06, .24, .85)
    wing_paint = mat('Wing enamel', WHITE, .06, .25, .82)
    livery = mat('Fuselage enamel', WHITE, .06, .24, .85)
    navy = mat('Midnight blue enamel', NAVY, .09, .25, .8)
    teal = mat('Original teal enamel', TEAL, .12, .23, .8)
    aluminum = mat('Brushed aluminum', (.6, .64, .68, 1), .96, .21)
    propmat = mat('Satin blade finish', (.13, .15, .17, 1), .76, .27)
    rubber = mat('Rubber', (.014, .017, .02, 1), 0, .76)
    leather = mat('Graphite upholstery', (.045, .058, .064, 1), 0, .62)
    trim = mat('Matte dark panel coating', (.018, .024, .029, 1), .02, .86)
    anodized = mat('Anodized cabin aluminum', (.075, .090, .105, 1), .82, .34)
    fabric = mat('Woven graphite seat fabric', (.070, .082, .092, 1), 0, .94)
    # Original crossed weave, baked into normal/roughness maps; no source photographs.
    nt=fabric.node_tree;bs=nt.nodes.get('Principled BSDF')
    texcoord=nt.nodes.new('ShaderNodeTexCoord')
    weave=[]
    for direction in ['X','Y']:
        wave=nt.nodes.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction=direction
        wave.inputs['Scale'].default_value=180
        nt.links.new(texcoord.outputs['Generated'],wave.inputs['Vector']);weave.append(wave)
    multiply=nt.nodes.new('ShaderNodeMath');multiply.operation='MULTIPLY'
    for i,wave in enumerate(weave):nt.links.new(wave.outputs['Fac'],multiply.inputs[i])
    bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00035;bump.inputs['Strength'].default_value=.5
    nt.links.new(multiply.outputs[0],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    exhaust = mat('Heat stained steel', (.26, .22, .17, 1), .94, .33)
    glass = mat('Tinted acrylic', (.21, .36, .39, .17), 0, .055, .9, glass=True)
    blur = mat('Propeller blur', (.18, .2, .21, .12), .3, .4, glass=True)
    red = mat('Red lens', (.55, .008, .004, 1), .02, .12, .8, 3)
    green = mat('Green lens', (.004, .48, .08, 1), .02, .12, .8, 3)
    lamp = mat('Clear lamp lens', (.8, .9, 1, 1), .05, .13, .8, 4)
    screen = mat('Passive display glass beside native 2D panel', (.008, .013, .018, 1), 0, .24, .3)
    # Source masks are evaluated on the body itself, so diffuse baking cannot miss a thin decal.
    # These two original art images are not exported; only the final shared UV atlas is exported.
    def scalar(nt,op,*values):
        node=nt.nodes.new('ShaderNodeMath');node.operation=op
        for i,value in enumerate(values):
            if isinstance(value,(int,float)):node.inputs[i].default_value=value
            else:nt.links.new(value,node.inputs[i])
        return node.outputs[0]
    def mix_scalar(nt,a,b,factor):
        return scalar(nt,'ADD',scalar(nt,'MULTIPLY',a,scalar(nt,'SUBTRACT',1,factor)),scalar(nt,'MULTIPLY',b,factor))
    def components(nt,socket):
        node=nt.nodes.new('ShaderNodeSeparateXYZ');nt.links.new(socket,node.inputs[0]);return node.outputs
    def source_frame(material):
        nt=material.node_tree;geo=nt.nodes.new('ShaderNodeNewGeometry')
        return nt,geo,components(nt,geo.outputs['Position']),components(nt,geo.outputs['Normal'])
    def color_mix(nt,factor,a,b):
        node=nt.nodes.new('ShaderNodeMixRGB');node.blend_type='MIX'
        nt.links.new(factor,node.inputs[0])
        for value,index in [(a,1),(b,2)]:
            if isinstance(value,tuple):node.inputs[index].default_value=value
            else:nt.links.new(value,node.inputs[index])
        return node.outputs[0]
    def line_mask(nt,distance,half_width):
        return scalar(nt,'MAXIMUM',0,scalar(nt,'SUBTRACT',1,scalar(nt,'DIVIDE',scalar(nt,'ABSOLUTE',distance),half_width)))
    def rectangle_distance(nt,x,y,cx,cy,hx,hy):
        return scalar(nt,'MAXIMUM',scalar(nt,'SUBTRACT',scalar(nt,'ABSOLUTE',scalar(nt,'SUBTRACT',x,cx)),hx),
                      scalar(nt,'SUBTRACT',scalar(nt,'ABSOLUTE',scalar(nt,'SUBTRACT',y,cy)),hy))
    nt,geo,pos,norm=source_frame(livery)
    uv=nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(scalar(nt,'DIVIDE',scalar(nt,'SUBTRACT',pos['X'],ART_X[0]),ART_X[1]-ART_X[0]),uv.inputs['X'])
    nt.links.new(scalar(nt,'DIVIDE',scalar(nt,'ADD',pos['Z'],ART_Z[1]),ART_Z[1]-ART_Z[0]),uv.inputs['Y'])
    paint_nodes=[]
    for side,label in [(-1,'left'),(1,'right')]:
        image=bpy.data.images.new('Original livery '+label,*ART_SIZE,alpha=True)
        image.colorspace_settings.name='Non-Color';image.alpha_mode='STRAIGHT'
        image.pixels.foreach_set(array('f',(value/255 for value in livery_pixels(side))))
        image.file_format='PNG';image.filepath_raw=str(out/('source-livery-'+label+'.png'));image.save()
        node=nt.nodes.new('ShaderNodeTexImage');node.image=image;node.extension='CLIP';node.interpolation='Linear'
        nt.links.new(uv.outputs['Vector'],node.inputs['Vector']);paint_nodes.append(node)
    right_side=scalar(nt,'LESS_THAN',pos['Y'],0)
    source_rgb=color_mix(nt,right_side,paint_nodes[0].outputs['Color'],paint_nodes[1].outputs['Color'])
    source_alpha=mix_scalar(nt,paint_nodes[0].outputs['Alpha'],paint_nodes[1].outputs['Alpha'],right_side)
    side_mask=scalar(nt,'GREATER_THAN',scalar(nt,'ABSOLUTE',norm['Y']),.40)
    paint_rgb=color_mix(nt,scalar(nt,'MULTIPLY',source_alpha,side_mask),WHITE,source_rgb)
    cowl=line_mask(nt,scalar(nt,'ADD',pos['X'],.38),.0035)
    hatch=line_mask(nt,rectangle_distance(nt,pos['X'],pos['Z'],-.72,.16,.13,.095),.003)
    fuselage_seams=scalar(nt,'MAXIMUM',cowl,scalar(nt,'MULTIPLY',hatch,side_mask))
    bs=nt.nodes.get('Principled BSDF')
    nt.links.new(color_mix(nt,scalar(nt,'MULTIPLY',fuselage_seams,.32),paint_rgb,(.055,.065,.075,1)),bs.inputs['Base Color'])
    bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=1;bump.inputs['Distance'].default_value=.0014
    nt.links.new(scalar(nt,'SUBTRACT',1,fuselage_seams),bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    # Upper wing access hatches, filler-cap rings, and a worn nonskid walk, all baked in place.
    nt,geo,pos,norm=source_frame(wing_paint);bs=nt.nodes.get('Principled BSDF')
    upper=scalar(nt,'GREATER_THAN',norm['Z'],.5)
    hatch=line_mask(nt,rectangle_distance(nt,pos['X'],pos['Y'],-1.82,1.35,.19,.12),.003)
    rings=[];caps=[]
    for side in [-1,1]:
        dx=scalar(nt,'ADD',pos['X'],1.70);dy=scalar(nt,'SUBTRACT',pos['Y'],side*1.10)
        radius=scalar(nt,'SQRT',scalar(nt,'ADD',scalar(nt,'MULTIPLY',dx,dx),scalar(nt,'MULTIPLY',dy,dy)))
        rings.append(line_mask(nt,scalar(nt,'SUBTRACT',radius,.045),.003))
        caps.append(scalar(nt,'LESS_THAN',radius,.042))
    cap=scalar(nt,'MULTIPLY',upper,scalar(nt,'MAXIMUM',*caps))
    trim_tab=line_mask(nt,rectangle_distance(nt,pos['X'],pos['Y'],-5.61,.82,.055,.20),.003)
    seams=scalar(nt,'MULTIPLY',upper,scalar(nt,'MAXIMUM',trim_tab,scalar(nt,'MAXIMUM',hatch,scalar(nt,'MAXIMUM',*rings))))
    walk_distance=rectangle_distance(nt,pos['X'],pos['Y'],-1.62,.775,.43,.175)
    walk=scalar(nt,'MULTIPLY',upper,scalar(nt,'MINIMUM',1,scalar(nt,'MAXIMUM',0,scalar(nt,'DIVIDE',scalar(nt,'MULTIPLY',walk_distance,-1),.012))))
    grain=nt.nodes.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=75
    nt.links.new(geo.outputs['Position'],grain.inputs['Vector'])
    walk_rgb=color_mix(nt,grain.outputs['Fac'],(.29,.32,.33,1),(.40,.43,.44,1))
    colored=color_mix(nt,walk,WHITE,walk_rgb)
    colored=color_mix(nt,cap,colored,(.60,.64,.68,1))
    nt.links.new(color_mix(nt,scalar(nt,'MULTIPLY',seams,.25),colored,(.08,.09,.10,1)),bs.inputs['Base Color'])
    previous_rough=bs.inputs['Roughness'].links[0].from_socket
    nt.links.new(mix_scalar(nt,mix_scalar(nt,previous_rough,.72,walk),.21,cap),bs.inputs['Roughness'])
    nt.links.new(mix_scalar(nt,mix_scalar(nt,.06,0,walk),.96,cap),bs.inputs['Metallic'])
    bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.0012;bump.inputs['Strength'].default_value=1
    height=scalar(nt,'ADD',scalar(nt,'SUBTRACT',1,seams),scalar(nt,'MULTIPLY',scalar(nt,'MULTIPLY',walk,grain.outputs['Fac']),.12))
    nt.links.new(height,bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])

    def relocate(obj, collection=low):
        for c in list(obj.users_collection): c.objects.unlink(obj)
        collection.objects.link(obj)
    def smooth(obj):
        for p in obj.data.polygons: p.use_smooth = True
    def active(obj):
        bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    def apply(obj):
        active(obj)
        for mod in list(obj.modifiers): bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    def mesh(name, points, faces, material, parent=None, pivot=(0, 0, 0)):
        data = bpy.data.meshes.new(name); data.from_pydata([body(p) for p in points], [], [tuple(reversed(face)) for face in faces]); data.update()
        obj = bpy.data.objects.new(name, data); low.objects.link(obj)
        obj.data.materials.append(material); smooth(obj)
        if parent: obj.parent = parent
        obj.location = body(pivot); parts[name] = obj
        return obj
    def empty(name, pivot=(0, 0, 0), parent=None):
        obj = bpy.data.objects.new(name, None); low.objects.link(obj)
        obj.location = body(pivot); obj.parent = parent; parts[name] = obj
        return obj
    def bevel(obj, width=.012, segments=3):
        mod = obj.modifiers.new('Machined edge radius', 'BEVEL'); mod.width = width; mod.segments = segments
        mod = obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL'); mod.keep_sharp = True; mod.weight = 30
    def ellipsoid(name, center, radii, material, parent=None, segments=32, rings=16):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=body(center))
        obj = bpy.context.object; obj.name = name; obj.scale = radii; relocate(obj)
        apply(obj); smooth(obj); obj.data.materials.append(material)
        if parent:
            world = obj.matrix_world.copy(); obj.parent = parent; obj.matrix_world = world
        parts[name] = obj
        return obj
    def box(name, center, scale, material, radius=.025, bevel_segments=3):
        bpy.ops.mesh.primitive_cube_add(size=1, location=body(center)); obj = bpy.context.object
        obj.name = name; obj.scale = scale; relocate(obj); apply(obj)
        obj.data.materials.append(material); bevel(obj, radius, bevel_segments); smooth(obj); parts[name] = obj
        return obj
    def tube(name, points, radius, material, collection=low, polyline=False):
        path_samples, bevel_resolution = next((detail for prefix, detail in TUBE_DETAIL.items()
                                               if name.startswith(prefix)), (12, 3))
        curve = bpy.data.curves.new(name, 'CURVE'); curve.dimensions = '3D'
        curve.resolution_u = path_samples
        curve.bevel_depth = radius; curve.bevel_resolution = bevel_resolution
        if polyline:
            spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
            for p,co in zip(spline.points,points):p.co=(*body(co),1)
        else:
            spline = curve.splines.new('BEZIER'); spline.bezier_points.add(len(points)-1)
            for p, co in zip(spline.bezier_points, points):
                p.co = body(co); p.handle_left_type = p.handle_right_type = 'AUTO'
        obj = bpy.data.objects.new(name, curve); collection.objects.link(obj); obj.data.materials.append(material)
        active(obj); bpy.ops.object.convert(target='MESH'); smooth(obj); parts[name] = obj
        return obj
    def loft(name, stations, material, segments=48, exponent=2.):
        points, faces = [], []
        for x, ry, rz, z in stations:
            for j in range(segments):
                a = j*2*pi/segments; yy,zz=superellipse_section(ry,rz,z,a,exponent);points.append((x,yy,zz))
        for i in range(len(stations)-1):
            for j in range(segments):
                a=i*segments+j; b=i*segments+(j+1)%segments
                faces.append((a, b, b+segments, a+segments))
        faces += [tuple(reversed(range(segments))), tuple((len(stations)-1)*segments+j for j in range(segments))]
        obj=mesh(name, points, faces, material)
        sub=obj.modifiers.new('Continuous curvature shell', 'SUBSURF'); sub.levels=2; sub.render_levels=2
        return obj
    fuselage = loft('airframe',[(x,ry,(bottom-top)/2,(bottom+top)/2) for x,ry,top,bottom in FUSELAGE_SECTIONS],livery,exponent=FUSELAGE_EXPONENT)
    apply(fuselage)
    # Retain the CLOSED, uncut outer hull as the strict interior containment volume.
    active(fuselage);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    hull=BVHTree.FromPolygons([v.co.copy() for v in fuselage.data.vertices],
                             [list(p.vertices) for p in fuselage.data.polygons])
    interior_reports={}
    fillet_checks={}
    def check_interior(objects,label):
        bpy.context.view_layer.update();checked={};bad=[]
        for obj in objects:
            if obj.type!='MESH' or not obj.name.startswith(INTERIOR_PREFIXES):continue
            for vertex in obj.data.vertices:
                point=obj.matrix_world @ vertex.co
                nearest,normal,face,distance=hull.find_nearest(point)
                inside=nearest is not None and (point-nearest).dot(normal)<=-.003
                issue=interior_vertex_error(body(point),inside,obj.name)
                if issue:bad.append(dict(node=obj.name,point_body=body(point),issue=issue))
            checked[obj.name]=len(obj.data.vertices)
        interior_reports[label]=dict(vertices=sum(checked.values()),parts=checked,violations=bad[:30])
        (out/'interior-checks.json').write_text(json.dumps(interior_reports,indent=2)+'\n')
        if bad:raise RuntimeError('Interior containment failed: '+json.dumps(bad[:6]))
    # Cockpit cavity through the upper skin: the interior must remain visible through glass.
    # The rear edge is upright; the opening follows the flat rail deck rather than
    # an ellipsoid cutting down through the rear bulkhead and windshield apron.
    outline=[(-3.01,-.43),(-2.80,-.49),(-2.40,-.50),(-1.65,-.46),
             (-1.30,-.29),(-1.15,0),(-1.30,.29),(-1.65,.46),
             (-2.40,.50),(-2.80,.49),(-3.01,.43)]
    n=len(outline);points=[(x,y,z) for z in [-1.35,.075] for x,y in outline]
    faces=[tuple(reversed(range(n))),tuple(n+j for j in range(n))]
    faces += [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
    cutter=mesh('temporary_cockpit_cut',points,faces,trim)
    active(cutter);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    bevel(cutter,.025,2);apply(cutter)
    cut=fuselage.modifiers.new('Open cockpit rim','BOOLEAN'); cut.operation='DIFFERENCE'; cut.solver='EXACT'; cut.object=cutter
    apply(fuselage); bpy.data.objects.remove(cutter,do_unlink=True); parts.pop('temporary_cockpit_cut')
    shell=fuselage.modifiers.new('Sheet metal skin','SOLIDIFY'); shell.thickness=.008
    apply(fuselage)
    # Separate cowl intake cutouts, dark recesses, and rolled rims.
    for side in [-1,1]:
        cutter=ellipsoid('temporary_intake',(.31,side*.215,-.08),(.18,.060,.055),trim)
        cut=fuselage.modifiers.new('Cowl intake','BOOLEAN'); cut.operation='DIFFERENCE'; cut.object=cutter
        apply(fuselage); bpy.data.objects.remove(cutter,do_unlink=True); parts.pop('temporary_intake')
        ellipsoid('intake_recess_'+str(side),(.19,side*.215,-.08),(.05,.052,.048),trim,segments=16,rings=8)
    # Both pieces sample the same smooth meridian and share the exact seam ring.
    sections=CANOPY_SECTIONS
    seam=canopy_section(CANOPY_SPLIT_X)
    slide=empty('canopy_slide')
    def glazing(name,stations,parent=None,rear_cap=False):
        points=[];faces=[];cols=32;ring=cols+1
        for x,width,height in stations:
            for j in range(ring):
                angle=j*pi/cols
                points.append((x,width*cos(angle),CANOPY_BASE_Z-height*sin(angle)))
        for i in range(len(stations)-1):
            for j in range(cols):
                a=i*ring+j;faces.append((a,a+1,a+1+ring,a+ring))
        if rear_cap:faces.append(tuple(reversed(range(ring))))
        return mesh(name,points,faces,glass,parent=parent)
    glazing('canopy_glass',[v for v in sections if v[0]<CANOPY_SPLIT_X]+[seam],slide,True)
    glazing('windshield',[seam]+[v for v in sections if v[0]>CANOPY_SPLIT_X])
    box('windshield_apron',(-1.10,0,-.420),(.10,.20,.05),paint,.01,bevel_segments=1)
    def bow(name,x,width,height,radius,material,parent=None,base=CANOPY_BASE_Z):
        obj=tube(name,[(x,width*cos(j*pi/32),base-height*sin(j*pi/32)) for j in range(33)],radius,material,polyline=True)
        obj.parent=parent
        return obj
    def surface_ribbons(name,patches,material,parent=None):
        points=[];faces=[]
        for xs,angles in patches:
            offset=len(points);ring=len(angles)
            points.extend(canopy_surface(x,angle) for x in xs for angle in angles)
            for i in range(len(xs)-1):
                for j in range(ring-1):
                    a=offset+i*ring+j;faces.append((a,a+1,a+ring+1,a+ring))
        return mesh(name,points,faces,material,parent=parent)
    angles=[j*pi/16 for j in range(17)]
    surface_ribbons('canopy_bow_rear',[([-3.04,-3.026],angles)],paint,slide)
    surface_ribbons('canopy_bow_front',[([CANOPY_SPLIT_X-.025,CANOPY_SPLIT_X-.011],angles)],paint,slide)
    surface_ribbons('windshield_frame',[([CANOPY_SPLIT_X+.005,CANOPY_SPLIT_X+.019],angles)],paint)
    spine_x=[-3.033+(CANOPY_SPLIT_X-.018+3.033)*i/16 for i in range(17)]
    surface_ribbons('canopy_latch_spine',[(spine_x,[pi/2-.016,pi/2+.016])],aluminum,slide)
    # Flush exterior handle at canopy centre-top, connected to the crown frame strip.
    # Its entire U-shaped outline is surface-mounted, including both ends and bridge.
    centre=(-3.04+CANOPY_SPLIT_X)/2
    xs=[centre-.045+i*.09/4 for i in range(5)]
    surface_ribbons('canopy_outside_latch',[(xs,[pi/2-.025,pi/2-.019]),
        (xs,[pi/2+.019,pi/2+.025]),([centre+.035,centre+.045],[pi/2-.025,pi/2+.025])],trim,slide)
    # Fixed hoop behind both seat backs. The POH places the inside latch at its centre top.
    bow('roll_over_bar',-2.82,.475,.535,.022,aluminum,base=-.405)
    tube('canopy_inside_latch',[(-2.80,0,-.94),(-2.77,0,-.965),(-2.72,0,-.965)],.010,trim,polyline=True)
    for label,side in [('left',-1),('right',1)]:
        # Straight sliders on cockpit side skins; front runners remain on rail throughout travel.
        tube('canopy_rail_'+label,[(-3.15,side*.55,-.412),(-1.90,side*.55,-.412)],.012,aluminum,polyline=True)
        sill_x=[-3.04+(CANOPY_SPLIT_X+3.04)*i/12 for i in range(13)]
        surface_ribbons('canopy_sill_'+label,[(sill_x,[pi-.020,pi] if side<0 else [0,.020])],paint,slide)
        runner=box('canopy_runner_'+label,(-2.0,side*.55,-.430),(.10,.035,.022),aluminum,.004,bevel_segments=1)
        runner.parent=slide
        tube('windshield_sill_'+label,[(seam[0],side*seam[1],-.4225)]+[(x,side*width,-.4225) for x,width,height in sections if x>CANOPY_SPLIT_X],.025,paint,polyline=True)
    # Every cabin fitting lies below the rail and within the original closed fuselage.
    box('cabin_floor',CABIN_FLOOR_CENTER,CABIN_FLOOR_SIZE,trim,bevel_segments=1)
    box('baggage_bulkhead',(CABIN_FLOOR_AFT-.015,0,-.035),(.03,.82,.43),trim,.012,bevel_segments=1)
    for side in [-1,1]:
        box('seat_cushion_'+str(side),(-2.28,side*.205,-.02),(.44,.34,.13),fabric,.05)
        back=box('seat_back_'+str(side),(-2.55,side*.195,-.12),(.10,.25,.48),fabric,.045)
        back.rotation_euler.y=-.12;apply(back)
        for offset in [-.065,.065]:
            tube('seat_stitch_'+str((side,offset)),[(-2.61,side*.205+offset,-.35),(-2.61,side*.205+offset,-.14),(-2.50,side*.205+offset,-.025)],.0018,aluminum)
        tube('belt_'+str(side),[(-2.54,side*.32,-.26),(-2.40,side*.205,-.16),(-2.12,side*.08,-.07)],.015,navy)
        tube('control_stick_'+str(side),[(-2.1,side*.205,.05),(-2.05,side*.205,-.18),(-1.98,side*.205,-.25)],.012,anodized)
        ellipsoid('stick_grip_'+str(side),(-1.98,side*.205,-.25),(.025,.026,.065),trim,segments=16,rings=8)
        box('display_bezel_'+str(side),(-1.768,side*.175,-.15),(.030,.28,.19),trim,.009)
        box('display_'+str(side),(-1.787,side*.175,-.15),(.004,.248,.163),screen,.003)
        # Side trim follows the cabin rather than a floating flat slab in front of the eye.
        points,faces=side_panel_geometry(side)
        lining=mesh('side_panel_'+str(side),points,faces,trim);bevel(lining,.004,2)
        box('armrest_'+str(side),(-2.26,side*.395,-.205),(.46,.065,.045),fabric,.018,bevel_segments=2)
        box('rudder_pedal_'+str(side),(-1.54,side*.20,.045),(.045,.13,.09),anodized,.008,bevel_segments=1)
    points,faces=dashboard_geometry()
    dash=mesh('panel_silhouette',points,faces,trim);bevel(dash,.006,2)
    points,faces=dashboard_geometry(glareshield=True)
    coaming=mesh('glareshield',points,faces,trim);bevel(coaming,.005,2)
    box('center_console',(-2.04,0,-.04),(.60,.15,.18),trim,bevel_segments=1)
    tube('throttle',[(-1.93,0,-.12),(-1.93,0,-.22)],.012,anodized)
    ellipsoid('throttle_grip',(-1.93,0,-.235),(.025,.042,.025),trim,segments=12,rings=6)
    # Original analytic closed cambered section (not a copied airfoil dataset).
    def foil(name,span,root,tip,lead,z,side=1,fraction=(0,1),start=0,end=None,
             vertical=False,pivot=(0,0,0),wing=False,sweep=.03,dihedral=0,tip_cap=False):
        points,faces=[],[];rows,samples=(5,24) if tip_cap else (14,32)
        for i in range(rows+1):
            t=i/rows;distance=start+((span if end is None else end)-start)*t
            chord=wing_chord(distance) if wing else root+(tip-root)*distance/span
            for j in range(2*samples):
                q=j/samples if j<=samples else (2*samples-j)/samples
                u=fraction[0]+(fraction[1]-fraction[0])*(1-cos(pi*q))/2
                thickness,camber=foil_section(chord,u,wing)
                xx=lead-sweep*distance-chord*u
                yy=side*distance;zz=z-distance*math.tan(math.radians(dihedral))-camber+(-thickness if j<=samples else thickness)
                if tip_cap:
                    # Small planform corner rounds and a 45 mm upturn, not a winglet.
                    yy=side*(distance-WING_TIP_RADIUS*t*t*abs(2*u-1)**10);zz-=.045*t*t
                point=(xx,yy,zz) if not vertical else (xx,(-thickness if j<=samples else thickness),z-distance)
                points.append(tuple(point[k]-pivot[k] for k in range(3)))
        ring=2*samples
        for i in range(rows):
            for j in range(ring):
                a=i*ring+j;b=i*ring+(j+1)%ring;faces.append((a,b,b+ring,a+ring))
        for row in [0,rows]:faces.append(tuple(row*ring+j for j in (reversed(range(ring)) if row==0 else range(ring))))
        obj=mesh(name,points,faces,wing_paint,pivot=pivot)
        # Beveling an already thin wing edge produced stepped/overlapping faces.
        if not wing:bevel(obj,.008,3)
        return obj
    root,tip=WING_ROOT_CHORD,WING_TIP_CHORD
    span=FACTS['span']/2
    for side,label in [(-1,'left'),(1,'right')]:
        common=dict(span=span,root=root,tip=tip,lead=-1.05,z=WING_ROOT_Z,side=side,
                    wing=True,sweep=WING_SWEEP,dihedral=FACTS['dihedral'])
        foil('wing_'+label,**common,end=span-WING_TIP_PANEL,fraction=(0,.726))
        # Long inboard flaps and shorter outer ailerons, with actual 8 mm hinge gaps.
        for name,start,end in [('flap',.57,span*.62-.004),('aileron',span*.62+.004,span-WING_TIP_PANEL-.005)]:
            hinge=(-1.05-WING_SWEEP*start-wing_chord(start)*.73,side*start,
                   WING_ROOT_Z-start*math.tan(math.radians(FACTS['dihedral']))-.012*wing_chord(start)*sin(pi*.73))
            foil(name+'_'+label,**common,start=start,end=end,fraction=(.734,1),pivot=hinge)
        foil('wingtip_'+label,**common,start=span-WING_TIP_PANEL,tip_cap=True)
        # Thin saddle tangent to the fuselage side and upper airfoil, ending before the flap hinge.
        def hull_hit(xx,start_z,side=side):
            hit=hull.ray_cast(Vector(body((xx,side*2,start_z))),Vector(body((0,-side,0))))
            return None if hit[0] is None else body(hit[0])
        points=wing_fillet_points(side,hull_hit)
        cols=WING_FILLET_COLS;rows=WING_FILLET_ROWS;faces=[]
        for i in range(rows):
            for j in range(cols):
                a=i*(cols+1)+j;faces.append((a,a+1,a+cols+2,a+cols+1))
        # The fillet must stay inside the wing/fuselage envelope, and out of the fuselage shell.
        envelope=wing_fillet_envelope_violations(points,side)
        buried=[p for p in points if (lambda hit:hit[0] is not None and (Vector(body(p))-hit[0]).dot(hit[1])<-.003)(hull.find_nearest(Vector(body(p))))]
        fillet_checks['wing_fillet_'+label]=dict(vertices=len(points),envelope_violations=len(envelope),
                                                 inside_fuselage=len(buried),max_rise_m=WING_FILLET_RISE,reach_m=WING_FILLET_REACH)
        if envelope or buried:raise RuntimeError('Wing fillet envelope failed: '+json.dumps(dict(envelope=envelope[:4],buried=buried[:4])))
        fillet=mesh('wing_fillet_'+label,points,faces,wing_paint)
        skin=fillet.modifiers.new('Fillet sheet thickness','SOLIDIFY');skin.thickness=.0015
        foil('stabilizer_'+label,FACTS['tail_span']/2,.84,.56,-4.95,-.13,side,fraction=(0,.486))
    elevator=empty('elevator')
    for side,label in [(-1,'left'),(1,'right')]:
        obj=foil('elevator_skin_'+label,FACTS['tail_span']/2,.84,.56,-4.95,-.13,side,
                 fraction=(.494,1),pivot=(-5.3616,0,-.145))
        obj.parent=elevator  # Identity parent: preserve each mesh's own hinge pivot.
    # Straight swept edges, a squared top, and the conventional POH elevator/trim-tab layout.
    foil('fin',FACTS['vertical_span'],1.10,.40,-4.82,-.13,vertical=True,fraction=(0,.546),sweep=.45)
    foil('rudder',FACTS['vertical_span'],1.10,.40,-4.82,-.13,vertical=True,fraction=(.554,1),sweep=.45,pivot=(-5.425,0,-.13))
    spinner=loft('spinner',[(.31,.185,.185,PROP_Z),(.34,.185,.185,PROP_Z),(.49,.150,.150,PROP_Z),(.64,.045,.045,PROP_Z),(.675,.003,.003,PROP_Z)],aluminum)
    apply(spinner)
    # Twisted foil blades: broad root, curved leading edge, tapered tips, closed trailing edge.
    pp,ff=[],[]; stations, samples=18,20
    for blade in range(FACTS['blades']):
        phase=blade*2*pi/FACTS['blades']; offset=len(pp)
        for i in range(stations+1):
            t=i/stations; radius=.13+(FACTS['prop_diameter']/2-.13)*t
            chord=.125*(.66+.55*sin(pi*t))*(1-.80*t**7)
            pitch=math.radians(38-22*t); sweep=.055*t*t
            for j in range(2*samples):
                q=j/samples if j<=samples else (2*samples-j)/samples
                u=(1-cos(pi*q))/2; thick=.065*chord*sin(pi*u)**.6
                along=(u-.35)*chord+sweep; normal=thick if j<=samples else -thick
                x=along*sin(pitch)+normal*cos(pitch)
                tangential=along*cos(pitch)-normal*sin(pitch)
                pp.append((x, radius*cos(phase)-tangential*sin(phase), radius*sin(phase)+tangential*cos(phase)))
        ring=2*samples
        for i in range(stations):
            for j in range(ring):
                a=offset+i*ring+j; b=offset+i*ring+(j+1)%ring; ff.append((a,b,b+ring,a+ring))
        ff.append(tuple(offset+stations*ring+j for j in range(ring)))
    mesh('propeller',pp,ff,propmat,pivot=(.40,0,PROP_Z))
    # Blur disc is exported but hidden in Cycles stills.
    mesh('prop_blur',[(0,0,0)]+[(0,FACTS['prop_diameter']/2*cos(j*2*pi/64),FACTS['prop_diameter']/2*sin(j*2*pi/64)) for j in range(64)],
         [(0,j+1,(j+1)%64+1) for j in range(64)],blur,pivot=(.41,0,PROP_Z))
    def parent_world(obj,parent):
        bpy.context.view_layer.update();world=obj.matrix_world.copy()
        obj.parent=parent;obj.matrix_world=world;bpy.context.view_layer.update()
    def teardrop_pant(index,x,y,z,parent):
        # Rounded nose faces +X; the tapered tail trails behind the tire, along -X.
        stations=[(-.45,.002,.003),(-.39,.035,.04),(-.29,.080,.09),(-.14,.115,.125),
                  (.02,.135,.15),(.15,.13,.15),(.26,.10,.125),(.32,.055,.075),(.35,.002,.003)]
        sections=[]
        for i in range(len(stations)-1):
            for sample in range(2):
                t=sample/2;a=stations[max(0,i-1)];b=stations[i];c=stations[i+1];d=stations[min(len(stations)-1,i+2)]
                radii=[max(.001,.5*((2*b[k])+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t)) for k in [1,2]]
                sections.append((b[0]+(c[0]-b[0])*t,*radii))
        sections.append(stations[-1]);points=[];faces=[];segments=24
        for xx,ry,rz in sections:
            for j in range(segments):
                angle=j*2*pi/segments;points.append((xx,ry*sin(angle),-.06+rz*cos(angle)))
        for i in range(len(sections)-1):
            for j in range(segments):
                a=i*segments+j;b=i*segments+(j+1)%segments;faces.append((a,b,b+segments,a+segments))
        faces.extend([tuple(reversed(range(segments))),tuple((len(sections)-1)*segments+j for j in range(segments))])
        pant=mesh('wheel_fairing_'+str(index),points,faces,paint,pivot=(x,y,z));parent_world(pant,parent)
        # A real tire slot, instead of flattening the whole underside into an ellipsoid blob.
        cutter=box('temporary_pant_cut',(x,y,z+.18),(.41,.22,.30),trim,.035,bevel_segments=2)
        apply(cutter);cut=pant.modifiers.new('Rounded tire opening','BOOLEAN');cut.operation='DIFFERENCE';cut.solver='EXACT';cut.object=cutter
        apply(pant);bpy.data.objects.remove(cutter,do_unlink=True);parts.pop('temporary_pant_cut')
        previous=Vector((x+.12,y*.75,.40)) if index<2 else Vector((x+.05,0,.42))
        end=Vector((x,y,z-.08));center=(previous+end)*.5
        joint=ellipsoid('temporary_leg_cuff',tuple(center),(.13 if index<2 else .075,.065,.19),paint,segments=20,rings=10)
        axis=Vector(body(tuple(end-previous)))
        joint.rotation_mode='QUATERNION';joint.rotation_quaternion=axis.to_track_quat('Z','Y');apply(joint)
        union=pant.modifiers.new('Continuous leg-to-pant fairing','BOOLEAN');union.operation='UNION';union.solver='EXACT';union.object=joint
        apply(pant);bpy.data.objects.remove(joint,do_unlink=True);parts.pop('temporary_leg_cuff')
        bevel(pant,.004,2)
        return pant
    gears=[(-1.959,-FACTS['track']/2,CONTACT_Z-.19,.19),(-1.959,FACTS['track']/2,CONTACT_Z-.19,.19),(-.549,0,CONTACT_Z-.16,.16)]
    for index,(x,y,z,radius) in enumerate(gears):
        oleo=empty('oleo_'+str(index),(x,y,z))
        axle=empty('steering',(0,0,0),oleo) if index==2 else oleo
        wheel=empty('wheel_'+str(index),(0,0,0),axle)
        bpy.ops.mesh.primitive_torus_add(major_segments=TIRE_SEGMENTS[0],minor_segments=TIRE_SEGMENTS[1],major_radius=radius*.73,minor_radius=radius*.27,location=body((x,y,z)),rotation=(pi/2,0,0))
        tire=bpy.context.object;tire.name='tire_'+str(index);relocate(tire);apply(tire);tire.data.materials.append(rubber);smooth(tire)
        parent_world(tire,wheel);parts[tire.name]=tire
        ellipsoid('hub_'+str(index),(x,y,z),(.10,.065,.10),aluminum,parent=wheel,segments=16,rings=8)
        teardrop_pant(index,x,y,z,axle)
        route=gear_sections(index,x,y,z)
        points=[];faces=[];segments=16
        # Oval airfoil-like fairing, broad in the flight direction, thin spanwise.
        for xx,yy,zz,chord,width in route:
            for j in range(segments):
                angle=2*pi*j/segments;points.append((xx+chord/2*cos(angle),yy+width/2*sin(angle),zz))
        for i in range(len(route)-1):
            for j in range(segments):
                a=i*segments+j;b=i*segments+(j+1)%segments;faces.append((a,b,b+segments,a+segments))
        faces += [tuple(reversed(range(segments))),tuple((len(route)-1)*segments+j for j in range(segments))]
        leg=mesh('gear_leg_'+str(index),points,faces,paint);parent_world(leg,axle)
        # Hydraulic plumbing is concealed inside the leg: no game-scale brake-line geometry.
    # A short forward-pointing L, mounted to the actual evaluated wing underside.
    anchor_x,anchor_y=-1.40,-2.45
    bpy.context.view_layer.update();wing=parts['wing_left'].evaluated_get(bpy.context.evaluated_depsgraph_get())
    hit,location,normal,face=wing.ray_cast(Vector(body((anchor_x,anchor_y,2))),Vector((0,0,1)))
    if not hit:raise RuntimeError('Pitot mount missed the authored wing underside')
    mount_z=-location.z
    pitot_route=[(anchor_x,anchor_y,mount_z-.003),(anchor_x,anchor_y,mount_z+.075),
                 (anchor_x+.025,anchor_y,mount_z+.10),(anchor_x+.22,anchor_y,mount_z+.10)]
    tube('pitot',pitot_route,.0065,aluminum,polyline=True)
    ellipsoid('pitot_mount',(anchor_x,anchor_y,mount_z),(.022,.018,.010),paint,segments=16,rings=8)
    # Short outlet and a rigid boarding platform, avoiding the V5 wire-like curved silhouettes.
    tube('exhaust',[(-.42,-.23,.26),(-.52,-.31,.43)],.026,exhaust,polyline=True)
    tube('step_left_support',[(-2.77,-.43,.22),(-2.82,-.68,.28)],.018,paint,polyline=True)
    box('step_left',(-2.85,-.71,.29),(.24,.15,.025),paint,.012,bevel_segments=2)
    tube('antenna_dorsal',[(-3.65,0,-.32),(-3.9,0,-.77)],.009,paint)
    tube('antenna_ventral',[(-3.8,0,.25),(-4.0,0,.57)],.007,paint)
    for side in [-1,1]:
        tube('tiedown_'+str(side),[(-2.1,side*2.9,-.03),(-2.1,side*2.94,.04),(-2.1,side*3.0,.04),(-2.1,side*3.04,-.03)],.005,aluminum)
        y=side*(FACTS['span']/2-.05)
        # Small seated tip lenses: side elevation projected the old 20 cm lens over the root.
        ellipsoid('nav_left' if side<0 else 'nav_right',wing_point(abs(y),.14,side,tip=True),(.035,.018,.010),red if side<0 else green,segments=20,rings=10)
        ellipsoid('strobe_left' if side<0 else 'strobe_right',wing_point(abs(y),.27,side,tip=True),(.023,.016,.009),lamp,segments=16,rings=8)
    ellipsoid('nav_tail',(-5.93,0,-.15),(.025,.028,.025),lamp,segments=16,rings=8)
    ellipsoid('beacon',(-5.64,0,-1.565),(.035,.035,.035),red,segments=16,rings=8)
    ellipsoid('landing',(-1.10,-2.8,.015),(.035,.10,.045),lamp,segments=20,rings=10)
    # Registration remains a named binding; its visible artwork is baked into airframe UVs.
    empty('registration',parent=fuselage)
    import re
    for obj in low.objects:
        obj.name=re.sub('[^A-Za-z0-9_-]', '_', obj.name)
    def fit_canopy_hardware(objects):
        bpy.context.view_layer.update()
        for names,surface in ((CANOPY_SURFACE_HARDWARE,'canopy_glass'),(WINDSHIELD_SURFACE_HARDWARE,'windshield')):
            glass_obj=objects[surface]
            glass_obj.data.calc_loop_triangles()
            vertices=[glass_obj.matrix_world @ v.co for v in glass_obj.data.vertices]
            # Ignore the flat rear closing cap: frames mount to the curved outer shell.
            curved=[tuple(t.vertices) for t in glass_obj.data.loop_triangles
                    if max(vertices[i].x for i in t.vertices)-min(vertices[i].x for i in t.vertices)>1e-7]
            tree=BVHTree.FromPolygons(vertices,curved,all_triangles=True)
            for name in names:
                obj=objects[name];inverse=obj.matrix_world.inverted()
                offset=.0025 if name=='canopy_outside_latch' else .0010
                for vertex in obj.data.vertices:
                    nearest,normal,face,distance=tree.find_nearest(obj.matrix_world @ vertex.co)
                    if nearest is None:raise RuntimeError('Missing hardware mounting face: '+name)
                    # Point normals out of the half-shell (Blender +Z is up).
                    outward=Vector((0,nearest.y,max(0.,nearest.z+CANOPY_BASE_Z)))
                    if normal.dot(outward)<0:normal=-normal
                    vertex.co=inverse @ (nearest+normal*offset)
                obj.data.update()

    # Freeze low meshes, recalculate consistent exterior normals, and unwrap as ONE atlas.
    for obj in list(low.objects):
        if obj.type=='MESH':
            apply(obj); active(obj); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
    fit_canopy_hardware({o.name:o for o in low.objects})
    check_interior(list(low.objects),'LOD0')
    # Fail before the six expensive bakes if an authoring change exceeds the hard budget.
    # Loop triangles measure n-gons exactly as triangles, not polygon counts or guessed ratios.
    counts={}
    for obj in low.objects:
        if obj.type=='MESH':
            obj.data.calc_loop_triangles(); counts[obj.name]=len(obj.data.loop_triangles)
    preflight=dict(triangles=sum(counts.values()),limit=BUDGETS[0],
                   mesh_triangles=dict(sorted(counts.items(),key=lambda row:(-row[1],row[0]))))
    (out/'mesh-budget.json').write_text(json.dumps(preflight,indent=2)+'\n')
    print('FLIGHTCRAFT_MESH_BUDGET '+json.dumps(preflight),flush=True)
    assert preflight['triangles']<=BUDGETS[0], ('LOD0 before baking',preflight['triangles'],BUDGETS[0])
    opaque=[o for o in low.objects if o.type=='MESH' and o.name not in ['canopy_glass','windshield','prop_blur']]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in opaque: obj.select_set(True)
    bpy.context.view_layer.objects.active=opaque[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.003)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Build high-poly bake source from the same design and bevel it at sub-millimeter scale.
    high_objects=[]
    for obj in opaque:
        cp=obj.copy(); cp.data=obj.data.copy(); high.objects.link(cp)
        cp.parent=None; cp.matrix_world=obj.matrix_world.copy()
        mod=cp.modifiers.new('High surface edge radii','BEVEL'); mod.width=.0015; mod.segments=3
        if obj.name.startswith(('wing_', 'stabilizer_', 'blade_')):
            sub=cp.modifiers.new('High surface refinement','SUBSURF'); sub.levels=1
        high_objects.append(cp)
    # Project high-only, painted rivet heads onto the ACTUAL hull and wing skin.
    # Their six-millimeter diameter and shallow dome survive a 4096-square normal bake.
    rivet_groups=[('fuselage',[],livery),('wing',[],wing_paint)]
    for x in [-5.2,-4.8,-4.3,-3.8,-3.4,-.75,-.5,-.3]:
        for j in range(40):
            angle=j*2*pi/40
            origin=Vector(body((x,2*sin(angle),2*cos(angle))))
            direction=Vector(body((0,-sin(angle),-cos(angle))))
            hit,location,normal,face=fuselage.ray_cast(origin,direction)
            if hit:rivet_groups[0][1].append((Vector(body(location)),Vector(body(normal))))
    for side,label in [(-1,'left'),(1,'right')]:
        wing=parts['wing_'+label]
        for station in range(9):
            y=side*(.72+station*.43);chord=wing_chord(abs(y))
            for j in range(16):
                u=.07+j*.041;x=-1.05-WING_SWEEP*abs(y)-chord*u
                hit,location,normal,face=wing.ray_cast(Vector(body((x,y,-2))),Vector((0,0,-1)))
                if hit:rivet_groups[1][1].append((Vector(body(location)),Vector(body(normal))))
    for label,rivets,material in rivet_groups:
        pp,ff=[],[]
        for center,normal in rivets:
            normal.normalize();seed=Vector((1,0,0)) if abs(normal.x)<.8 else Vector((0,1,0))
            u=normal.cross(seed).normalized();v=normal.cross(u).normalized();start=len(pp)
            for j in range(8):
                angle=j*2*pi/8;point=center+(u*cos(angle)+v*sin(angle))*.003-normal*.0001
                pp.append(tuple(point))
            pp.extend([tuple(center+normal*.0009),tuple(center-normal*.00035)])
            for j in range(8):ff.extend([(start+j,start+(j+1)%8,start+8),(start+(j+1)%8,start+j,start+9)])
        obj=mesh('bake_rivets_'+label,pp,ff,material);relocate(obj,high);parts.pop(obj.name)
        active(obj);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
        bevel(obj,.00035,2);high_objects.append(obj)
    def joined_copy(objects,name,collection):
        copies=[]
        for obj in objects:
            cp=obj.copy(); cp.data=obj.data.copy(); collection.objects.link(cp)
            cp.parent=None; cp.matrix_world=obj.matrix_world.copy(); apply(cp); copies.append(cp)
        bpy.ops.object.select_all(action='DESELECT')
        for cp in copies: cp.select_set(True)
        bpy.context.view_layer.objects.active=copies[0]; bpy.ops.object.join()
        obj=bpy.context.object; obj.name=name; return obj
    source=joined_copy(high_objects,'High bake source',high)
    def triangulate(obj):
        tri=obj.modifiers.new('Stable game-mesh triangles','TRIANGULATE')
        tri.quad_method='BEAUTY'; tri.ngon_method='BEAUTY'
        apply(obj)
    # Leave high-poly subdivision surfaces on their original topology. The game mesh must
    # use the SAME triangles for the normal bake and export; Blender cannot derive tangents
    # on n-gons. UVs and vertex positions survive this operation unchanged.
    for obj in low.objects:
        if obj.type=='MESH': triangulate(obj)
    for obj in opaque:
        try:
            obj.data.calc_tangents()
            obj.data.free_tangents()
        except RuntimeError as error:
            raise RuntimeError('Normal-map tangent preflight failed: '+obj.name) from error
    target=joined_copy(opaque,'UV bake target',high)
    for obj in high_objects: bpy.data.objects.remove(obj,do_unlink=True)
    # Hide all authored low meshes while baking, retaining the joined target/source only.
    low.hide_render=True
    scene.render.bake.use_selected_to_active=True; scene.render.bake.cage_extrusion=.035
    scene.render.bake.max_ray_distance=.07; scene.render.bake.margin=12
    scene.cycles.bake_type='NORMAL'; scene.cycles.samples=24
    images={}
    originals={m:m.node_tree.nodes.get('Principled BSDF') for m in mats.values()}
    def bake(kind,name):
        image=bpy.data.images.new(name,TEXTURE_SIZE,TEXTURE_SIZE,alpha=False)
        image.colorspace_settings.name='sRGB' if name in ['basecolor','emissive'] else 'Non-Color'
        for m in set(target.data.materials):
            node=m.node_tree.nodes.new('ShaderNodeTexImage'); node.image=image; m.node_tree.nodes.active=node
        bpy.ops.object.select_all(action='DESELECT'); source.select_set(True); target.select_set(True)
        bpy.context.view_layer.objects.active=target
        scene.render.bake.use_pass_direct=False; scene.render.bake.use_pass_indirect=False; scene.render.bake.use_pass_color=True
        bpy.ops.object.bake(type=kind)
        if name=='ao':
            # Limit baked occlusion to a gentle cavity contribution; direct paint remains clean.
            pixels=array('f',[0.0])*(TEXTURE_SIZE*TEXTURE_SIZE*4);image.pixels.foreach_get(pixels)
            for i in range(0,len(pixels),4):
                value=.78+.22*pixels[i];pixels[i]=value;pixels[i+1]=value;pixels[i+2]=value
            image.pixels.foreach_set(pixels);del pixels
        image.filepath_raw=str(out/(name+'.png')); image.file_format='PNG'; image.save()
        images[name]=image
    bake('DIFFUSE','basecolor'); bake('NORMAL','normal'); bake('AO','ao')
    # Bake source material scalar channels through emission, preserving procedural roughness.
    def channel(mode):
        for m,bs in originals.items():
            nt=m.node_tree; output=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
            em=nt.nodes.new('ShaderNodeEmission'); nt.links.new(em.outputs[0],output.inputs['Surface'])
            if mode=='mr':
                combine=nt.nodes.new('ShaderNodeCombineColor'); combine.inputs[0].default_value=1
                if bs.inputs['Roughness'].is_linked:
                    nt.links.new(bs.inputs['Roughness'].links[0].from_socket,combine.inputs[1])
                else: combine.inputs[1].default_value=bs.inputs['Roughness'].default_value
                if bs.inputs['Metallic'].is_linked:nt.links.new(bs.inputs['Metallic'].links[0].from_socket,combine.inputs[2])
                else:combine.inputs[2].default_value=bs.inputs['Metallic'].default_value
                nt.links.new(combine.outputs[0],em.inputs['Color'])
            elif mode=='curvature':
                geo=nt.nodes.new('ShaderNodeNewGeometry'); nt.links.new(geo.outputs['Pointiness'],em.inputs['Color'])
            else:
                em.inputs['Color'].default_value=bs.inputs['Emission Color'].default_value
                em.inputs['Strength'].default_value=bs.inputs['Emission Strength'].default_value
    channel('mr'); bake('EMIT','metallic-roughness')
    channel('curvature'); bake('EMIT','curvature')
    channel('emissive'); bake('EMIT','emissive')
    for m,bs in originals.items():
        output=next(n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL')
        m.node_tree.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
    bpy.data.objects.remove(source,do_unlink=True); bpy.data.objects.remove(target,do_unlink=True)
    high.hide_render=True; high.hide_viewport=True; low.hide_render=False
    # Shared atlas used by every opaque piece. Separate glass carries glTF alpha blending.
    atlas=mat('Baked PBR atlas',(1,1,1,1),1,1,.7)
    nt=atlas.node_tree; bs=nt.nodes.get('Principled BSDF')
    def tex(name):
        n=nt.nodes.new('ShaderNodeTexImage'); n.image=images[name]; n.label=name; return n
    nt.links.new(tex('basecolor').outputs['Color'],bs.inputs['Base Color'])
    mr=tex('metallic-roughness'); split=nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(mr.outputs['Color'],split.inputs[0])
    nt.links.new(split.outputs[1],bs.inputs['Roughness']); nt.links.new(split.outputs[2],bs.inputs['Metallic'])
    normal=nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tex('normal').outputs['Color'],normal.inputs['Color'])
    nt.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
    nt.links.new(tex('emissive').outputs['Color'],bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value=1
    # Recognized glTF occlusion socket, without multiplying AO into direct-lit base color.
    group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
    group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
    occlusion=nt.nodes.new('ShaderNodeGroup'); occlusion.node_tree=group
    nt.links.new(tex('ao').outputs['Color'],occlusion.inputs['Occlusion'])
    variants={}
    for obj in opaque:
        original=obj.data.materials[0]
        if original not in variants:
            variant=atlas.copy(); variant.name='Baked '+original.name
            variant.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value=originals[original].inputs['Coat Weight'].default_value
            variants[original]=variant
        obj.data.materials.clear(); obj.data.materials.append(variants[original])
    reports=[]
    originals_low=list(low.objects)
    for lod,filename in enumerate(['exterior.glb','exterior-lod1.glb','exterior-lod2.glb']):
        export_objects=originals_low
        if lod:
            collection=bpy.data.collections.new('LOD'+str(lod)); scene.collection.children.link(collection)
            mapping={}
            for obj in originals_low:
                cp=obj.copy()
                if obj.type=='MESH': cp.data=obj.data.copy()
                collection.objects.link(cp); cp.name=obj.name+'_LOD_COPY'; mapping[obj]=cp
            for obj,cp in mapping.items():
                cp.parent=mapping.get(obj.parent)
                ratio=lod_ratio(obj.name,lod)
                if cp.type=='MESH' and len(cp.data.polygons)>8 and ratio<1:
                    dec=cp.modifiers.new('Game LOD reduction','DECIMATE'); dec.ratio=ratio
                    dec.use_collapse_triangulate=True; apply(cp)
                if cp.type=='MESH': triangulate(cp)
            export_objects=list(mapping.values())
            fit_canopy_hardware({obj.name:cp for obj,cp in mapping.items()})
        bpy.ops.object.select_all(action='DESELECT')
        saved_names={}
        for obj in originals_low:
            saved_names[obj]=obj.name
            if lod: obj.name='SOURCE_'+obj.name
        for obj in export_objects:
            if lod: obj.name=next(saved_names[src] for src,cp in mapping.items() if cp==obj)
            obj.select_set(True)
        check_interior(export_objects,'LOD'+str(lod))
        path=out/filename
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                                  export_yup=False,export_animations=False,export_cameras=False,
                                  export_lights=False,export_normals=True,export_tangents=True,
                                  export_image_format='AUTO',export_apply=True,export_extras=False)
        if lod:
            for cp in export_objects: bpy.data.objects.remove(cp,do_unlink=True)
            for obj,name in saved_names.items(): obj.name=name
        body_axes_glb(path); report=validate_glb(path,lod)
        for obj in originals_low:
            if obj.type=='MESH' and obj.name.startswith(PRESERVE_LOD_MESHES):
                obj.data.calc_loop_triangles()
                assert report['mesh_triangles'].get(obj.name)==len(obj.data.loop_triangles), (
                    filename,'preserved mesh lost triangles during export',obj.name)
        if lod:validate_lod_bounds(reports[0],report)
        reports.append(report)
    assert reports[0]['triangles']>reports[1]['triangles']>reports[2]['triangles']
    assert REQUIRED<=set(PACK_NODE_NAMES.get(o.name,o.name) for o in originals_low)
    # Cycles proof uses the actual game mesh and baked maps, not the hidden bake source.
    parts['prop_blur'].hide_render=True
    # Sky and sun use matching angles; the separate SUN supplies the direct light.
    elevation=math.radians(28);azimuth=math.radians(295)
    sun_direction=Vector((cos(elevation)*cos(azimuth),cos(elevation)*sin(azimuth),sin(elevation)))
    bpy.ops.object.light_add(type='SUN');sun=bpy.context.object;sun.name='Outdoor sun'
    sun.data.energy=3;sun.data.angle=math.radians(.53);sun.data.color=(1,.93,.83)
    sun.rotation_euler=(-sun_direction).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.exposure=-.7
    bpy.ops.mesh.primitive_plane_add(size=2000,location=(0,0,-CONTACT_Z-.005));ground=bpy.context.object
    concrete=mat('Original procedural apron',(.26,.28,.29,1),0,.86)
    nt=concrete.node_tree;bs=nt.nodes.get('Principled BSDF');geo=nt.nodes.new('ShaderNodeNewGeometry')
    noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=35
    nt.links.new(geo.outputs['Position'],noise.inputs['Vector'])
    nt.links.new(color_mix(nt,noise.outputs['Fac'],(.22,.235,.245,1),(.29,.30,.31,1)),bs.inputs['Base Color'])
    ground.data.materials.append(concrete)
    # Write poses before rendering so even an interrupted proof can be reproduced.
    cameras={};camera_objects={}
    for label in list(VIEWS)+list(ORTHO_VIEWS):
        ortho=ORTHO_VIEWS.get(label)
        eye,look=(ortho['eye'],ortho['target']) if ortho else VIEWS[label]
        bpy.ops.object.camera_add(location=body(eye));camera=bpy.context.object;camera.name=label
        direction=(Vector(body(look))-camera.location).normalized()
        if ortho:
            requested_up=Vector(body(ortho['up']));right=direction.cross(requested_up).normalized();up=right.cross(direction).normalized()
            camera.rotation_euler=Matrix((right,up,-direction)).transposed().to_euler()
            camera.data.type='ORTHO';camera.data.sensor_fit='HORIZONTAL';camera.data.ortho_scale=ortho['scale']
            projection=dict(projection='orthographic',ortho_width_m=ortho['scale'])
        else:
            camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
            camera.data.type='PERSP';camera.data.lens=43;camera.data.sensor_width=36
            projection=dict(projection='perspective',vertical_fov_rad=2*math.atan((36/1.6)/(2*43)))
        up=camera.rotation_euler.to_quaternion() @ Vector((0,1,0))
        cameras[label]=dict(eye_body_m=eye,target_body_m=look,up_body=body(up),size=[1600,1000],**projection)
        camera_objects[label]=camera
    for label in ('beauty','elevation-side'):
        cameras[label+'-open']={**cameras[label], 'canopy_open_fraction':1.0}
        camera_objects[label+'-open']=camera_objects[label]
    (out/'cameras.json').write_text(json.dumps(cameras,indent=2)+'\n')
    dimensions=dict(bounds_body_m=reports[0]['bounds_body_m'],length_m=reports[0]['dimensions_m'][0],span_m=reports[0]['dimensions_m'][1],height_m=reports[0]['dimensions_m'][2],
                    required_m=dict(length=FACTS['length'],span=FACTS['span'],height=FACTS['height']),
                    tolerance_fraction=.01,lod_extremum_tolerance_m=LOD_BOUNDS_TOLERANCE_M,
                    lod_bounds_body_m=[r['bounds_body_m'] for r in reports],
                    lod_bounds_nodes_body=[r['bounds_nodes_body'] for r in reports],
                    fuselage_stations_x_halfwidth_top_bottom_m=FUSELAGE_SECTIONS,
                    section_exponent=FUSELAGE_EXPONENT,canopy_stations_x_halfwidth_height_m=CANOPY_SECTIONS,canopy_meridian_bezier=CANOPY_PROFILE,
                    note='Body dimensions checked from exported vertices; orthographic views use no perspective distortion; ortho_width_m is horizontal image width.')
    (out/'orthographic-dimensions.json').write_text(json.dumps(dimensions,indent=2)+'\n')
    for label,camera in camera_objects.items():
        slide.location.x=-CANOPY_TRAVEL_M*cameras[label].get('canopy_open_fraction',0.0)
        bpy.context.view_layer.update()
        scene.camera=camera;scene.render.filepath=str(out/('cycles-'+label+'.png'))
        scene.cycles.samples=96;bpy.ops.render.render(write_still=True)
    # Separate pilot-seat proof retains the accepted exterior camera manifest unchanged.
    pilot_cameras={}
    for label,(yaw,pitch,opened) in PILOT_LOOKS.items():
        forward=(math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),-math.sin(pitch))
        target=tuple(a+b for a,b in zip(PILOT_EYE_M,forward))
        up_body=(-math.sin(pitch)*math.cos(yaw),-math.sin(pitch)*math.sin(yaw),-math.cos(pitch))
        direction=Vector(body(forward));up=Vector(body(up_body));right=direction.cross(up).normalized()
        bpy.ops.object.camera_add(location=body(PILOT_EYE_M));camera=bpy.context.object;camera.name=label
        camera.rotation_euler=Matrix((right,up,-direction)).transposed().to_euler()
        camera.data.type='PERSP';camera.data.sensor_fit='HORIZONTAL';camera.data.sensor_width=36
        fov=math.radians(52);camera.data.lens=(36/1.6)/(2*math.tan(fov/2));camera.data.clip_start=.015
        slide.location.x=-CANOPY_TRAVEL_M*opened;bpy.context.view_layer.update()
        pilot_cameras[label]=dict(eye_body_m=PILOT_EYE_M,target_body_m=target,up_body=up_body,
            projection='perspective',vertical_fov_rad=fov,size=[1600,1000],canopy_open_fraction=opened)
        scene.camera=camera;scene.render.filepath=str(out/('cycles-'+label+'.png'))
        scene.cycles.samples=96;bpy.ops.render.render(write_still=True)
    (out/'pilot-cameras.json').write_text(json.dumps(pilot_cameras,indent=2)+'\n')
    slide.location.x=0.0
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'sling2-exterior.blend'))
    report=dict(blender=bpy.app.version_string,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),registration=REGISTRATION_TEXT,facts=FACTS,lods=reports,textures=TEXTURE_SIZE,
                cameras=cameras,coordinate_conversion='proper rotation: x,-y,-z; no reflection',geometry_revision=GEOMETRY_REVISION,wing_fillet=dict(build_checks=fillet_checks,exported=[r['wing_fillets'] for r in reports],rise_m=WING_FILLET_RISE,reach_m=WING_FILLET_REACH),
                canopy=dict(node='canopy_slide',axis_body=[-1,0,0],travel_m=CANOPY_TRAVEL_M,travel_source='estimate; POH 7.7 gives no travel',
                            clearance_checks=[dict(lod=i,clearance_m=r['canopy_clearance_m']) for i,r in enumerate(reports)],
                            hardware_checks=[r['canopy_hardware'] for r in reports],meridian_bezier=CANOPY_PROFILE),
                lod_policy=dict(preserve_prefixes=PRESERVE_LOD_MESHES,silhouette_prefixes=SILHOUETTE_LOD_PREFIXES,
                                silhouette_ratio=.18,lod1_ratio=.18,lod2_ratio=.029,glazing_lod2_ratio=.06,extremum_tolerance_m=LOD_BOUNDS_TOLERANCE_M),
                lighting=dict(sun_direction_body=body(sun_direction),sun_rgb=[3,2.79,2.49],exposure_ev=-.7),status='awaiting visual review; shape contours are estimates')
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'cameras.json').write_text(json.dumps(cameras,indent=2)+'\n')
    print('FLIGHTCRAFT_EXTERIOR_VALIDATION '+json.dumps(report),flush=True)


def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('output',type=Path)
    parser.add_argument('--validate-only',action='store_true'); parsed=parser.parse_args(args)
    out=parsed.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    if parsed.validate_only:
        reports=[validate_glb(out/name,i) for i,name in enumerate(['exterior.glb','exterior-lod1.glb','exterior-lod2.glb'])]
        for report in reports[1:]:validate_lod_bounds(reports[0],report)
        print(json.dumps(reports,indent=2))
    else:
        build(out)


if __name__=='__main__':
    main()
