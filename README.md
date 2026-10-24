# GTM Atlas · GTM 学习与求职工作台

GTM Atlas 将 GTM（Go-to-Market）知识学习、岗位理解、模拟面试和简历修改放在同一个工作空间中。项目文件夹名为 `GTM desk`，网页产品名为 **GTM Atlas**。

项目帮助正在了解 GTM、准备相关岗位求职或梳理业务经历的用户，完成“学习知识 → 理解岗位 → 练习表达 → 改善简历”的过程。AI 基于知识资料和用户确认的真实经历提供帮助，不能把岗位要求或参考案例直接写成候选人做过的事情。

仓库包含前端、Python 后端、知识资料、领域提示规则、简历模板、数据库 SQL 和 Docker 配置。运行时调用真实模型服务；缺少接口配置时明确提示，不使用模拟回答代替真实结果。

## 当前阶段与使用入口

项目已具备知识学习、AI 问答、Mock 和简历工作台的主要代码与部署结构，目前处于**功能完善与真实服务联调阶段**。完成基础要求不等于所有云端功能已经验收。

截至 2026-10-23，本次开发过程中已检查：本机 Docker API 的健康接口、Supabase 数据库连通性、renderer 内的 XeLaTeX、Cloudflare 临时隧道公网健康接口、指定 Vercel 来源的 CORS，以及未登录账号接口返回 401。这些是当时的检查结果，不能保证电脑重启后的状态，也不代表实际问答、邮件、简历 PDF 或双账号隔离全部通过。

支持两种对外运行方式：

| 方式 | 前端 | 后端 | 适用情况 |
| --- | --- | --- | --- |
| 本机联调 | Vercel | 自己电脑上的 Docker，通过 Cloudflare 临时隧道访问 | 当前无服务器，先测试完整连接 |
| 持续部署 | Vercel | 持续在线的 Docker 主机，通过 HTTPS 域名访问 | 后续正式对外使用 |

常用入口：前端主页 `/`、资料 `/learn`、问答 `/learn/ask`、面经与 Mock `/interviews`、简历 `/career`、历史 `/history`、设置 `/settings`、名词完整页 `/glossary`。后端 API 文档为 `/docs`，健康接口为 `/api/v1/health`。

阅读顺序：了解功能 → 目录与 Skill → 环境变量 → Docker 启动 → 选择公网访问方式 → Vercel → 功能验收。下文示例域名和 Key 都是占位符，不含真实凭证，也不记录会过期的临时隧道地址。

## 主要功能

### 知识学习

资料入口 `/learn` 使用卡片目录和全文阅读，栏目依次为：

| 栏目 | 内容与交互 |
| --- | --- |
| GTM 概览 | HTML 学习页面，支持框内预览和打开完整页面 |
| 岗位 JD | 公共岗位资料栏目，供后续扩充 |
| 面经 | 面试经验研究笔记、问题和岗位认知 |
| 在职经验 | 业务经验和学习笔记 |
| GTM 专有名词库 | 名词、解释和场景例子，两列表格，支持预览和完整页面 |

目前正式 Markdown 知识库包含 **10 份岗位 JD、30 篇面经研究笔记和 30 篇学习/在职经验笔记**。三类资料均使用 `research-notes/research-jNN.md`、`research-iNN.md`、`research-lNN.md` 单篇结构；JD 直接匹配与相关职能扩展的边界保留在各单篇中。研究笔记不等于原帖逐字全文，也不代表企业官方结论。合成资料仅保留在 `tests/fixtures/`，不进入正式知识库。

### AI 问答与语音输入

- 全局助手使用全站可检索知识，文章和简历场景使用相应范围的上下文。
- 先检索资料，再调用 LLM 生成回答，并检查引用是否属于本次检索结果。
- 登录后支持多轮问答保存、历史恢复、New chat、清空上下文和删除会话。
- New chat 保留旧会话；清空上下文保留历史展示，但不将旧轮次继续发送给模型。
- 可选语音输入先转写至草稿，用户校对后再提交。未配置 STT 时仍可键盘输入。

### 面经与 Mock

根据岗位、行业、语言、难度、题数等条件规划面试，结合面经参考生成问题。对用户回答提供维度反馈、有限追问和复盘；保存练习进度与回答，可从历史继续。授权的简历事实可用于个性化追问。

### 简历工作台

```text
选择目标岗位 / 上传或粘贴 JD
  → 上传简历原件 → 提取文字、关键信息和段落归属
  → 用户核对确认 → 诊断 → 选择允许修改的段落
  → AI 提出建议 → 用户审核授权
  → 填充 TeX 模板 → 生成新版本 → 导出 TeX / 编译下载 PDF
```

可提取文字的 PDF、TXT 直接读取；扫描 PDF 和图片由单独配置的图像模型识别。识别结果需人工核对。支持段落锁定、修改授权、新增数字检查、历史版本和从旧版继续生成新版。

默认模板来自用户提供的 TeX 文件，原件为 `templates/latex/gtm-original/source.tex`，可填充模板为同目录 `resume.tex.j2`。只查看诊断不会自动生成修改版本。

## 系统架构

```text
浏览器
  │ HTTPS
  ▼
Vercel：Vue 前端 + VitePress 静态手册
  │ HTTPS API
  ▼
Docker 主机：api（FastAPI）
  ├─ Supabase Auth：账号、登录、邮箱验证与会话
  ├─ Supabase PostgreSQL：偏好、历史、业务记录、知识与向量
  ├─ Supabase 私有 Storage：上传原件和生成文件
  ├─ 模型服务：LLM / STT / Vision / Embedding
  └─ 共享持久卷：编译任务和产物
                  │
                  ▼
            renderer：隔离 PDF Worker
```

部署方案使用 Supabase 托管的 PostgreSQL，**无需在本机或生产 Docker 中另装 PostgreSQL**。本地开发可使用 SQLite。无服务器时，架构图中 Vercel 到 Docker 的 HTTPS 连接可由 Cloudflare Tunnel 转发。

| 技术 | 职责 |
| --- | --- |
| Vue 3、TypeScript、Vue Router | 页面、工作台和交互 |
| Vite、VitePress | 前端构建和静态知识手册 |
| FastAPI、Pydantic、Uvicorn | HTTP API、参数校验和服务运行 |
| LangGraph | 问答、面试评价、简历审批及状态恢复 |
| SQLAlchemy、psycopg、Alembic | 数据访问和迁移 |
| PostgreSQL、pgvector | 业务存储、全文检索信号和向量检索 |
| PyMuPDF、Jinja2、XeLaTeX | PDF 提取、模板填充、编译及产物检查 |
| Docker Compose | 管理 API 与 PDF Worker |

## 目录与文件说明

```text
GTM desk/
├─ apps/web/                  # Vue 前端、静态页面、VitePress 手册
│  ├─ src/components/         # 聊天、输入框、目录、概览和名词库组件
│  ├─ src/pages/              # 首页、学习、面试、简历、账号与设置
│  ├─ src/content/            # 前端术语内容
│  ├─ public/gtm-overview/    # GTM 概览 HTML 和章节
│  ├─ handbook/              # VitePress 配置及生成入口
│  └─ scripts/handbook.mjs    # 从知识源生成手册
├─ services/api/              # 认证、业务 API、存储、数据模型
├─ packages/
│  ├─ agent_core/            # 模型接口、受控领域规则、checkpoint
│  ├─ rag/                   # 资料入库、分块、增量索引、检索
│  ├─ learning/              # 问答流程和引用校验
│  ├─ mock/                  # 面试规划、评价、追问、复盘
│  ├─ career/                # 简历解析、诊断、检索和授权
│  └─ document_renderer/     # 模板填充、任务队列、PDF 检查
├─ knowledge/                # 正式知识 Markdown，内容维护的事实源
│  ├─ interviews/            # 面经
│  ├─ learning/              # 学习 / 在职经验
│  └─ jobs/                  # 公共 JD 扩展位置
├─ profiles/                 # 岗位、行业和评分规则配置
├─ skills/                   # 应用内部使用的受控领域提示规则
├─ templates/latex/          # 简历模板和原始 TeX
├─ supabase/                 # 初始化 SQL 与验证 SQL
├─ infra/                    # Dockerfile、Compose、Worker、迁移、反向代理
├─ scripts/                  # 本地启动辅助脚本
├─ tests/                    # 离线测试、合成夹具、回归评测
├─ docs/                     # 部署、架构、内容维护和验收文档
├─ .env                      # 实际读取的私有配置，不提交 Git
├─ .gitignore                # 排除密钥、依赖、构建产物和本地数据
├─ .dockerignore             # 排除无需打入镜像的文件
├─ pyproject.toml            # Python 项目和依赖声明
├─ requirements.lock         # Python 依赖锁定清单
├─ vercel.json               # Vercel 构建与路由
└─ IMPLEMENTATION_PLAN.md    # 实施规划记录
```

| 关键文件 | 内容 |
| --- | --- |
| `apps/web/src/main.ts` | 前端页面路由 |
| `apps/web/src/App.vue` | 全站导航和全局助手 |
| `apps/web/src/state.ts` | 前端状态、API 地址和凭证刷新 |
| `apps/web/src/pages/Utility.vue` | 登录、历史、设置和搜索 |
| `apps/web/src/content/gtm-glossary.ts` | 名词库数据，后续补充入口 |
| `services/api/main.py` | 应用入口、启动索引、健康检查和基础接口 |
| `services/api/config.py` | 读取根目录 .env，确定数据库和数据目录 |
| `services/api/db.py` | 账号、业务记录、文档和分块模型 |
| `services/api/supabase.py`、`storage.py` | Supabase Auth 和文件存储 |
| `services/api/routes_knowledge.py` | 资料、问答、语音、管理员索引接口 |
| `services/api/routes_mock.py`、`routes_career.py` | 面试、简历和版本 API |
| `packages/agent_core/providers.py` | LLM、STT、Embedding 请求 |
| `packages/career/graph.py` | 简历文字提取、Vision 请求和诊断 |
| `packages/rag/knowledge.py` | 分块、向量生成与混合检索 |
| `infra/renderer_worker.py` | 循环读取 PDF 编译任务 |
| `packages/document_renderer/render.py` | TeX 填充、XeLaTeX 编译与 PDF 检查 |
| `supabase/schema.sql`、`verify.sql` | 初始化表、触发器、RLS、私有桶及检查 |

`skills/` 是应用自己的提示规则，不允许用户上传文档注册任意工具或执行程序。

## Agent 与 Skill 如何协作

本项目的 Agent 由后端业务流程和 LangGraph 节点组织。Skill 是每类任务的受控提示规则，不是独立进程，也不是模型训练或微调。

```text
前端操作 → API 路由 → 业务流程 / LangGraph 节点
  → LLMProvider.complete(task, payload)
  → 按任务文字选择 Skill → registry 读取对应 SKILL.md
  → 全局 system 规则 + Skill 正文 + 本次数据 → 模型请求
  → 后端结构、来源及业务校验 → 返回建议或结果
```

| Skill | 主要规范 | 当前接入方式 |
| --- | --- | --- |
| resume-extraction | 字段原文来源、事实 ID 完整映射、不补全履历 | 简历字段提取时注入 |
| resume-diagnosis | JD 对照、STAR 缺口、事实与表达问题、优先级 | 简历诊断时注入 |
| resume-rewriting | STAR 表达、职责保真、授权 patch、一页内容预算 | 改写建议时注入 |
| interview-planning | 题数、维度覆盖、难度、岗位侧重、授权经历 | Mock 出题时注入 |
| interview-evaluation | 六维 0–4/null 锚点、原答证据、单次追问 | 回答评价时注入 |
| learning-qa | 证据范围、引用、来源差异和时效边界 | 问答任务时注入 |
| resume-fact-check | 数字、责任、因果及来源审核 | 规范文件；尚无独立模型审核步骤 |
| latex-render | 一页目标、留白、排版和 PDF 交付检查 | 规范文件；实际编译由 Python Worker 执行 |

当前每次模型请求通过任务关键词选择一份 Skill，未使用 description 做自动语义发现，也不是模型自主调用整套技能。tools 字段是注册元数据，不表示模型实际获得工具调用权限；检索、改写校验和编译由后端代码控制。修改或新增 Skill 名称时还需检查 providers.py 中的路由。

简历规则已补充 STAR、A4 一页优先、避免大面积无意义留白、信息密度、职责映射和事实对照案例。没有量化结果时写真实交付物，不能编造数字，也不能把“参与”提升为“主导”。

**提示规则与程序保障要区分**：当前 renderer 的自动页数阈值仍为最多 2 页，尚未自动执行一页硬限制、留白率或字号检查；一页目标需要最终 PDF 预览和内容/模板调整。写了规则不代表已实现自动排版验收。

Dockerfile 将 skills 复制进镜像，修改本机 Skill 后需要重新 build 并更新 API 容器；仅 restart 不会同步文件。现有结构化校验仍需保留，不能把模型遵守提示当作唯一保障。

## 知识资料与 Embedding

知识源包括 `knowledge/` 下的 Markdown、GTM 概览 HTML 正文及名词库 JSON。每篇 Markdown 需要 frontmatter，包含 ID、标题、类别、显示编号、许可、质量状态、来源和岗位/行业标签。只索引 `public_display` 且未弃用的资料；概览和名词库从原文件自动提取，不需维护 Markdown 副本。

入库按章节和约 1800 字符上限分块，检查重复 ID/正文并保存哈希。内容和模型名称未变化时跳过重建；删除或撤销许可的资料会从索引移除。API 启动时执行索引，管理员也可调用 `POST /api/v1/admin/knowledge/reindex` 重建。

Embedding 的作用：

1. 入库时，将公共知识片段生成向量并保存。
2. 搜索时，将问题、JD 或修改要求生成向量，查找相近资料。
3. 搜索、AI 问答、Mock 出题、简历诊断和改写复用这套检索。

PostgreSQL 模式组合词法信号、全文检索和向量余弦排序，通过 RRF 融合。中文词法预处理使用二字片段，不是完整中文分词或 BM25。未配置 Embedding 时只做词法检索；配置了但调用失败时会报错，不会自动降级。

当前请求、校验和数据库字段固定 **1536 维**。`EMBEDDING_DIMENSIONS` 当前没有被代码读取；换成 1024 维模型需要修改代码、迁移数据库并重建索引。相同维度但不同模型的向量也不能混用。

个人简历不会进入公共向量库；私人 JD 以授权上下文提供。GTM 概览与名词库已作为站内参考资料接入检索和引用；引用可打开索引正文及原页面，不混入 JD、面经、在职经验卡片。资料扩充、统一 Markdown 契约与两份采集 Skill 见 [内容维护指南](docs/CONTENT_GUIDE.md)。

## 环境变量与模型接口

后端实际读取根目录 `.env`。如本机还有 `.env.supabase.formal`，它只是配置副本，Docker 不直接读取。不要提交任何已填入密钥的配置副本，不要用模板覆盖已有 `.env`。

| 配置项 | 用途与说明 |
| --- | --- |
| `AUTH_MODE`、`STORAGE_MODE` | 正式环境均为 supabase；本地可用 local |
| `SUPABASE_URL` | Supabase 项目 URL |
| `SUPABASE_ANON_KEY` | 当前代码使用的 legacy anon key，供 Auth 请求使用 |
| `SUPABASE_SERVICE_ROLE_KEY` | 后端受控访问私有文件等操作，仅可留在服务器 |
| `SUPABASE_STORAGE_BUCKET` | 私有桶，初始化 SQL 创建 gtm-private |
| `DATABASE_URL` | SQLAlchemy 数据库连接串；未设置默认本地 SQLite |
| `ALLOWED_ORIGINS` | 前端完整来源，多个域名用逗号分隔，不带末尾斜杠 |
| `PROVIDER_MODE=live` | 使用真实模型服务 |
| `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` | 问答、面试和简历 AI 功能所需的文本服务 |
| `STT_BASE_URL`、`STT_API_KEY`、`STT_MODEL` | 可选语音转写，未配置可用键盘 |
| `VISION_BASE_URL`、`VISION_API_KEY`、`VISION_MODEL` | 可选图片识别，未配置可用可读文件或手动录入 |
| `EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL` | 可选语义检索，未配置仅词法检索 |
| `DATA_DIR` | 本地默认 .data，生产容器为 /data |
| `ADMIN_EMAIL` | 可调用公共知识重建接口的账号邮箱 |
| `RENDER_ENABLED` | API 保持 false；Worker 镜像内部设置为 true |

适配器使用 OpenAI 兼容的 `/chat/completions`、`/audio/transcriptions`、`/embeddings` 接口。基础地址按服务商要求包含 `/v1` 等前缀，不要重复填写完整 endpoint。模型名称、批量上限、图片能力和费用需以提供方说明为准。

Vision 必须使用支持图片输入的模型。它可以与文本模型共用服务商和 Key，但不能只凭品牌名判断图片能力。实际兼容性需要用真实调用验证。

## 推荐部署：Supabase + Docker + Vercel

### 1. 初始化 Supabase

在新的 Supabase 项目执行 [schema.sql](supabase/schema.sql)，再用 [verify.sql](supabase/verify.sql) 检查。已执行过 SQL 的项目不应把初始化文件当作升级迁移重复使用。

配置 Email 登录、邮箱验证和生产邮件服务，在 Authentication 中设置前端 Site URL / Redirect URLs。密码由 Supabase Auth 管理，不在业务表保存明文密码。

当前前端密码提示为“请输入密码”，前后端应用已移除原 12～128 字符限制，仅要求非空。Supabase 仍独立执行其密码策略，短密码注册能否成功以云端规则为准；修改应用校验不会自动修改 Supabase 项目设置。

在 Docker 主机的项目根目录 `.env` 中填写真实值（本机或服务器均适用）：

```dotenv
AUTH_MODE=supabase
STORAGE_MODE=supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
SUPABASE_STORAGE_BUCKET=gtm-private
DATABASE_URL=postgresql+psycopg://postgres.YOUR_PROJECT:ENCODED_PASSWORD@YOUR_POOLER_HOST:5432/postgres?sslmode=require
ALLOWED_ORIGINS=https://YOUR_SITE.vercel.app
PROVIDER_MODE=live
LLM_BASE_URL=YOUR_PROVIDER_BASE_URL
LLM_API_KEY=YOUR_PROVIDER_KEY
LLM_MODEL=YOUR_MODEL_NAME
RENDER_ENABLED=false
```

以上全是占位符。数据库信息从 Connect 的 **Session pooler（5432）**复制，协议使用 `postgresql+psycopg://`，密码特殊字符需要 URL 编码，保留 TLS 参数。可选 AI 接口按上一节补充。

### 2. 启动 Docker

需要运行中的 Docker Engine / Docker Desktop 和 Compose。命令在项目根目录执行，**不需要移动文件或创建 Docker 文件夹**：

```powershell
cd "C:\Users\64954\Desktop\GTM desk"
docker compose -f infra/compose.production.yaml config --quiet
docker compose -f infra/compose.production.yaml up -d --build
docker compose -f infra/compose.production.yaml ps -a
```

Linux 服务器进入克隆后的项目目录，使用相同 Compose 命令。生产配置只启动 api 和 renderer，数据库使用 Supabase。首次构建需要安装 Python 依赖、LaTeX 和中文字体；首次启用 Embedding 会生成资料向量并产生服务费用。renderer 的 Debian 软件源已改用清华 HTTPS 镜像，并设置下载重试和超时，以应对原源下载 502。

容器显示 Started 只说明主进程已启动，不保证应用初始化完成。API 启动时会检查知识资料、连接数据库，并为需要更新的片段生成索引；首次运行可能较慢。出现 `Waiting for application startup` 时需结合日志检查进度，不能据此断言正常或失败。`Application startup complete` 或健康接口稳定返回 JSON 中的 status=ok，才说明 API 已能接收请求。

Docker 配置每 30 秒请求一次健康接口，反复出现 `GET /api/v1/health ... 200 OK` 是正常健康检查，不会调用大模型。LangGraph 的弃用警告与真正的异常堆栈应分开判断。

```powershell
# 检查后端
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health

# 查看日志；Ctrl+C 只退出日志查看
docker compose -f infra/compose.production.yaml logs -f api
docker compose -f infra/compose.production.yaml logs --tail=100 renderer

# 检查 PDF 编译器
docker compose -f infra/compose.production.yaml exec renderer xelatex --version

# 修改代码后重新构建并更新
docker compose -f infra/compose.production.yaml up -d --build

# 修改 .env 后重新创建 API，使环境变量生效
docker compose -f infra/compose.production.yaml up -d --force-recreate api

# 暂停 / 恢复
docker compose -f infra/compose.production.yaml stop
docker compose -f infra/compose.production.yaml start
```

`-d` 表示后台运行，关闭终端不会停止容器。`restart: unless-stopped` 由 Docker 管理退出后的重启，但关机、休眠或 Docker 引擎停止时仍无法服务。正式环境需持续在线的服务器。

持久卷保存队列和编译产物，需要备份。不要用 `docker compose down -v` 排障，它会删除这套 Compose 的持久卷；Supabase 数据库独立于这些卷。

### 3. 选择公网 HTTPS 访问方式

#### 方式 A：自己的电脑 + Cloudflare 临时隧道

适合当前没有服务器的联调。Docker 的 8000 端口仍只绑定本机，由 cloudflared 主动连接 Cloudflare 并转发请求，不需要购买域名，也无需额外的 PDF Token。

Windows 可通过 winget 安装官方程序（仅首次需要）：

```powershell
winget install --id Cloudflare.cloudflared --exact --source winget
```

本机已安装时不要重复安装。默认安装位置可为 `C:\Program Files (x86)\cloudflared\cloudflared.exe`，以实际安装目录为准。先确认本机健康接口可用，再在另一个 PowerShell 窗口运行：

```powershell
& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:8000
```

`&` 调用引号中的程序；tunnel 建立隧道；--url 指向本机后端；--protocol http2 指定连接 Cloudflare 的协议。窗口需保持运行，Ctrl+C 会结束这次前台隧道。后台运行的隧道需按实际进程 ID 停止，不要固定复用以前的 PID。

日志会给出 `https://随机名称.trycloudflare.com`，先访问该地址下的 `/api/v1/health`，确认返回 JSON，再填入 Vercel。该地址可从外网访问后端，现有登录鉴权仍需生效。

临时隧道没有持续在线保证。电脑休眠、关机、断网或隧道进程结束会中断服务；重开通常产生新域名，需更新 Vercel 的 VITE_API_BASE_URL 并重新部署。ALLOWED_ORIGINS 填的是前端域名，不随隧道地址变化而修改。长期固定地址需另配命名隧道和自有域名，或使用下述服务器方案。

#### 方式 B：持续在线的 Docker 主机 + 反向代理

把同一项目和私有配置部署到持续在线的主机。生产 Compose 只绑定主机 `127.0.0.1:8000`，通过 Caddy 或平台代理提供公网 HTTPS。项目已有 [Caddyfile](infra/Caddyfile)，通过 API_DOMAIN 指定域名，并配置 DNS 和 80/443 访问。代理上传上限至少 11 MB，请求超时建议至少 120 秒。

这两种方式都要求公网 HTTPS API。浏览器中的 `127.0.0.1:8000` 指向访问者自己的电脑，不能作为 Vercel 网站对公众使用的后端地址。

### 4. 部署 Vercel 前端

- GitHub 提交前检查暂存列表，不包含密钥、用户文件、`.data`、`.venv`、`node_modules`。
- 忽略规则不会取消已跟踪文件；真实密钥如已上传，需更换密钥并处理仓库泄露。
- Vercel Root Directory 选择仓库根目录，构建依赖根目录的 knowledge。
- 使用 Node.js 22、Framework Preset 选择 Other；vercel.json 已定义构建与输出。
- 环境变量填写 `VITE_API_BASE_URL=https://YOUR_API_DOMAIN`，不带 `/api/v1`。
- Docker 的 ALLOWED_ORIGINS 填前端正式域名，预览域名需单独允许。
- 修改 Vite 环境变量后重新部署前端。

前端只需公开的 API 地址，不需要数据库密码、模型 Key、Supabase service role 或 Vercel API Token。详细设置见 [部署指南](docs/DEPLOYMENT.md)；其中旧模板复制命令仅在文件存在且不会覆盖现有配置时使用，实际配置以根目录 .env 为准。

### 5. 日常关闭与下次恢复

关闭顺序：停止隧道 → 在项目根目录运行 Compose stop → 按需退出 Docker Desktop。不要用 down -v 作为关机操作。

```powershell
# 暂停 api 和 renderer，保留数据
docker compose -f infra/compose.production.yaml stop

# 下次打开 Docker Desktop 后恢复已有容器
docker compose -f infra/compose.production.yaml start

# 检查本机 API，再启动隧道
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health

# 查看后台隧道进程；先确认身份，再用实际 ID 停止
Get-Process -Name cloudflared -ErrorAction SilentlyContinue
# Stop-Process -Id 实际进程ID
```

容器已被 down 移除时，使用 up -d 重新创建；没有代码或依赖变化时不必重新 build。查看 logs -f 时按 Ctrl+C 只停止日志查看，不能据此判断容器或后台隧道已关闭。重开临时隧道后按新地址完成 Vercel 更新和 Redeploy。

## 前端微调与内容维护

| 修改目标 | 源文件 |
| --- | --- |
| 首页 | apps/web/src/pages/Home.vue |
| 学习页标题与说明 | apps/web/src/pages/Learn.vue |
| 面经与 Mock | apps/web/src/pages/Interviews.vue |
| 简历工作台 | apps/web/src/pages/Career.vue |
| 登录、历史、设置、搜索 | apps/web/src/pages/Utility.vue |
| 导航和全局助手外框 | apps/web/src/App.vue |
| 知识栏目和资料卡片 | apps/web/src/components/ResourceGallery.vue |
| 名词、解释和例子 | apps/web/src/content/gtm-glossary.ts |
| 名词表格与预览外框 | apps/web/src/components/GtmGlossary.vue、GtmGlossaryPreview.vue |
| 名词完整页 | apps/web/src/pages/Glossary.vue |
| GTM 概览正文 | apps/web/public/gtm-overview/ 下的 HTML |
| 面经和在职经验正文 | knowledge/ 下的 Markdown |
| 全局排版与颜色 | apps/web/src/style.css、tokens.css |

.vue 文件的 template 负责页面结构，script 负责交互，style 负责样式；gtm-glossary.ts 单独保存内容数据，预览和完整页共用。apps/web/index.html 是入口，不含所有页面正文。不要直接修改 dist 或生成的 handbook/articles，构建会覆盖它们。

前端源码修改后重新构建或部署 Vercel；只改前端通常不需要重建 Docker API。修改 knowledge 则需同时考虑 API 索引和静态手册构建，不能只刷新浏览器。

## 本地开发

推荐 Python 3.11、Node.js 22。Python 声明最低 3.10，生产镜像使用 3.11。下面命令不会创建或覆盖 .env：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock
.venv/Scripts/python -m pip install --no-deps -e .
npm --prefix apps/web ci
npm --prefix apps/web run build
.venv/Scripts/python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000
```

构建后 FastAPI 可同时提供网页、API 和手册：

| 地址 | 内容 |
| --- | --- |
| http://127.0.0.1:8000/ | 网站 |
| http://127.0.0.1:8000/docs | OpenAPI 交互文档 |
| http://127.0.0.1:8000/api/v1/health | 健康及配置状态 |
| http://127.0.0.1:8000/handbook/ | VitePress 手册 |

热更新：另开终端运行 `npm --prefix apps/web run dev`，访问 Vite 输出地址；开发代理将 /api 转发至 8000。也可用 scripts/start.ps1。不要让本地 Uvicorn 和 Docker API 同时占用 8000。

独立本地环境可设 AUTH_MODE=local、STORAGE_MODE=local；未设置 DATABASE_URL 时使用 .data/atlas.db。已有生产 .env 时应隔离开发配置，不要直接覆盖或误连生产数据库。本地账号不会自动成为 Supabase Auth 账号。

| Compose 文件 | 用途 |
| --- | --- |
| infra/compose.production.yaml | 正式方案：API + Worker，连接 Supabase |
| infra/compose.yaml | 自带本地 PostgreSQL / pgvector，API 启动执行 Alembic |
| infra/compose.renderer-local.yaml | 本地 Python / SQLite API 配合 Docker Worker，挂载 .data 子目录 |

这些是不同运行方案，不要混用任务队列。Supabase 生产初始化使用 schema.sql，生产 Compose 不重复运行 Alembic 初始建表，后续结构变化需单独迁移。

## PDF Worker 工作原理

renderer 是本项目定义的服务，不是 Docker 自带功能或第三方 PDF API，不需要额外 Key。

```text
API 填充模板 → 保存 resume.tex → 写入 JSON 任务
  → renderer 每隔约 2 秒检查队列 → XeLaTeX 编译
  → 检查事实文本、边界和页数 → 写入结果
  → 页面刷新状态 → API 同步合格 PDF 到私有 Storage → 鉴权下载
```

Worker 无网络，不持有数据库或模型密钥，只挂载队列和产物卷；采用非 root、只读根目录、资源限制。禁用 shell escape，用户文本经过 TeX 转义。默认超过 2 页、缺失事实文本或边界检查失败时不提供 PDF，需调整内容重试。

API 的 RENDER_ENABLED=false 是正常设置，Worker 镜像内单独为 true。健康接口的 render_enabled 只反映 API 进程配置，不是 Worker 健康检查。空闲 Worker 可能没有日志，应结合容器状态、编译器和实际任务验证。

未启动 Worker 时可导出 TeX，PDF 保持等待。编译完成后需刷新任务状态以处理结果和同步云端。

## 数据保存与访问权限

| 数据 | 正式存储位置 |
| --- | --- |
| 账号凭证、密码哈希 | Supabase Auth |
| 偏好、Mock、聊天、简历事实、版本、任务 | Supabase PostgreSQL |
| 公共文档、分块、向量 | PostgreSQL 知识表 |
| 上传原件及同步的生成文件 | Supabase 私有 Storage |
| 编译队列、工作区和产物 | Docker 持久卷 |
| 公共知识 Markdown、模板、源码 | Git 仓库 |

API 校验对象所有者，Supabase 配置 RLS 和私有桶策略。数据库凭证和 service role 可绕过 RLS，只能留在服务器，不能替代业务鉴权。

Mock、简历版本和聊天默认保存到用户删除。删除聊天会删除其问答；删除简历会话会清理关联记录和适用文件。备份按平台保留策略处理。直接删除 Supabase Auth 账号不会自动清理全部 Storage 对象和 Docker 产物，完整销户需要额外清理。

浏览器凭证保存在当前站点 localStorage，关闭网页或浏览器后重新进入会恢复登录，访问凭证过期时自动刷新。主动退出会清除本地凭证并同步其他标签页，同时请求撤销服务端会话；网络失败时仍清除本地登录并提示撤销失败。清除站点数据或服务端会话失效后需重新登录，云端历史保留。旧版 sessionStorage 凭证在加载时迁移；已签发 access token 按 Supabase 有效期策略处理。

语音最长 120 秒、8 MB，用户点击麦克风后直接录音，首次使用需浏览器麦克风授权；停止后发送到 STT 服务转写，回填草稿供用户校对后提交。应用不保存原始音频，第三方保留政策需由部署者确认；非 localhost 环境需要 HTTPS 获取麦克风权限。

## 测试与验收

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m tests.evals.run
npm --prefix apps/web run build
```

测试使用临时目录、合成数据和专用模型替身，不应继承真实服务密钥。离线测试不代表真实模型、Supabase、邮件和 Docker PDF 已完成云端验收。检索评测只是小型回归样例，不能代表真实业务召回率。

上线前至少完成：

1. 两个独立账号注册、验证、登录与私有记录隔离。
2. 多轮问答、历史恢复、New chat、清空上下文和删除。
3. Mock 答题、追问、复盘与重新登录后恢复。
4. 可读及扫描简历提取、事实确认、授权改写和历史版本。
5. Worker 编译、PDF 检查、私有存储同步和下载。
6. 真实模型的引用、事实保真、语音质量、费用与错误处理。

近期离线回归记录：Skill 扩充后全套 34 项测试通过；密码限制调整后，新增短/长密码与空密码用例，并与认证相关测试合计 10 项通过；前端构建通过。这些是各次修改的历史记录，并非本次文档更新重新运行了全量测试，也不等于真实模型能力已验收。

详见 [验收清单](docs/ACCEPTANCE.md)、[部署检查](docs/DEPLOYMENT_CHECKS.md)。历史检查报告仅代表当时状态，不代表当前环境已经验收。

## 后续优先事项

将耗时知识入库从 API 启动过程拆出并补充进度日志；将 Skill 关键词路由改为显式任务参数；落实一页与留白的实际排版检查；完成真实云端双账号及 PDF 全流程验收。以上是改进方向，不代表当前已经实现。

当前未实现完整流式回答、通用会话导出、收藏/阅读进度、共享队列和企业身份体系。文档或单元测试不能替代真实部署中的隔离、备份和模型全流程验收。

更多资料：[实施规划](IMPLEMENTATION_PLAN.md) · [架构说明](docs/ARCHITECTURE.md) · [部署指南](docs/DEPLOYMENT.md) · [内容维护](docs/CONTENT_GUIDE.md)。
