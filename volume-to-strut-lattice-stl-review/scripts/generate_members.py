"""FreeCAD CAD clipping, whole-member exclusion and surface support attachment."""
import os,sys,json,math
from pathlib import Path
from collections import defaultdict,deque
sys.path.insert(0,str(Path(__file__).resolve().parent))
import Part,Mesh,MeshPart
from boundary_rules import side_safe, ends_valid, prune_interior_leaves
from stream_stl import Writer,combine
from common import load,sha,fingerprint,lower_plan,intersects,dot
from cad_support import vec,read_shape,cylinder,facets,floor_below

def main():
 c=load(os.environ['SURFACE_LATTICE_CONFIG']);work=Path(c['work_dir']);prep=json.loads((work/'preparation.json').read_text());g=c['geometry'];tol=c['validation']['tolerance_mm'];ss=c['surface_support']
 if prep['config_hash']!=fingerprint(c) or prep['source_hash']!=sha(c['input_step']):raise ValueError('Stale preparation')
 for key,h in prep['brep_hashes'].items():
  if sha(work/(key+'.brep'))!=h:raise ValueError('CAD preparation changed')
 for name in ['members.json','lattice.stl']:
  if (work/name).exists():raise FileExistsError('Use fresh work directory')
 inner=read_shape(work/'inner.brep');opening=prep['opening_planes'];boundary=inner.Shells[0]
 ip=[]
 for f in inner.Faces:
  if type(f.Surface).__name__!='Plane':ip=[];break
  n=list(f.normalAt(0,0));d=dot(n,list(f.CenterOfMass))
  if any(dot(n,list(v.Point))>d+tol for v in inner.Vertexes):ip=[];break
  ip.append((n,d))
 def fully_inside(a,b,r):return bool(ip) and all(max(dot(n,a),dot(n,b))+r<d-tol for n,d in ip)
 def fully_outside(a,b,r):return bool(ip) and any(min(dot(n,a),dot(n,b))-r>d+tol for n,d in ip)
 nodes,candidates=lower_plan(c,prep['local_bounds']);retained=[];removed=[];node_shapes={};strut_shapes={};links=defaultdict(set);roots=set();serial=0
 def node_shape(nid):
  if nid not in node_shapes:
   n=nodes[nid]
   if intersects(n['point'],n['point'],n['radius']+tol,opening):node_shapes[nid]=None
   else:
    if fully_outside(n['point'],n['point'],n['radius']):node_shapes[nid]=None;return None
    s=Part.makeSphere(n['radius'],vec(n['point']))
    if not fully_inside(n['point'],n['point'],n['radius']):s=s.common(inner)
    if c['cover']['thickness_mm']==0 and not side_safe(s,inner,tol):s=Part.makeCompound([])
    node_shapes[nid]=s if not s.isNull() and len(s.Solids)==1 and s.isValid() and s.Volume>tol**3 else None
  return node_shapes[nid]
 def try_strut(s,commit=True,require_both=False):
  a=nodes[s['a']];b=nodes[s['b']]
  if fully_outside(a['point'],b['point'],s['radius']):return None
  if any(intersects(n['point'],n['point'],n['radius']+tol,opening) for n in [a,b]) or intersects(a['point'],b['point'],s['radius']+tol,opening):
   if commit:removed.append(s)
   return None
  sa=node_shape(s['a']);sb=node_shape(s['b'])
  if sa is None and sb is None:return None
  if require_both and (sa is None or sb is None):return None
  interior=fully_inside(a['point'],b['point'],s['radius']);shape=cylinder(a['point'],b['point'],s['radius'])
  if not interior:shape=shape.common(inner)
  if shape.isNull() or len(shape.Solids)!=1 or not shape.isValid() or shape.Volume<=tol**3:return None
  connected=[nid for nid,ns in [(s['a'],sa),(s['b'],sb)] if ns is not None and (interior or ns.common(shape).Volume>tol**3)]
  if not connected or (require_both and len(connected)!=2):return None
  if c['cover']['thickness_mm']==0 and (not side_safe(shape,inner,tol) or not ends_valid(shape,inner,[a['point'],b['point']],[s['a'] in connected,s['b'] in connected],tol)):return None
  if commit:
   if len(retained)>=ss['max_members']:raise ValueError('Member budget exceeded')
   retained.append(s);strut_shapes[s['id']]=shape
   if len(connected)==2:links[connected[0]].add(connected[1]);links[connected[1]].add(connected[0])
   if not interior and shape.common(boundary).Area>tol**2:roots.update(connected)
  return shape
 for index,s in enumerate(candidates):
  try_strut(s)
  if index%500==0:print('BASE_MEMBERS',index,'of',len(candidates),flush=True)
 reachable=set(roots);todo=deque(roots)
 while todo:
  for nid in links[todo.popleft()]-reachable:reachable.add(nid);todo.append(nid)
 base_anchors=sorted(reachable)
 results=[];contacts=[]
 def new_node(nid,p,kind):nodes[nid]={'point':p,'radius':g['top_node_diameter_mm']/2,'kind':kind}
 def edge(a,b,kind,target):
  nonlocal serial
  serial+=1;return {'id':f'top{serial}','a':a,'b':b,'radius':g['top_strut_diameter_mm']/2,'kind':kind,'target_id':target}
 def angle_ok(a,b):
  dz=b[2]-a[2];run=math.hypot(b[0]-a[0],b[1]-a[1])
  return dz>tol and math.degrees(math.atan2(dz,run))>=g['minimum_angle_deg']+.5-1e-8
 for target in prep['targets']:
  if len(results)%100==0:print('SURFACE_TARGETS',len(results),'of',len(prep['targets']),flush=True)
  tid=target['id'];p=target['point'];contact=tid+'_contact';new_node(contact,p,'surface_contact')
  if intersects(p,p,nodes[contact]['radius']+tol,opening):
   results.append({'target_id':tid,'status':'excluded_by_powder_opening'});continue
  floor=floor_below(inner,p,tol);height=p[2]-floor[2]
  if height<=tol*10:raise ValueError('Insufficient cavity depth at '+tid)
  drop=min(g['layer_rise_mm'],height/2);pitch=g['top_pitch_mm'];chosen=None
  offsets=[(0,0),(0,pitch),(0,-pitch),(pitch,0),(-pitch,0),(pitch,pitch),(-pitch,pitch),(pitch,-pitch),(-pitch,-pitch),(0,1.5*pitch),(0,-1.5*pitch),(1.5*pitch,0),(-1.5*pitch,0)]
  offsets += [(dx,dy) for step in [pitch/2,pitch/4,3*pitch/4] for dx,dy in [(0,step),(0,-step),(step,0),(-step,0),(step,step),(-step,step),(step,-step),(-step,-step)]]
  placements=[(d,dx,dy) for d in [drop,drop*.5,drop*.25] for dx,dy in offsets]
  for anchor in sorted(base_anchors,key=lambda a:math.dist(nodes[a]['point'],p)):
   ap=nodes[anchor]['point']
   if angle_ok(ap,p) and p[2]-ap[2]>drop+tol:
    fraction=drop/(p[2]-ap[2]);placements.append((drop,(ap[0]-p[0])*fraction,(ap[1]-p[1])*fraction))
  for attempt,(actual_drop,dx,dy) in enumerate(placements):
   mid=tid+f'_under{attempt}';q=[p[0]+dx,p[1]+dy,p[2]-actual_drop]
   if not angle_ok(q,p) or not inner.isInside(vec(q),1e-7,True):continue
   new_node(mid,q,'surface_lower_layer');up=edge(mid,contact,'surface_top',tid)
   if try_strut(up,False,True) is None:continue
   options=[]
   for anchor in base_anchors:
    ap=nodes[anchor]['point']
    if q[2]-2.5*g['layer_rise_mm']<=ap[2]<q[2] and angle_ok(ap,q):options.append((math.dist(ap,q),anchor))
   connections=[]
   for _,anchor in sorted(options):
    down=edge(anchor,mid,'surface_transition',tid)
    if try_strut(down,False,True) is not None:connections.append(down)
    if len(connections)>=g['supports_per_node']:break
   fallback=False
   if not connections:
    floor_offsets=[(0,0),(0,pitch),(0,-pitch),(pitch,0),(-pitch,0),(0,2*pitch),(0,-2*pitch),(2*pitch,0),(-2*pitch,0)]
    floor_offsets += [(dx,dy) for step in [pitch/2,pitch/4,3*pitch/4] for dx,dy in [(0,step),(0,-step),(step,0),(-step,0),(step,step),(-step,step),(step,-step),(-step,-step)]]
    for floor_attempt,(fx,fy) in enumerate(floor_offsets):
     try:bottom=floor_below(inner,[q[0]+fx,q[1]+fy,q[2]],tol)
     except ValueError:continue
     if not angle_ok(bottom,q):continue
     anchor=tid+f'_floor{attempt}_{floor_attempt}';new_node(anchor,bottom,'surface_floor_anchor');down=edge(anchor,mid,'surface_floor_fallback',tid)
     if try_strut(down,False,True) is not None:connections=[down];fallback=True;break
    if not connections:continue
   chosen=(mid,up,connections,fallback);break
  if chosen is None:raise ValueError('Cannot support '+tid+' without crossing the powder clearance or leaving the cavity; revise placement/parameters')
  mid,up,connections,fallback=chosen
  for s in connections+[up]:
   if try_strut(s,True,True) is None:raise ValueError('Support changed between planning and commit')
  contacts.append((target,contact,mid))
  results.append({'target_id':tid,'status':'supported','contact_node':contact,'lower_node':mid,'struts':[s['id'] for s in connections+[up]],'floor_fallback':fallback,'actual_drop_mm':p[2]-nodes[mid]['point'][2]})
 # Extra diagonals between neighboring local layers retain angle and clearance.
 for target,contact,own_mid in contacts:
  count=1
  near=sorted((math.dist(nodes[mid]['point'],nodes[contact]['point']),mid) for _,_,mid in contacts if mid!=own_mid and angle_ok(nodes[mid]['point'],nodes[contact]['point']))
  for length,mid in near:
   if count>=g['supports_per_node'] or length>2*g['layer_rise_mm']:break
   s=edge(mid,contact,'surface_brace',target['id'])
   if try_strut(s,True,True) is not None:count+=1
 removed_dangling=[]
 if c['cover']['thickness_mm']==0:retained,removed_dangling=prune_interior_leaves(retained,node_shapes,inner,tol)
 used={nid for s in retained for nid in [s['a'],s['b']] if node_shape(nid) is not None}
 emitted=[];volume={}
 with Writer(work/'lattice.stl') as writer:
  for mid in sorted(used)+[s['id'] for s in retained]:
   shape=node_shape(mid) if mid in used else strut_shapes[mid]
   mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=ss['mesh_deflection_mm'],AngularDeflection=.5,Relative=False)
   writer.add(mesh);emitted.append(mid);volume[mid]=shape.Volume
   if len(emitted)%1000==0:print('EXPORTED_MEMBERS',len(emitted),flush=True)
  count=writer.count
 print('TESSELLATED',count,'triangles',flush=True)
 if not count:raise ValueError('No lattice generated')
 combine([work/'cover.stl',work/'lattice.stl'],work/'combined.stl')
 # Save exact clipped members for independent geometric validation.
 Part.makeCompound([node_shape(nid) for nid in sorted(used)]+[strut_shapes[s['id']] for s in retained]).exportBrep(str(work/'lattice.brep'))
 report={'config_hash':fingerprint(c),'nodes':nodes,'retained_nodes':sorted(used),'retained_struts':retained,'removed_struts':removed,'removed_dangling_struts':removed_dangling,'nonempty_members':emitted,'volumes_mm3':volume,'surface_support_results':results,'base_root_nodes':sorted(roots),'lattice_hash':sha(work/'lattice.stl'),'combined_hash':sha(work/'combined.stl'),'lattice_brep_hash':sha(work/'lattice.brep')}
 (work/'members.json').write_text(json.dumps(report,indent=2));print('SURFACE_MEMBERS_GENERATED struts='+str(len(retained))+' targets='+str(len(results)),flush=True)
main()
