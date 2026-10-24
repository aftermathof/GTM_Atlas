# 部署准备验收（2026-10-23）

## 已验证

- `pytest -q --tb=short`：**34 passed**。保留 PyMuPDF、LangGraph、Starlette/AnyIO 的上游弃用警告。
- `npm run build`：Vue TypeScript 检查、Vite 和 VitePress 构建通过。
- `docker compose -f infra/compose.production.yaml config --no-env-resolution --quiet`：配置语法通过；此命令不启动容器，也不验证尚未创建的 `.env` 实值。
- 测试覆盖：两账号的会话/简历/Mock 隔离、重启后恢复、完整历史保存、模型输入轮次/长度上限、清空上下文、新会话、关联聊天删除、私有文件下载与删除、失败队列事实清理。
- Supabase HTTP 合同的离线测试覆盖注册邮箱确认、登录、访问凭证验证、刷新、注销、私有 Storage 读写，以及桶级 `DELETE` + `prefixes`。模拟 HTTP 边界；未调用真实 Supabase。
- 浏览器使用合成 QA 账号验证：登录、问答入库、New chat、恢复历史、清空上下文标记、历史页链接恢复，控制台无错误；结束后已退出并关闭临时测试页面。
- 上传范围审计使用临时 Git 索引检查 `.gitignore`：不包含 `.data`、`.venv`、`node_modules` 或真实 `.env`。候选文件清单见 `GITHUB_UPLOAD_FILES.txt`。
- 代码只读复查的三项问题已修正：新编译卷的 UID 10001 权限、Storage 删除合同、失败任务事实文件残留。

## 待云端验收

- 实际 Supabase SQL 执行、Auth 邮件、数据库连接、RLS 和私有桶隔离。
- Docker 镜像构建/容器运行、独立卷权限与 XeLaTeX PDF 编译。
- GitHub 推送、Vercel 正式构建路由、公网 HTTPS/CORS。
- 真实 LLM/STT/Vision/Embedding 的质量、配额与响应时间。

本机 Docker 引擎未启动，且没有用户云端项目凭证，因此未将上述事项标为完成。完整部署流程与两账号验收步骤见 `DEPLOYMENT.md`。

## 正式模式与界面验收

- 运行时仅调用真实模型，缺少 Key 或旧模拟配置返回 503；所有固定模型回复仅存在于 tests 的替身中。
- 正式 knowledge 及本地索引均为 60 篇真实来源研究笔记，合成文档数为 0；6 份早期资料移入测试夹具，Docker/Vercel 不发布测试目录。
- 三份配置模板已改名 `.env.formal`、`.env.supabase.formal`、`apps/web/.env.formal`，引用与忽略规则同步更新。
- 默认栏目与顺序：GTM 概览、岗位 JD、面经、在职经验、GTM 专有名词库；无全部资料与基础示例开关；知识/面经页无 JD 上传入口，简历流程的 JD 上传保留。
- 全局助手固定全站公共知识范围，不受资料页岗位/行业过滤影响；无范围下拉框和欢迎区。当前文章、当前简历的专属问答继续按原权限隔离。
- 1440px 桌面与 390px 手机验证通过，无页面横向溢出；在职经验展示 30 张卡片，控制台无错误。
- 当前未提供真实服务配置，因此不宣称外部 LLM、STT、Embedding、Supabase 或 Docker 已完成线上验收。
