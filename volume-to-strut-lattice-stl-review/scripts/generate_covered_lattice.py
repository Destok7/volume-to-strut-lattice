"""Blender assembly after FreeCAD prepare_cover.py and generate_members.py."""
import json,sys,shutil,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from common import load,sha,fingerprint
def import_exact_stl(path,name):
 data=Path(path).read_bytes();count=struct.unpack_from('<I',data,80)[0]
 if len(data)!=84+50*count:raise ValueError('Expected binary STL from FreeCAD')
 vertices=[];faces=[];index={}
 for values in struct.iter_unpack('<12fH',data[84:]):
  face=[]
  for start in [3,6,9]:
   point=tuple(values[start:start+3])
   if point not in index:index[point]=len(vertices);vertices.append(point)
   face.append(index[point])
  faces.append(tuple(face))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update();obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
 return obj
def main():
 c=load(sys.argv[sys.argv.index('--')+1]);work=Path(c['work_dir']);p=json.loads((work/'preparation.json').read_text());m=json.loads((work/'members.json').read_text())
 if p['config_hash']!=fingerprint(c) or m['config_hash']!=fingerprint(c) or sha(work/'cover.stl')!=p['cover_stl_hash'] or sha(work/'lattice.stl')!=m['lattice_hash']:raise ValueError('Stale or altered inputs')
 for path in [c['output_stl'],c['output_blend']]:
  if Path(path).exists():raise FileExistsError('Use fresh output paths: '+path)
  Path(path).parent.mkdir(parents=True,exist_ok=True)
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 for name in (['cover','lattice'] if c['cover']['thickness_mm']>0 else ['lattice']):
  obj=import_exact_stl(work/(name+'.stl'),name.title())
 bpy.ops.object.select_all(action='SELECT');bpy.context.view_layer.objects.active=obj
 obj['skill']='volume-to-strut-lattice-stl-review';obj['angle_threshold_deg']=c['surface_support']['angle_threshold_deg'];obj['mesh_note']='Intersecting closed shells; slicer union required'
 if sha(work/'combined.stl')!=m['combined_hash']:raise ValueError('Combined STL changed')
 bpy.ops.wm.save_as_mainfile(filepath=c['output_blend']);shutil.copyfile(work/'combined.stl',c['output_stl'])
 m.update(output_hash=sha(c['output_stl']),blend_hash=sha(c['output_blend']));(work/'members.json').write_text(json.dumps(m,indent=2))
 print('SURFACE_LATTICE_ASSEMBLED',flush=True)
if __name__=='__main__':main()

