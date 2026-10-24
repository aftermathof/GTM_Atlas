# 文件夹与维护入口

## 要改什么，打开哪里

| 内容 | 文件或目录 | 作用 |
| --- | --- | --- |
| GTM 概览 | [../knowledge/site/gtm-overview/](../knowledge/site/gtm-overview/) | `index.html` 是首页，`chapter-01.html` 至 `chapter-04.html` 是正文；直接编辑 HTML |
| GTM 专有名词 | [../knowledge/glossary/gtm-glossary.json](../knowledge/glossary/gtm-glossary.json) | 词条、全称、解释和例子；网站与 AI 使用同一份数据 |
| 岗位 JD | [../knowledge/jobs/research-notes/](../knowledge/jobs/research-notes/) | 每个 Markdown 文件对应一个岗位 |
| 面经 | [../knowledge/interviews/research-notes/](../knowledge/interviews/research-notes/) | 每个 Markdown 文件对应一篇面经 |
| 在职经验 | [../knowledge/learning/research-notes/](../knowledge/learning/research-notes/) | 每个 Markdown 文件对应一篇经验资料 |
| 首页与导航、全局助手容器 | [../apps/web/src/App.vue](../apps/web/src/App.vue)、[../apps/web/src/pages/Home.vue](../apps/web/src/pages/Home.vue) | 导航、品牌、助手全屏与主页入口 |
| 知识目录与阅读页 | [../apps/web/src/pages/Learn.vue](../apps/web/src/pages/Learn.vue) | 目录和文章阅读 |
| 面经与 Mock | [../apps/web/src/pages/Interviews.vue](../apps/web/src/pages/Interviews.vue) | 设置、作答、复盘、问问 AI |
| 简历工作台 | [../apps/web/src/pages/Career.vue](../apps/web/src/pages/Career.vue) | 上传、事实校对、诊断、经历编辑与版本 |
| 多轮简历改写 | [../apps/web/src/components/BlockRewriteDialog.vue](../apps/web/src/components/BlockRewriteDialog.vue) | 单块经历的改写对话 |
| 历史、登录与偏好 | [../apps/web/src/pages/Utility.vue](../apps/web/src/pages/Utility.vue) | 我的空间与账号界面 |
| 聊天、语音输入 | [../apps/web/src/components/ChatPanel.vue](../apps/web/src/components/ChatPanel.vue)、[../apps/web/src/components/Composer.vue](../apps/web/src/components/Composer.vue) | 会话、上下文、输入与转写 |
| 颜色、字体、间距 | [../apps/web/src/tokens.css](../apps/web/src/tokens.css)、[../apps/web/src/style.css](../apps/web/src/style.css) | 全站样式；组件专有样式在对应 Vue 文件里 |
| API 请求与前端登录状态 | [../apps/web/src/state.ts](../apps/web/src/state.ts) | 请求、登录、列表缓存与共享状态 |
| API 接口 | [../services/api/](../services/api/) | `routes_career.py` 简历；`routes_mock.py` Mock；`routes_knowledge.py` 资料和问答 |
| 模型与 Agent | [../packages/agent_core/](../packages/agent_core/) | 模型适配、领域规则加载与状态检查点 |
| 知识索引与检索 | [../packages/rag/](../packages/rag/) | Markdown 与 HTML/JSON 入库、分块、检索 |
| 业务流程 | [../packages/career/](../packages/career/)、[../packages/mock/](../packages/mock/)、[../packages/learning/](../packages/learning/) | 简历、Mock、知识问答 |
| 简历模板与编译 | [../templates/latex/](../templates/latex/)、[../packages/document_renderer/](../packages/document_renderer/) | TeX 模板、排版、PDF 任务 |
| 部署与数据库 | [../infra/](../infra/)、[../supabase/](../supabase/) | Docker、隔离 Worker、迁移、初始化 SQL |

## 当前维护文档

- [项目介绍与运行方法](../README.md)：安装、环境配置、启动与部署入口。
- [内容格式与模板维护](CONTENT_GUIDE.md)：知识资料格式、GTM 概览、名词库、简历模板。
- [系统架构](ARCHITECTURE.md)：模块边界与技术结构。
- [部署指南](DEPLOYMENT.md)：Docker、Supabase、Vercel 和公网访问。
- [本机服务维护](LOCAL_OPERATIONS.md)：关闭、重启、更新 API、临时隧道与访问故障定位。
- [云服务器方案](CLOUD_HOSTING_PLAN.md)：后续服务器与固定域名方案。
- [功能验收](ACCEPTANCE.md)：功能检查清单；历史检查结果应重新验证。
- [采集技能](collector-skills/)：BOSS JD 与小红书研究资料采集；与根目录运行时 `skills/` 用途不同。

## 内容如何进入网站和 AI

`knowledge/site/` 是前端配置的静态页面源目录。Vite 在构建时把其内容原样复制到 `apps/web/dist/`，所以 HTML 的访问地址仍是 `/gtm-overview/`；不需要在前端再维护第二份副本。

`knowledge/glossary/gtm-glossary.json` 通过前端导出文件导入页面，后端也读取同一数据。`packages/rag/reference_sources.py` 从概览 HTML 和名词 JSON 提取知识内容；移动目录不改变文档 ID、网页地址和引用链接。

`apps/web/handbook/articles/`、手册索引和 `apps/web/dist/` 是自动生成的内容。正文修改回到 `knowledge/`，不要直接改生成结果。

内容维护后：前端发布重新运行 Vercel 构建；后端知识索引在 API 启动时增量检查。仅整理路径不需要重跑 SQL。

## 历史资料放在哪里

- `archive/plans/`：开发实施计划、模板接入计划、早期部署计划。
- `archive/DEPLOYMENT_CHECKS_2026-10-23.md`：当天的部署检查快照，不能代表当前在线状态。
- `archive/import-reports/`：概览原始文件哈希与研究笔记导入来源记录。

归档文件保留当时的数字、路径和待办，查询开发历史时才阅读；运行与维护以当前文档为入口。

已移除的生成快照：过时的 `openapi.json`、手工上传清单和旧缓存清理报告。当前 API 结构看运行中的 `/docs` 或 `/openapi.json`；Git 提交范围看 `git status --short`、`git ls-files`，无需维护第二份清单。

## 本地数据不要当作废文件删除

`.env` 是私有配置，`.data/` 可能包含上传原件、生成版本与运行数据库；Docker 数据卷也可能保存私有文件。`.venv/`、`node_modules/` 是本机依赖。它们不提交 Git，但不属于本次可以随意删除的内容。

本机 `.data/README.md` 说明数据用途；散落的开发产物已分类放入 `.data/development-archive/`，移动清单记录 SHA256。归档脚本保留旧路径，仅供历史追溯。数据库、上传目录、原始采集证据、测试配置使用的数据路径及隧道日志保留原位。
