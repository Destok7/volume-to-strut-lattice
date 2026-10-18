import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as App,Part
from boundary_rules import side_safe,ends_valid
from cad_support import cylinder
box=Part.makeBox(24,24,32)
bottom=cylinder([6,6,-5],[12,12,10],1).common(box)
top=cylinder([12,12,23],[18,18,38],1).common(box)
side=cylinder([-5,12,3],[6,12,23],1).common(box)
inside=cylinder([6,6,6],[12,12,24],1)
assert side_safe(bottom,box,.01) and side_safe(top,box,.01)
assert not side_safe(side,box,.01)
for point in [[12,12,32],[0,12,32],[12,12,0],[.5,12,12]]:
 sphere=Part.makeSphere(1,App.Vector(*point))
 assert side_safe(sphere,box,.01)==side_safe(sphere.common(box),box,.01)
assert ends_valid(bottom,box,[[6,6,-5],[12,12,10]],[False,True],.01)
assert ends_valid(top,box,[[12,12,23],[18,18,38]],[True,False],.01)
assert not ends_valid(inside,box,[[6,6,6],[12,12,24]],[False,True],.01)
poly=[App.Vector(x,0,z) for x,z in [(0,0),(24,0),(24,32),(0,24)]]
slope=Part.Face(Part.makePolygon(poly+[poly[0]])).extrude(App.Vector(0,24,0))
member=cylinder([6,12,10],[6,12,40],1).common(slope)
assert side_safe(member,slope,.01)
assert ends_valid(member,slope,[[6,12,10],[6,12,40]],[True,False],.01)
barrel=Part.makeCylinder(12,24,App.Vector(12,0,24),App.Vector(0,1,0)).common(Part.makeBox(24,24,24,App.Vector(0,0,24)))
curve=Part.makeBox(24,24,24).fuse(barrel).removeSplitter()
member=cylinder([12,12,10],[12,12,40],1).common(curve)
assert side_safe(member,curve,.01)
assert ends_valid(member,curve,[[12,12,10],[12,12,40]],[True,False],.01)
from boundary_rules import prune_interior_leaves
points={'a':[12,12,0],'b':[12,12,12],'c':[12,12,24],'d':[12,12,32],'e':[18,12,18],'f':[20,12,20]}
shapes={n:Part.makeSphere(1,App.Vector(*p)).common(box) for n,p in points.items()}
edges=[{'id':str(i),'a':a,'b':b} for i,(a,b) in enumerate([('a','b'),('b','c'),('c','d'),('b','e'),('e','f')])]
kept,removed=prune_interior_leaves(edges,shapes,box,.01)
assert {s['id'] for s in kept}=={'0','1','2'} and len(removed)==2
print('UNCOVERED_BOUNDARY_TESTS_PASS',flush=True)
