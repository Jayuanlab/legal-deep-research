from pathlib import Path
p=Path(__file__).with_name('app.js');s=p.read_text(encoding='utf-8')
old="rule:'规范要点'})[c.role]";new="rule:'规范要点',notice:'解除通知与生效'})[c.role]"
assert s.count(old)==1
p.write_text(s.replace(old,new),encoding='utf-8')
assert new in p.read_text(encoding='utf-8')
