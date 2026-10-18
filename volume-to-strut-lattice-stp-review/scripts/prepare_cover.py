"""FreeCADCmd entrypoint; SURFACE_LATTICE_CONFIG is an absolute JSON path."""
import os,sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import Part
from common import load,dot,add,mul,cross,unit,fingerprint,sha
from cad_support import vec,xyz,solid,planes,export_mesh,probe_faces,targets_for_faces

def main():
 c=load(os.environ['SURFACE_LATTICE_CONFIG']);work=Path(c['work_dir']);work.mkdir(parents=True,exist_ok=True)
 if (work/'preparation.json').exists():raise FileExistsError('Use a fresh work directory')
 tol=c['validation']['tolerance_mm'];t=c['cover']['thickness_mm'];source=Part.read(c['input_step']);solid(source,'Source')
 inner=source.copy() if t==0 else source.makeOffsetShape(-t,min(tol/10,1e-4),False,False,0,2);solid(inner,'Lattice boundary')
 if inner.cut(source).Volume>tol**3:raise ValueError('Inward offset escapes source')
 distance=inner.distToShape(source.Shells[0])[0]
 if abs(distance-t)>tol:raise ValueError('Offset minimum wall thickness mismatch: '+str(distance))
 report=[]
 for i,f in enumerate(source.Faces,1):
  report.append({'index':i,'center_mm':xyz(f.CenterOfMass),'surface_type':type(f.Surface).__name__,'normal':xyz(f.normalAt(*[sum(f.ParameterRange[k:k+2])/2 for k in [0,2]])),'area_mm2':f.Area})
 (work/'source_faces.json').write_text(json.dumps(report,indent=2))
 o=c['powder_opening']
 if t==0:
  cover=Part.makeCompound([]);port=Part.makeCompound([])
 else:
  o=c['powder_opening'];fi=o.get('face_index')
  if not isinstance(fi,int) or not 1<=fi<=len(source.Faces):raise ValueError('Choose powder_opening.face_index from source_faces.json')
  face=source.Faces[fi-1]
  if type(face.Surface).__name__!='Plane':raise ValueError('Powder opening still requires a planar vertical side face')
  n=xyz(face.normalAt(0,0));w=[0,0,1]
  if abs(dot(n,w))>1e-7:raise ValueError('Powder opening requires a vertical side face')
  center=o.get('center_mm')
  if not isinstance(center,list) or len(center)!=3 or not all(math.isfinite(x) for x in center):raise ValueError('Provide opening center_mm on selected face')
  h=unit(cross(w,n));hw=o['width_mm']/2;hh=o['height_mm']/2
  corners=[add(center,mul(w,-hh)),add(center,mul(h,hw)),add(center,mul(w,hh)),add(center,mul(h,-hw))]
  diamond=Part.Face(Part.makePolygon([vec(p) for p in corners+[corners[0]]]))
  if diamond.cut(face).Area>tol**2:raise ValueError('Complete diamond must fit selected face')
  depth=t+o['inward_clearance_mm'];start=[add(p,mul(n,2)) for p in corners]
  port=Part.Face(Part.makePolygon([vec(p) for p in start+[start[0]]])).extrude(vec(mul(n,-(depth+2))));solid(port,'Opening')
  raw=source.cut(inner);cover=raw.cut(port).removeSplitter();solid(cover,'Cover')
  if raw.Volume-cover.Volume<=tol**3 or port.common(inner).Volume<=tol**3 or cover.common(port).Volume>tol**3:raise ValueError('Invalid through-opening')
 probes,face_report=probe_faces(inner,c);targets=targets_for_faces(inner,c,probes)
 if not targets and t>0:raise ValueError('No eligible roof or ledge below threshold')
 for name,s in [('source',source),('inner',inner),('cover',cover),('opening',port)]:s.exportBrep(str(work/(name+'.brep')))
 # Supplement contacts from the canonical exported CAD as well. CAD reload can
 # change planar triangulation diagonals and hence the adaptive probe locations.
 from cad_support import read_shape
 canonical=read_shape(work/'inner.brep');audit_probes,_=probe_faces(canonical,c)
 limit=c['geometry']['top_pitch_mm']/math.sqrt(2)
 for probe in audit_probes:
  if not any(t['face_index']==probe['face_index'] and math.dist(t['point'],probe['point'])<=limit for t in targets):
   targets.append({**probe,'id':f'target{len(targets)}'})
 print('SURFACE_PROBES original='+str(len(probes))+' canonical='+str(len(audit_probes)),flush=True)
 probes.extend(audit_probes)
 omitted=[]
 if t==0:
  from boundary_rules import side_safe
  safety_cache={}
  def safe_target(target):
   key=tuple(round(x,8) for x in target['point'])
   if key not in safety_cache:safety_cache[key]=side_safe(Part.makeSphere(c['geometry']['top_node_diameter_mm']/2,vec(target['point'])),canonical,tol)
   if len(safety_cache)%1000==0:print('BOUNDARY_PROBES',len(safety_cache),flush=True)
   return safety_cache[key]
  omitted=[target for target in targets if not safe_target(target)]
  targets=[target for target in targets if safe_target(target)]
  probes=[probe for probe in probes if safe_target(probe)]
  for i,probe in enumerate(probes):
   if not any(target['face_index']==probe['face_index'] and math.dist(target['point'],probe['point'])<=limit for target in targets):targets.append({**probe,'id':f'uncovered_probe{i}'})
 cornersbb=[vec([x,y,z]) for x in [inner.BoundBox.XMin,inner.BoundBox.XMax] for y in [inner.BoundBox.YMin,inner.BoundBox.YMax] for z in [inner.BoundBox.ZMin,inner.BoundBox.ZMax]]
 coords=[[dot(xyz(p),axis) for axis in c['_frame']] for p in cornersbb]
 prep={'config_hash':fingerprint(c),'source_hash':sha(c['input_step']),'mode':'uncovered' if t==0 else 'covered','omitted_side_contacts':omitted,'opening_planes':planes(port),'local_bounds':[[min(p[i] for p in coords) for i in range(3)],[max(p[i] for p in coords) for i in range(3)]],'targets':targets,'probes':probes,'surface_faces':face_report,'minimum_wall_distance_mm':distance,'opening_roof_angle_deg':math.degrees(math.atan2(o['height_mm'],o['width_mm'])) if t>0 else None,'brep_hashes':{k:sha(work/(k+'.brep')) for k in ['source','inner','cover','opening']}}
 (work/'preparation.json').write_text(json.dumps(prep,indent=2));print('SURFACE_COVER_PREPARED targets='+str(len(targets)),flush=True)
main()
