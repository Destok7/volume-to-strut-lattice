"""STEP compound export with member-wise CAD round-trip verification."""
import math,time
from pathlib import Path
from collections import defaultdict
from itertools import product
import Part,MeshPart
from common import sha

def primitive_description(shape):
 """Recognize complete positive spheres/cylinders; never trimmed substitutes."""
 if shape.Orientation!='Forward' or len(shape.Shells)!=1:return None
 faces=shape.Faces
 if len(faces)==1 and type(faces[0].Surface).__name__=='Sphere':
  f=faces[0];surface=f.Surface;r=surface.Radius
  if f.Orientation!='Forward' or abs(f.Area-4*math.pi*r*r)>1e-6:return None
  return ('sphere',r,[surface.Center])
 if len(faces)!=3:return None
 cylindrical=[f for f in faces if type(f.Surface).__name__=='Cylinder']
 caps=[f for f in faces if type(f.Surface).__name__=='Plane']
 if len(cylindrical)!=1 or len(caps)!=2 or cylindrical[0].Orientation!='Forward':return None
 surface=cylindrical[0].Surface;r=surface.Radius;centres=[]
 for cap in caps:
  if len(cap.Wires)!=1 or len(cap.Edges)!=1:return None
  edge=cap.Edges[0];curve=edge.Curve
  if type(curve).__name__!='Circle' or abs(curve.Radius-r)>1e-7 or abs(edge.Length-2*math.pi*r)>1e-6:return None
  if abs(cap.Area-math.pi*r*r)>1e-6:return None
  if abs(abs(curve.Axis.dot(surface.Axis))-1)>1e-9:return None
  if (curve.Center-surface.Center).cross(surface.Axis).Length>1e-7:return None
  centres.append(curve.Center)
 length=(centres[0]-centres[1]).Length
 if length<1e-7 or abs(cylindrical[0].Area-2*math.pi*r*length)>1e-6:return None
 return ('cylinder',r,centres)

def primitive_equal(a,b):
 if a is None or b is None or a[0]!=b[0] or abs(a[1]-b[1])>1e-7:return False
 return any(all((x-y).Length<=1e-7 for x,y in zip(a[2],candidate)) for candidate in [b[2],list(reversed(b[2]))])

def sampled_surface_match(a,b,tol):
 """Independent fallback for failed Boolean comparisons of coincident surfaces.

 This is explicitly a finite surface audit, not a continuum distance proof.
 Never use it to repair or modify either shape.
 """
 if sorted(type(f.Surface).__name__ for f in a.Faces)!=sorted(type(f.Surface).__name__ for f in b.Faces):return None
 if abs(a.Area-b.Area)>tol*max(a.Area,b.Area):return None
 maximum=0.;count=0
 for first,second in [(a,b),(b,a)]:
  seen=set()
  for face in first.Faces:
   mesh=MeshPart.meshFromShape(Shape=face,LinearDeflection=tol*2,AngularDeflection=.5,Relative=False)
   facets=mesh.Facets;points=[v.Point for v in face.Vertexes]
   for edge in face.Edges:
    if edge.Length>1e-7:points.extend(edge.discretize(Number=17))
   # Bound audit cost; the report explicitly identifies finite sampling.
   for facet in facets[::max(1,math.ceil(len(facets)/128))]:
    points.extend(facet.Points)
    p=sum((__import__('FreeCAD').Vector(*v) for v in facet.Points),__import__('FreeCAD').Vector())/3
    _,pairs,_=face.distToShape(Part.Vertex(p));points.append(pairs[0][0])
   for point in points:
    key=tuple(round(x,8) for x in point)
    if key in seen:continue
    seen.add(key);d=second.distToShape(Part.Vertex(point))[0];maximum=max(maximum,d);count+=1
    if d>tol:return None
 return {'sampled_max_surface_distance_mm':maximum,'sample_count':count}

def export_and_check(cover,lattice,path,tol,verify_existing=False):
 path=Path(path)
 if path.exists() and not verify_existing:raise FileExistsError('Output already exists: '+str(path))
 if verify_existing and not path.is_file():raise FileNotFoundError(path)
 path.parent.mkdir(parents=True,exist_ok=True)
 expected=list(cover.Solids)+list(lattice.Solids)
 if not expected:raise ValueError('No CAD solids to export')
 t=time.perf_counter()
 if not verify_existing:Part.makeCompound(expected).exportStep(str(path))
 export_seconds=time.perf_counter()-t
 print('STEP_WRITTEN solids='+str(len(expected)),flush=True)
 t=time.perf_counter();loaded=Part.read(str(path));actual=loaded.Solids;read_seconds=time.perf_counter()-t
 if len(actual)!=len(expected):raise ValueError('STEP changed member count')
 print('STEP_REOPENED solids='+str(len(actual)),flush=True)
 cell=max(1.,tol*2)
 def key(s):
  b=s.BoundBox;return tuple(math.floor(x/cell) for x in [(b.XMin+b.XMax)/2,(b.YMin+b.YMax)/2,(b.ZMin+b.ZMax)/2])
 def box(s):
  b=s.BoundBox;return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
 buckets=defaultdict(list)
 for i,s in enumerate(expected):buckets[key(s)].append(i)
 used=set();max_difference=0.;max_volume_delta=0.;fallbacks=[];primitive_matches=0;descriptions={};t=time.perf_counter()
 for index,s in enumerate(actual):
  if s.isNull() or not s.isValid() or s.Volume<=tol**3:raise ValueError('Invalid STEP solid '+str(index))
  k=key(s);sb=box(s);match=None
  description=primitive_description(s)
  for offset in product([-1,0,1],repeat=3):
   for candidate in buckets.get(tuple(a+b for a,b in zip(k,offset)),[]):
    if candidate in used:continue
    ref=expected[candidate]
    if candidate not in descriptions:descriptions[candidate]=primitive_description(ref)
    if primitive_equal(description,descriptions[candidate]):
     match=candidate;primitive_matches+=1;break
    # Trimmed-surface mass properties and conservative BREP bounding boxes can
    # vary on reload. Neither is an exact geometry-equality criterion.
    # Preserve each member rather than verifying only the union or total volume.
    difference=max(s.cut(ref).Volume,ref.cut(s).Volume)
    fallback=None
    if difference>tol**3:fallback=sampled_surface_match(s,ref,tol)
    if difference<=tol**3 or fallback is not None:
     match=candidate
     if fallback is None:max_difference=max(max_difference,difference)
     else:
      fallbacks.append({'step_member_index':index,'source_member_index':candidate,'failed_boolean_difference_volume_mm3':difference,**fallback})
      print('STEP_COINCIDENT_SURFACE_AUDIT',index,'points',fallback['sample_count'],flush=True)
     max_volume_delta=max(max_volume_delta,abs(s.Volume-ref.Volume));break
   if match is not None:break
  if match is None:raise ValueError('STEP member differs from original CAD '+str(index))
  used.add(match)
  if (index+1)%500==0:print('STEP_VERIFIED',index+1,'of',len(actual),flush=True)
 if len(used)!=len(expected):raise ValueError('STEP lost a CAD member')
 return {'step_roundtrip':'PASS','solid_count':len(actual),'cover_solids':len(cover.Solids),'lattice_solids':len(lattice.Solids),'analytic_primitive_matches':primitive_matches,'max_successful_boolean_difference_volume_mm3':max_difference,'max_volume_integration_delta_mm3':max_volume_delta,'coincident_surface_fallback_count':len(fallbacks),'coincident_surface_fallbacks':fallbacks,'roundtrip_limitations':['Fallback surface comparisons use finite tessellation-seeded CAD samples, not a continuum distance proof.'],'output_sha256':sha(path),'output_bytes':path.stat().st_size,'timings_seconds':{'write_step':export_seconds,'read_step':read_seconds,'compare_members':time.perf_counter()-t},'fused':False}
