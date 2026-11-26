from pathlib import Path
root=Path(__file__).parent/'runs/report-v3'
text=(root/'reviewed-report.md').read_text(encoding='utf-8')
intro='# 实跑输出：待修订稿\n\n通知专节与材料台账已补齐，但复读仍发现摘要遗漏确认条件、未知事实被先行认定及引用支持不足等问题。自动流程complete不等于专业审核合格。\n\n请先看[具体复读记录](manual-review.md)。下列内容为本轮模型原始输出，保留原文便于检查，不作事实已查明或法律意见已定稿的表示。\n\n---\n\n'
(root/'report-with-review-notes.md').write_text(intro+text,encoding='utf-8')
