# 阿里云向量模型配置与迁移

选择阿里云百炼 `text-embedding-v4`，通过OpenAI兼容接口输出1024维稠密向量。本项目沿用Zhiyu中已有的阿里云接入依据，凭证只读加载 `D:/zhiyu/apps/web` 环境配置中的 `DASHSCOPE_API_KEY`，缺失时才查看 `BAILIAN_API_KEY`；不会把原Jina的 `OPENAI_EMBEDDINGS_API_KEY` 发给阿里云。

[阿里云官方兼容接口文档](https://www.alibabacloud.com/help/en/model-studio/embedding-interfaces-compatible-with-openai)说明支持此模型、1024维及每批最多10条；本项目保持每批8条。北京地域现有 `dashscope.aliyuncs.com` 域名仍可使用，本机已用现有凭证完成真实请求。若以后迁到工作空间专用域名，应重新验证配置和索引身份。

## 持久配置

`model-settings.json`仅保存非敏感模型选择：

```json
{
  "embedding": {
    "provider": "aliyun",
    "model": "text-embedding-v4",
    "dimensions": 1024,
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
  }
}
```

代码从Zhiyu读取真实密钥，配置文件不包含密钥。语言模型继续使用原部署配置，不因向量模型迁移改变。`LEGAL_EMBEDDING_PROVIDER` 可作为单进程覆盖；阿里云配置还支持 `LEGAL_EMBEDDING_MODEL`、`LEGAL_EMBEDDING_DIMENSIONS`、`LEGAL_EMBEDDING_BASE_URL` 覆盖。

## 索引与验证

两个模型虽同为1024维，却是不同向量空间。文档向量以端点、模型、维度和协议组成的身份隔离，原Jina记录保留，新模型完整重建全部2911个正文分片。先用进程覆盖构建新索引，再写入持久选择并在无活动研究时重启服务。

```powershell
$env:LEGAL_EMBEDDING_PROVIDER = 'aliyun'
python -X utf8 probe_models.py
python -X utf8 vectors.py
python -X utf8 check_retrieval.py
```

网页“当前向量”显示当前模型、维度与索引就绪状态；/api/health可读取相同公开信息，不返回密钥。过期或缺失的索引不能与新查询向量混用。临时服务故障的有界重试与显式BM25降级继续生效，鉴权、证书及索引错误仍直接报错。

## 同题评测

新模型的查询向量也必须重新生成。评测缓存按模型身份隔离；默认结果目录已有其他模型基线时会在请求API前拒绝覆盖，需指定独立输出目录：

```powershell
python -X utf8 evaluation/evaluate.py --embed-missing --output evaluation/results-aliyun
python -X utf8 evaluation/compare_embedding_models.py
```

原Jina基线保留在 `evaluation/results/`，阿里云基线在 `evaluation/results-aliyun/`，同题对比在 `evaluation/embedding-model-comparison.md`。两次使用相同400题和语料快照；核对BM25的400题候选及指标一致，以排除更改数据或关键词排序造成的混淆。原v1/v2的同模型精确重放校验器不应拿来判定跨模型排名必须相同。

若需临时重现原模型基线，可在单独进程中设置 `LEGAL_EMBEDDING_PROVIDER=zhiyu`，它恢复读取Zhiyu现有向量配置（本次迁移时为Jina）。修改持久配置后须确认对应索引完整，并在无活动研究时重启；不要通过复制同维度向量伪造重建完成。

模型更换不改变官方原文、条文版本、案例停止参照过滤或事实/引用验证。召回指标不等于法律回答正确率，单次验证也不代表长期网络稳定性。

## 本次验证结果

2026-11-12，2592件资料的2911个分片已全部重新生成阿里云向量，服务健康检查显示索引就绪。82项自动测试通过，劳动赔偿、违约金两组真实检索的引用片段与原文一致，桌面页面模型标识及索引状态检查通过。

400题同题对比完成，BM25候选及指标全部一致。法条混合检索已标注Recall@4由91.42%升至93.00%，MRR由0.8408降至0.8338；案例混合检索文档Recall@2保持100%，锚点Recall@2由63.64%降至63.07%。提升和下降均保留在报告中。本次验证涵盖向量API、索引、检索和界面，未重新执行完整语言模型研究流程。
