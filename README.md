# GTM Atlas · GTM 学习与求职工作台

项目目录为 **GTM desk**，网页产品名为 **GTM Atlas**。将 GTM（Go-to-Market）知识学习、岗位 JD、面经与 Mock、简历修改和个人学习笔记放在同一工作台中。

运行时使用真实模型服务；缺少接口配置时明确提示。离线测试使用隔离数据和模型替身，不代表外部服务已经验收。

## 当前功能

| 功能 | 页面与能力 | 主要维护位置 |
| --- | --- | --- |
| 知识学习 | `/learn`：GTM 概览、在职经验、名词库、《爆品操盘GTM》与 SOP；卡片、博主合集、搜索、分页与全文阅读 | `apps/web/src/features/knowledge/`、`knowledge/` |
| 岗位与面试 | `/interviews`：岗位 JD、面经与 Mock；自定义题数、回答、追问、反馈、复盘及历史恢复 | `apps/web/src/pages/Interviews.vue`、`packages/mock/` |
| 简历工作台 | `/career`：目标 JD、原件提取、事实核对、诊断、分段授权改写、版本、TeX/PDF 导出 | `apps/web/src/features/career/`、`packages/career/`、`templates/latex/` |
| 学习笔记 | `/notes`：创建文件夹、文件夹内新增笔记、Markdown 编辑与实时预览、保存和删除 | `apps/web/src/features/notes/`、`services/api/routes_notes.py` |
| AI 问答 | 全局、文章、笔记、Mock 与简历场景；多轮历史、句内编号引用、可选语音输入 | `apps/web/src/features/ai/`、`packages/learning/`、`packages/rag/` |
| 账号与历史 | 邮箱登录、验证、找回密码、会话恢复、历史管理与账号隔离 | `apps/web/src/features/auth/`、`services/api/routes_auth.py`、`services/api/supabase.py` |

应用页面要求登录，未登录进入登录／注册页。常用辅助入口为 `/history`、`/settings`、`/glossary`；后端交互文档为 `/docs`，健康接口为 `/api/v1/health`。

Mock 不要求在固定答题步数内结束，也不限制每题的追问次数。模型根据回答和前序对话判断是否继续追问；信息充分、不再需要追问时进入下一题，全部题目完成后生成复盘。

学习笔记首页和每个文件夹分别从 **N01** 编号，按各自笔记创建顺序生成展示编号，分页接续；不同文件夹互不影响。原有笔记保留在首页，编辑笔记会保留其文件夹归属。文件夹和笔记随账号保存到 `business_records`，分别使用 `note_folder`、`learning_note`，沿用现有表，无需新增建表 SQL。

笔记支持 Ctrl / ⌘ + S 保存、撤销与未保存离开提醒，通过版本号防止多页面覆盖。AI 只检索当前账号已保存的笔记，相关片段随请求发送至配置的模型；删除笔记不删除既有聊天中的引用快照。

登录后按账号预加载资料、笔记及历史，后台正文请求最多同时 3 个；退出或切换账号后旧缓存不可用。资料管理接口会检查维护权限，允许修改、删除符合条件的公共在职经验研究笔记，并使相关缓存与检索失效。

## 按功能找文件

```text
GTM desk/
├─ apps/web/                    # Vue 3 + TypeScript 前端
│  ├─ src/
│  │  ├─ features/
│  │  │  ├─ ai/                 # 引用编号与 AI 文本处理
│  │  │  ├─ auth/               # 登录路由守卫
│  │  │  ├─ career/             # 简历显示文本处理
│  │  │  ├─ knowledge/          # 资料卡片、排序、分页、概览预加载
│  │  │  └─ notes/              # 笔记缓存、Markdown 编辑、文件夹编号
│  │  ├─ pages/                 # 路由页面
│  │  ├─ components/            # 阅读器、编辑器、助手与共享界面
│  │  ├─ content/               # 引用根目录知识源的前端入口
│  │  ├─ state.ts               # API、认证会话与共享缓存
│  │  └─ preload.ts             # 跨功能预加载调度
│  ├─ tests/                    # 全部前端回归测试
│  ├─ scripts/handbook.mjs       # 从知识源生成 VitePress 手册
│  └─ handbook/                 # 手册配置、索引与生成文章
├─ services/api/                # FastAPI 路由、鉴权、存储和数据模型
├─ packages/
│  ├─ agent_core/               # 模型适配、Skill 注册、检查点
│  ├─ rag/                      # 公共知识索引、私有笔记与参考资料检索
│  ├─ learning/                 # 知识问答流程
│  ├─ mock/                     # 面试规划和评价
│  ├─ career/                   # 简历解析、事实、授权改写
│  └─ document_renderer/        # 模板填充、编译队列与 PDF 检查
├─ knowledge/
│  ├─ jobs/research-notes/       # 岗位 JD
│  ├─ interviews/research-notes/ # 面经
│  ├─ learning/research-notes/   # 在职经验与学习资料
│  ├─ glossary/                 # GTM 术语 JSON
│  └─ site/                     # 概览、全书、SOP 与公开配图
├─ profiles/                    # 岗位、行业和评分配置
├─ skills/                      # 应用运行时领域提示规则
├─ templates/latex/             # 简历模板与用户提供的 TeX 原件
├─ infra/                       # Docker、PDF Worker、迁移、字体与代理
├─ supabase/                    # 初始化 SQL 与验证 SQL
├─ scripts/                     # 本地启动和知识资料校验
├─ tests/                       # 后端测试、合成夹具与检索评测
├─ docs/                        # 维护文档、采集技能、整理说明与历史归档
├─ .data/                       # 本机数据、上传、产物、隧道日志；不提交 Git
├─ .venv/                       # 本机 Python 环境；不提交 Git
├─ pyproject.toml               # Python 项目声明
├─ requirements.lock            # Python 依赖锁定
└─ vercel.json                  # 前端构建与路由配置
```

页面与共享组件按现有层次保留；只有业务辅助模块归到 `features/`。后端已按功能分包，数据库迁移、静态网页地址和领域规则加载路径保持现有约定。

完整文件导航见 [docs/README.md](docs/README.md)，前端说明见 [apps/web/README.md](apps/web/README.md)。

## 知识资料维护

当前源码包含 **10 份岗位 JD、30 篇面经、167 篇在职经验／学习资料**。研究笔记保留作者、出处与阅读边界，不等于原帖逐字全文或企业官方结论。合成资料仅放在 `tests/fixtures/`。

| 内容 | 唯一源目录 |
| --- | --- |
| GTM 概览首页与四章 | `knowledge/site/gtm-overview/` |
| GTM 专有名词与例子 | `knowledge/glossary/gtm-glossary.json` |
| 《爆品操盘GTM》全书 | `knowledge/site/gtm-book/` |
| SOP 七阶段、15 份资料与操盘手册 | `knowledge/site/gtm-sop/` |
| 博主研究笔记与公开配图 | `knowledge/learning/research-notes/`、`knowledge/site/xhs-author-assets/` |

资料同时用于网页与 AI 检索；许可、出处和索引规则见 [内容维护指南](docs/CONTENT_GUIDE.md)。不要编辑 `dist/` 或自动生成的 `handbook/articles/`。修改知识源后重新构建前端和 API 镜像，使静态内容与索引同步。

## 本地开发

推荐 **Python 3.11、Node.js 22**；Python 最低 3.10。以下命令在项目根目录执行，已有依赖环境可跳过安装步骤。

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock
.venv/Scripts/python.exe -m pip install --no-deps -e .
npm --prefix apps/web ci
npm --prefix apps/web run build
.venv/Scripts/python.exe -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000
```

后端启动时读取根目录 `.env`。已有配置不要覆盖；独立开发使用自己的本地配置，`AUTH_MODE=local`、`STORAGE_MODE=local`，未设置 `DATABASE_URL` 时默认 `.data/atlas.db`。本地账号不会自动同步为 Supabase 账号。

启动后访问 `http://127.0.0.1:8000/`；API 文档为 `/docs`，静态手册为 `/handbook/`。热更新另开终端运行 `npm --prefix apps/web run dev`，Vite 将 `/api` 代理到 8000；也可使用 `scripts/start.ps1`。本地 Uvicorn 与 Docker API 不要同时占用 8000。

## 部署与模型配置

正式方案是 **Vercel 前端 + Docker API／隔离 PDF Worker + Supabase Auth／PostgreSQL／私有 Storage**。无服务器时可用本机 Docker 配合 Cloudflare 临时隧道联调；本机休眠或隧道退出会影响访问。

- 后端 `.env` 保存数据库、Supabase 和模型配置；Vercel 仅需要公开的 `VITE_API_BASE_URL`。
- 文本模型使用 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`；STT、Vision、Embedding 按需独立配置。
- 未配置 Embedding 时使用词法检索；向量固定为 1536 维，换维度需要改代码、迁移及重建索引。
- renderer 不持有模型或数据库密钥，通过文件队列编译 TeX 并检查 PDF；API 的 `RENDER_ENABLED=false` 不表示 Worker 停止。
- 私有笔记使用关键词与中文词组检索，每次最多 6 个相关片段，不额外生成公共向量。

部署步骤、配置表和隧道命令见 [部署指南](docs/DEPLOYMENT.md)。日常开关、日志和故障定位见 [本机服务维护](docs/LOCAL_OPERATIONS.md)。

```powershell
docker compose -f infra/compose.production.yaml config --quiet
docker compose -f infra/compose.production.yaml up -d --build
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

修改前端需重新发布前端；修改 API 或知识源需重建 API；修改 PDF 编译环境才需要重建 renderer。文件夹功能发布时同时更新前端和 API。现有数据库升级不能靠重复执行初始化 SQL。

## 测试与验收

```powershell
npm --prefix apps/web test
npm --prefix apps/web run build
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe scripts/validate_knowledge.py
.venv/Scripts/python.exe -m tests.evals.run
```

`npm test` 统一执行 `apps/web/tests/*.test.mjs`，包含 Node 22 下读取 TypeScript 和 VM 模块所需的参数。完整构建包含类型检查、Vite 与 VitePress 手册构建。

测试使用隔离 SQLite、临时文件和模型替身。真实模型、邮件、Supabase、Docker PDF 与公网访问须在实际环境按 [验收清单](docs/ACCEPTANCE.md) 检查；文档不记录临时地址和在线状态快照。

## 数据与清理边界

| 类型 | 处理原则 |
| --- | --- |
| `.env`、其他本机配置副本 | 保留，不提交密钥，不用模板覆盖 |
| `.data/atlas.db`、上传、JD、产物、队列、采集证据与隧道日志 | 保留；不整体删除 `.data/` |
| `.venv/`、`apps/web/node_modules/` | 保留本机依赖；不能作为垃圾目录直接删除 |
| `__pycache__/`、`.pytest_cache/`、`.data/pytest-*`、`.data/tests/` | 可再生成的测试缓存和临时数据 |
| `dist/`、手册生成文章、VitePress 缓存 | 可构建重建；本机预览使用最新构建 |
| 历史方案、截图与导入依据 | 放入 `docs/archive/`，与当前操作文档分开 |

2026-10-28 的目录整理与验证范围见 [整理说明](docs/maintenance/2026-10-28-workspace-organization.md)。本机详细移动和清理清单、保护文件哈希位于 `.data/maintenance/`。

## 维护文档

- [目录与维护入口](docs/README.md)
- [系统架构与边界](docs/ARCHITECTURE.md)
- [部署配置与公网访问](docs/DEPLOYMENT.md)
- [本机服务维护](docs/LOCAL_OPERATIONS.md)
- [知识内容与模板维护](docs/CONTENT_GUIDE.md)
- [功能验收](docs/ACCEPTANCE.md)
- [后续云服务器方案](docs/CLOUD_HOSTING_PLAN.md)

目前仍使用单机文件队列与进程内限流；未实现通用流式回答、多人笔记协作、企业身份体系与分布式队列。扩容和模板调整需要相应的运行与 PDF 排版验证。
