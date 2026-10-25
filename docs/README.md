# 文件夹与维护入口

## 根目录怎么分

| 路径 | 保存内容 |
| --- | --- |
| `apps/web/` | Vue 前端、前端测试脚本与构建配置 |
| `services/api/` | FastAPI 接口、账号、数据存储与业务路由 |
| `packages/` | AI、RAG、Mock、简历处理和 PDF 排版逻辑 |
| `knowledge/` | 网站与 AI 使用的 JD、面经、在职经验、概览和术语资料 |
| `profiles/`、`skills/` | 岗位配置、评分标准与运行时 Skill |
| `templates/` | 简历 TeX 原件与模板 |
| `infra/`、`supabase/` | Docker、PDF Worker、数据库迁移与 SQL |
| `scripts/`、`tests/` | 本地启动、资料校验与自动化回归测试 |
| `docs/` | 维护指南；旧截图与来源记录放在 `archive/` |
| `.data/` | 本机业务数据、上传、隧道日志和维护记录；不提交 Git |
| `.venv/`、`apps/web/node_modules/` | 已安装的 Python / 前端依赖；保留供本机使用 |

根目录保留项目入口、依赖清单、环境配置及部署配置，维持现有构建与 Docker 路径。

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
| 学习笔记 | [../apps/web/src/pages/Notes.vue](../apps/web/src/pages/Notes.vue)、[../apps/web/src/components/NoteEditor.vue](../apps/web/src/components/NoteEditor.vue) | 笔记卡片、标题与 Markdown 编辑器 |
| 删除确认弹窗 | [../apps/web/src/components/ConfirmDelete.vue](../apps/web/src/components/ConfirmDelete.vue) | 历史记录和聊天共用的站内删除确认 |
| 颜色、字体、间距 | [../apps/web/src/tokens.css](../apps/web/src/tokens.css)、[../apps/web/src/style.css](../apps/web/src/style.css) | 全站样式；组件专有样式在对应 Vue 文件里 |
| API 请求与前端登录状态 | [../apps/web/src/state.ts](../apps/web/src/state.ts) | 请求、登录、列表缓存与共享状态 |
| API 接口 | [../services/api/](../services/api/) | `routes_career.py` 简历；`routes_mock.py` Mock；`routes_knowledge.py` 资料和问答 |
| 模型与 Agent | [../packages/agent_core/](../packages/agent_core/) | 模型适配、领域规则加载与状态检查点 |
| 知识索引与检索 | [../packages/rag/](../packages/rag/) | Markdown 与 HTML/JSON 入库、分块、检索 |
| 业务流程 | [../packages/career/](../packages/career/)、[../packages/mock/](../packages/mock/)、[../packages/learning/](../packages/learning/) | 简历、Mock、知识问答 |
| 简历照片与分块 | [../packages/career/photo.py](../packages/career/photo.py)、[../services/api/resume_blocks.py](../services/api/resume_blocks.py) | 照片保留、完整经历与空白编辑块 |
| 模板字段与字体 | [../packages/document_renderer/layout.py](../packages/document_renderer/layout.py)、[../infra/renderer-fonts/](../infra/renderer-fonts/) | 标题、经历抬头、正文和技能分项；真实图标与许可证 |
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

## 资料来源记录

`screenshots/` 保留近期界面效果图；旧版笔记界面截图已归到 [archive/screenshots/](archive/screenshots/)，保留文件原名供历史对照。

`archive/import-reports/` 保留概览原始文件哈希与研究笔记导入记录，用于核对资料来源。已完成的开发计划、过期部署快照和一次性调试归档已清理；当前维护以本页列出的文档为入口。

当前 API 结构看运行中的 `/docs` 或 `/openapi.json`；Git 变更看 `git status --short`，无需另存手工清单。

## 本地数据不要当作废文件删除

`.env` 是私有配置，`.data/` 可能包含上传原件、生成版本与运行数据库；Docker 数据卷也可能保存私有文件。`.venv/`、`node_modules/` 是本机依赖。它们不提交 Git，但不属于本次可以随意删除的内容。

本机 `.data/README.md` 说明数据用途；`.data/maintenance/` 保存清理记录与文件完整性校验。数据库、上传目录、采集原始证据及隧道日志保留原位。

2026-10-26 整理时清除了独立验收脚本、验收数据库、测试临时目录和 Python 缓存。Docker 临时补丁保存在 `.data/maintenance/docker-hotfixes/`，正式部署文件仍在 `infra/`。现有前端 `dist/` 保留，供本机预览；此轮整理没有重建或重启服务。

## 可以重新生成的文件

前端 `dist/`、`handbook/articles/`、`handbook/.generated.json`、VitePress 缓存，后端 `__pycache__/`、`.pytest_cache/` 和 `.data/pytest-*` 都是生成产物。清理后运行构建或测试即可重建；不必在主目录长期堆积多轮输出。

`.data/maintenance/` 保存本机清理清单与保护文件的哈希校验，随 `.data/` 一起被 Git 忽略。正式业务源码、字体支持文件、采集证据、依赖环境和用户上传不属于缓存。
