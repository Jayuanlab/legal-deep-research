# 2026-11-12 官方法条与案例扩库

法条2314 → 2782（+468）；案例278 → 319（+41），合计3101件资料。阿里云text-embedding-v4、1024维；2911个旧分片复用，新增510个分片，合计3421个。

## 新增司法解释

| 来源发布版本 | 条数 | 施行日期 | 官方原文 |
| --- | ---: | --- | --- |
| 最高人民法院关于审理劳动争议案件适用法律问题的解释（一）（法释〔2020〕26号） | 54 | 2021-01-01 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/282121.html) |
| 最高人民法院关于审理劳动争议案件适用法律问题的解释（二）（法释〔2025〕12号） | 21 | 2025-09-01 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/472691.html) |
| 最高人民法院关于民事诉讼证据的若干规定（2019年修正（法释〔2019〕19号）） | 100 | 2020-05-01 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/212721.html) |
| 最高人民法院关于审理民间借贷案件适用法律若干问题的规定（2020年第二次修正（法释〔2020〕17号）） | 31 | 2021-01-01 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/282621.html) |
| 最高人民法院关于审理买卖合同纠纷案件适用法律问题的解释（2020年修正（法释〔2020〕17号）） | 33 | 2021-01-01 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/282621.html) |
| 最高人民法院关于适用《中华人民共和国民法典》侵权责任编的解释（一）（法释〔2024〕12号） | 26 | 2024-09-27 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/443891.html) |
| 最高人民法院关于审理使用人脸识别技术处理个人信息相关民事案件适用法律若干问题的规定（法释〔2021〕15号） | 16 | 2021-08-01 | [官方原文](https://www.court.gov.cn/fabu/xiangqing/315851.html) |
| 最高人民法院关于适用《中华人民共和国民法典》婚姻家庭编的解释（二）（法释〔2025〕1号） | 23 | 2025-02-01 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/452771.html) |
| 最高人民法院关于适用《中华人民共和国民法典》婚姻家庭编的解释（一）（法释〔2020〕22号） | 91 | 2021-01-01 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/282071.html) |
| 最高人民法院关于审理建设工程施工合同纠纷案件适用法律问题的解释（一）（法释〔2020〕25号） | 45 | 2021-01-01 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/282111.html) |
| 最高人民法院关于适用《中华人民共和国民法典》时间效力的若干规定（法释〔2020〕15号） | 28 | 2021-01-01 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/282051.html) |

## 新增典型案例

| 批次 | 件数 | 官方原文 |
| --- | ---: | --- |
| labor-cases / 劳动争议 | 6 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/472681.html) |
| contract-cases / 合同 | 10 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/419392.html) |
| consumer-2023 / 消费者权益 | 10 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/393481.html) |
| consumer-2025 / 消费者权益 | 5 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/467931.html) |
| platform-2026 / 平台经营 | 5 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/507691.html) |
| privacy-cases / 个人信息保护（刑事） | 5 | [官方原文](https://www.court.gov.cn/zixun/xiangqing/499271.html) |

## 存档与适用边界

laws-expansion.json逐条保存司法解释原文；cases-extra.json逐案保存最高法院典型案例发布正文，目录与导语不作为案例正文。每件均保留来源URL、原始响应哈希、正文哈希；典型案例额外保存原文字符位置及原栏目分节，不编造案号、法院或判决结果。它们不等同指导案例，亦非原始判决全文。原278件指导案例未改动，缺45号的范围说明继续保留。

解释（二）第二十一条明示解释（一）第三十二条第一款自2025-09-01废止。E27032保留完整历史条文及部分废止说明，为防止混用而保守排除整条研究检索，不宣称整条均被废止。其余款如需适用须单独核验。六件停止参照指导案例仍然过滤。未对全部规范完成截至今日的效力清理。

人脸识别规定的公布日期在本次选定原文中未核实，published_at保留null；施行日期依据第十六条。各规范末条后的时间适用款项完整保留，修订决定与重新公布全文按规范标题边界分离，避免跨文件拼接。

## 构建与验证

inspect_expansion_sources.py默认只检查本地存档，--refresh才下载官网；collect_expansion.py始终离线解析。stage_expansion.py先备份旧数据库至legal-next.sqlite3、保存扩库前评测及资料快照，再构建索引；重复执行会拒绝覆盖既有快照。verify_staged_expansion.py逐项确认原资料未变、重新核对400题原文锚点并执行测试。publish_expansion.py在服务停止且无活动研究时复制最新研究记录并切换数据库。

本轮85项测试通过；audit_corpus.py检查来源、原文哈希、唯一编号及民法典完整性，无问题。真实查询向量的小样本诊断16/16命中预期来源，见 [检索检查结果](../evaluation/expansion-smoke.json)，原文片段逐一与本地来源核对。该诊断不等于法律回答正确率，也不替代扩库后的完整400题重评。

新库已切换至工作台，12条既有研究任务记录全部保留。桌面浏览检查通过：实时数量、阿里云索引就绪、典型案例区别标识、部分废止条文提示均正常；没有提交额外语言模型研究任务。旧库保存在legal-before-expansion.sqlite3。

## 原始来源记录

- labor-i：`data/raw/expansion-labor-i.html`；SHA256 `c6fc220940b232e365a4abd5458769e5dd38a40445b5057cf54724d7e6abf420`；采集UTC 2026-11-12T15:02:10.922767+00:00。
- labor-ii：`data/raw/expansion-labor-ii.html`；SHA256 `adebfb788510a17b75972367fd6ceee055215ab75151f3fdd1ab5ffc70ff87c4`；采集UTC 2026-11-12T15:02:10.825128+00:00。
- evidence：`data/raw/expansion-evidence.html`；SHA256 `15bb756cd88f51ccb63cb0ea3dab3aad43671ad6c36a46e3d0eda60569708e78`；采集UTC 2026-11-12T15:02:35.653355+00:00。
- lending：`data/raw/expansion-lending.html`；SHA256 `5b29f0fa9f83cc17dedfe48001a669dd898939cd4295a0eb4242f0c16eabfe0f`；采集UTC 2026-11-12T15:02:36.363212+00:00。
- sale：`data/raw/expansion-sale.html`；SHA256 `5b29f0fa9f83cc17dedfe48001a669dd898939cd4295a0eb4242f0c16eabfe0f`；采集UTC 2026-11-12T15:02:36.102054+00:00。
- tort-i：`data/raw/expansion-tort-i.html`；SHA256 `064cab50a30ecc619ceb75c3b29f0ea0332ee9ec833ead1316781b8ddf16b74c`；采集UTC 2026-11-12T15:02:11.362031+00:00。
- face：`data/raw/expansion-face.html`；SHA256 `e526fa0726152dffabf9911b81895635cba1e123ff687f7e94f5bc99c2e87c02`；采集UTC 2026-11-12T15:02:36.177043+00:00。
- family-ii：`data/raw/expansion-family-ii.html`；SHA256 `30ede477bfa49bf55f6180c43a5c3ab0c3731192e356f285aba94c58a1ca9dc9`；采集UTC 2026-11-12T15:02:36.738233+00:00。
- family-i：`data/raw/expansion-family-i.html`；SHA256 `882e8f1db4399967b76e57cb574270fceab98ec55cbbd9594c05c49b64e6642e`；采集UTC 2026-11-12T15:03:47.110113+00:00。
- construction：`data/raw/expansion-construction.html`；SHA256 `5ae1726e6d67a28dbf1e49325b9a976a6afc9bcf8132e877adcd044273e73903`；采集UTC 2026-11-12T15:03:47.253823+00:00。
- time-effect：`data/raw/expansion-time-effect.html`；SHA256 `49375d8246ded41c15388380650c7151e4c2935e6f20f5a8d212de11badc03a0`；采集UTC 2026-11-12T15:03:47.150746+00:00。
- labor-cases：`data/raw/expansion-labor-cases.html`；SHA256 `211143f843da7c94179d3cb262a9bfea4be8cbe05259b04d8fc3980614282596`；采集UTC 2026-11-12T15:02:36.708159+00:00。
- contract-cases：`data/raw/expansion-contract-cases.html`；SHA256 `e72b16c68dbe62dc085e6fd02db8742ae641a5c4f65aba964eb1fa326c3574bb`；采集UTC 2026-11-12T15:02:36.963398+00:00。
- consumer-2023：`data/raw/expansion-consumer-2023.html`；SHA256 `179f52c670ef8c7a41f3b7b05f42a2d29759c16988a3251ba7fc91708995470d`；采集UTC 2026-11-12T15:02:37.461449+00:00。
- consumer-2025：`data/raw/expansion-consumer-2025.html`；SHA256 `460f009151eae68dca190154158d1b843bc31490a5fce8997863ae4a4b4657cd`；采集UTC 2026-11-12T15:02:37.179567+00:00。
- platform-2026：`data/raw/expansion-platform-2026.html`；SHA256 `c9e33cdefb7a41e0b563fc682ba4e08153828d7573f25664e6456301301d19fa`；采集UTC 2026-11-12T15:02:37.489054+00:00。
- privacy-cases：`data/raw/expansion-privacy-cases.html`；SHA256 `60dddd165d744b32db835685e92ef33dec2d8a792d447c278ffec01c3e1fc49e`；采集UTC 2026-11-12T15:02:37.713104+00:00。
