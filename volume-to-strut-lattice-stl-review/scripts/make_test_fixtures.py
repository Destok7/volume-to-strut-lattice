import FreeCAD as App,Part,json,math,os
from pathlib import Path
root=Path(os.environ['SURFACE_LATTICE_TEST_DIR']).resolve();root.mkdir(parents=True,exist_ok=True)
# 30-degree roof and a lower horizontal ledge on the same concave part.
def prism(poly,depth=24):
 pts=[App.Vector(x,0,z) for x,z in poly]
 return Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(App.Vector(0,depth,0))
sloped=prism([(0,0),(40,0),(40,48),(24,48-16/math.sqrt(3)),(24,30),(0,30)])
# Cylindrical roof: local inclinations span 0 to >45 degrees.
barrel=Part.makeCylinder(20,24,App.Vector(20,0,28),App.Vector(0,1,0)).common(Part.makeBox(40,24,60,App.Vector(0,0,28)))
curved=Part.makeBox(40,24,28).fuse(barrel).removeSplitter()
for name,shape in [('sloped',sloped),('curved',curved)]:
 assert shape.isValid() and len(shape.Solids)==1
 path=root/(name+'.step');shape.exportStep(str(path));reread=Part.read(str(path))
 fi=next(i+1 for i,f in enumerate(reread.Faces) if type(f.Surface).__name__=='Plane' and f.normalAt(0,0).y<-.999)
 config={'input_step':str(path),'work_dir':str(root/(name+'_run1')),'output_stl':str(root/(name+'.stl')),'output_blend':str(root/(name+'.blend')),'powder_opening':{'face_index':fi,'center_mm':[12,0,12]}}
 (root/(name+'.json')).write_text(json.dumps(config,indent=2))
 print(name,fi,flush=True)
