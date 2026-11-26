"""Freeze original dataset, code and results without overwriting an archive."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'archives'/'retrieval-v1'

def archive():
    if not OUT.resolve().is_relative_to(ROOT):raise ValueError('Archive outside evaluation workspace')
    files=[ROOT/name for name in ('laws.jsonl','cases.jsonl','controls.jsonl','manifest.json','README.md','build_dataset.py','evaluate.py','verify_replay.py')]
    files+=list((ROOT/'results').glob('*'))
    for source in files:
        if not source.is_file():continue
        target=OUT/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if target.read_bytes()!=source.read_bytes():raise ValueError('Refusing to overwrite existing archive: '+str(target))
        else:target.write_bytes(source.read_bytes())
    print('Archived original v1 dataset, code and baseline:',OUT)

if __name__=='__main__':archive()
