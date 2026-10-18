"""Run a fresh job with explicit local FreeCAD and Blender executable paths."""
import argparse,os,subprocess,json,time
from pathlib import Path
from common import load
def main():
 parser=argparse.ArgumentParser();parser.add_argument('config');parser.add_argument('--freecad',required=True);parser.add_argument('--blender',required=True);a=parser.parse_args()
 c=load(a.config);work=Path(c['work_dir'])
 if work.exists() and any(work.iterdir()):raise FileExistsError('Use a fresh empty work directory')
 for p in [c['output_stl'],c['output_blend']]:
  if Path(p).exists():raise FileExistsError('Output exists: '+p)
 work.mkdir(parents=True,exist_ok=True);scripts=Path(__file__).resolve().parent;env=dict(os.environ,SURFACE_LATTICE_CONFIG=str(Path(a.config).resolve()))
 fc=[a.freecad,'-u',str(work/'freecad-user.cfg'),'-s',str(work/'freecad-system.cfg')]
 stages=[('prepare',fc+[str(scripts/'prepare_cover.py')],'SURFACE_COVER_PREPARED'),('members',fc+[str(scripts/'generate_members.py')],'SURFACE_MEMBERS_GENERATED'),('assemble',[a.blender,'--background','--factory-startup','--python',str(scripts/'generate_covered_lattice.py'),'--',str(Path(a.config).resolve())],'SURFACE_LATTICE_ASSEMBLED'),('validate',fc+[str(scripts/'validate_surface_lattice.py')],'SURFACE_LATTICE_VALIDATION_OK')]
 timings={};started=time.perf_counter()
 for name,command,marker in stages:
  print('RUNNING '+name,flush=True)
  stage_start=time.perf_counter()
  with (work/(name+'.log')).open('w',encoding='utf-8') as log:
   result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
  output=(work/(name+'.log')).read_text(encoding='utf-8',errors='replace')
  timings[name]={'seconds':time.perf_counter()-stage_start,'returncode':result.returncode,'marker_present':marker in output}
  (work/'timings.json').write_text(json.dumps({'stages':timings,'elapsed_seconds':time.perf_counter()-started},indent=2))
  if result.returncode or marker not in output:
   errors=[line for line in output.splitlines() if any(x in line for x in ['Exception','Error','Traceback'])]
   raise RuntimeError(name+' failed; see '+str(work/(name+'.log'))+'\n'+'\n'.join(errors[-8:]))
  print('PASSED '+name,flush=True)
 report=json.loads((work/'validation.json').read_text())
 if report['status']!='PASS':raise RuntimeError('Validation did not pass')
 print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
