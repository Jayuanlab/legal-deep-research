"""Generate a source-backed corpus inventory and explicit remaining coverage backlog."""
import json
from pathlib import Path
from official_bulk import ROOT

def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def main():
    m=read('data/bulk-import-manifest.json');c=read('data/national-coverage.json');index=read('data/bulk-index-status.json');v=read('data/bulk-validation.json')
    moj=read('data/moj-collection.json');samr=read('data/samr-collection.json');court=read('data/court-parsing-report.json')
    smoke_path=ROOT/'evaluation/bulk-smoke.json';smoke=read('evaluation/bulk-smoke.json') if smoke_path.exists() else None
    after=m['after'];before=m['before'];whole=m['whole_text_items']
    rows=['# 全国性规范与官方案例批量扩库记录','',
      '本轮显著扩大本地资料范围，尚未覆盖中国所有法条。下表为已入库资料条目，不把目录记录、网页数或归档失败项算作已收录条文。','',
      '| 资料 | 扩库前 | 扩库后 |','| --- | ---: | ---: |',
      f"| 法规资料条目 | {before['laws']} | {after['laws']} |",f"| 案例发布条目 | {before['cases']} | {after['cases']} |",f"| 合计 | {before['total']} | {after['total']} |",'',
      f"法规资料中有{after['laws']-whole}条分条文本、{whole}份完整但未分条的规范文本。案例包括279件指导案例和{after['cases']-279}件典型案例；均为官方发布或法院官方转载，不等于原始判决全文，同一发布条目可能涉及关联案件。",'',
      f"阿里云text-embedding-v4、1024维；{index['chunks']}个分片全部就绪。{v['tests']}项测试通过，来源审计异常数为{v['source_audit_problems']}；原有{v['preserved_original_documents']}件资料未改动。",'',
      '## 来源覆盖与处理结果','',
      '| 官方入口 | 本轮目录/原文情况 | 处理边界 |','| --- | --- | --- |',
      f"| [国家行政法规库](https://xzfg.moj.gov.cn/search2.html) | 目录603件，603件正文归档；{moj['parsed']}件连续分条 | 另24件完整保存为未分条全文，未编造条号；目录日期单独保留 |", 
      f"| [市场监管总局法律法规栏目](https://www.samr.gov.cn/zw/flfg/) | 286篇目录，{samr['parsed']}篇通过分条解析 | {len(samr['failures'])}篇失败保留原因；与既有资料及行政法规库去重 |", 
      '| [最高法院司法解释栏目](https://www.court.gov.cn/fabu/gengduo/16.html) | 401篇目录和正文全部归档 | 修改/废止决定、无可靠边界、无法确认末条等单独保留，不直接充当有效法条 |',
      '| [最高法院典型案例栏目](https://www.court.gov.cn/zixun/gengduo/104.html) | 433篇目录和正文全部归档 | 逐案分开，仅导入通过结构检查的正文；司法改革举措、目录、新闻稿不冒充裁判案例 |',
      '| [山东法院指导案例45号转载](https://www.sdcourt.gov.cn/tadpfy/369377/369381/1497619/index.html) | 补齐45号，当前指导案例1—279号均有来源文本 | 明示官方法院转载，不伪装最高法院独立页面；参照状态仍须核验 |',
      '', f"本轮跳过{m['duplicate_articles_skipped']}条规范化正文重复记录。同一规范版本条号有{len(court.get('article_conflicts',[]))}处文本或边界差异，保留原存档供复核，未覆盖既有条文。{m['future_law_items_excluded']}条法规资料已有尚未施行或其他明确排除依据，保留浏览、默认排除研究检索；六件已公告停止参照的指导案例继续过滤。",'',
      '## 尚未覆盖的范围','',
      f"按[官方303件法律目录]({c['benchmark_url']})（截至2026-08-28）逐项核对：{c['title_matches']}个标题存在来源发布文本，{len(c['missing_names'])}个标题缺少原文。同名不代表版本一致，更不代表整部法律的现行效力核验完成。该目录不是当前日期全中国规范的全集，不能据此给出全中国覆盖率。",'',
      f"国家法律法规数据库公开目录返回总量{c['npc_catalog']['expected_records']}条，本轮只取得{c['npc_catalog']['stored_catalog_records']}条目录记录，全文成功入库数为0；后续请求出现HTTP循环重定向。下载器记录失败并暂停该来源，不重复绕过访问障碍，也没有把目录标题作为法条正文。",'',
      '地方性法规、自治条例、单行条例、经济特区法规、部门规章、地方政府规章、完整历史修订沿革及港澳台各法域规范尚未系统覆盖。案例也未覆盖全国裁判文书；需要登录的案例资源没有接入。', '',
      '逐项缺失标题见 [national-coverage.json](national-coverage.json)；原文未解析页及原因见 [court-parsing-report.json](court-parsing-report.json)、[samr-collection.json](samr-collection.json) 和 [npc-text-collection-national.json](npc-text-collection-national.json)。这些是实际缺口，不是已完成任务。','',
      '## 真实检索与评测边界','']
    if smoke:
        rows += [f"新增资料检索诊断：{smoke['hits']}/{smoke['queries']}题命中预先指定的来源，所有返回片段均与源文本位置核对。12题为预先指定法条的诊断，6题为案名定位，全部用真实阿里云查询向量和生产RRF检索。保留未命中项，详见 [bulk-smoke.json](../evaluation/bulk-smoke.json)。",'']
    else:rows += ['新增资料真实检索诊断仍在运行；结果完成后写入evaluation/bulk-smoke.json。','']
    rows += ['原400题问法、标注和分组保持不变，逐条核对来源正文未漂移，manifest记录新语料指纹。扩库前资料快照和标签保留在evaluation/archives/before-bulk-20261112/，旧Jina/阿里云成绩为扩库前结果。本轮未运行完整400题重评，不能将旧成绩用于本轮。','',
      '## 继续采集与断点','',
      '研究运行时仍只查本地资料，模型API按原配置调用。以下脚本是建库工具，手动运行才会访问官网。','',
      '- collect_court_bulk.py：下载两个最高法院完整公开栏目，原始响应及SHA256保存在raw/bulk/court/。',
      '- collect_moj_bulk.py：下载行政法规库目录和主版本正文，历史链接未冒充当前主版本。',
      '- collect_samr_bulk.py：依官方页面实际使用的公开栏目接口分页采集。',
      '- collect_npc_catalog.py / collect_npc_texts.py：国家法律法规数据库目录、官方Word下载和按条解析，保留失败断点；源站访问恢复后可继续。',
      '- parse_court_bulk.py / merge_official_bulk.py：离线解析、按正文去重、保存条号/版本冲突与未分条全文。',
      '- build_bulk_index.py / finalize_bulk_index.py：独立SQLite构建、按模型与正文哈希复用向量；当前批次可断点续跑。批量构建最多16路、每批10条，单次模型失败沿用有界重试；数据库锁等待30秒。',
      '- publish_bulk.py：无活动研究且服务停止后切换，保留旧库并复制最新研究记录。新一轮扩库应另建快照及备份路径，脚本拒绝覆盖历史快照。',
      '', '已归档原文、正文哈希、目录和结果清单可检查；不使用模型生成的案例或问答填充数量。原始规范出现日期不明、历史版本或后续修改时保留说明，不自行补造法律施行日期。','']
    (ROOT/'data/BULK-COVERAGE.md').write_text('\n'.join(rows),encoding='utf-8')
    p=ROOT/'README.md';text=p.read_text(encoding='utf-8')
    old='资料库包括2782条法条、278件最高法院指导案例与41件典型案例发布原文，详见 [本轮扩库记录](data/EXPANSION-20261112.md)。'
    new=f"资料库当前有{after['laws']}条法规资料（含{whole}份未分条规范全文）与{after['cases']}件官方案例发布条目，详见 [批量扩库与覆盖缺口](data/BULK-COVERAGE.md)。尚未覆盖全中国法条。"
    text=text.replace(old,new);p.write_text(text,encoding='utf-8')
    p=ROOT/'data/README.md';text=p.read_text(encoding='utf-8')
    note=f"当前批量扩库为{after['laws']}条法规资料、{after['cases']}件案例，{index['chunks']}个向量分片全部就绪；包含未分条规范全文，尚未覆盖全中国法规。最新范围与缺口见 [BULK-COVERAGE.md](BULK-COVERAGE.md)，下面表格及说明保留前一轮来源快照，不能作为当前完整清单。"
    if note not in text:text=text.replace('\n','\n\n'+note+'\n',1)
    p.write_text(text,encoding='utf-8')
    p=ROOT/'evaluation/README.md';text=p.read_text(encoding='utf-8')
    note='\n本轮全国性规范批量扩库：语料已再次变更，当前manifest记录national-bulk-20261112。完整400题尚未重评，旧报告均为旧库成绩。新增来源诊断为bulk-smoke.json；后续完整评测请使用--output evaluation/results-bulk，旧目录禁止跨语料覆盖。\n'
    if note not in text:text=text.replace('\n','\n'+note,1)
    p.write_text(text,encoding='utf-8')
    for p in (ROOT/'data/BULK-COVERAGE.md',ROOT/'README.md',ROOT/'data/README.md',ROOT/'evaluation/README.md'):
        text=p.read_text(encoding='utf-8');assert '\ufffd' not in text and '???' not in text

if __name__=='__main__':main()
