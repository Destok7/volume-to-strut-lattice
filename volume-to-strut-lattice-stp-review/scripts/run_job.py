"""Run STEP-only lattice generation, CAD validation and export. No Blender."""
import argparse,os,subprocess,json,time
from pathlib import Path
from common import load

def main():
 parser=argparse.ArgumentParser();parser.add_argument('config');parser.add_argument('--freecad',required=True);a=parser.parse_args()
 c=load(a.config);work=Path(c['work_dir']);output=Path(c['output_step'])
 if work.exists() and any(work.iterdir()):raise FileExistsError('Use a fresh empty work directory')
 if output.exists():raise FileExistsError('Output already exists')
 work.mkdir(parents=True,exist_ok=True);scripts=Path(__file__).resolve().parent
 env=dict(os.environ,SURFACE_LATTICE_CONFIG=str(Path(a.config).resolve()))
 fc=[a.freecad,'-u',str(work/'freecad-user.cfg'),'-s',str(work/'freecad-system.cfg')]
 stages=[('prepare','prepare_cover.py','SURFACE_COVER_PREPARED'),('members','generate_members.py','SURFACE_MEMBERS_GENERATED'),('cad_validate','validate_surface_lattice.py','SURFACE_CAD_VALIDATION_OK'),('step_export','assemble_step_lattice.py','SURFACE_STEP_VALIDATION_OK')]
 timings={};started=time.perf_counter()
 for name,script,marker in stages:
  print('RUNNING '+name,flush=True);start=time.perf_counter()
  with (work/(name+'.log')).open('w',encoding='utf-8') as log:result=subprocess.run(fc+[str(scripts/script)],env=env,stdout=log,stderr=subprocess.STDOUT)
  output=(work/(name+'.log')).read_text(encoding='utf-8',errors='replace')
  timings[name]={'seconds':time.perf_counter()-start,'returncode':result.returncode,'marker_present':marker in output}
  (work/'timings.json').write_text(json.dumps({'stages':timings,'elapsed_seconds':time.perf_counter()-started},indent=2))
  if result.returncode or marker not in output:raise RuntimeError(name+' failed; see '+str(work/(name+'.log')))
  print('PASSED '+name,flush=True)
 report=json.loads((work/'validation.json').read_text())
 if report['status']!='PASS' or report['step_roundtrip']!='PASS':raise ValueError('Validation failed')
 print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()

