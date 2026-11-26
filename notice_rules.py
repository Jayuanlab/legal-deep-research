"""Local scope checks for contractual termination procedure, not current-law certification."""
import json,re
NOTICE_QUERY='民法典 第五百六十五条 解除通知 到达 期限届满 起诉状副本 仲裁申请书副本 送达'

def requires_notice(issue):
 text=issue.get('title','')+' '+issue['question']
 if re.search('赔偿|损失',text) and not re.search('解除权|通知|生效|行使',text):return False
 return bool(re.search('解除权|解除合同|解除通知|通知解除|解除方式|解除生效',text))

def is_notice_law(d):
 return d.get('doc_type')=='law' and d.get('law_name')=='中华人民共和国民法典' and str(d.get('article'))=='565' and d.get('reference_status')!='not_reference'

def local_notice_sources():
 from corpus import connection
 from vectors import chunks
 with connection() as db:
  docs=[json.loads(r[0]) for r in db.execute("SELECT payload FROM documents WHERE doc_type='law' AND json_extract(payload,'$.law_name')=? AND json_extract(payload,'$.article') IN (?,?)",('中华人民共和国民法典','565',565))]
 return [dict(d,id=p['id'],parent_id=d['id'],text=p['text'],fragment=dict(index=p['index'],start=p['start'],end=p['end'],source_length=len(d['text'])),retrieval='本地明确条号定位（不推定当前效力）') for d in docs if is_notice_law(d) for p in chunks(d)]

def notice_errors(claim,sources):
 if claim.get('role')!='notice':return []
 errors=[];text=claim['statement']
 if not any(is_notice_law(sources.get(ref.get('source_id'),{})) for ref in claim['references'] if isinstance(ref,dict)):errors.append('解除通知分析必须引用本次证据中的民法典第565条，不能以解除权成立规则代替。')
 for pattern,message in [
  ('解除权|依法|合法|有权','缺少依法享有解除权的前提'),
  ('通知.{0,15}到达|到达.{0,15}通知','缺少普通通知到达规则'),
  ('期限.{0,10}届满','缺少附期限通知的届满时点'),
  ('未(?:能)?履行|仍不履行|没有履行','缺少债务人在期限内实际未履行的条件，不能仅凭通知载明期限就认定届满解除'),
  ('起诉|诉讼','缺少直接起诉的解除路径'),('仲裁','缺少直接申请仲裁的解除路径'),
  ('副本','缺少起诉状或仲裁申请书副本'),('送达','缺少副本送达时点'),('确认','缺少法院或仲裁机构确认主张的条件')]:
  if not re.search(pattern,text):errors.append(message)
 return errors
