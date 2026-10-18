"""FreeCAD helpers for exact offsets, surface probes and clipped members."""
import math
import FreeCAD as App
import Part, Mesh, MeshPart
from common import eligible_surface, surface_angle, dot

def vec(p):return App.Vector(*p)
def xyz(p):return [p.x,p.y,p.z]
def solid(s,label):
 if s.isNull() or not s.isValid() or len(s.Solids)!=1:raise ValueError(label+' must be one valid solid')
def read_shape(path):
 s=Part.Shape();s.read(str(path));return s
def facets(s,deflection):
 mesh=MeshPart.meshFromShape(Shape=s,LinearDeflection=deflection,AngularDeflection=.5,Relative=False)
 return [tuple(vec(list(p)) for p in f.Points) for f in mesh.Facets]
def export_mesh(s,path,deflection):Mesh.Mesh(facets(s,deflection)).write(str(path))
def cylinder(a,b,r):
 d=vec(b)-vec(a)
 return Part.makeCylinder(r,d.Length,vec(a),d)
def planes(s):
 result=[]
 for f in s.Faces:
  if type(f.Surface).__name__!='Plane':raise ValueError('Expected planar opening')
  n=xyz(f.normalAt(0,0));result.append([n,dot(n,xyz(f.CenterOfMass))])
 return result
def project(face,p):
 _,pairs,_=face.distToShape(Part.Vertex(p));q=pairs[0][0]
 uv=face.Surface.parameter(q);n=face.normalAt(*uv)
 return q,n,uv
def vertical_hits(face,x,y,zlow,zhigh):
 line=Part.makeLine(vec([x,y,zlow]),vec([x,y,zhigh]));hit=face.section(line)
 return [v.Point for v in hit.Vertexes]
def floor_below(inner,p,tol):
 hits=[]
 for face in inner.Faces:
  for q in vertical_hits(face,p[0],p[1],inner.BoundBox.ZMin-1,p[2]-tol*4):
   if q.z<p[2]-tol*3:hits.append(q.z)
 if not hits:raise ValueError('No cavity floor below support target')
 z=max(hits)
 if not inner.isInside(vec([p[0],p[1],(z+p[2])/2]),1e-7,True):raise ValueError('Support ray is not inside cavity')
 return [p[0],p[1],z]

def probe_faces(inner,c):
 """CAD normals at adaptive face samples, not a continuum coverage proof."""
 step=c['geometry']['top_pitch_mm']/2;ss=c['surface_support'];tol=c['validation']['tolerance_mm'];probes=[];reports=[]
 for fi,face in enumerate(inner.Faces,1):
  vertices,triangles=face.tessellate(ss['sampling_deflection_mm']);seen=set();rows=[]
  for ids in triangles:
   a,b,d=[vertices[k] for k in ids];n=max(1,math.ceil(max((a-b).Length,(b-d).Length,(d-a).Length)/step))
   if n>1000:raise ValueError('Surface sampling budget exceeded')
   for i in range(n):
    for j in range(n-i):
     u=(i+1/3)/n;v=(j+1/3)/n
     if u+v>=1:continue
     q,normal,uv=project(face,a+(b-a)*u+(d-a)*v)
     key=tuple(round(x,5) for x in xyz(q))
     if key in seen:continue
     seen.add(key)
     if eligible_surface(xyz(normal),ss['angle_threshold_deg']):
      below=q-App.Vector(0,0,max(tol*4,.05))
      if inner.isInside(below,1e-7,False):rows.append({'face_index':fi,'point':xyz(q),'normal':xyz(normal),'uv':list(uv),'angle_deg':surface_angle(xyz(normal))})
   if len(probes)+len(rows)>200000:raise ValueError('Surface sampling budget exceeded')
  reports.append({'face_index':fi,'surface_type':type(face.Surface).__name__,'eligible_probes':len(rows)})
  probes.extend(rows)
 return probes,reports

def targets_for_faces(inner,c,probes):
 pitch=c['geometry']['top_pitch_mm'];threshold=c['surface_support']['angle_threshold_deg'];targets=[]
 for fi in sorted({p['face_index'] for p in probes}):
  face=inner.Faces[fi-1];box=face.BoundBox;group=[]
  for ix in range(math.ceil(box.XMin/pitch),math.floor(box.XMax/pitch)+1):
   for iy in range(math.ceil(box.YMin/pitch),math.floor(box.YMax/pitch)+1):
    for q in vertical_hits(face,ix*pitch,iy*pitch,box.ZMin-1,box.ZMax+1):
     q,n,uv=project(face,q)
     if eligible_surface(xyz(n),threshold) and inner.isInside(q-App.Vector(0,0,.05),1e-7,False):
      group.append({'face_index':fi,'point':xyz(q),'normal':xyz(n),'uv':list(uv),'angle_deg':surface_angle(xyz(n))})
  limit=pitch/math.sqrt(2)
  for p in (p for p in probes if p['face_index']==fi):
   if not any(math.dist(p['point'],q['point'])<=limit for q in group):group.append(dict(p))
  targets.extend(group)
 for i,t in enumerate(targets):t['id']=f'target{i}'
 if len(targets)>c['surface_support']['max_members']//3:raise ValueError('Surface support budget exceeded')
 return targets
