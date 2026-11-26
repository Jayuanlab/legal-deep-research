# 法条库与案例库召回评测集 v2

本轮全国性规范批量扩库：语料已再次变更，当前manifest记录national-bulk-20261112。完整400题尚未重评，旧报告均为旧库成绩。新增来源诊断为bulk-smoke.json；后续完整评测请使用--output evaluation/results-bulk，旧目录禁止跨语料覆盖。

2026-11-12进一步扩库：候选资料现为2782条法条、319件案例，400题原问法、qrel与分组不变，manifest单独记录新语料指纹及corpus_revision。扩库前的原始资料快照、标签、两种模型结果归档在archives/retrieval-v2-before-corpus-expansion/及archives/corpus-before-expansion-20261112.json。已有results/、results-aliyun/和模型对比是扩库前结果，不能作为当前库成绩；重新评测须使用新输出目录。新增资料的16题真实检索诊断见expansion-smoke.json。

当前共 **400题**，从v1的80题增加320题。固定现有语料和检索算法，检验单次查询的文档召回、排序及片段定位，不计Deep Research拆题、补检索或答案生成正确率。

当前向量模型迁移到阿里云text-embedding-v4。Jina历史基线仍在results/，阿里云结果另存results-aliyun/；默认目录已有不同模型时会在调用API前拒绝覆盖。[同题模型对比](embedding-model-comparison.md)核对相同400题、语料快照及BM25控制，再比较两种向量模型，不能要求跨模型排名逐条相同。

| 类型 | 总题数 | v1保留 | v2新增 | 不同的正例来源 |
| --- | ---: | ---: | ---: | ---: |
| 法条 laws.jsonl | 200 | 48 | 152 | 118条法条 |
| 案例 cases.jsonl | 176 | 24 | 152 | 100件案例 |
| 边界 controls.jsonl | 24 | 8 | 16 | 库外、噪声及6件停止参照案例 |

开发集139题、测试集237题、控制集24题。所有查询唯一；原80题的查询、相关来源、锚点、编号和分组均保留不变，使用cohort=regression_v1标记；新增题标为expansion_v2。旧版文件、生成脚本和已跑基线完整冻结在 [archives/retrieval-v1](archives/retrieval-v1/README.md)，新结果会分别统计旧题与新题。

## 新增内容与标注来源

法条新增76个来源，每个有两种不同问法，覆盖合同、定金与保证、劳动服务期与竞业、股东出资和知情权、个人信息自动化决策与未成年人、消费者、婚姻继承、侵权和民事诉讼等。包含多条依据组合题、相近规范的条件区分，以及较少法律术语的口语题。

案例新增76件不同来源，每案两问，覆盖刑事、知识产权、海事、行政、执行、环境公益、公司、劳动等。新增案例题不靠指导案例号、完整案名或当事人真名定位。两问可能关注不同程序节点、证据条件或裁判要点，各自设置原文锚点；不得简单复制一个锚点给整案所有问题。

题目由本助手与研究任务根据本地官方存档编写，具有合成与来源改写性质，不是用户真实查询日志。未调用被测qwen生成题目或自动判分，尚无独立法律专家全面相关性评审。官方链接、原文存在和哈希校验只能证明可回溯，不能替代标签语义与适用性复核。

每条正例包含query、domain、style、split、cohort及qrels；qrel记录doc_id、grade、evidence_quote、title、source_url、text_sha256。grade=2为直接主题依据，grade=1为补充依据。confusable_ids仅为容易混淆的对照，不自动判为不相关。

相关性标签不穷尽全库。未标注候选为unjudged，不自动算作负例，也不自动转为正例。案例是历史发布文本的检索相关性，不代表当前个案必然可直接参照。

## 分组与独立性

共享任一qrel的查询按连通分量分组，dev/test不共享正例来源；定位题只在dev。v1的分组不因扩充发生变化，新增正例来源也不与v1的正例来源重叠。语料库本身仍共享，主题和当事人关联并未全部隔离，不是完全域外泛化测试。

同源两问相互关联，**400题不等于400个独立案件或法条**。指标按题宏平均；不按400个独立样本计算置信区间。旧题已有基线，属于回归集；新题是在已知旧基线后设计的扩展挑战，结果另列cohort，不宣传为完全盲测。若用test题调参，需记载test已被使用并另增保留集。

## 运行

在legal-demo目录执行：

```powershell
# 从冻结v1和增补研究记录重新构建v2，只读本地原文。
python -X utf8 evaluation/build_v2.py
# 显式允许为缺失查询调用当前阿里云 embedding API；8条一批，可续跑。
python -X utf8 evaluation/evaluate.py --embed-missing --output evaluation/results-expanded
# 查询向量已有缓存时完全离线重放，不调用任何模型API或联网搜索。
python -X utf8 evaluation/evaluate.py --output evaluation/results-expanded
# 生成Jina历史基线与阿里云基线的同题对比。
python -X utf8 evaluation/compare_embedding_models.py
# 原80题逐题保持一致的核对只适用于原Jina模型，不适用于跨模型排名。
# 如需重现该历史核对，可在独立进程中选择 LEGAL_EMBEDDING_PROVIDER=zhiyu 后运行 verify_expansion.py。
# 仅跑开发集或BM25；用独立输出目录保留全量基线。
python -X utf8 evaluation/evaluate.py --split dev --output evaluation/results-dev
python -X utf8 evaluation/evaluate.py --bm25-only --output evaluation/results-bm25
# 以当前评测器复测冻结的v1，输出到独立目录，避免改动归档。
python -X utf8 evaluation/evaluate.py --dataset evaluation/archives/retrieval-v1 --output evaluation/results-v1-replay
```

build_dataset.py仅保留v1方法，当前v2存在时拒绝直接运行，防止意外覆盖。archive_v1.py为首次冻结使用，已有归档内容不同时会拒绝覆盖。不要重新生成或改写归档来掩盖差异。

查询向量缓存按模型配置标识隔离并校验查询文本、维度、有限数值和归一化，不保存密钥。语料或标签指纹变化会中止评测，需复核标签并更新版本。新题与语料源码见 [expansion/law_seeds.py](expansion/law_seeds.py)、[案例核对A](expansion/case-research-a.md)、[案例核对B](expansion/case-research-b.md)；quality-audit.json保存唯一性、来源与近重复检查。

## 评测方法

保持生产配额：法条K=4，案例K=2。BM25调用corpus.search，纯向量使用同一索引、同一查询向量并取每篇资料最匹配分片；混合检索直接调用vectors.retrieve。缓存仅复用查询向量、固定索引快照和完全相同的JSON解码结果，生产排序算术、RRF、分片选择和配额不变。不同基线均排除停止参照案例。

- Hit@1、Hit@K：首条或前K条是否命中已标注来源。
- 已标注Recall@K：命中的已知相关来源数/该题qrel总数，多请求题可部分命中。
- MRR@K：首个已知相关结果的倒数排名，未命中为0。
- 已标注nDCG@K：增益2^grade−1，未标注结果不计已知增益；不等于穷尽标签的真实nDCG。
- 锚点Recall@K：返回分片包含指定原句的比例，区分文档命中与证据位置。未含指定句也可能含其他有用论证，需人工复核。BM25返回全文，不与分片方法比较该指标。

同一案例的多个分片按parent_id去重。没有正例的控制题不进入Recall/MRR/nDCG均值，而单独报告停止参照泄漏和无答案仍返回候选的数量。当前排序器没有独立拒答阈值，返回候选不代表能形成答案。

## 结果文件

- [results/report.md](results/report.md)：Jina历史基线的总表及失败题。
- [results-aliyun/report.md](results-aliyun/report.md)：当前阿里云基线，含旧题/新增题、开发/测试集和问法切片。
- [embedding-model-comparison.md](embedding-model-comparison.md)：固定数据与算法后的两模型对比。
- results/summary.json：机器可读分组指标及版本指纹。
- results/details.jsonl：每题每种方法的候选编号、分片、来源、标签与分数。
- results/review_pool.jsonl：未标注候选，供后续人工审查。
- results/expansion-regression.json：原80题与冻结v1逐题核对的结果（本轮完成后生成）。

排序耗时不含查询向量API生成，不代表线上端到端延迟。原Jina评测记录中，80题三种方法共240个结果与冻结v1完全一致，另对16题离线重放、提供方请求数0；这些是历史同模型核对，不是阿里云排名一致性承诺。本次模型迁移不改数据标签、BM25、分片、RRF或检索配额。
