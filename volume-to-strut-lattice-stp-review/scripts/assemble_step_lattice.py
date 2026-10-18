import os,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import load,sha,fingerprint
from cad_support import read_shape
from step_export import export_and_check

def main():
 c=load(os.environ['SURFACE_LATTICE_CONFIG']);work=Path(c['work_dir'])
 report=json.loads((work/'cad_validation.json').read_text(encoding='utf-8'))
 if report['status']!='PASS' or report['config_hash']!=fingerprint(c) or report['source_hash']!=sha(c['input_step']):raise ValueError('Missing/stale CAD validation')
 for name in ['cover','lattice']:
  if sha(work/(name+'.brep'))!=report[name+'_brep_hash']:raise ValueError('Validated CAD changed')
 step=export_and_check(read_shape(work/'cover.brep'),read_shape(work/'lattice.brep'),c['output_step'],c['validation']['tolerance_mm'],verify_existing=os.environ.get('STEP_VERIFY_EXISTING')=='1')
 report.update(step);report['output_step']=c['output_step'];report['closed_meshes']='not applicable'
 (work/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('SURFACE_STEP_VALIDATION_OK '+json.dumps(step),flush=True)
try:main()
except Exception:
 import traceback;traceback.print_exc();raise

