"""Pure Python regression checks; integration fixtures are run in FreeCAD."""
import unittest,tempfile,json,math
from pathlib import Path
from common import load,eligible_surface,lower_plan,intersects
class Rules(unittest.TestCase):
 def config(self,**changes):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'c.json';p.write_text(json.dumps({'input_step':'source.step','work_dir':'work','output_step':'part.step',**changes}));return load(p)
 def test_defaults(self):
  c=self.config();self.assertEqual(c['surface_support']['angle_threshold_deg'],45);self.assertEqual(c['cover']['thickness_mm'],2)
 def test_uncovered(self):
  c=self.config(cover={'thickness_mm':0},powder_opening={'width_mm':0,'height_mm':0})
  self.assertEqual(c['cover']['thickness_mm'],0)
  self.assertFalse(intersects([0,0,0],[1,1,1],1,[]))
 def test_strict_threshold(self):
  for angle,expected in [(0,True),(30,True),(44.99,True),(45,False),(45.01,False),(90,False),(180,False)]:
   n=[math.sin(math.radians(angle)),0,math.cos(math.radians(angle))]
   self.assertEqual(eligible_surface(n),expected,angle)
 def test_curved_normal_changes(self):
  selected=[angle for angle in range(-90,91,5) if eligible_surface([math.sin(math.radians(angle)),0,math.cos(math.radians(angle))])]
  self.assertEqual(selected,list(range(-40,41,5)))
 def test_bottom_excluded(self):self.assertFalse(eligible_surface([0,0,-1]))
 def test_world_xy_required(self):
  with self.assertRaises(ValueError):self.config(build_frame={'normal':[0,1,0]})
 def test_invalid_parameters(self):
  for update in [{'surface_support':{'angle_threshold_deg':90}},{'surface_support':{'unknown':1}},{'cover':{'thickness_mm':-1}},{'powder_opening':{'width_mm':20,'height_mm':10}}]:
   with self.assertRaises(ValueError):self.config(**update)
 def test_grid_has_no_global_top_region(self):
  c=self.config();nodes,struts=lower_plan(c,[[0,0,0],[30,30,60]])
  self.assertTrue(struts);self.assertTrue(all(s['radius']==1.2 for s in struts))
  for s in struts:
   a=nodes[s['a']]['point'];b=nodes[s['b']]['point'];angle=math.degrees(math.atan2(b[2]-a[2],math.hypot(b[0]-a[0],b[1]-a[1])))
   self.assertGreaterEqual(angle,50.5)
 def test_radius_exclusion(self):
  planes=[([1,0,0],1),([-1,0,0],1),([0,1,0],1),([0,-1,0],1),([0,0,1],1),([0,0,-1],1)]
  self.assertFalse(intersects([-2,1.2,0],[2,1.2,0],0,planes));self.assertTrue(intersects([-2,1.2,0],[2,1.2,0],.3,planes))
if __name__=='__main__':unittest.main()
