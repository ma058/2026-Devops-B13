"""Export personal evidence without token/env secrets; manifest excludes itself."""
import argparse,io,json,subprocess,tarfile,uuid
from pathlib import Path
from member2_profiles import canonical,digest
from member2_evidence import evidence_files, scan_evidence
ROOT=Path(__file__).resolve().parents[2]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    config=json.loads(a.config.read_bytes())
    run=ROOT/config['run_relative']
    blob=Path(config['token_file']).read_bytes().strip()
    # A failed run is still exported by CI. Recheck exactly the exportable
    # runtime set here so a scan failure cannot upload the original secret.
    if scan_evidence(run) != 0:
        raise ValueError('EVIDENCE_SCAN_REJECTED: original run retained; no archive created')
    destination=a.out.resolve();destination.mkdir(parents=True,exist_ok=False)
    bundle=destination/'source.bundle'
    subprocess.run(['git','bundle','create',str(bundle),'HEAD'],cwd=ROOT,check=True)
    content={'source.bundle':bundle.read_bytes(),'source-commit.txt':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT)}
    for path in evidence_files(run):
        raw=path.read_bytes()
        if blob and blob in raw:raise ValueError('SECRET_IN_EXPORT:'+str(path))
        content['evidence/'+path.relative_to(run).as_posix()]=raw
    manifest={n:{'bytes':len(b),'sha256':digest(b)} for n,b in content.items()}
    content['MANIFEST.json']=canonical(manifest)+b'\n'
    archive=destination/('member2-e13e14-'+config['run_name']+'.tar.gz')
    with tarfile.open(archive,'x:gz') as t:
        for n,b in content.items():
            info=tarfile.TarInfo(n);info.size=len(b);info.mode=0o600;t.addfile(info,io.BytesIO(b))
    with tarfile.open(archive) as t:
        for n,b in content.items():assert t.extractfile(n).read()==b
    archive.with_suffix('.gz.sha256').write_text(digest(archive.read_bytes())+'  '+archive.name+'\n')
    print('EXPORT_ARCHIVE='+str(archive));print('EXPORT_SHA256='+digest(archive.read_bytes()))

if __name__=='__main__':main()
