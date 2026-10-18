"""Memory-bounded equivalent of edge balance and rounded facet composition checks."""
import struct,heapq,tempfile,math
from pathlib import Path
from collections import Counter
import Part
from cad_support import vec,xyz
from mesh_checks import triangle_hits

def records(path,fmt):
 size=fmt.size
 with open(path,'rb') as f:
  while True:
   b=f.read(size)
   if not b:break
   yield fmt.unpack(b)

def merged(paths,fmt):
 last=None;total=0
 for record in heapq.merge(*(records(p,fmt) for p in paths)):
  key=record[:-1]
  if last is not None and key!=last:
   yield last,total
   total=0
  last=key;total+=record[-1]
 if last is not None:yield last,total

def planes(shape):
 out=[]
 for f in shape.Faces:
  if type(f.Surface).__name__!='Plane':return []
  u0,u1,v0,v1=f.ParameterRange;n=f.normalAt((u0+u1)/2,(v0+v1)/2);p=f.CenterOfMass
  d=n.dot(p)
  if any(n.dot(v.Point)-d>1e-7 for v in shape.Vertexes):return []
  out.append((xyz(n),d))
 return out

def audit(work,c,source,inner,prep,tol,mesh_tol):
 ef=struct.Struct('<7q');tf=struct.Struct('<10q');facet=struct.Struct('<12fH')
 tri_paths={};scratch=Path(tempfile.mkdtemp(prefix='mesh_audit_',dir=str(work)))
 for name,path,boundary in [('cover',work/'cover.stl',source),('lattice',work/'lattice.stl',inner),('combined',Path(c['output_stl']),None)]:
  edges=Counter();tris=Counter();edge_paths=[];tri_paths[name]=[];checked=set();ps=planes(boundary) if boundary is not None else []
  def flush():
   i=len(edge_paths);ep=scratch/(name+str(i)+'.edges');tp=scratch/(name+str(i)+'.triangles')
   with ep.open('wb') as f:
    for k,v in sorted(edges.items()):
     if v:f.write(ef.pack(*k,v))
   with tp.open('wb') as f:
    for k,v in sorted(tris.items()):f.write(tf.pack(*k,v))
   edge_paths.append(ep);tri_paths[name].append(tp);edges.clear();tris.clear();checked.clear()
  with path.open('rb') as f:
   f.read(80);count=struct.unpack('<I',f.read(4))[0]
   if (not count and not (name=='cover' and c['cover']['thickness_mm']==0)) or path.stat().st_size!=84+50*count:raise ValueError('Invalid binary STL '+name)
   for i in range(count):
    values=facet.unpack(f.read(50));points=[values[j:j+3] for j in (3,6,9)]
    if not all(math.isfinite(x) for p in points for x in p):raise ValueError('Nonfinite mesh coordinate')
    keys=[tuple(int(round(round(x,5)*100000)) for x in p) for p in points]
    tris[sum(sorted(keys),())]+=1
    for a,b in zip(keys,keys[1:]+keys[:1]):
     if a!=b:edges[min(a,b)+max(a,b)]+=1 if a<b else -1
    # Combined geometry is checked by exact rounded facet composition below.
    if boundary is not None:
     for point in points:
      key=tuple(round(x,6) for x in point)
      if key in checked:continue
      checked.add(key)
      if ps and all(sum(n[j]*point[j] for j in range(3))<=d-1e-7 for n,d in ps):continue
      q=vec(point)
      if not boundary.isInside(q,1e-7,True) and boundary.distToShape(Part.Vertex(q))[0]>mesh_tol:raise ValueError('Mesh escapes boundary '+name)
     if prep['opening_planes'] and not any(all(sum(n[j]*point[j] for j in range(3))>d-tol for point in points) for n,d in prep['opening_planes']):
      if triangle_hits(points,prep['opening_planes'],tol):raise ValueError('Mesh obstructs opening '+name)
    if (i+1)%50000==0:flush()
    if (i+1)%500000==0:print('VALIDATION mesh facets',name,i+1,'of',count,flush=True)
   if tris:flush()
  if any(balance for _,balance in merged(edge_paths,ef)):raise ValueError('Unbalanced mesh '+name)
  for ep in edge_paths:ep.unlink()
  print('VALIDATION mesh passed '+name,flush=True)
 expected=merged(tri_paths['cover']+tri_paths['lattice'],tf);actual=merged(tri_paths['combined'],tf)
 from itertools import zip_longest
 if any(a!=b for a,b in zip_longest(expected,actual)):raise ValueError('Combined STL differs from components')
 for paths in tri_paths.values():
  for path in paths:path.unlink()
 scratch.rmdir()
