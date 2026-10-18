"""Independent checks of CAD members, local normals, contact and STL exports."""
import os,sys,json,math
from pathlib import Path
from collections import deque,defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parent))
import Part,Mesh
from boundary_rules import side_safe, ends_valid
from common import load,sha,fingerprint
from cad_support import read_shape,vec,xyz,cylinder,project,probe_faces
from mesh_checks import triangles,closed_shell_edges,triangle_hits,disjoint

def main():
 c=load(os.environ['SURFACE_LATTICE_CONFIG']);work=Path(c['work_dir']);p=json.loads((work/'preparation.json').read_text());m=json.loads((work/'members.json').read_text());tol=c['validation']['tolerance_mm'];ss=c['surface_support']
 if p['config_hash']!=fingerprint(c) or m['config_hash']!=fingerprint(c) or p['source_hash']!=sha(c['input_step']):raise ValueError('Configuration/source changed')
 for key,h in p['brep_hashes'].items():
  if sha(work/(key+'.brep'))!=h:raise ValueError('CAD preparation changed')
 for path,h in [(work/'cover.stl',p['cover_stl_hash']),(work/'lattice.stl',m['lattice_hash']),(work/'lattice.brep',m['lattice_brep_hash']),(Path(c['output_stl']),m['output_hash']),(Path(c['output_blend']),m['blend_hash'])]:
  if sha(path)!=h:raise ValueError('Artifact changed: '+str(path))
 source=read_shape(work/'source.brep');inner=read_shape(work/'inner.brep');cover=read_shape(work/'cover.brep');port=read_shape(work/'opening.brep');lattice=read_shape(work/'lattice.brep')
 uncovered=c['cover']['thickness_mm']==0
 if uncovered:
  if cover.Solids or port.Solids or p['opening_planes']:raise ValueError('Uncovered mode contains cover or port')
  if source.cut(inner).Volume>tol**3:raise ValueError('Uncovered boundary differs from source')
 elif not cover.isValid() or len(cover.Solids)!=1 or cover.common(port).Volume>tol**3 or port.common(inner).Volume<=tol**3:raise ValueError('Invalid cover/opening')
 if abs(inner.distToShape(source.Shells[0])[0]-c['cover']['thickness_mm'])>tol:raise ValueError('Inward offset thickness mismatch')
 if inner.cut(source).Volume>tol**3:raise ValueError('Inner cavity escapes source')
 ids=m['retained_nodes']+[s['id'] for s in m['retained_struts']];solids=lattice.Solids
 if len(ids)!=len(solids) or len(set(ids))!=len(ids):raise ValueError('CAD member count/identity mismatch')
 shapes=dict(zip(ids,solids));removed={s['id'] for s in m['removed_struts']}
 if removed&set(ids):raise ValueError('Removed strut was emitted')
 for member_index,(mid,shape) in enumerate(shapes.items()):
  if member_index%500==0:print('VALIDATING CAD',member_index,'of',len(shapes),flush=True)
  if not shape.isValid() or abs(shape.Volume-m['volumes_mm3'][mid])>tol**3:raise ValueError('Invalid stored CAD member '+mid)
  if uncovered and not side_safe(shape,inner,tol):raise ValueError('Uncovered member cut by side '+mid)
  if shape.cut(inner).Volume>tol**3:raise ValueError('CAD member escapes cavity '+mid)
  if not uncovered and not disjoint(shape.BoundBox,port.BoundBox) and shape.common(port).Volume>tol**3:raise ValueError('CAD member obstructs opening '+mid)
 print('VALIDATION CAD containment passed',flush=True)
 end_degrees=defaultdict(int)
 links=defaultdict(set);roots=set();minimum=90.;struts={s['id']:s for s in m['retained_struts']}
 for strut_index,s in enumerate(m['retained_struts']):
  if strut_index%500==0:print('VALIDATING STRUTS',strut_index,'of',len(struts),flush=True)
  a=m['nodes'][s['a']]['point'];b=m['nodes'][s['b']]['point'];angle=math.degrees(math.atan2(abs(b[2]-a[2]),math.hypot(b[0]-a[0],b[1]-a[1])));minimum=min(minimum,angle)
  if angle<c['geometry']['minimum_angle_deg']+.5-1e-6:raise ValueError('Strut angle violation')
  expected=cylinder(a,b,s['radius'])
  if not uncovered and not disjoint(expected.BoundBox,port.BoundBox) and expected.common(port).Volume>tol**3:raise ValueError('Original whole strut intersects port '+s['id'])
  actual=shapes[s['id']]
  if actual.cut(expected).Volume>tol**3:raise ValueError('Member does not match cylinder '+s['id'])
  attached=[nid for nid in [s['a'],s['b']] if nid in shapes and shapes[nid].common(actual).Volume>tol**3]
  for nid in attached:end_degrees[nid]+=1
  if uncovered and not ends_valid(actual,inner,[a,b],[s['a'] in attached,s['b'] in attached],tol):raise ValueError('Dangling interior/side strut '+s['id'])
  if s['kind']!='base' and len(attached)!=2:raise ValueError('Surface strut has unattached end '+s['id'])
  if len(attached)==2:links[attached[0]].add(attached[1]);links[attached[1]].add(attached[0])
  if s['kind'] in ['base','surface_floor_fallback'] and actual.common(inner.Shells[0]).Area>tol**2:roots.update(attached)
 for nid in m['retained_nodes']:
  if uncovered and (end_degrees[nid]==0 or (end_degrees[nid]==1 and shapes[nid].common(inner.Shells[0]).Area<=tol**2)):raise ValueError('Dangling interior node '+nid)
  n=m['nodes'][nid];expected=Part.makeSphere(n['radius'],vec(n['point']))
  if not uncovered and not disjoint(expected.BoundBox,port.BoundBox) and expected.common(port).Volume>tol**3:raise ValueError('Original node intersects port')
  if shapes[nid].cut(expected).Volume>tol**3:raise ValueError('Node does not match sphere')
 print('VALIDATION member geometry and angles passed',flush=True)
 reachable=set(roots);todo=deque(roots)
 while todo:
  for nid in links[todo.popleft()]-reachable:reachable.add(nid);todo.append(nid)
 results={r['target_id']:r for r in m['surface_support_results']};supported=[];excluded=[];target_map={t['id']:t for t in p['targets']}
 if set(results)!=set(target_map):raise ValueError('Missing surface support result')
 for tid,t in target_map.items():
  face=inner.Faces[t['face_index']-1];q,n,_=project(face,vec(t['point']));angle=math.degrees(math.acos(max(-1,min(1,n.z/n.Length))))
  if (q-vec(t['point'])).Length>tol or not angle<ss['angle_threshold_deg']-1e-9:raise ValueError('Ineligible surface target '+tid)
  if not inner.isInside(q-vec([0,0,max(.05,tol*4)]),1e-7,False):raise ValueError('No cavity below target')
  r=results[tid]
  if r['status']=='excluded_by_powder_opening':
   if uncovered:raise ValueError('Uncovered target incorrectly excluded by powder port')
   # Independent physical proximity check permits conservative corner removal.
   distance=port.distToShape(Part.Vertex(q))[0]
   if distance>c['geometry']['top_node_diameter_mm']/2*2+tol:raise ValueError('Unjustified opening exclusion')
   excluded.append(t);continue
  if r['status']!='supported':raise ValueError('Unsupported target')
  nid=r['contact_node']
  if nid not in shapes or nid not in reachable:raise ValueError('Contact not connected to cover')
  if face.common(shapes[nid]).Area<=tol**2:raise ValueError('No finite CAD contact area '+tid)
  for sid in r['struts']:
   if sid not in struts or abs(struts[sid]['radius']-c['geometry']['top_strut_diameter_mm']/2)>1e-9:raise ValueError('Wrong top strut diameter')
  supported.append(t)
 # Re-evaluate CAD samples; every eligible probe must have a local target.
 probes,face_report=probe_faces(inner,c)
 if uncovered:
  safety_cache={}
  def safe_probe(probe):
   key=tuple(round(x,8) for x in probe['point'])
   if key not in safety_cache:safety_cache[key]=side_safe(Part.makeSphere(c['geometry']['top_node_diameter_mm']/2,vec(probe['point'])),inner,tol)
   return safety_cache[key]
  probes=[probe for probe in probes if safe_probe(probe)]
 limit=c['geometry']['top_pitch_mm']/math.sqrt(2)+tol
 for probe in probes:
  if not any(t['face_index']==probe['face_index'] and math.dist(t['point'],probe['point'])<=limit for t in supported+excluded):raise ValueError('Uncovered eligible surface probe')
 print('VALIDATION surface contacts and sampled coverage passed',flush=True)
 from stream_mesh_audit import audit
 audit(work,c,source,inner,p,tol,ss['mesh_deflection_mm']*2+tol)
 report={'status':'PASS','supported_targets':len(supported),'opening_excluded_targets':len(excluded),'eligible_probe_count':len(probes),'surface_faces':face_report,'whole_struts_removed':len(removed),'dangling_struts_removed':len(m.get('removed_dangling_struts',[])),'retained_struts':len(struts),'minimum_strut_angle_deg':minimum,'surface_angle_threshold_deg':ss['angle_threshold_deg'],'cover_thickness_mm':c['cover']['thickness_mm'],'cad_contacts_verified':True,'closed_meshes':True,'opening_clear':None if uncovered else True,'mode':'uncovered' if uncovered else 'covered','side_end_audit_passed':True if uncovered else None,'omitted_side_contact_count':len(p.get('omitted_side_contacts',[])),'output_sha256':sha(c['output_stl']),'limitations':['Finite surface sampling; not a continuous coverage proof.','Intersecting closed shells need slicer union; not a fused solid.','No certification of strength, powder evacuation or support-free manufacture.']}
 (work/'validation.json').write_text(json.dumps(report,indent=2));print('SURFACE_LATTICE_VALIDATION_OK '+json.dumps(report),flush=True)
main()


