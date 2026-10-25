# 部署与数据库迁移

以下命令均在项目根目录执行。

| 文件 | 用途 |
| --- | --- |
| `compose.production.yaml` | Supabase 模式的 API 与隔离 PDF Worker |
| `compose.yaml` | 包含 PostgreSQL 的独立部署栈 |
| `compose.renderer-local.yaml` | 本机 API 配合隔离 PDF Worker |
| `Dockerfile.api` | 后端及知识库镜像 |
| `Dockerfile.renderer`、`renderer_worker.py` | PDF 编译镜像与队列处理 |
| `renderer-fonts/` | 模板使用的 Font Awesome 字体、支持文件及许可证；构建时安装 |
| `Caddyfile` | 自有服务器反向代理配置 |
| `migrations/` | Alembic 数据库迁移；按所选部署模式使用 |

更新当前生产模式 API：

```powershell
docker compose -f infra/compose.production.yaml up -d --build api
docker compose -f infra/compose.production.yaml ps
docker compose -f infra/compose.production.yaml logs --tail 50 api
```

修改模板、字体或编译依赖后同步更新两个服务：

```powershell
docker compose -f infra/compose.production.yaml up -d --build api renderer
```

三份 Compose 配置用于不同部署方式，按 [部署指南](../docs/DEPLOYMENT.md) 选择。Supabase 初始化与验证 SQL 在 [../supabase/](../supabase/)，不是每次修改 Markdown 都要执行。

本机关闭、重启与临时隧道见 [本机服务维护](../docs/LOCAL_OPERATIONS.md)。
