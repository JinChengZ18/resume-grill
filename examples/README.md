# examples

放**脱敏**的可公开样例（用于文档/演示）。真实简历跑出的产物写到 `workspace/output/`（已忽略、不入库，含个人隐私）。

## agent_engineer_demo

一份完全脱敏的示例简历（虚构「张三」，某 Agent / AI Infra 岗，2 年经验，无任何联系方式）跑完整流水线的真实产物：

- `agent_engineer_demo_kit_A.html` — 面试官手册（面试前速览；面试中逐题提问，要听的点和折叠的示范回答紧跟在题下；面试后按维度打分并生成面评草稿）。这份载荷是旧格式，手册里的要听的点和评分维度由渲染器从判分提示自动生成。
- `agent_engineer_demo_index.html` — 总入口，列出下面所有页面。
- `agent_engineer_demo_guide.md` — 纯文本存档（画像、强项、待确认事项、开场题、核心主题与示范回答）。
- `agent_engineer_demo_weakness.html`、`agent_engineer_demo_resume.html`、`agent_engineer_demo_jd.html` — 弱点分析、简历优化与 JD 匹配（JD 为演示编写；简历里没有的事实保留为占位符）。
- `agent_engineer_demo_payload.json` — 分析载荷（可据此复现全部页面）。

复现全部页面（改 `payload.json` 内容后同样可重渲）：
```
python scripts/render.py examples/agent_engineer_demo/agent_engineer_demo_payload.json examples/agent_engineer_demo agent_engineer_demo
```

要新增一份可分享样例：拿一份虚构简历文本跑流水线，或把真实产物里的姓名/公司/联系方式等替换为占位符后再放这里。
