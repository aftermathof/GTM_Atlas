# GTM Atlas Implementation Plan

**Goal:** 实现 plan.md V5.1 的本地可运行产品，生产架构为 Vue/VitePress + FastAPI + LangGraph + PostgreSQL/pgvector。

**Architecture:** 单仓单 API，learning/mock/career 独立状态图。业务状态与不可变版本落库；模型、STT、渲染独立 Provider。Vue 负责交互工作台，VitePress 构建同源知识手册。示例内容为本项目自写合成内容。

## Global constraints

- 原始 plan.md 保留。无既有 V4 工程，不声称继承。
- 视觉依据为 Documents/Codex/2026-10-22/new-chat-3/outputs/GTM同款前端设计Prompt.md。
- 私有操作必须登录并检查对象所有者；语音不得自动发送；改写必须事实确认和段落授权。
- 生产 PostgreSQL + pgvector；开发 SQLite 明确标注，不等同于生产验证。
- 外部 Provider 未配置必须明确报错或标注 mock；编译只允许隔离容器，不运行宿主机任意 TeX。

## M0 — 工程与门户

- [x] 建立 apps/web（Vue 工作台及 VitePress 手册）、services/api、packages、infra、tests。
- [x] 三入口、导航、岗位上下文、登录、历史、设置、全局 AI 抽屉。
- [x] VoiceInput 统一 MediaRecorder → STT → 草稿确认，取消和错误保留原文；真实服务待配置复测。
- 验证：前端生产构建、API 登录与跨用户访问测试；桌面/手机检查。

## M1 — 知识与问答

- [x] knowledge/ 自写示例、frontmatter 校验、按标题分块、SHA256 增量与删除传播。
- [x] packages/rag：许可优先，岗位筛选，词法与向量 RRF，证据包与真实引用校验（PG向量分支待环境验收）。
- [x] packages/learning：LangGraph resolver/retrieve/compose/validate，Provider 显式模式。
- 验证：不足证据、非法许可不入库/不传模型、删除撤销、引用回链；可复现 eval。

## M2 — 面经与 Mock

- [x] 固定种子、能力覆盖、3/5/10题、中英文、显式授权引用简历。
- [x] LangGraph 逐题评价/有界追问，数据库持久化、幂等提交、报告与历史。
- 验证：同种子题型一致、3维度覆盖、重复提交、重建服务恢复、跨用户隔离。

## M3 — 简历

- [x] PDF/图片上传、不可变原件、可选文字提取；扫描件经独立视觉服务，未配置清楚提示。
- [x] Resume IR 事实确认、解释性诊断、段落锁定、授权 patch 校验、不可变版本/回滚。
- [x] 三套受控 LaTeX 模板；隔离 Worker 编译、PDF QA、鉴权导出、异步任务实现。
- [ ] Docker隔离编译与真实中文PDF实机验收（当前Docker未运行）。
- 验证：只诊断不生成、未确认/未授权拒绝、锁定段不变、教育保留、版本回滚与下载权限。

## M4 — 工程与交付

- [x] Alembic、pgvector 初始化、Docker Compose、固定依赖、.env.formal、README。
- [x] tracing、限额、统一错误、数据删除、验收映射、开源/自研清单、OpenAPI。
- [x] 核心 pytest、类型与构建、浏览器验证；记录真实通过项及环境限制。
- [ ] 真实Provider、PG并发、STT准确率、专家标注数据集与生产强化；具体缺口见docs/ARCHITECTURE.md。

## Test-first workflow

核心安全/业务边界先写 tests/test_workflows.py 并执行观察失败，再实现模块并运行通过。
运行：`.venv/Scripts/python -m pytest -q`；前端：`npm run build`（类型检查 + Vue + VitePress）。
部署及第三方服务真实识别测试以环境能力为准，不能以 mock 测试代替。
