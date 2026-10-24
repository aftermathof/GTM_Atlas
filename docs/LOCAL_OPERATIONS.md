# 本机服务关闭与重启

当前方案由 Vercel 前端、本机 Cloudflare 临时隧道、Docker API 与 PDF Worker、Supabase 组成。本机休眠、关机或断网会影响后端访问。

## 启动与更新

打开 Docker Desktop，等待引擎启动。在项目根目录运行：

```powershell
docker compose -f infra/compose.production.yaml up -d
docker compose -f infra/compose.production.yaml ps
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

修改后端代码或 `knowledge/` 内容后，需要重新构建 API：

```powershell
docker compose -f infra/compose.production.yaml up -d --build api
```

前端改动需重新部署到 Vercel。`git push` 只同步 Git；是否触发 Vercel 构建取决于项目的 Git 集成配置。

## 临时隧道

本机健康检查通过后，在另一个 PowerShell 窗口启动已安装的 `cloudflared`：

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

若命令不在 PATH，使用本机实际安装路径。保留此窗口运行，使用日志中本次返回的 HTTPS 地址。临时隧道重启后地址可能改变，需要同步前端 API 配置并重新部署。配置项及部署步骤见 [部署指南](DEPLOYMENT.md)。

本机健康检查失败时先检查 Docker 日志；本机成功但公网失败时检查隧道与网络；公网成功但网页失败时检查前端 API 地址和跨域配置。不要把所有 `Failed to fetch` 都当成数据库问题。

## 关闭

隧道前台运行时，在对应窗口按 `Ctrl+C`。若由后台进程启动，先核对具体进程再停止。

暂停容器且保留数据：

```powershell
docker compose -f infra/compose.production.yaml stop
```

不要为日常关闭执行 `down -v`，它会删除该 Compose 栈的数据卷。根目录 `.env`、本机 `.data/` 与 Docker 数据卷应按实际存储模式备份；它们不会随 Git 自动备份。
