"""Uncovered boundary rules; exact planar checks, sampled curved normals."""
import Part, MeshPart, math
from cad_support import vec

def side_safe(shape, boundary, tol):
 """Reject material cut by a vertical side; only local roofs/floors may cut it.

 For curved cut patches check CAD normals at tessellation seeds and edges.
 This finite classifier is conservative near a vertical tangent (1e-6 guard).
 """
 if shape.isNull() or not shape.Solids:return False
 for face in boundary.Faces:
  planar=type(face.Surface).__name__=='Plane'
  if planar and abs(face.normalAt(0,0).z)>1e-6:continue
  a=shape.BoundBox;b=face.BoundBox
  if a.XMax<b.XMin-tol or b.XMax<a.XMin-tol or a.YMax<b.YMin-tol or b.YMax<a.YMin-tol or a.ZMax<b.ZMin-tol or b.ZMax<a.ZMin-tol:continue
  # Analytic spheres and horizontal-axis cylinders have n.z=0 only at
  # their equatorial plane. Strict bounding-box separation proves that a
  # patch cannot contain a vertical tangent, avoiding needless meshing.
  surface=face.Surface;kind=type(surface).__name__
  equator=surface.Center.z if kind=='Sphere' or (kind=='Cylinder' and abs(surface.Axis.z)<1e-9) else None
  if equator is not None and (a.ZMin>equator+tol or a.ZMax<equator-tol):continue
  patch=shape.common(face)
  if patch.Area<=tol**2:continue
  if equator is not None and (patch.BoundBox.ZMin>equator+tol or patch.BoundBox.ZMax<equator-tol):continue
  if planar:
   if abs(face.normalAt(0,0).z)<=1e-6:return False
   continue
  points=[v.Point for v in patch.Vertexes]
  for edge in patch.Edges:
   if edge.Length>tol:points.extend(edge.discretize(Number=9))
  for f in patch.Faces:
   mesh=MeshPart.meshFromShape(Shape=f,LinearDeflection=min(.05,tol*2),AngularDeflection=.1,Relative=False)
   facets=mesh.Facets
   for facet in facets[::max(1,math.ceil(len(facets)/128))]:
    points.append(sum((vec(p) for p in facet.Points),vec([0,0,0]))/3)
  if not points:return False
  for point in points:
   u,v=face.Surface.parameter(point)
   if abs(face.normalAt(u,v).z)<=1e-6:return False
 return True

def ends_valid(shape,boundary,points,attached,tol):
 """Missing nodes are permitted only when clipping removes a terminal end.

 Checking the raw cap independently prevents missing interior nodes from being
 interpreted as acceptable boundary terminations. Side safety is checked too.
 """
 if not side_safe(shape,boundary,tol):return False
 for point,connected in zip(points,attached):
  if connected:continue
  q=vec(point)
  if boundary.isInside(q,1e-7,True):return False
  if shape.common(boundary.Shells[0]).Area<=tol**2:return False
 return True

def prune_interior_leaves(struts,node_shapes,boundary,tol):
 """Recursively omit branches ending at an interior node, even with a sphere."""
 from collections import Counter
 kept=list(struts);removed=[];terminal={}
 while True:
  degree=Counter(n for s in kept for n in [s['a'],s['b']] if node_shapes.get(n) is not None)
  bad=set()
  for n,count in degree.items():
   if count!=1:continue
   if n not in terminal:terminal[n]=node_shapes[n].common(boundary.Shells[0]).Area>tol**2
   if not terminal[n]:bad.add(n)
  if not bad:return kept,removed
  following=[]
  for s in kept:
   (removed if s['a'] in bad or s['b'] in bad else following).append(s)
  kept=following
