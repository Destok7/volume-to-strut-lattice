"""Configuration, convex geometry and member-level removal, in millimetres."""
import hashlib,json,math
from collections import defaultdict
from pathlib import Path

GEOMETRY=dict(lower_pitch_mm=12.,lower_node_diameter_mm=3.3,lower_strut_diameter_mm=2.4,
 top_pitch_mm=6.,top_node_diameter_mm=5.,top_strut_diameter_mm=5.,layer_rise_mm=11.1,
 minimum_angle_deg=50.,supports_per_node=4,top_layer_count=2)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def sub(a,b):return [x-y for x,y in zip(a,b)]
def add(a,b):return [x+y for x,y in zip(a,b)]
def mul(a,s):return [x*s for x in a]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def unit(a):
 m=math.sqrt(dot(a,a))
 if m<1e-9:raise ValueError('Zero direction vector')
 return mul(a,1/m)
def load(path):
 path=Path(path).resolve();c=json.loads(path.read_text(encoding='utf-8-sig'))
 allowed={'input_step','work_dir','output_stl','output_blend','geometry','build_frame','cover','powder_opening','validation','metadata','object_name','surface_support'}
 if set(c)-allowed:raise ValueError('Unsupported keys: '+str(set(c)-allowed))
 c['geometry']={**GEOMETRY,**c.get('geometry',{})}
 if set(c['geometry'])-set(GEOMETRY):raise ValueError('Unknown geometry key')
 c['cover']={'thickness_mm':2.,**c.get('cover',{})}
 c['powder_opening']={'width_mm':12.,'height_mm':18.,'minimum_angle_deg':50.,'inward_clearance_mm':6.,**c.get('powder_opening',{})}
 c['validation']={'tolerance_mm':.01,**c.get('validation',{})}
 c['build_frame']={'normal':[0,0,1],'x_hint':[1,0,0],**c.get('build_frame',{})}
 c['surface_support']={'angle_threshold_deg':45.,'sampling_deflection_mm':.1,'mesh_deflection_mm':.03,'max_members':20000,**c.get('surface_support',{})}
 ss=c['surface_support']
 if set(ss)!={'angle_threshold_deg','sampling_deflection_mm','mesh_deflection_mm','max_members'}:raise ValueError('Unknown surface_support key')
 if any(not isinstance(x,(float,int)) or not math.isfinite(x) for x in ss.values()):raise ValueError('Invalid surface support values')
 if not 0<ss['angle_threshold_deg']<90 or not 0<ss['sampling_deflection_mm']<=.5 or not 0<ss['mesh_deflection_mm']<=.1:raise ValueError('Invalid surface support threshold or deflection')
 if ss['max_members']!=int(ss['max_members']) or not 1<=ss['max_members']<=100000:raise ValueError('Invalid member budget')
 for key in ['input_step','work_dir','output_stl','output_blend']:
  p=Path(c[key]);c[key]=str((path.parent/p).resolve() if not p.is_absolute() else p.resolve())
 outputs=[Path(c[k]) for k in ['output_stl','output_blend']]
 if len(set(outputs+[Path(c['input_step'])]))!=3:raise ValueError('Input and output paths must differ')
 g=c['geometry'];o=c['powder_opening'];t=c['cover']['thickness_mm']
 if set(c['cover'])!={'thickness_mm'} or set(c['validation'])!={'tolerance_mm'}:raise ValueError('Unsupported cover/validation key')
 if set(c['build_frame'])!={'normal','x_hint'}:raise ValueError('Unsupported frame key')
 if set(o)-{'width_mm','height_mm','minimum_angle_deg','inward_clearance_mm','face_index','center_mm'}:raise ValueError('Unsupported opening key')
 for v in [*g.values(),t,c['validation']['tolerance_mm']]+([o['width_mm'],o['height_mm'],o['minimum_angle_deg'],o['inward_clearance_mm']] if t>0 else []):
  if not isinstance(v,(float,int)) or not math.isfinite(v):raise ValueError('Parameters must be finite numbers')
 if any(g[k]<=0 for k in GEOMETRY if k!='bevel_resolution') or t<0:raise ValueError('Lattice dimensions must be positive; cover thickness must be nonnegative')
 if g['top_layer_count']!=2:raise ValueError('Exactly two top layers are supported')
 if not 0<g['minimum_angle_deg']<89.5:raise ValueError('Invalid lattice angle')
 if g['supports_per_node']!=int(g['supports_per_node']) or not 1<=g['supports_per_node']<=32:raise ValueError('Invalid support count')
 if g['top_pitch_mm']<g['top_node_diameter_mm']:raise ValueError('Top nodes overlap in-plane')
 if t>0:
  if min(o['width_mm'],o['height_mm'])<=0 or o['inward_clearance_mm']<0:raise ValueError('Invalid opening dimensions')
  angle=math.degrees(math.atan2(o['height_mm'],o['width_mm']))
  if not 0<o['minimum_angle_deg']<90 or angle+1e-8<o['minimum_angle_deg']:raise ValueError('Diamond roof violates minimum angle')
 if c['validation']['tolerance_mm']<=0 or (t>0 and c['validation']['tolerance_mm']>=t/10):raise ValueError('Invalid tolerance')
 w=unit(c['build_frame']['normal']);u=unit(sub(c['build_frame']['x_hint'],mul(w,dot(c['build_frame']['x_hint'],w))));v=cross(w,u)
 if dot(w,[0,0,1])<1-1e-10:raise ValueError('This skill uses the world XY plane and +Z build direction; reorient the STEP first')
 c['_frame']=[u,v,w];return c

def surface_angle(normal):
 return math.degrees(math.acos(min(1.,max(-1.,unit(normal)[2]))))

def eligible_surface(normal,threshold=45.):
 # Cavity outward +Z normals identify roofs; bottom faces point down.
 return surface_angle(normal)<threshold-1e-9

def lower_plan(c,bounds):
 """Unclipped lower grid; no privileged highest-face top layers."""
 g=c['geometry'];lo,hi=bounds;p=g['lower_pitch_mm'];rise=g['layer_rise_mm'];u,v,w=c['_frame'];nodes={};layers=[];segments=[]
 count=math.ceil((hi[2]-lo[2])/rise)+2
 estimate=count*(math.ceil((hi[0]-lo[0])/p)+4)*(math.ceil((hi[1]-lo[1])/p)+4)
 if estimate*max(1,g['supports_per_node'])>c['surface_support']['max_members']:raise ValueError('Member budget exceeded')
 for k in range(count):
  shift=p/2 if k%2 else 0;z=lo[2]-rise/2+k*rise;layer=[]
  for ix in range(math.floor((lo[0]-shift)/p)-1,math.ceil((hi[0]-shift)/p)+2):
   for iy in range(math.floor((lo[1]-shift)/p)-1,math.ceil((hi[1]-shift)/p)+2):
    q=[ix*p+shift,iy*p+shift,z];nid=f'b{k}_{ix}_{iy}'
    nodes[nid]={'point':add(add(mul(u,q[0]),mul(v,q[1])),mul(w,q[2])),'radius':g['lower_node_diameter_mm']/2,'kind':'base','layer':k};layer.append(nid)
  layers.append(layer)
 maxrun=rise/math.tan(math.radians(g['minimum_angle_deg']+.5))
 cell=maxrun+1e-8
 for k in range(len(layers)-1):
  buckets=defaultdict(list)
  for a in layers[k]:
   ap=nodes[a]['point'];buckets[(math.floor(ap[0]/cell),math.floor(ap[1]/cell))].append(a)
  for b in layers[k+1]:
   bp=nodes[b]['point'];near=[];bx=math.floor(bp[0]/cell);by=math.floor(bp[1]/cell)
   local=[a for dx in [-1,0,1] for dy in [-1,0,1] for a in buckets[(bx+dx,by+dy)]]
   for a in local:
    ap=nodes[a]['point'];run=math.hypot(bp[0]-ap[0],bp[1]-ap[1])
    if run<=maxrun+1e-8:near.append((run,a))
   for _,a in sorted(near)[:int(g['supports_per_node'])]:segments.append({'id':f'bstrut{len(segments)}','a':a,'b':b,'radius':g['lower_strut_diameter_mm']/2,'kind':'base'})
 return nodes,segments
def fingerprint(c):return hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def intersects(a,b,r,planes):
 """Conservative capsule/convex-solid test; never only test centre lines.
 Expanded halfspaces overestimate the Minkowski sum at corners, so extra
 near-corner members can be removed but a radius intersection is not missed.
 """
 if not planes:return False  # No cover: no powder-port exclusion.
 low,high=0.,1.;delta=sub(b,a)
 for n,d in planes:
  q=d+r-dot(n,a);s=dot(n,delta)
  if abs(s)<1e-12:
   if q<0:return False
  elif s>0:high=min(high,q/s)
  else:low=max(low,q/s)
  if low>high:return False
 return high>=0 and low<=1
