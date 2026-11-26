# 增补法律原文来源与核验边界

本文件由 collect_laws_extra.py 根据本地存档生成。默认运行仅离线读取；显式 --refresh 才采集。

独立解析沿用 ingest.py 的 HTML 块级换行及中文条号思路，避免导入其数据库依赖。严格检查条号从1至末条连续、无重复、无乱序；删除章节目标题及末条之后的页脚，保留各款项。原始HTTP响应字节不改写，source_sha256覆盖原始字节；text_sha256覆盖规范化条文UTF-8字节。

published_at 表示本次版本法律公布日期，不采用网页转载日期。date 表示本次版本施行日期，不确定即null；末条保留的最初施行日不能直接当成修正版本施行日。网页时间另见各来源记录。

仅证明存档所载版本及结构完整，不证明采集日或研究日仍为最新现行法；当前效力、后续修法、过渡安排及个案时间适用待核验。研究阶段不联网，不调用向量模型，不写SQLite或现有laws.json。

## 中华人民共和国劳动合同法（2012年修正）

- 官方来源：[https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_0abfdd261c03417b949df19d869add8d.html](https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_0abfdd261c03417b949df19d869add8d.html)
- 公布日期：2012-12-28；版本施行日期：null。末条为原法施行日2008-01-01；本次未存档修正决定的施行条款，版本施行日期置null。
- 网页可见发布时间：2021-06-10 09:10；CMS PubDate：2025-07-23 16:17（可能为迁移/更新，与法律公布日期无关）。
- 条数：98；编号：E20001—E20098。
- 采集时间（UTC）：2026-11-12T06:24:56.419380+00:00；解码：utf-8。
- 存档：`data/raw/extra-labor-contract.html`；原文SHA256：`dae82a50c21a2091069a62dd64f9da0423175b3d92599c89bf9fff0e24f3a8ce`。
- 末条截断锚点：本法自2008年1月1日起施行。

## 中华人民共和国劳动法（2018年第二次修正）

- 官方来源：[https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_d9aa750028b14b99a776cb93726a360d.html](https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_d9aa750028b14b99a776cb93726a360d.html)
- 公布日期：2018-12-29；版本施行日期：null。末条为原法施行日1995-01-01；本次未存档修正决定的施行条款，版本施行日期置null。
- 网页可见发布时间：2021-06-10 10:52；CMS PubDate：2025-07-23 16:26（可能为迁移/更新，与法律公布日期无关）。
- 条数：107；编号：E21001—E21107。
- 采集时间（UTC）：2026-11-12T06:24:56.779738+00:00；解码：utf-8。
- 存档：`data/raw/extra-labor.html`；原文SHA256：`3ed4356995368f5d3fd41b0dff3c415e159f3486b3b432d51cd1ed049f95a4df`。
- 末条截断锚点：本法自1995年1月1日起施行。

## 中华人民共和国公司法（2023年第二次修订）

- 官方来源：[https://www.samr.gov.cn/xyjgs/flfg/art/2024/art_d4e84936a8a744f8928ac7aec7594345.html](https://www.samr.gov.cn/xyjgs/flfg/art/2024/art_d4e84936a8a744f8928ac7aec7594345.html)
- 公布日期：2023-12-29；版本施行日期：2024-07-01。版本施行日期依据第二百六十六条，保留其第二款过渡规定。
- 网页可见发布时间：2024-03-25 16:01；CMS PubDate：2024-05-07 11:19（可能为迁移/更新，与法律公布日期无关）。
- 条数：266；编号：E22001—E22266。
- 采集时间（UTC）：2026-11-12T06:24:57.178269+00:00；解码：utf-8。
- 存档：`data/raw/extra-company.html`；原文SHA256：`508c097b6467c1b851292a4ab096e683f558a7f844d839b1317c97f06e50daf3`。
- 末条截断锚点：具体实施办法由国务院规定。

## 中华人民共和国消费者权益保护法（2013年第二次修正）

- 官方来源：[https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/art_0a323e046fba43f0b6e9e977f1e8d5fc.html](https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/art_0a323e046fba43f0b6e9e977f1e8d5fc.html)
- 公布日期：2013-10-25；版本施行日期：null。末条为原法施行日1994-01-01；本次未存档修正决定的施行条款，版本施行日期置null。
- 网页可见发布时间：2019-06-25 02:15；CMS PubDate：2025-07-23 15:19（可能为迁移/更新，与法律公布日期无关）。
- 条数：63；编号：E23001—E23063。
- 采集时间（UTC）：2026-11-12T06:24:57.737342+00:00；解码：utf-8。
- 存档：`data/raw/extra-consumer.html`；原文SHA256：`ef2b03e7e9460dffa97d05977f69ba294b1bdcd56d1a9064e858a5abc8b17556`。
- 末条截断锚点：本法自1994年1月1日起施行。

## 中华人民共和国民事诉讼法（2023年第五次修正）

- 官方来源：[https://ipc.court.gov.cn/zh-cn/news/view-6231.html](https://ipc.court.gov.cn/zh-cn/news/view-6231.html)
- 公布日期：2023-09-01；版本施行日期：null。末条为原法施行条款；本次未存档修正决定的施行条款，版本施行日期置null。第144、275条条号后无空格，原样保留。
- 网页可见发布时间：2026-11-03 15:45:02；CMS PubDate：null（可能为迁移/更新，与法律公布日期无关）。
- 条数：306；编号：E24001—E24306。
- 采集时间（UTC）：2026-11-12T06:24:58.986109+00:00；解码：utf-8。
- 存档：`data/raw/extra-civil-procedure.html`；原文SHA256：`128593d12db41e996d6c84af239830f7693f438dfb71542ae366af84bcde7e09`。
- 末条截断锚点：《中华人民共和国民事诉讼法（试行）》同时废止。

## 中华人民共和国个人信息保护法（2021年通过文本）

- 官方来源：[https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm](https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm)
- 公布日期：2021-08-20；版本施行日期：2021-11-01。施行日期依据第七十四条。
- 网页可见发布时间：2021年08月20日 21:21；CMS PubDate：null（可能为迁移/更新，与法律公布日期无关）。
- 条数：74；编号：E25001—E25074。
- 采集时间（UTC）：2026-11-12T06:24:59.172085+00:00；解码：utf-8。
- 存档：`data/raw/extra-personal-information.html`；原文SHA256：`50b62bb9868648fe0417d8757a8cff62641eba6d879403f363d771f8c6d3acff`。
- 末条截断锚点：本法自2021年11月1日起施行。

## 最高人民法院关于适用《中华人民共和国民法典》有关担保制度的解释（法释〔2020〕28号）

- 官方来源：[https://www.court.gov.cn/zixun/xiangqing/282721.html](https://www.court.gov.cn/zixun/xiangqing/282721.html)
- 公布日期：2020-12-31；版本施行日期：2021-01-01。公布日期依据官方落款；施行日期依据第七十一条。
- 网页可见发布时间：2020-12-31 21:13:53；CMS PubDate：null（可能为迁移/更新，与法律公布日期无关）。
- 条数：71；编号：E26001—E26071。
- 采集时间（UTC）：2026-11-12T07:38:41.437809+00:00；解码：utf-8。
- 存档：`data/raw/extra-guarantee-interpretation.html`；原文SHA256：`5e8c275fcf50bc3cec155f872036b9ef582578d35cb9c1e39adcaacc3ef7d323`。
- 末条截断锚点：本解释自2021年1月1日起施行。
