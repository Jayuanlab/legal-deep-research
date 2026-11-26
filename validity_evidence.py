"""Conservative legal-title/edition and operative-clause helpers."""
import re
from law_validity import norm

def titles(text):
 stack=[];start=None;out=[]
 for i,ch in enumerate(text):
  if ch in '《〈':
   if not stack:start=i
   stack.append(ch)
  elif ch in '》〉' and stack:
   stack.pop()
   if not stack:out.append((text[start+1:i],start,i+1))
 return out

def canonical(text):
 s=norm(text).replace('、','').replace('，','').replace(',','')
 # Publisher prefix is optional, but the complete normative title is required.
 return re.sub(r'^最高人民法院(?:最高人民检察院)?','',s)

def exact_title(a,b):return canonical(a)==canonical(b)

def amended_sections(text):
 matches=list(re.finditer(r'(?m)^\s*[一二三四五六七八九十百]+、\s*(?:修改|对|将|删去)',text))
 out=[]
 for i,m in enumerate(matches):
  end=matches[i+1].start() if i+1<len(matches) else len(text)
  block=text[m.start():end]
  ts=titles(block)
  if ts and ts[0][1]<35:
   out.append(dict(name=ts[0][0],quote=block[:9000],start=m.start(),end=end))
 return out

def edition_years(header):
 text=header.translate(str.maketrans('０１２３４５６７８９','0123456789'))
 return sorted(set(int(m[1]) for m in re.finditer(r'((?:19|20)\d{2})年[^\n。]{0,180}?(?:通过|修订|修正|公布|发布)',text)))

def repeal_targets(sentence):
 # Do not let a nested cited law match a longer implementing regulation.
 if not re.search('同时废止|予以废止|废止《',sentence):return []
 ts=titles(sentence)
 return [dict(name=t,start=s,end=e,scope=sentence[e:(ts[i+1][1] if i+1<len(ts) else len(sentence))]) for i,(t,s,e) in enumerate(ts)]
