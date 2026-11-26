from pathlib import Path
p=Path(__file__).with_name('app.js');s=p.read_text(encoding='utf-8')
old="${esc(x.elapsed??'')} 秒</small>";new="${esc(x.elapsed??'')} 秒${x.elapsed_scope?' · '+esc(x.elapsed_scope):''}</small>"
assert s.count(old)==1;s=s.replace(old,new)
old='${e.elapsed}s ${e.stage} / ${e.state}';new="${e.elapsed}s${e.elapsed_scope?' ('+e.elapsed_scope+')':''} ${e.stage} / ${e.state}"
assert s.count(old)==1;s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
