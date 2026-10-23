# Vercel + Supabase 部署改造

用户已确认：Vercel 前端；Supabase Auth/Postgres/私有 Storage；Docker 主机运行 FastAPI 与无网络 PDF Worker。

## 实施与验收

- [x] 清理安装缓存、测试输出和 Python 字节码；保留 `.data/atlas.db`、上传、生成版本、60 篇资料、模板、测试和锁文件。清单写入 `CLEANUP_REPORT.json`。
- [x] Supabase Auth 通过服务端调用注册、登录、刷新、注销和 token 校验；本地账号模式仍用于离线开发。验证伪造 token 与跨账号请求被拒绝，业务表不保存 Supabase 密码。
- [x] 提供与 SQLAlchemy 现有表一致的初始化 SQL，绑定 `auth.users`、RLS 和私有 Storage；知识表只公开许可内容。数据库初始化由部署步骤执行，不在每次容器启动重建。
- [x] 简历/JD 原件与 TeX/PDF 上传私有 Storage；Docker 持久卷用于无网络 Worker 的队列与编译工作区。下载始终先校验归属；检查 Storage 错误不会冒充成功。
- [x] 独立 `chat_thread` 聚合关联问答记录。上下文边界保存在会话中，模型只接收边界之后最近 10 轮；每轮只发送有上限的文本。恢复会话必须校验 owner 和资料范围。New chat 保留旧会话；清空上下文保留记录；删除会话删除其问答和轨迹。
- [x] 前端提供恢复、新建、清空和删除入口；历史页支持 Mock、简历与聊天查看/删除；保留旧逐条问答的查看兼容。
- [x] Vercel 构建 Vue/VitePress，通过 HTTPS 直接调用 Docker API（避免 Vercel 函数上传容量限制）；CORS 限定域名，密钥只在服务端环境变量。提供生产 Compose、环境模板和逐步部署文档。
- [x] 新增行为测试先确认失败，再实现；运行全部 pytest 与前端构建。云端尚无凭证时明确区分离线测试与线上验收。

## 保留规则

默认持续保留账号偏好、Mock 回答与复盘、简历事实与版本、AI 会话与引用，直到用户删除。清空上下文只影响后续模型输入。清理脚本不得删除用户数据。Supabase 备份和模型提供方的保留周期由部署者另外管理。

## 执行

在当前非 Git 工作目录内直接实现。先交付可检查的源码与部署说明，不自动创建云资源或向 GitHub 上传本地用户数据。

## 验证边界

31 项离线测试、前端构建和 Compose 语法检查通过；Supabase/Docker/Vercel 云端验收未执行，见 DEPLOYMENT_CHECKS.md。
