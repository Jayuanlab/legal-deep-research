"""Bounded UTF-8 edits for existing desktop components."""
from pathlib import Path
path=Path(__file__).parent/'app.js'
s=path.read_text(encoding='utf-8')
old='<h3>${esc(d.title)}</h3><small>'
assert s.count(old)==1
s=s.replace(old,'<h3>${esc(d.title)}</h3>${validityHTML(d)}<small>')
helper='''function validityHTML(d){
 if(d.doc_type!=='law')return '';
 const v=d.validity||{code:'unknown',label:'效力待核验',reason:'尚未完成当前效力核验，不能据收录推定有效。'};
 const code=['repealed','partially_repealed','superseded','not_yet_effective','needs_review','unknown'].includes(v.code)?v.code:'unknown';
 return `<div class="validity-block"><span class="validity-status ${code}">${esc(v.label)}</span>${v.effective_from?'<small> 状态生效：'+esc(v.effective_from)+'</small>':''}<details><summary>效力依据与适用范围</summary><p>${esc(v.reason||'')}</p>${v.scope?'<p>范围：'+esc(v.scope)+'</p>':''}${v.checked_at?'<small>核对日期：'+esc(v.checked_at)+'</small>':''}${v.source_url?'<p><a href="'+esc(v.source_url)+'" target="_blank" rel="noopener noreferrer">查看效力依据 ↗</a></p>':''}</details></div>`;
}
'''
s=helper+s
needle="let catalogData=null;"
assert s.count(needle)==1
s=s.replace(needle,needle+'''\nconst validitySelect=document.createElement('select');validitySelect.id='library-validity';validitySelect.setAttribute('aria-label','法律效力');validitySelect.innerHTML='<option value="">全部效力状态</option><option value="repealed">已废止／失效</option><option value="partially_repealed">部分条款已废止</option><option value="superseded">已修改的历史版本</option><option value="not_yet_effective">尚未施行</option><option value="needs_review">效力存疑，待核验</option><option value="unknown">效力待核验</option>';$('#library-query').before(validitySelect);validitySelect.onchange=()=>{libraryPage=1;loadLibrary()};\n''')
needle="function fillTopics(){topicSelect.innerHTML="
assert s.count(needle)==1
s=s.replace(needle,"function fillTopics(){validitySelect.hidden=$('#library-type').value!=='law';if(validitySelect.hidden)validitySelect.value='';topicSelect.innerHTML=")
needle="if(topicSelect.value)params.set('topic',topicSelect.value);"
assert s.count(needle)==1
s=s.replace(needle,needle+"if($('#library-type').value==='law'&&validitySelect.value)params.set('validity',validitySelect.value);")
assert '\ufffd' not in s and '???' not in s
path.write_text(s,encoding='utf-8')
print('Updated status badges, provenance details and law-only status filter')
