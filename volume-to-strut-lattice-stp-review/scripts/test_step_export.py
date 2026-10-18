"""FreeCAD regression: primitive recognition, STEP round trip and corruption."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import Part,FreeCAD as App
from step_export import export_and_check,primitive_description,primitive_equal

def main():
 for direction in [(0,0,1),(1,0,1),(1,1,2),(-2,3,4)]:
  a=Part.makeCylinder(1.2,11.1,App.Vector(10,20,30),App.Vector(*direction));b=a.copy()
  assert primitive_description(a) is not None and primitive_equal(primitive_description(a),primitive_description(b))
  b.translate(App.Vector(.2,0,0));assert not primitive_equal(primitive_description(a),primitive_description(b))
 sphere=Part.makeSphere(2.5,App.Vector(3,4,5));assert primitive_description(sphere) is not None
 assert not primitive_equal(primitive_description(sphere),primitive_description(Part.makeSphere(2.6,App.Vector(3,4,5))))
 assert primitive_description(sphere.common(Part.makeBox(20,20,5))) is None
 cover=Part.makeBox(10,10,1);lattice=Part.makeSphere(1,App.Vector(3,3,4));original_read=Part.read
 with tempfile.TemporaryDirectory(prefix='step_lattice_test_') as folder:
  root=Path(folder);result=export_and_check(cover,lattice,root/'good.step',.01)
  assert result['step_roundtrip']=='PASS' and result['solid_count']==2
  def modified(path):
   solids=original_read(path).Solids;solids[1].translate(App.Vector(.2,0,0));return Part.makeCompound(solids)
  for name,reader in [('shifted',modified),('duplicated',lambda path:Part.makeCompound([cover,cover]))]:
   Part.read=reader
   try:
    try:export_and_check(cover,lattice,root/(name+'.step'),.01)
    except ValueError:pass
    else:raise AssertionError('Modified STEP accepted: '+name)
   finally:Part.read=original_read
 print('STEP_EXPORT_TESTS_PASS',flush=True)
main()
