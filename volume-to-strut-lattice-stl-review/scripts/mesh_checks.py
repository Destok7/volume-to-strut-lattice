"""Independent FreeCAD validation of CAD cover, member clearance and exports."""
import os,sys,json,math
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as App,Part,Mesh
from common import load,fingerprint,sha,dot,sub
def vec(p):return App.Vector(*p)
def read_shape(path):
 s=Part.Shape();s.read(str(path));return s
def disjoint(a,b):return a.XMax<b.XMin or b.XMax<a.XMin or a.YMax<b.YMin or b.YMax<a.YMin or a.ZMax<b.ZMin or b.ZMax<a.ZMin
def triangles(mesh):
 return Counter(tuple(sorted(tuple(round(float(x),5) for x in p) for p in f.Points)) for f in mesh.Facets)
def closed_shell_edges(mesh):
 # A combined export can have coincident edges from distinct closed members.
 # Require balanced directed edges, not a misleading manifold-solid claim.
 balance=Counter()
 for f in mesh.Facets:
  p=[tuple(round(float(x),5) for x in v) for v in f.Points]
  for a,b in zip(p,p[1:]+p[:1]):
   if a!=b:balance[tuple(sorted((a,b)))]+=1 if a<b else -1
 return sum(v!=0 for v in balance.values())
def triangle_hits(points,planes,tol):
 # Clip the actual exported triangle to the interior of the opening.
 p=[list(x) for x in points]
 for n,d in planes:
  if not p:return False
  q=[]
  for a,b in zip(p,p[1:]+p[:1]):
   da=dot(n,a)-d+tol;db=dot(n,b)-d+tol
   if da<=0:q.append(a)
   if (da<=0)!=(db<=0):
    f=da/(da-db);q.append([x+f*(y-x) for x,y in zip(a,b)])
  p=q
 if len(p)<3:return False
 a=p[0];area=0
 for i in range(1,len(p)-1):
  u=sub(p[i],a);v=sub(p[i+1],a);cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];area+=math.sqrt(dot(cross,cross))/2
 return area>tol**2
