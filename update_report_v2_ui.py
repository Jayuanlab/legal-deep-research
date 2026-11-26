from pathlib import Path
p=Path(__file__).parent/'app.js';s=p.read_text(encoding='utf-8')
a=s.index('function renderReport(text){');b=s.index('function tab(name)',a)
replacement=r'''function renderReport(text){
 function inline(raw){
  const pattern=/\[([A-Z][A-Za-z0-9]*(?:_\d+)?)\]|\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)|\*\*([^*\n]+)\*\*/g;
  let out='',last=0;for(const m of raw.matchAll(pattern)){out+=esc(raw.slice(last,m.index));if(m[1])out+=`<button class="citation" data-ref="${esc(m[1])}" title="查看证据 ${esc(m[1])}">${esc(m[1])}</button>`;else if(m[2])out+=`<a href="${esc(m[3])}" target="_blank" rel="noopener noreferrer">${esc(m[2])}</a>`;else out+='<strong>'+esc(m[4])+'</strong>';last=m.index+m[0].length}return out+esc(raw.slice(last));
 }
 let html='',list=false;for(const line of text.split('\n')){const heading=line.match(/^(#{1,4})\s+(.+)$/),bullet=line.match(/^[-*]\s+(.+)$/);if(!bullet&&list){html+='</ul>';list=false}if(!line.trim())continue;if(heading){const tag='h'+heading[1].length;html+=`<${tag}>${inline(heading[2])}</${tag}>`}else if(bullet){if(!list){html+='<ul>';list=true}html+='<li>'+inline(bullet[1])+'</li>'}else html+='<p>'+inline(line)+'</p>'}if(list)html+='</ul>';return html;
}
'''
s=s[:a]+replacement+s[b:]
old="${esc(c.claim_id)} · ${esc(c.status)}"
assert s.count(old)==1
s=s.replace(old,"${esc(c.claim_id)} · ${esc(({conclusion:'结论',application:'事实适用',supporting:'支持理由',counterargument:'抗辩与回应',case_comparison:'类案比较',action:'行动建议',rule:'规范要点'})[c.role]||'主张')} · ${esc(c.status)}")
p.write_text(s,encoding='utf-8');assert '\ufffd' not in s
print('Updated structured report rendering and generic source links')
