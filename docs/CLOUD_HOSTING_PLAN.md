# GTM Atlas 云服务器与固定域名部署方案

核对日期：2026-10-24。本文是部署方案，没有购买资源、修改 DNS 或执行云端迁移。

## 1. 推荐与预算

推荐保留 Vercel 前端和现有 Supabase，将 FastAPI 与 PDF renderer 迁移到一台持续运行的 Linux 云服务器，通过 Caddy 提供固定域名和 HTTPS，取消临时 Cloudflare Tunnel。

适用范围：个人项目、小规模试用、低并发。单台主机不是高可用集群，重启、发布、故障仍可能短暂中断。

本次从 DigitalOcean 官网公开价格表读到：

| 配置 | SSD | 月价 | 用途 |
| --- | --- | --- | --- |
| 1 vCPU / 1 GiB | 25 GiB | US$6 | 仅轻量 API 试运行；完整 PDF 功能余量不足 |
| 1 vCPU / 2 GiB | 50 GiB | US$12 | 完整后端低并发起步配置，先做内存与 PDF 验收 |
| 2 vCPU / 4 GiB | 80 GiB | US$24 | 更宽裕的构建、检索、PDF 并行资源 |

Porkbun 当前普通非溢价 .com 的注册、续费均显示 US$11.08/年。具体域名必须可注册；高级域名、税费、汇率和结算价格另计。

按 US$1 ≈ ¥7.3 仅作预算换算：

| 方案 | 服务器全年 | 域名全年 | 基础全年合计 | 折合每月 |
| --- | --- | --- | --- | --- |
| 1 GiB 轻量试运行 | US$72 | US$11.08 | 约 ¥607 | 约 ¥51 |
| 2 GiB 完整功能起步 | US$144 | US$11.08 | 约 ¥1,133 | 约 ¥95 |
| 4 GiB 较宽裕配置 | US$288 | US$11.08 | 约 ¥2,184 | 约 ¥182 |

这不是全网绝对最低价，而是本次有官网明码价格依据的常规预算。新客优惠、年付特价可能更低，要核对机房、续费、内存、流量、公网 IPv4 及售后，不能只比较首年标价。

以上不含：模型/Embedding/STT/Vision 调用、额外备份、超额流量、付费邮件、Vercel/Supabase 升级和税费。现有免费套餐能否继续免费，取决于额度、休眠规则与用途条款。付费 VPS 不会使 Supabase 免费项目也自动获得持续在线保障。

建议先预留每月 ¥100–150 的基础运维预算，模型费用单独按实际用量核算；需要付费数据库和前端套餐时重新计算。

## 2. 架构和选区

```text
用户浏览器
  ├─ HTTPS → Vercel：前端页面
  └─ HTTPS → api.你的域名 → 云服务器上的 Caddy
                                  └─ 127.0.0.1:8000 → Docker FastAPI
                                          ├─ Supabase Auth / Postgres / Storage
                                          ├─ 模型、Embedding、STT、Vision API
                                          └─ 本机持久队列 → 隔离 PDF renderer
```

域名只需购买一个，API 使用其 api 子域名，不需要为子域名单独买域名。前端可以继续使用现有 Vercel 域名。

先在 Supabase 控制台确认数据库区域，再选主机区域。优先让 API 与数据库在同区域或附近；若数据库在新加坡，可先测试新加坡主机。面向中国大陆的访问需同时测用户到主机的线路，地域相近不等于线路一定快。

香港/新加坡方案通常无需中国大陆服务器网站备案；域名实名认证等要求以注册商为准。若采用中国大陆主机，需要按服务商要求办理备案并确认境外数据库及模型的网络可达性。

## 3. 主机准备

1. 建议 Ubuntu 24.04 LTS、x86_64、2 GiB 内存、约 50 GiB 持久盘、公网 IPv4。配置是预算起点，不是已经通过负载测试的容量承诺。
2. 安装 Docker Engine、Compose 插件、Git 和主机版 Caddy；启用 Docker/Caddy 开机启动。
3. 使用 SSH 密钥和普通运维用户；SSH 仅允许可信来源，公网开放 80/443。API 8000 保持回环绑定，不向公网开放数据库端口。
4. 配置磁盘用量告警、Docker 日志轮转。小内存主机可设置适量 swap 作为应急，不能替代真实内存。
5. 域名 DNS 建立 api 的 A 记录指向服务器 IPv4。没有可用 IPv6 时不要添加 AAAA；首次验收建议先使用直接 DNS 解析。

## 4. 部署现有项目

先将准备上线的源码与 knowledge Markdown 提交到仓库，或通过安全文件传输复制。不要同步 .env、.data、用户上传文件到 Git。

在服务器将项目放在 /opt/gtm-atlas，并安全创建根目录 .env。沿用现有 Supabase 和模型配置，设置：

```dotenv
ALLOWED_ORIGINS=https://gtm-atlas-v1.vercel.app
PROVIDER_MODE=live
```

数据库、Supabase service role 和模型密钥只放服务器 .env，并限制文件读取权限。复用现有 Supabase 项目时，不重新执行初始化 schema.sql；真实表结构升级按独立迁移处理。

从服务器的项目根目录执行：

```bash
cd /opt/gtm-atlas
docker compose -f infra/compose.production.yaml config --quiet
docker compose -f infra/compose.production.yaml up -d --build
docker compose -f infra/compose.production.yaml ps
curl --fail http://127.0.0.1:8000/api/v1/health
```

首次部署启动 api 和 renderer；后续仅更新 Markdown 时才单独重建 api。首次 Embedding 导入可能需要等待并产生调用费。现有 Compose 已设置 restart: unless-stopped，但还需要宿主机 Docker 服务正常启动。

PDF 容器已有无网络、非 root、只读根文件系统和 768MB 内存上限。不要为上线移除这些隔离设置；2 GiB 主机需串行验证 PDF 生成与问答，并观察峰值内存。

## 5. 固定域名和 HTTPS

仓库已有 infra/Caddyfile。最简单的主机配置是将其中域名变量替换为实际域名，写入主机 /etc/caddy/Caddyfile：

```caddyfile
api.example.com {
    request_body {
        max_size 11MB
    }
    reverse_proxy 127.0.0.1:8000
}
```

上面的 example.com 必须替换为已购买并完成 DNS 解析的实际域名。也可以沿用仓库的 {$API_DOMAIN} 写法，但必须把该环境变量配置到 Caddy 的 systemd 服务环境；仅在 SSH 终端 export 不会自动传给服务。

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable --now caddy
sudo systemctl reload caddy
curl --fail https://api.example.com/api/v1/health
```

80/443、DNS 与证书签发条件满足时，Caddy 自动申请和续期证书，无需购买付费 SSL。此处按主机安装 Caddy；若改为容器运行，127.0.0.1 的网络含义不同，不能直接照抄上游地址。

## 6. 迁移数据与前端切换

1. 数据库继续使用同一 Supabase 项目，无需整库搬迁。确认新旧服务版本兼容。
2. 当前本机 Docker 的 private-data、render-artifacts、render-queue 三类命名卷应盘点并备份。新服务器空卷不会自动带上本机待处理 PDF、队列和本地文件。
3. 切换前暂停旧端写入/处理任务，做一致性备份，经安全传输恢复到新主机实际使用的命名卷，核对 UID/GID 10001 的访问权限。不要把旧队列直接合并到正在消费的新队列。
4. 测试 HTTPS API、登录、知识列表、带引用的 AI 问答、上传下载、PDF 和两个账号的权限隔离；测试主机重启后服务恢复。
5. 在 Vercel 设置 VITE_API_BASE_URL=https://api.实际域名，不带 /api/v1；重新部署前端。API 的 ALLOWED_ORIGINS 需允许实际前端域名。
6. 在浏览器 Network 核对请求已经指向新域名。验收后关闭旧临时隧道与旧 API，防止两端同时处理业务。保留迁移前备份。

若需要回滚，先停止新端写入并评估切换后新产生的数据、文件和任务，再切回旧端。不能只恢复旧镜像却忽略新增文件。

## 7. 以后更新 Markdown 的流程

本机修改并校验 → Git commit/push → 服务器拉取同一版本 → 重建 API → 检查健康与列表。git push 只有配置了自动部署才会自动更新服务器。

```bash
cd /opt/gtm-atlas
git pull --ff-only
docker compose -f infra/compose.production.yaml up -d --build api
curl --fail https://api.example.com/api/v1/health
```

仅改后端知识 Markdown 时不需要改固定域名，不需要重复执行 Supabase 初始化 SQL。若同次修改涉及前端静态内容或页面代码，还要触发 Vercel 构建。后端启动会按现有导入逻辑更新索引，应等待健康并核对实际内容；简单重启旧镜像不会复制新文件。

## 8. 备份、监控与速度

- 备份数据库、Storage 以及主机三个持久卷；备份放到另一存储位置，定期做恢复测试。托管数据库和 Storage 的备份范围分别确认。
- 外部监测 HTTPS health，并监测 API 错误、磁盘、内存、证书和备份失败。容器 unhealthy 不会仅凭 restart 策略自动重启，监测应能告警并触发人工处理。
- 发布前保留上一版本、备份文件和恢复步骤。单机重建可能短暂中断，不承诺零停机。
- 不执行 docker compose down -v，以免误删持久卷。
- CORS 不是防滥用措施；公网开放模型功能前核对应用鉴权、现有限流和模型消费上限。
- 云部署改善持续可用性并移除临时隧道链路，但检索与生成仍需独立优化。按相同问题测总耗时、数据库检索和模型耗时后比较，不承诺迁移后秒回。

## 9. 报价依据

- DigitalOcean Droplets：https://www.digitalocean.com/pricing/droplets
- Porkbun 域名价格：https://porkbun.com/products/domains/com
- 当前项目配置：infra/compose.production.yaml、infra/Caddyfile、docs/DEPLOYMENT.md。

价格是本次读取到的公开标价，按选区、库存、税费和结账页面确认；本方案没有实际订购或做云服务器线路测试。
