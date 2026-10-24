# 部署：GitHub → Vercel + Supabase + Docker 后端

## 组成与数据去向

|服务|用途|持久化内容|
|---|---|---|
|GitHub|源码与知识 Markdown|60 篇资料、模板、配置、测试；不上传用户数据|
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
3. Authentication → Providers 启用 Email。建议开启 Confirm email，配置可用于生产的 SMTP、邮件发送额度和密码策略（至少 12 字符）。应用注册后会提示邮箱验证；验证完成后返回登录页。
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
|`business_records` 其他 kind|私有 JD、任务、反馈、checkpoint 与执行轨迹|
|`knowledge_documents/knowledge_chunks`|公共知识及索引；私有 JD 不进入公共知识表|
|`auth_tokens`|仅保留本地开发兼容结构；Supabase 模式不使用|

RLS 限制用户只能读取自己的资料/业务行；浏览器无业务写入权限，所有修改都经 API 进行 owner 和业务规则校验，不能从 Supabase REST 伪造审核、成绩或文件状态。私有桶只允许读自己的 UUID 前缀；写入/删除只经受控 API。数据库连接串和 service role 会绕过 RLS，必须只放服务器，因此 API 的 owner 校验仍是必须的。

执行 `supabase/verify.sql` 可检查初始化对象。真实账号隔离还需最后一节的两个账号验收。

## 2. 上传 GitHub

在 GitHub 建仓库，建议首发使用私有仓库。当前目录原本尚未初始化 Git。使用 GitHub Desktop 的 Add local repository/Create repository，或在项目根目录运行：

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

仓库已有 `.gitignore`、`.dockerignore`、`.vercelignore`；依赖锁文件、测试、Markdown 知识源、原始需求和 TeX 模板需要提交。保留本机 `.venv`、`node_modules` 和构建结果以便继续预览，这些不会提交。清理记录见 `docs/CLEANUP_REPORT.json`。

## 3. 部署 Docker API 和 PDF Worker

使用一台支持 Docker Compose 和持久磁盘的 Linux 主机。此配置按**单 API 进程、单 Worker**运行；不要无状态扩容或让两个 Worker 消费同一队列。没有持久卷的临时容器不适用。

1. 将仓库克隆到主机。
2. 将 `.env.supabase.formal` 复制为根目录 `.env`，填入 Supabase URL、anon/service_role key、数据库连接串、正式前端域名以及模型配置。`.env` 不提交。
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

当前交付未连接用户的 Supabase/Vercel/GitHub，也未持有云端密钥；初始化 SQL、线上邮件、Docker LaTeX、Supabase Storage/RLS 和公网 HTTPS 必须在部署环境完成上述验收。
