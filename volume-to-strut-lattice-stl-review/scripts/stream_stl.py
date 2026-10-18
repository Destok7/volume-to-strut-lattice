"""Write member meshes in bounded batches, preserving facet orientation."""
import struct,shutil
from pathlib import Path

FACET=struct.Struct('<12fH')

class Writer:
 def __init__(self,path):
  self.path=Path(path);self.file=self.path.open('wb');self.count=0
  self.file.write(b'CAD lattice: dimensions in mm'.ljust(80,b'\0')+struct.pack('<I',0))
 def add(self,mesh):
  block=bytearray()
  for facet in mesh.Facets:
   normal=facet.Normal;values=[normal.x,normal.y,normal.z]
   for p in facet.Points:values.extend(p)
   block.extend(FACET.pack(*values,0));self.count+=1
   if len(block)>=1024*1024:self.file.write(block);block.clear()
  self.file.write(block)
 def close(self):
  if self.count>=2**32:raise ValueError('STL facet-count limit exceeded')
  self.file.seek(80);self.file.write(struct.pack('<I',self.count));self.file.close()
 def __enter__(self):return self
 def __exit__(self,exc_type,exc,tb):
  self.close()

def combine(paths,output):
 paths=[Path(p) for p in paths];total=0
 for path in paths:
  with path.open('rb') as f:
   f.seek(80);count=struct.unpack('<I',f.read(4))[0]
  if path.stat().st_size!=84+50*count:raise ValueError('Invalid component STL '+str(path))
  total+=count
 if total>=2**32:raise ValueError('STL facet-count limit exceeded')
 with Path(output).open('wb') as out:
  out.write(b'CAD cover and lattice: dimensions in mm'.ljust(80,b'\0')+struct.pack('<I',total))
  for path in paths:
   with path.open('rb') as f:f.seek(84);shutil.copyfileobj(f,out,1024*1024)
