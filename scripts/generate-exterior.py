#!/usr/bin/env python3
"""Original analytic Sling 2 exterior, using Python's standard library only.
Rebuild this pack in place, or pass --sling-out PATH. No imported art or traced photos.
Geometry follows POH dimensional facts and independent visual review of the three views.
Body coordinates are forward, right, down, in meters, with node-local hinge pivots.
"""
import argparse
import json
import math
import pathlib
import struct

PI = math.pi
WHITE = [0.88, 0.91, 0.93, 1]
NAVY = [0.025, 0.085, 0.15, 1]
TEAL = [0.015, 0.48, 0.55, 1]
ORANGE = [0.95, 0.29, 0.06, 1]
GLASS = [0.10, 0.24, 0.34, 1]
TIRE = [0.028, 0.032, 0.038, 1]
METAL = [0.49, 0.55, 0.60, 1]

def sub(a, b): return [x-y for x, y in zip(a,b)]
def cross(a,b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def unit(a):
    n = math.sqrt(sum(x*x for x in a))
    return [x/n for x in a] if n > 1e-12 else [0,0,-1]

class Model:
    def __init__(self, coarse):
        self.coarse = coarse
        self.nodes = []
        self.meshes = []
        self.materials = []
        self.views = []
        self.accessors = []
        self.binary = bytearray()
        self.triangles = 0
    def array(self, values, kind):
        while len(self.binary)%4: self.binary.append(0)
        start = len(self.binary)
        for v in values: self.binary.extend(struct.pack('<'+'f'*len(v),*v))
        view = len(self.views)
        self.views.append(dict(buffer=0,byteOffset=start,byteLength=len(self.binary)-start))
        accessor = dict(bufferView=view,componentType=5126,count=len(values),type=kind)
        if kind == 'VEC3':
            accessor.update(min=[min(v[i] for v in values) for i in range(3)],max=[max(v[i] for v in values) for i in range(3)])
        self.accessors.append(accessor)
        return len(self.accessors)-1
    def node(self, name, pos=(0,0,0), parent=None):
        i=len(self.nodes)
        self.nodes.append(dict(name=name,translation=list(pos)))
        if parent is not None: self.nodes[parent].setdefault('children',[]).append(i)
        return i
    def mesh(self, node, points, faces, color, smooth=True):
        normals=[[0,0,0] for _ in points]
        for a,b,c in faces:
            n=cross(sub(points[b],points[a]),sub(points[c],points[a]))
            for i in [a,b,c]: normals[i]=[x+y for x,y in zip(normals[i],n)]
        positions=[]; ns=[]
        for a,b,c in faces:
            normal=unit(cross(sub(points[b],points[a]),sub(points[c],points[a])))
            for i in [a,b,c]: positions.append(points[i]); ns.append(unit(normals[i]) if smooth else normal)
        if color not in self.materials: self.materials.append(color)
        prim=dict(attributes={'POSITION':self.array(positions,'VEC3'),'NORMAL':self.array(ns,'VEC3')},material=self.materials.index(color))
        if 'mesh' not in self.nodes[node]:
            self.nodes[node]['mesh']=len(self.meshes);self.meshes.append(dict(primitives=[]))
        self.meshes[self.nodes[node]['mesh']]['primitives'].append(prim)
        self.triangles+=len(faces)
    def loft(self,node,sections,color,segments=None):
        segments=segments or (10 if self.coarse else 32)
        points=[];faces=[]
        for x, ry, rz, z in sections:
            for j in range(segments):
                a=2*PI*j/segments
                points.append([x,ry*math.sin(a),z+rz*math.cos(a)])
        for i in range(len(sections)-1):
            for j in range(segments):
                a=i*segments+j;b=i*segments+(j+1)%segments;c=b+segments;d=a+segments
                faces.extend([(a,b,c),(a,c,d)])
        self.mesh(node,points,faces,color)
    def ellipsoid(self,node,center,radii,color):
        n=8 if self.coarse else 24
        rows=5 if self.coarse else 12
        points=[];faces=[]
        for i in range(rows+1):
            t=PI*i/rows
            for j in range(n):
                a=2*PI*j/n
                points.append([center[0]+radii[0]*math.cos(t),center[1]+radii[1]*math.sin(t)*math.sin(a),center[2]+radii[2]*math.sin(t)*math.cos(a)])
        for i in range(rows):
            for j in range(n):
                a=i*n+j;b=i*n+(j+1)%n;c=b+n;d=a+n
                faces.extend([(a,b,c),(a,c,d)])
        self.mesh(node,points,faces,color)
    def rod(self,node,a,b,r,color):
        delta=sub(b,a); axis=unit(delta);u=unit(cross(axis,[0,1,0] if abs(axis[1])<.9 else [1,0,0]));v=cross(axis,u)
        n=6 if self.coarse else 12;points=[];faces=[]
        for p in [a,b]:
            for j in range(n):
                t=2*PI*j/n;points.append([p[k]+r*(math.cos(t)*u[k]+math.sin(t)*v[k]) for k in range(3)])
        for j in range(n):
            a=j;b=(j+1)%n;faces.extend([(a,b,b+n),(a,b+n,a+n)])
        self.mesh(node,points,faces,color)
    def foil(self,node,span,root,tip,lead,z,dihedral,color,vertical=False,fraction=(0,1),side=1,sweep=-.10):
        # Analytic cambered closed section, cosine chord sampling. No external airfoil data.
        n=6 if self.coarse else 18; stations=3 if self.coarse else 7
        points=[];faces=[]
        for s in range(stations):
            t=s/(stations-1); y=span*t*side; chord=root+(tip-root)*t
            for j in range(2*n):
                q=j/n if j<=n else (2*n-j)/n
                u=fraction[0]+(fraction[1]-fraction[0])*(1-math.cos(PI*q))/2
                # Finite trailing edge and rounded nose; original analytic surface.
                thick=.075*chord*math.sin(PI*u)**.65
                camber=.025*chord*math.sin(PI*u)
                zz=z-abs(y)*math.tan(dihedral)-camber+(-thick if j<=n else thick)
                x=lead+sweep*abs(y)-chord*u
                points.append([x,zz-z,y+z] if vertical else [x,y,zz])
        ring=2*n
        for s in range(stations-1):
            for j in range(ring):
                a=s*ring+j;b=s*ring+(j+1)%ring;c=b+ring;d=a+ring
                faces.extend([(a,b,c),(a,c,d)])
        for row in [0,stations-1]:
            for j in range(1,ring-1): faces.append((row*ring,row*ring+j,row*ring+j+1))
        self.mesh(node,points,faces,color)
    def save(self,path):
        children={c for n in self.nodes for c in n.get('children',[])}
        doc=dict(asset=dict(version='2.0',generator='FlightCraft original analytic exterior generator'),scene=0,scenes=[dict(nodes=[i for i in range(len(self.nodes)) if i not in children])],nodes=self.nodes,meshes=self.meshes,materials=[dict(pbrMetallicRoughness=dict(baseColorFactor=c,metallicFactor=.15,roughnessFactor=.42),doubleSided=True) for c in self.materials],buffers=[dict(byteLength=len(self.binary))],bufferViews=self.views,accessors=self.accessors)
        data=json.dumps(doc,separators=(',',':')).encode();data+=b' '*((-len(data))%4)
        binary=bytes(self.binary);binary+=b'\0'*((-len(binary))%4)
        path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(data)+len(binary))+struct.pack('<II',len(data),0x4e4f534a)+data+struct.pack('<II',len(binary),0x004e4942)+binary)
        print(path, self.triangles, 'triangles', path.stat().st_size, 'bytes')

# Original block-letter glyphs, expressed as geometry, no font asset.
FONT={'N':['10001','11001','11001','10101','10011','10011','10001'],'1':['00100','01100','00100','00100','00100','00100','01110'],'2':['01110','10001','00001','00010','00100','01000','11111'],'3':['11110','00001','00001','01110','00001','00001','11110'],'4':['00010','00110','01010','10010','11111','00010','00010'],'B':['11110','10001','10001','11110','10001','10001','11110'],'C':['01111','10000','10000','10000','10000','10000','01111'],'L':['10000','10000','10000','10000','10000','10000','11111'],'5':['11111','10000','11110','00001','00001','10001','01110'],'7':['11111','00001','00010','00100','01000','01000','01000'],'9':['01110','10001','10001','01111','00001','00010','01100'],'F':['11111','10000','10000','11110','10000','10000','10000']}

def generate(kind,out):
    sling=kind=='sling2'; corvid=kind=='corvid'
    span=9.165 if sling else 10 if corvid else 8
    length=6.675 if sling else 6.8 if corvid else 5.9
    height=2.45 if sling else 2.7 if corvid else 2.35
    area=11.845 if sling else 15 if corvid else 11
    prop=1.79 if sling else 1.9 if corvid else 1.85
    nose=.675 if sling else 2.5 if corvid else 2.3
    tail=nose-length
    prop_z=-.32 if sling else .01
    wing_lead=-1.05 if sling else .7
    wing_z=.18 if sling else -.68 if corvid else .22
    accent=TEAL if sling or corvid else ORANGE
    reg='N371FC' if sling else 'N373FC' if corvid else 'N925FC'
    gears=[(-1.959,-.975,.85),(-1.959,.975,.85),(-.464,0,.85)] if sling else [(-.45,-1.1,1.15),(-.45,1.1,1.15),(1.8,0,1.15)] if corvid else [(.55,-1.05,1),(.55,1.05,1),(-3.1,0,.32)]
    moving=[];lights=[]
    def bind(name,motion,axis,travel=(-.42,.42),gear=0,radius=.19):
        moving.append(dict(node=name,motion=motion,axis=axis,travel_rad=list(travel),gear_index=gear,wheel_radius_m=radius))
    for coarse in [False,True]:
        m=Model(coarse); moving=[];lights=[]
        body=m.node('airframe')
        front=nose-.35
        cabin=-1.7 if sling else -.15
        # Tapered fuselage stations, rounded engine cowling, and a narrow tail cone.
        sections=[(tail,.015,.025,-.13),(tail+.4,.10,.13,-.09),(tail+1.1,.20,.23,-.04),(cabin-1,.40,.33,.02),(cabin,.56 if sling else .48,.42,0),(cabin+.7,.48,.38,0),(front-.5,.31,.30,-.25 if sling else .01),(front,.20,.20,prop_z)]
        sections=sorted(sections)
        m.loft(body,sections,WHITE)
        # Lower livery and slender colored sweep over the rear fuselage.
        for sign in [-1,1]:
            points=[];faces=[]
            for i,(x,ry,rz,z) in enumerate(sections):
                for level in [.10,.22]:
                    points.append([x,sign*(ry*math.sqrt(1-level*level)+.003),z+level*rz])
                if i: a=2*(i-1);faces.extend([(a,a+1,a+3),(a,a+3,a+2)])
            m.mesh(body,points,faces,accent,False)
        canopy=m.node('canopy')
        m.ellipsoid(canopy,[cabin,0,-.38],[.92 if sling else .72,.50 if sling else .43,.58 if sling else .48],GLASS)
        for sign in [-1,1]:
            m.rod(body,[cabin-.7,sign*.29,-.45],[cabin+.68,sign*.29,-.45],.025,WHITE)
        # Spinner: 3-blade Sling configuration from POH 1.4; no manufacturer marks.
        spinner=m.node('spinner');m.loft(spinner,[(front,.20,.20,prop_z),(nose-.16,.12,.12,prop_z),(nose,.001,.001,prop_z)],WHITE)
        pnode=m.node('propeller',[front+.015,0,prop_z]); bind('propeller','propeller',[1,0,0])
        blades=3 if sling else 2
        for blade in range(blades):
            a=2*PI*blade/blades
            pts=[]
            for r,w in [(.14,.06),(prop*.35,.10),(prop*.49,.055),(prop*.5,.015)]:
                for side in [-1,1]:pts.append([side*.018,r*math.cos(a)+side*w*math.sin(a),r*math.sin(a)-side*w*math.cos(a)])
            m.mesh(pnode,pts,[(0,1,3),(0,3,2),(2,3,5),(2,5,4),(4,5,7),(4,7,6)],NAVY,False)
        blur=m.node('prop_blur',[front+.02,0,prop_z]);bind('prop_blur','prop_blur',[1,0,0])
        n=20 if coarse else 64;pts=[[0,0,0]]+[[0,prop*.5*math.cos(2*PI*j/n),prop*.5*math.sin(2*PI*j/n)] for j in range(n)]
        m.mesh(blur,pts,[(0,j+1,(j+1)%n+1) for j in range(n)],[.55,.60,.65,.14],False)
        # Span/area-driven tapered wings with separate, hinge-local trailing surfaces.
        half=span/2; avg=area/span;root=avg*2*1.375/(1+1.375) if sling else avg*1.08;tip=2*avg-root
        for sign,label in [(-1,'left'),(1,'right')]:
            wing=m.node('wing_'+label)
            m.foil(wing,half,root,tip,wing_lead,wing_z,math.radians(5) if sling else .025,WHITE,fraction=(0,.72),side=sign,sweep=.05 if sling else -.10)
            for motion,low,high in [('flaps',.10,.56),('aileron',.58,.98)]:
                pivot=[wing_lead+(.05 if sling else -.10)*half*low-(root+(tip-root)*low)*.72,sign*half*low,wing_z-half*low*math.tan(math.radians(5) if sling else .025)]
                node=m.node(motion+'_'+label,pivot)
                r=root+(tip-root)*low;t=root+(tip-root)*high
                # The local trailing surface begins on its hinge line.
                m.foil(node,half*(high-low),r,t,r*.72,0,math.radians(5) if sling else .025,accent if motion=='aileron' else WHITE,fraction=(.72,1),side=sign,sweep=.05 if sling else -.10)
                bind(motion+'_'+label,motion,[0,1,0],(0,PI/6) if motion=='flaps' else ((-.419,.419) if sign<0 else (.419,-.419)))
            tipnode=m.node('tip_'+label)
            m.ellipsoid(tipnode,[wing_lead-.6,sign*(half-.10),wing_z-half*.087 if sling else wing_z],[.45,.10,.055],accent)
            if corvid:m.rod(body,[-.45,sign*.45,.35],[.05,sign*3.2,wing_z],.028,METAL)
        if sling:
            # Features independently constructed after inspecting POH section 1.3 three views:
            # curved wing tips, wheel pants, dorsal fin fillet, canopy rails, rear windows,
            # cowling inlet, pitot below the port wing, and aft-raked dorsal antenna.
            for sign in [-1,1]:
                m.ellipsoid(body,[cabin-.77,sign*.405,-.40],[.19,.035,.16],GLASS)
                m.rod(body,[cabin-.70,sign*.50,-.28],[cabin+.70,sign*.50,-.28],.018,METAL)
                m.rod(body,[cabin-.55,sign*.43,-.28],[cabin-.55,sign*.34,-.87],.025,WHITE)
                tipnode=m.node('curved_tip_'+('left' if sign<0 else 'right'))
                m.ellipsoid(tipnode,[wing_lead-.42,sign*(half-.065),wing_z-half*math.tan(math.radians(5))-.02],[.52,.065,.065],WHITE)
            m.ellipsoid(body,[front-.10,0,.18],[.02,.12,.065],NAVY)
            m.rod(body,[cabin-1.65,0,-.32],[cabin-2.1,0,-.72],.014,NAVY)
            m.rod(body,[wing_lead-.20,-2.6,wing_z-.12],[wing_lead-.20,-2.6,wing_z+.18],.012,METAL)
            m.rod(body,[wing_lead-.20,-2.6,wing_z+.18],[wing_lead+.12,-2.6,wing_z+.18],.012,METAL)
        # Conventional horizontal stabilizer + elevator, and swept fin + separate rudder.
        tail_lead=tail+1.13; tail_z=-.13
        hspan=2.825 if sling else 2.9 if corvid else 2.5
        tail_root=.92 if sling else .78;tail_tip=.66 if sling else .48
        tail_parent=None
        if sling:
            # Section 1.3 gives the 0.92 m root chord; section 1.4 gives -4° incidence.
            tail_parent=m.node('horizontal_tail',[tail_lead,0,tail_z])
            m.nodes[tail_parent]['rotation']=[0,math.sin(math.radians(-4)/2),0,math.cos(math.radians(-4)/2)]
        for sign,label in [(-1,'left'),(1,'right')]:
            origin=[0,0,0] if sling else [tail_lead,0,tail_z]
            stab=m.node('stabilizer_'+label,origin,tail_parent)
            m.foil(stab,hspan/2,tail_root,tail_tip,0,0,0,WHITE,fraction=(0,.52),side=sign,sweep=.08 if sling else -.10)
            pivot=[-tail_root*.52,0,0] if sling else [tail_lead-tail_root*.52,0,tail_z]
            e=m.node('elevator_'+label,pivot,tail_parent)
            m.foil(e,hspan/2,tail_root,tail_tip,tail_root*.52,0,0,accent,fraction=(.52,1),side=sign,sweep=.08 if sling else -.10)
            bind('elevator_'+label,'elevator',[0,-1,0],(-.349,.524))
        # Top of fin is fixed by the height datum; broad swept fin, no T-tail.
        top=max(g[2] for g in gears)-height
        # The Sling three-view has a tall, swept conventional fin with a curved dorsal
        # transition and a full-height, aft-sloping rudder hinge. Original surface lofts.
        if sling:
            fin=m.node('vertical_stabilizer')
            levels=[(-.14,tail+1.65,tail+.68),(-.28,tail+1.20,tail+.65),(-.60,tail+.98,tail+.55),(top+.16,tail+.62,tail+.39),(top,tail+.58,tail+.36)]
            pts=[];faces=[]
            for z,front_edge,hinge in levels:
                pts.extend([[front_edge,0,z],[hinge,-.035,z],[hinge,.035,z]])
            for i in range(len(levels)-1):
                a=3*i;b=a+3
                faces.extend([(a,a+1,b+1),(a,b+1,b),(a,a+2,b+2),(a,b+2,b)])
            m.mesh(fin,pts,faces,WHITE)
            rudder=m.node('rudder',[tail+.64,0,-.14])
            pts=[[.04,-.025,0],[-.28,-.025,top+.14],[-.62,-.025,top+.14],[-.38,-.025,.12]]
            m.mesh(rudder,pts,[(0,1,2),(0,2,3)],accent,False)
        else:
            pts=[[tail+1.45,0,-.16],[tail+.67,0,top],[tail+.18,0,top+.08],[tail+.08,0,-.16]]
            fin=m.node('vertical_stabilizer');m.mesh(fin,pts,[(0,1,2),(0,2,3)],WHITE,False)
            rudder=m.node('rudder',[tail+.25,0,-.15]);m.mesh(rudder,[[0,-.015,0],[.04,-.015,top+.23],[-.23,-.015,top+.32],[-.25,-.015,.15]],[(0,1,2),(0,2,3)],accent,False)
        bind('rudder','rudder',[0,0,-1],(-.3665,.3665))
        for i,(x,y,z) in enumerate(gears):
            radius=.19 if i<2 else .16 if sling or corvid else .09
            oleo=m.node('oleo_'+str(i),[x,y,z-radius]);bind('oleo_'+str(i),'oleo',[0,0,-1],(0,0),i)
            m.rod(body,[x-.12,y*.35,.26],[x,y,z-radius-.22],.045,WHITE)
            m.rod(oleo,[0,0,-.25],[0,0,0],.025,METAL)
            parent=oleo
            if i==2:
                parent=m.node('steering',[0,0,0],oleo);bind('steering','steering',[0,0,1],(-.4,.4) if sling or corvid else (.55,-.55),i)
            if sling:m.ellipsoid(parent,[-.01,0,0],[.34,.125,.135],WHITE)
            wheel=m.node('wheel_'+str(i),[0,0,0],parent);bind('wheel_'+str(i),'wheel',[0,1,0],(0,0),i,radius)
            m.ellipsoid(wheel,[0,0,0],[radius,.075,radius],TIRE)
            for sign in [-1,1]:
                m.ellipsoid(wheel,[0,sign*.071,0],[radius*.45,.008,radius*.45],METAL)
                # Contrasting radial hub mark makes rotation visible.
                m.rod(wheel,[0,sign*.081,0],[radius*.4,sign*.081,0],.012,WHITE)
        tip_z=wing_z-half*math.tan(math.radians(5) if sling else .025)
        for name,light_kind,pos,color in [('nav_left','nav_red',[wing_lead-.4,-half,tip_z],[1,.015,.01,1]),('nav_right','nav_green',[wing_lead-.4,half,tip_z],[.01,1,.08,1]),('nav_tail','nav_white',[tail+.03,0,-.1],[1,1,1,1]),('strobe_left','strobe',[wing_lead-.6,-half+.03,tip_z-.06],[1,1,1,1]),('strobe_right','strobe',[wing_lead-.6,half-.03,tip_z-.06],[1,1,1,1]),('beacon','beacon',[tail+.65,0,top+.02],[1,.015,.01,1]),('landing','landing',[front-.1,-.19,prop_z+.12],[1,.96,.80,1])]:
            node=m.node(name,pos);m.ellipsoid(node,[0,0,0],[.035,.025,.025],color);lights.append(dict(node=name,kind=light_kind,power_load=('nav' if light_kind.startswith('nav_') else light_kind) if sling else 'lights'))
        regnode=m.node('registration')
        for sign in [-1,1]:
            for letter,ch in enumerate(reg):
                for row,line in enumerate(FONT[ch]):
                    for col,pixel in enumerate(line):
                        if pixel=='1':
                            x=cabin-1.10-letter*.16-col*.025 if sign<0 else cabin-1.10-len(reg)*.16+letter*.16+col*.025
                            z=-.22+row*.035
                            # Rear cabin side, where the fuselage remains wide enough.
                            def surface_point(xx,zz):
                                a,b=next(((a,b) for a,b in zip(sections,sections[1:]) if a[0]<=xx<=b[0]),(sections[0],sections[1]))
                                t=(xx-a[0])/(b[0]-a[0]);ry=a[1]+t*(b[1]-a[1]);rz=a[2]+t*(b[2]-a[2]);zc=a[3]+t*(b[3]-a[3])
                                yy=sign*(ry*math.sqrt(max(.01,1-((zz-zc)/rz)**2))+.012)
                                return [xx,yy,zz]
                            dx=-.023 if sign<0 else .023
                            m.mesh(regnode,[surface_point(x,z),surface_point(x+dx,z),surface_point(x+dx,z+.032),surface_point(x,z+.032)],[(0,1,2),(0,2,3)],NAVY,False)
        # Bounds include the physical tail end, not just an isolated marker.
        out.mkdir(parents=True,exist_ok=True)
        m.save(out/('exterior-lod1.glb' if coarse else 'exterior.glb'))
    exterior=dict(aircraft=kind,model='exterior.glb',lod1='exterior-lod1.glb',span_m=span,length_m=length,height_m=height,wing_area_m2=area,prop_diameter_m=prop,moving_parts=moving,lights=lights,registration=dict(node='registration',text=reg))
    (out/'exterior.json').write_text(json.dumps(exterior,indent=2)+'\n')
    if sling:
        manifest=json.loads((out/'pack.json').read_text());manifest['format_version']=2;manifest['exterior']=[exterior];manifest['version']='0.2.0';(out/'pack.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--sling-out',type=pathlib.Path)
    args=parser.parse_args()
    generate('sling2',args.sling_out or pathlib.Path(__file__).resolve().parents[1])
