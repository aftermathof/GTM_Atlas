# GTM Atlas

根据 [plan.md](plan.md) V5.1 开发的 GTM 学习与求职工作台：知识学习、面经与 Mock、简历诊断及授权改写，共享全局助手与语音输入组件。界面沿用用户提供的 GTM 精确设计规范。

## GitHub / Vercel / Supabase 部署

完整步骤见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。在新的 Supabase 项目 SQL Editor 执行 [supabase/schema.sql](supabase/schema.sql)，账号密码交给 Supabase Auth，私有业务记录存 Postgres，文件存私有 Storage。Vercel 托管前端；FastAPI 和无网络 PDF Worker 使用 [infra/compose.production.yaml](infra/compose.production.yaml) 部署在 Docker 主机。生产环境使用 `.env.supabase.formal`，前端配置 `VITE_API_BASE_URL`。

AI 问答支持登录后多轮保存、恢复历史、New chat、清空上下文及删除会话。New chat 保留旧记录；清空上下文只排除旧轮次，记录仍可查看。Mock 与简历版本默认保存，均可在历史页删除。以下 SQLite/本地 token 说明仅适用于 `AUTH_MODE=local` 开发模式。

## 本机预览

构建后一个 FastAPI 进程同时提供网页、API 与 VitePress 手册：

```powershell
cd 'C:\Users\64954\Desktop\GTM desk'
.venv/Scripts/python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000
```

- 网站：<http://127.0.0.1:8000>
- OpenAPI 与交互文档：<http://127.0.0.1:8000/docs>
- VitePress 知识手册：<http://127.0.0.1:8000/handbook/>

注册一个自己的账号，密码至少12字符。Mock 和简历必须登录。模型只调用真实服务，需配置有效的 LLM Key；缺失配置时明确报错，不返回模拟结果；未配置 STT 时不会返回虚构的识别结果。

已接入用户提供的 **30篇面经研究笔记 + 30篇学习/在职经验笔记**，资料展览室位于 `/learn`，栏目依次为GTM概览、岗位JD、面经、在职经验、GTM专有名词库，默认打开概览。卡片可打开完整研究笔记。当前这批来源不含独立JD；合成资料已移出正式知识库，仅保留在测试夹具中。原帖链接用于溯源，研究笔记不等于原帖逐字全文或企业官方结论。

简历默认使用用户提供的 `resume_template.tex`。原件保存在 `templates/latex/gtm-original/source.tex`，哈希与原文件一致；受控模板保持原字体、紫色、分栏与分隔线。字段提取与归属可人工校正，再由后端填充。资料导入、扩充、模板路径与本轮验收见 [docs/CONTENT_GUIDE.md](docs/CONTENT_GUIDE.md)。

## 从零安装

需要 Python 3.10+、Node.js 20+、uv。Docker 仅用于 PostgreSQL 与隔离 PDF 编译。

```powershell
uv venv --python C:/Python310/python.exe .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.lock -e .
Copy-Item .env.formal .env
cd apps/web
npm ci
npm run build
cd ../..
.venv/Scripts/python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000
```

仅首次安装复制 `.env`，不要覆盖已有密钥。若 uv/npm 的系统缓存无写权限，设置 `UV_CACHE_DIR=.data/uv-cache` 或使用 `npm ci --cache ./.npm-cache`。

前端热更新可在另一个终端运行 `cd apps/web; npm run dev`，访问 Vite 输出的本机地址；Vite 将 `/api` 代理到8000端口。`scripts/start.ps1` 可同时启动 API 与 Vite，退出前端时关闭它启动的 API。

## 配置真实服务

配置只在服务端 `.env`，修改后重启 API。浏览器不接收密钥。

|能力|配置|未配置时|
|---|---|---|
|文本模型|`PROVIDER_MODE=live`、`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`|未配置Key报503，不生成模拟输出|
|语音转写|`STT_BASE_URL`、`STT_API_KEY`、`STT_MODEL`|键盘输入可用；录音入口明确提示|
|扫描OCR|`VISION_BASE_URL`、`VISION_API_KEY`、`VISION_MODEL`|提示需要OCR，可手动录入再确认|
|语义检索|`EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL`|本地词法检索，界面明确标记|
|数据库|`DATABASE_URL`|SQLite本地开发数据库|

Adapter 使用 OpenAI-compatible chat/completions、audio/transcriptions、embeddings 接口；base URL 应包含服务需要的 `/v1` 等前缀。DeepSeek文本服务默认地址可直接使用，但它不提供此项目假定的STT或视觉能力，必须分别配置。

Embedding固定1536维，启用或更换模型后重新启动完成增量重建。PostgreSQL模式执行原生FTS+pgvector余弦检索+RRF；中文词法预处理使用二字片段，并不宣称是BM25或完整中文分词系统。SQLite仅是便于本机启动的开发降级，不能代替PostgreSQL验收。

语音最长120秒、8MB。用户主动勾选第三方STT传输同意后才能开始，转写追加到草稿，校对后才进入业务接口。应用不保存音频，仅保存耗时元数据；第三方服务自身保留策略由部署者确认。部署到非localhost时需HTTPS才能获得麦克风权限。

## PostgreSQL 与隔离 PDF Worker

先启动 Docker Desktop。首次复制 `.env.formal` 到 `.env` 并按需填入服务配置。

```powershell
docker compose -f infra/compose.yaml up --build
```

API容器启动时运行Alembic，初始化pgvector、FTS和向量索引。开发默认密码仅供本机，公开部署前必须更换 `POSTGRES_PASSWORD` 并配置HTTPS、备份及运维鉴权。

Renderer独立容器**无网络**，只通过私有卷读取受控JSON任务，不持有数据库或模型密钥。容器只读根目录、非root、CPU/内存/进程限制；XeLaTeX禁用shell-escape，输入全部转义。生成PDF检查文本完整、教育等所有事实、边界及页数。通过后API才允许鉴权下载。原始文件和历史版本不覆盖。

本机未启动Worker时可以完成诊断、建议、授权版本生成与 `.tex` 导出；PDF任务显示等待Worker，不会冒充已完成。启动容器方案后在「修改与版本」点击刷新编译状态。当前模板页数目标为不超过2页，超出时拦截并需手动精简；没有自动压缩字体隐藏溢出。

单独使用生产数据库迁移：

```powershell
.venv/Scripts/python -m alembic upgrade head
```

## 核心使用流程

1. 知识：浏览目录/搜索 → 文章与段落 → 当前文章问答或学习库问答 → 点击引用回原文。没有足够依据时明确拒答。
2. Mock：登录 → 选择岗位、行业、题数、语言、随机种子 → 文字或确认后的语音答题 → 最多一次自适应追问/题 → 六维反馈与报告。刷新或服务重启后可从历史继续。
3. 简历：选择岗位并上传/粘贴目标JD → 上传不可变简历原件 → 模型提取来源绑定的关键信息与段落归属（需要有效模型配置）→ 校对确认事实 → 查看诊断。只诊断不会生成版本。用户上传的JD是私有资料，不进入公共索引。
4. 改写：选择项目/实际经历等未锁定段落 → 根据目标JD、学习框架与面经参考生成建议 → 核对建议和来源 → 确认授权 → 填入后台模板生成版本 → `.tex`导出/隔离PDF任务 → 预览或下载。AI建议只回填草稿，不自动生成。简历RAG仅使用许可范围内的资料，不把岗位要求写成候选人事实。
5. 回滚：选择旧版本 → 回到此版本 → 仅勾选想保留修改的段落（例如技能栏） → 生成新版本。旧版完整保留。

Mock由模型按JD、岗位、语言、难度规划并持久化题目，再对用户确认的回答评分与追问。基础简历分数是可解释的完整性规则，AI仅提供诊断文字，**不宣称是精确岗位匹配、官方ATS或录用概率**。数字与锁定保护为确定性规则；复杂语义事实保真仍需要用户核对。

## 测试与评测

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m tests.evals.run
cd apps/web
npm run build
```

测试临时文件固定在工作区 `.data/pytest-temp`。若在受限Windows沙箱运行TestClient卡在socketpair，需要允许本机socket或在正常终端运行；不是业务接口需要联网。

检索eval包含30条人工编写的玩具Query与3篇自写文章，输出 `.data/eval-report.json`。这里只是回归样例，不声称代表真实RAG质量或统计显著性。真实语义召回、引用支持度、STT中英混合准确率与人工评分一致性需使用实际服务和人工数据集复测。

完整验收映射、人工操作与已知限制见 [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md)。组件职责与依赖清单见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 数据与权限

- 用户简历、会话、版本、下载和checkpoint按owner鉴权。本地模式 Bearer 令牌只存服务端哈希，7天过期；Supabase 模式使用 Auth 签发的访问/刷新凭证。浏览器仅存当前标签页 sessionStorage，退出时撤销当前会话。
- `knowledge/` Markdown是事实源；只索引 `public_display` 且未弃用的资料。其他许可首版全部保守排除，不能靠网页隐藏实现许可控制。
- 索引支持SHA256增量、重复ID与相同正文检查、删除传播。重建可由配置的 `ADMIN_EMAIL` 登录账号调用管理员接口。
- 领域Skills仅从仓库受控目录读取，版本1、工具白名单；用户Markdown不能注册工具或升级为Skill。模型无任意工具执行权限。
- API请求限流、上传大小限制、超时、无无限模型重试；不记录模型密钥或原始音频，SQL异常隐藏参数。当前限流为单进程内存实现，公开多副本部署须改为共享网关/Redis限流。
- 历史页可删除简历会话及版本；没有其他会话引用时删除原件。测试数据是合成内容，实际部署应制定数据库/备份保留和删除策略。
