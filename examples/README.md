# examples

放**脱敏**的可公开样例（用于文档/演示）。真实简历跑出的产物写到 `workspace/output/`（已忽略、不入库，含个人隐私）。

## agent_engineer_demo

一份完全脱敏的示例简历（虚构「张三」，某 Agent / AI Infra 岗，2 年经验，无任何联系方式）跑完整流水线的真实产物：

- `agent_engineer_demo_guide.md` — 完整指南（画像、真实强项、关键红旗、开场题、6 道核心验伪题含答案键、补充探针）。
- `agent_engineer_demo_scorecard.html` — 现场评分卡（一页 A4，浏览器打开或打印）。
- `agent_engineer_demo_qa_cards.html` — 攻防卡片（答案可折叠自测，浏览器打开）。
- `agent_engineer_demo_payload.json` — 分析载荷（可据此复现三件套）。

复现三件套（改 `payload.json` 内容后同样可重渲）：
```
python scripts/render.py examples/agent_engineer_demo/agent_engineer_demo_payload.json examples/agent_engineer_demo agent_engineer_demo
```

要新增一份可分享样例：拿一份虚构简历文本跑流水线，或把真实产物里的姓名/公司/联系方式等替换为占位符后再放这里。
