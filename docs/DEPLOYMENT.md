# 部署：GitHub → Vercel + Supabase + Docker 后端

## 组成与数据去向

|服务|用途|持久化内容|
|---|---|---|
|GitHub|源码与知识 Markdown|公共知识源、模板、配置、测试；不上传用户数据|
|Vercel|Vue 前端和 VitePress 手册|静态构建；不运行 Python 或 LaTeX|
|Supabase Auth|邮箱注册、验证、密码登录、刷新会话|账号与密码哈希，由 Supabase 管理|
|Supabase Postgres|业务记录、知识检索索引|偏好、Mock、简历事实/版本、聊天和引用、任务/checkpoint|
|Supabase 私有 Storage|原始与生成文件|JD、简历原件、TeX；PDF 通过 QA 后在 API 刷新任务状态时同步|
|Docker 主机|FastAPI 和无网络 PDF Worker|持久卷保存编译队列、TeX/PDF 工作区；需要备份|

不在业务表另存密码。`public.users.password_hash` 为兼容本地 ORM 保留的空列，SQL 约束禁止写入任何值。`public.users.auth_uid` 关联 `auth.users`；注册触发器自动同步资料。

保留规则：默认保留用户的 Mock 回答与复盘、简历修改版本和问答记录，直到用户删除。New chat 创建新的独立会话，旧会话保留。清空上下文保留历史可见，只将旧轮次排除出后续模型输入；当前所选文章/JD/简历范围仍保留。后续模型最多接收最近 10 轮，每轮历史问题 500 字、回答 1000 字；完整原文存数据库不截断。

删除会话会删除其问答与轨迹。删除简历会话会删除其版本、关联聊天、任务和文件；原件没有其他简历会话引用时才删除。删除 Mock 会删除回答、复盘与 checkpoint。云备份中的历史副本按 Supabase/主机备份保留策略到期清除，业务删除不承诺立即销毁备份。Supabase 控制台直接删除 Auth 账号会级联删除业务表行，但不会自动删除 Storage 对象或 Docker 文件；完整销户需管理员按该用户 UUID 清理私有桶和主机副本。

## 1. 创建 Supabase 项目并执行 SQL

1. 使用一个**新项目**。在 SQL Editor 打开并执行仓库根目录 `supabase/schema.sql` 的全部内容。它会创建与当前应用一致的表、pgvector 索引、Auth 资料同步触发器、RLS 和 `gtm-private` 私有桶。
2. 不要在旧的本地 PostgreSQL 表上直接叠加这份 SQL。`CREATE TABLE IF NOT EXISTS` 不能把旧表迁移成新表。当前 SQLite 本地账号不会自动成为 Supabase Auth 账号；部署默认是新环境，已有本机数据仍保留。
3. Authentication → Providers 启用 Email。建议开启 Confirm email，配置可用于生产的 SMTP、邮件发送额度和项目密码策略（应用只校验非空，实际策略由 Supabase 执行）。应用注册后会提示邮箱验证；验证完成后返回登录页。
4. Authentication → URL Configuration 设置正式 Vercel 域名为 Site URL，并将其加入 Redirect URLs。注册验证走 Supabase 的邮件链接，完成后用户回站登录，不需要前端接收 service role key。
5. 从 Project Settings/API 取得 Project URL、anon key 和 service_role key。后两项填入 Docker 主机环境；本项目不需要把 Supabase key 放到 Vercel 前端。
6. 从 Connect 复制 **Session pooler，5432 端口**的连接串（也可用支持 IPv6 的直接连接）。改为 `postgresql+psycopg://`，追加 `?sslmode=require`；密码中的特殊字符需 URL 编码。不用事务池 6543 端口作为本方案默认连接。

表对应关系：

|表|内容|
|---|---|
|`auth.users`|Supabase 账号凭证|
|`public.users`|账号 ID、邮箱、偏好；密码列始终为空|
|`business_records` `kind=mock/mock_answer`|Mock 题目、回答、评分、复盘|
|`business_records` `kind=resume/career/resume_version`|原件信息、事实、诊断、修改及历史版本|
|`business_records` `kind=chat_thread/conversation`|会话范围、上下文边界、完整问题/答案/引用|
|`business_records` `kind=learning_note/note_folder`|私有学习笔记与文件夹；笔记通过 `folder_id` 关联文件夹|
|`business_records` 其他 kind|私有 JD、任务、反馈、checkpoint 与执行轨迹|
|`knowledge_documents/knowledge_chunks`|公共知识及索引；私有 JD 不进入公共知识表|
|`auth_tokens`|仅保留本地开发兼容结构；Supabase 模式不使用|

RLS 限制用户只能读取自己的资料/业务行；浏览器无业务写入权限，所有修改都经 API 进行 owner 和业务规则校验，不能从 Supabase REST 伪造审核、成绩或文件状态。私有桶只允许读自己的 UUID 前缀；写入/删除只经受控 API。数据库连接串和 service role 会绕过 RLS，必须只放服务器，因此 API 的 owner 校验仍是必须的。

执行 `supabase/verify.sql` 可检查初始化对象。真实账号隔离还需最后一节的两个账号验收。

## 2. 上传 GitHub

在 GitHub 建仓库，建议首发使用私有仓库。现有项目已使用 Git；日常更新只需检查差异、提交并推送。仅在全新的源码副本尚无 `.git` 时初始化；不要重复覆盖 remote 或切换现有分支。首次初始化示例：

```powershell
git init
git add .
git status --short
git diff --cached --stat
```

确认暂存列表不含 `.env`、`.data`、`.venv`、`node_modules` 和任何真实用户上传文件，然后提交并用 GitHub Desktop Publish repository，或将 GitHub 仓库页面给出的 remote 添加后 push。

```powershell
git commit -m "Prepare GTM Atlas for Vercel and Supabase deployment"
git branch -M main
```

仓库已有 `.gitignore`、`.dockerignore`、`.vercelignore`；依赖锁文件、测试、Markdown 知识源、维护文档和 TeX 模板需要提交。保留本机 `.venv`、`node_modules` 和构建结果以便继续预览，这些不会提交。目录和本地数据边界见 [维护入口](README.md)。

## 3. 部署 Docker API 和 PDF Worker

使用一台支持 Docker Compose 和持久磁盘的 Linux 主机。此配置按**单 API 进程、单 Worker**运行；不要无状态扩容或让两个 Worker 消费同一队列。没有持久卷的临时容器不适用。

1. 将仓库克隆到主机。
2. 在根目录 `.env` 配置 Supabase、数据库、前端域名和模型接口。已有配置保留；`.env.supabase.formal` 仅是可能存在的本机私有副本，不是仓库提供的安装模板，不要直接复制覆盖 `.env`。配置项见下方表格。
3. `ALLOWED_ORIGINS` 填完整 Vercel 正式域名（多个域名逗号分隔，无末尾斜杠）。Vercel 每个 Preview 域名不会自动获准；需要时显式加入。
4. 设置 `PROVIDER_MODE=live` 并填服务端模型 Key。运行时已移除模拟返回，未配置服务会明确报错。STT、Vision、Embedding 需各自有效服务。
5. 执行：

```sh
docker compose -f infra/compose.production.yaml config --quiet
docker compose -f infra/compose.production.yaml up -d --build
docker compose -f infra/compose.production.yaml ps
curl --fail http://127.0.0.1:8000/api/v1/health
```

首次启动从 Markdown 构建公共知识索引，启用 Embedding 时会调用提供方，需要等待。初始化 SQL 已登记当前 migration；生产 Compose 不自动重复执行 Alembic 创建表。后续真实 schema 变更需要单独迁移。

API 只绑定主机 `127.0.0.1:8000`。在主机安装并启动 Caddy，将 `infra/Caddyfile` 用作配置，将 `API_DOMAIN` 设置为你的 API 域名，DNS 指向主机并开放 80/443。Caddy 自动签发 HTTPS 证书并转发 API。也可用主机平台的 HTTPS 反向代理，目标端口 8000，上传限制至少 11 MB，请求超时至少 120 秒。**不能让 Vercel 网页访问 `127.0.0.1:8000`，必须提供公网 HTTPS API 地址。**

Worker 无网络、不含 Supabase/数据库密钥，只挂载 artifacts 和队列卷。API 在用户刷新任务状态时将通过 QA 的 PDF 同步到 Supabase，确认上传成功后才返回 ready；同步失败返回错误，可重试，不会冒充已同步。完成编译但尚未刷新状态的 PDF 仍在 Docker 持久卷。备份这些卷，且不要使用 `docker compose down -v` 删除它们。

两个镜像在构建时预建并授权编译目录，新命名卷据此初始化为 UID 10001 可写。如果复用了旧的 root 所有者卷，先备份，再停服务并让主机管理员将这两个卷的目录所有者修正为 UID/GID 10001；不要通过删除卷解决权限问题。

应用按原方案保持单机文件队列和单进程限流。首次公开试用建议同时使用主机网关限流；多副本需另外实现共享队列/分布式限流。本次不把它改造成多机服务。

## 4. 连接 Vercel

1. Import GitHub 仓库，Root Directory 选择**仓库根目录**，不要改成 `apps/web`，因为构建需要根目录的 `knowledge/`。
2. 使用 Node.js 22，Framework Preset 选 Other。根目录 `vercel.json` 已配置安装、构建、输出目录和 SPA/VitePress 路由。
3. 添加环境变量 `VITE_API_BASE_URL=https://你的API域名`（填写 origin，不带 `/api/v1`）。它是可公开的地址。不要添加数据库密码、模型 Key 或 Supabase service role key 到 `VITE_*`。
4. Deploy。修改 Vite 环境变量之后要重新部署，因为 API 地址在构建时写入。
5. 确认首页、`/learn`、`/learn/ask`、`/history` 刷新能打开，`/handbook/` 及某个手册文章正常。

前端直接 HTTPS 请求 API，API 通过 CORS 限定域名。API 请求/文件不会经过 Vercel Function，不受其请求体容量限制。Auth 访问凭证和刷新凭证保存在当前站点 localStorage，关闭标签页或浏览器后重新打开会恢复会话，访问凭证过期时自动使用刷新凭证续期；旧版 sessionStorage 会话在页面加载时迁移。主动退出会清除本地凭证并同步其他已打开标签页的退出状态，同时请求服务端撤销会话；撤销失败也会清除本地登录并显示失败信息。清除浏览器站点数据、服务端撤销或刷新会话失效后需要重新登录，临时断网不主动删除凭证。Supabase 已签发 access JWT 的效力按项目有效期策略执行，建议短期有效期。

## 5. 上线前用两个账号验收

- A 注册、验证邮箱、登录；刷新页面后仍可用。B 独立注册。
- A 创建 Mock、答题并结束，重新登录后能看到回答和复盘。
- A 上传简历、确认事实、生成版本；Worker 编译后刷新状态，TeX/PDF 可下载，Supabase 私有桶出现对应对象。
- A 连续问两轮、离开页面、从历史恢复，再追问；New chat 后旧会话仍在。
- 清空上下文后旧消息显示“已移出上下文”，再提问时不使用旧轮次；删除会话后 API 与历史页均无法恢复。
- B 使用 A 的会话/版本/下载 ID 应得到 404；Supabase REST 和 Storage 也不能读取 A 的内容。
- A 删除简历/Mock/聊天，确认对应记录和适用文件被删除；其他账号及其他会话不受影响。
- 开启真实模型后核验引用、事实保真和真实多轮语义；离线 mock 测试不代表真实模型已验收。

仓库文档不记录账号连接状态、真实密钥和临时服务地址；初始化 SQL、线上邮件、Docker LaTeX、Supabase Storage/RLS 和公网 HTTPS 应在实际部署环境完成上述验收。

## 邮件找回密码

登录页右下角「忘记密码」使用 Supabase Auth 邮件重置流程，无需将服务端 Key 暴露给前端。在 Supabase 的 Authentication / URL Configuration 中，将 Site URL 设置为当前前端域名，并在 Redirect URLs 允许该域名下的 `/login?reset=1`（或对应的受控通配规则）。更换前端域名时同步更新。

邮件链接返回后，新密码表单仅在当前页面内使用恢复令牌，读取后移除 URL fragment；更新成功后返回登录。找回邮件沿用 Supabase 的邮件配置与发送限额。上线后用自己的测试账号检查真实收件和失效链接；自动化测试不会发送邮件。

此功能增加了 API 接口，发布前端的同时需更新 API；不涉及数据库 SQL 或 renderer。

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


## 本机 Cloudflare 临时隧道


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
