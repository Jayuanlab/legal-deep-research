# 法律 Deep Research 工作台

面向法律研究任务的工作台：模型拆题、混合检索、证据评估、补检索与引用验证。完整本地法库和运行产物不随代码仓库提交，首次使用需要按下方命令建立资料库。建库阶段可下载官方公开资料，研究阶段只检索本地库；真实向量和语言模型通过 API 调用。

本仓库默认只保存源码、配置模板、评测定义和研究说明。SQLite 法库、原始法规文件、向量缓存、用户材料、运行报告和模型输出均由 `.gitignore` 排除。请将密钥写入本地 `.env`，参考 `.env.example`。

报告生成已升级为`legal-report-v3`：在逐争点核验的事实适用、正反论证、类案和建议之外，解除争点必须核对第565条的三条通知路径；事实材料台账区分用户陈述、待核实事实与待收集原件，并关联已核验分析。格式与判断边界见 [执行流程](RESEARCH-FLOW.md)，同题观察分别保存于`runs/report-v2/`及`runs/report-v3/`，历史任务不改写。

## 运行

资料库支持按效力筛选及查看依据。全库1,204个来源版本已纳入扫描：367条已废止、61条部分失效、1,960条属于已修改的历史版本；尚未施行与待核验分别标记。详见 [全库效力核验记录](data/VALIDITY-ALL.md)。未找到明确依据的记录不视为现行有效。

需要 Python 3.10+（包含 SQLite FTS5），依赖见 requirements.txt。

```powershell
python -m pip install -r requirements.txt
python -X utf8 corpus.py
python -X utf8 vectors.py
python -X utf8 server.py --port 8765
```

访问 http://127.0.0.1:8765 。默认读取本机 Zhiyu 配置并调用真实向量和语言模型。资料向量化会将资料发送给向量服务，研究时会发送问题以及召回资料给对应服务。应用仅绑定本机。

## 模型模式

默认只读 `D:/zhiyu/apps/web` 的 `.env`、`.env.development`、`.env.local`、`.env.development.local`，后者覆盖前者，进程环境变量优先。可通过 ZHIYU_PROJECT_ROOT 修改项目根目录。当前向量模型由非敏感的model-settings.json选择阿里云text-embedding-v4、1024维，密钥仍只读DASHSCOPE_API_KEY或BAILIAN_API_KEY。不会复制密钥到当前项目。配置和索引迁移说明见 [ALIYUN-EMBEDDING.md](ALIYUN-EMBEDDING.md)。

语言模型选择 Zhiyu 部署级 INTERACTION_PROCESSOR_LLM 配置，并沿用 qwen3.7-plus 的 OpenCode Go 端点迁移逻辑；没有读取用户数据库的模型中心配置。当前适配 Anthropic Messages 和 Chat Completions。阿里云向量使用OpenAI兼容接口，不传Jina专用字段；显式选择zhiyu向量配置时才恢复读取LLM_EMBEDDING_*及OPENAI_EMBEDDINGS_API_KEY。

可显式覆盖文本模型：

```powershell
$env:LEGAL_API_BASE = 'https://your-provider.example/v1'
$env:LEGAL_API_KEY = 'your-key'
$env:LEGAL_MODEL = 'your-model'
$env:LEGAL_PROTOCOL = 'openai_compatible'
python -X utf8 server.py --port 8765
```

密钥仅从服务端环境读取。传输错误区分超时、TLS、连接、非JSON及HTTP状态；临时故障在同一时间预算内有限重试。向量服务重试后仍暂不可用时，研究任务明确标记降级到本地BM25并保留原文分片；语言模型仍真实执行拆题、评估及引用验证。鉴权、证书、响应结构及索引错误不以降级掩盖；语言模型持续失败则任务终止。停止按钮提交取消标记，在当前请求结束后阻止后续调用，不能保证提供方立即终止当前推理。显式设置 LEGAL_RULE_DEMO=1 才使用旧版离线BM25与模板模式；它与真实模型研究的检索降级不同。

## 实现边界

- 拆题：模型输出独立争点和查询，覆盖检查对照原问题，避免漏答。
- 检索：阿里云text-embedding-v4语义向量的余弦排名与SQLite FTS5 BM25通过RRF融合，法条和案例分别召回；没有神经重排模型。
- 向量：完整正文按最多1800字符、重叠120字符分片，保留来源位置；SQLite 持久化，按服务、模型、维度、协议和内容哈希隔离。配置变化或资料更新后须运行 vectors.py，不接受过期索引。建库支持缓存与限流重试。
- 生成：先生成带逐字引文的结构化主张，再经过原文片段和模型支持性验证；仅发布通过检查的主张。
- 补检索：法律证据不足时自动定向检索、重新评估，最多两轮；检查失败可在预算内修订一次。
- 任务：后台研究、实时步骤记录、浏览器刷新恢复查看、停止后续调用；任务状态持久化。
- 数据：UTF-8 JSON 为可维护的数据源，SQLite 是持久化检索库；法条与案例分类型查询、分页展示，并在研究时分别召回。
- 未实现：实时联网研究、规范效力自动核验、账号权限、多用户历史列表。

这是一份新建的演示代码，不能用来证明原项目已实现同等能力。资料明细与来源见 [data/README.md](data/README.md)。

完整链路、预算、任务API和验证边界见 [RESEARCH-FLOW.md](RESEARCH-FLOW.md)。

当前新增案件材料工作台：可建立案件，上传 TXT/MD、DOCX、文字型 PDF，勾选本次研究材料并确认客户目标。电子材料以原文片段、页码或段落追溯；不同记载保留待核。合同交付争议新增处理方案比较和拒绝式全文一致性复核。扫描件仍需 OCR，材料未经鉴真；研究只选读有预算限制的片段。上传保存本地，开始研究时才将所选片段发送至配置的语言模型。自动检查通过也仅为待律师复核的初稿。详细范围、验证方法和回滚见 [v4 变更验收记录](runs/workbench-v4/CHANGE-AND-ACCEPTANCE.md)。

## 更新资料

```powershell
# 默认只使用已存档的两个官方页面重建法条，不访问网络。
python -X utf8 ingest.py
# 仅显式刷新来源时下载固定官方页面；不是研究阶段的联网搜索。
python -X utf8 ingest.py --refresh
# 新增六部法律及担保制度司法解释，默认使用存档；--refresh 才重新下载。
python -X utf8 collect_laws_extra.py
# 仅刷新担保解释，其他来源仍使用存档。
python -X utf8 collect_laws_extra.py --refresh --source guarantee-interpretation
# 以下是建库命令：缓存缺失时下载固定官网页面，--refresh 重新下载。
python -X utf8 collect_cases.py
python -X utf8 collect_case_status.py
# 只从已有 laws.json、laws-extra.json、cases.json 重建，不访问网络。
python -X utf8 corpus.py
python -X utf8 vectors.py
python -X utf8 audit_corpus.py
```

新增资料清单及独立数据库构建方式见扩库记录。直接修改资料后依次运行 corpus.py、vectors.py、audit_corpus.py。案例重新采集后需运行 collect_case_status.py 恢复公告标记。已明确不再参照的6件案例保留浏览，默认排除研究检索。指导案例45号已从山东法院官方转载补齐；全国裁判案例及全部规范仍有缺口，详见批量覆盖清单。不要对外部 JSON 直接建立信任；未开放不可信来源上传。

## 验证

法条与案例召回评测集、三种检索基线及离线重放方法见 [evaluation/README.md](evaluation/README.md)，扩库前报告见 [阿里云评测报告](evaluation/results-aliyun/report.md)，迁移效果见 [同题模型对比](evaluation/embedding-model-comparison.md)，[Jina历史报告](evaluation/results/report.md)单独保留。当前v2包含200条法条题、176条案例题和24条边界控制题，共400题，覆盖118条法条和100件案例。原80题及旧基线已冻结归档，新增320题另列统计；标注基于官方存档但未经独立法律专家穷尽复核。

```powershell
python -X utf8 -m unittest discover -s . -p 'test_*.py' -v
```
