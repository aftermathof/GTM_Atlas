# 文件夹与维护入口

本页按当前源码组织维护入口；项目介绍、运行命令与功能说明见 [根 README](../README.md)。

## 顶层分工

| 目录 | 保存内容 |
| --- | --- |
| `apps/web/` | Vue 页面、前端业务辅助模块、前端测试与手册构建 |
| `services/api/` | FastAPI 路由、鉴权、数据模型和存储 |
| `packages/` | AI、检索、Mock、简历和 PDF 的业务实现 |
| `knowledge/` | 公共知识 Markdown、术语 JSON、静态学习页面与公开图片 |
| `profiles/`、`skills/` | 运行时岗位／行业配置、评分标准和领域提示规则 |
| `templates/latex/` | 简历原始 TeX 和可填充模板 |
| `infra/`、`supabase/` | Docker、Worker、字体、代理、数据库迁移和 SQL |
| `scripts/`、`tests/` | 本地启动、知识校验、后端回归与评测 |
| `docs/` | 当前维护指南、采集技能、整理说明和历史材料 |
| `.data/` | 本机业务数据、采集证据、隧道日志与维护记录；不提交 Git |
| `.venv/`、`apps/web/node_modules/` | 本机依赖环境 |

根目录保留入口、依赖与部署配置。后端和知识库已按功能分类，不为目录外观改变运行路径。

## 修改入口

| 功能 | 路径 |
| --- | --- |
| 页面路由、导航与全局助手容器 | [main.ts](../apps/web/src/main.ts)、[App.vue](../apps/web/src/App.vue) |
| AI 引用与文本 | [features/ai/](../apps/web/src/features/ai/)、[ChatPanel.vue](../apps/web/src/components/ChatPanel.vue)、[Markdown.vue](../apps/web/src/components/Markdown.vue) |
| 账号与登录 | [features/auth/](../apps/web/src/features/auth/)、[Utility.vue](../apps/web/src/pages/Utility.vue)、[EmailConfirmed.vue](../apps/web/src/pages/EmailConfirmed.vue) |
| 资料卡片、博主合集、分页与预加载 | [features/knowledge/](../apps/web/src/features/knowledge/)、[ResourceGallery.vue](../apps/web/src/components/ResourceGallery.vue) |
| 知识正文阅读和管理 | [Learn.vue](../apps/web/src/pages/Learn.vue)、[KnowledgeEditor.vue](../apps/web/src/components/KnowledgeEditor.vue)、[routes_knowledge_management.py](../services/api/routes_knowledge_management.py) |
| 面经、岗位 JD 与 Mock | [Interviews.vue](../apps/web/src/pages/Interviews.vue)、[packages/mock/](../packages/mock/)、[routes_mock.py](../services/api/routes_mock.py) |
| 简历文本、页面与改写 | [features/career/](../apps/web/src/features/career/)、[Career.vue](../apps/web/src/pages/Career.vue)、[BlockRewriteDialog.vue](../apps/web/src/components/BlockRewriteDialog.vue)、[packages/career/](../packages/career/) |
| 笔记文件夹、编号、缓存与编辑 | [features/notes/](../apps/web/src/features/notes/)、[Notes.vue](../apps/web/src/pages/Notes.vue)、[NoteEditor.vue](../apps/web/src/components/NoteEditor.vue)、[routes_notes.py](../services/api/routes_notes.py) |
| 私有笔记检索 | [packages/rag/notes.py](../packages/rag/notes.py) |
| API、会话与共享缓存 | [state.ts](../apps/web/src/state.ts)、[preload.ts](../apps/web/src/preload.ts) |
| 语音输入与共享确认弹窗 | [Composer.vue](../apps/web/src/components/Composer.vue)、[ConfirmDelete.vue](../apps/web/src/components/ConfirmDelete.vue) |
| 全站颜色与排版 | [tokens.css](../apps/web/src/tokens.css)、[style.css](../apps/web/src/style.css) |
| 模型服务与规则注册 | [packages/agent_core/](../packages/agent_core/) |
| 公共索引与参考资料 | [packages/rag/](../packages/rag/)、[routes_knowledge.py](../services/api/routes_knowledge.py) |
| 简历模板、照片与 PDF | [templates/latex/](../templates/latex/)、[packages/document_renderer/](../packages/document_renderer/)、[photo.py](../packages/career/photo.py) |
| Docker、字体与数据库 | [infra/](../infra/)、[supabase/](../supabase/) |
| 前端测试与生成脚本 | [apps/web/tests/](../apps/web/tests/)、[apps/web/scripts/](../apps/web/scripts/) |
| 后端测试、夹具与检索评测 | [tests/](../tests/) |

## 知识的唯一来源

| 内容 | 目录 |
| --- | --- |
| GTM 概览 | [knowledge/site/gtm-overview/](../knowledge/site/gtm-overview/) |
| GTM 专有名词 | [gtm-glossary.json](../knowledge/glossary/gtm-glossary.json) |
| 岗位 JD、面经、在职经验 | [jobs/](../knowledge/jobs/)、[interviews/](../knowledge/interviews/)、[learning/](../knowledge/learning/) |
| 《爆品操盘GTM》 | [knowledge/site/gtm-book/](../knowledge/site/gtm-book/) |
| SOP 与操盘手册 | [knowledge/site/gtm-sop/](../knowledge/site/gtm-sop/) |
| 博主研究资料配图 | [knowledge/site/xhs-author-assets/](../knowledge/site/xhs-author-assets/) |

`knowledge/site/` 是 Vite 的静态资料源；构建复制到 `apps/web/dist/`，网页仍使用 `/gtm-overview/`、`/gtm-book/` 和 `/gtm-sop/` 等地址。`src/content/` 只提供引用入口，不维护正文副本。

`apps/web/handbook/articles/`、手册索引和 `.generated.json` 由 `scripts/handbook.mjs` 生成。修改知识源后重新构建前端与 API，保持静态页面和检索一致。

## 当前文档

- [系统架构](ARCHITECTURE.md)：模块、数据流与实现边界。
- [部署指南](DEPLOYMENT.md)：环境变量、Supabase、Docker、Vercel 与隧道。
- [本机服务维护](LOCAL_OPERATIONS.md)：启动、关闭、日志与故障定位。
- [内容维护](CONTENT_GUIDE.md)：知识格式、参考资料与简历模板。
- [功能验收](ACCEPTANCE.md)：自动化检查与实际环境复测。
- [云服务器方案](CLOUD_HOSTING_PLAN.md)：后续托管与固定域名方案。
- [2026-10-28 整理说明](maintenance/2026-10-28-workspace-organization.md)：归位范围、保护与校验。
- [采集技能](collector-skills/)：BOSS 与小红书资料采集；不同于根目录应用运行时 `skills/`。

## 归档与清理

`screenshots/` 保留近期界面图；[archive/](archive/) 保存旧截图、来源校验与已完成的开发方案。历史记录中的路径与命令反映当时状态，当前操作以本页与各维护指南为准。

`.data/README.md` 说明本机数据用途。`.data/maintenance/` 保存归位映射、清理清单与保护文件哈希，不记录配置正文。数据库、上传、产物、编译任务、采集证据和隧道日志保留原位。

可清理项为项目 `__pycache__/`、`.pytest_cache/`、`.data/pytest-*` 和测试专用 `.data/tests/`。前端 `dist/`、手册生成文章与 VitePress 缓存可重建；本机使用时保留最新构建。依赖环境、字体、许可证和用户原件不作为缓存删除。
