# FoxWork 线上部署说明（PostgreSQL + Caddy）

> 本套部署面向全新服务器（`118.24.244.36`，Ubuntu 26.04 x86_64），与仓库内旧的
> MySQL 版（`docker-compose.yaml`，指向 `service.fastapiadmin.com`）完全独立、互不影响。

## 1. 架构

| 容器 | 镜像 | 说明 | 对外端口 |
| --- | --- | --- | --- |
| `foxwork-caddy` | `caddy:2-alpine` | TLS 自动签发 + 反向代理 + 静态站点 | 80 / 443 |
| `foxwork-backend` | `foxwork-backend:latest`（本地构建） | FastAPI，连 postgres/redis | 仅 127.0.0.1:8001 |
| `foxwork-postgres` | `postgres:18-alpine` | PostgreSQL 18 | 仅 127.0.0.1:5432 |
| `foxwork-redis` | `redis:7-alpine` | 会话/缓存/限流 | 仅 127.0.0.1:6379 |

域名路由（由 `docker/Caddyfile` 定义）：

- `admin.xfoxlab.com.cn` → 运营后台（`frontend/web` 产物，Vue3 SPA）
- `wxh5.xfoxlab.com.cn` → 小程序 H5（`frontend/app` 产物，uni-app）
- 两个域名的 `/api/v1/*` 都反代到 `backend:8001`

## 2. 前置条件

1. **域名解析**：`admin.xfoxlab.com.cn`、`wxh5.xfoxlab.com.cn` 的 A 记录指向 `118.24.244.36`。
   Caddy 的自动 HTTPS 依赖 DNS 生效，否则证书签发会失败。
2. **安全组**：腾讯云安全组放行 `80`、`443`（以及 SSH `12211`）。
3. **安装 Docker**（服务器为全新系统时）：
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker ubuntu   # 让 ubuntu 免 sudo 用 docker，重新登录生效
   ```

## 3. 部署步骤

### 3.1 构建前端产物（本机）

```bash
cd frontend/web && pnpm run build:prod      # 产物 → frontend/web/dist
cd ../app  && pnpm run build:h5             # 产物 → frontend/app/dist/build/h5
```

### 3.2 上传前端产物到服务器

```bash
# 运营后台
rsync -az -e "ssh -i ~/.ssh/foxwork_prod -p 12211" frontend/web/dist/ \
  ubuntu@118.24.244.36:/home/ubuntu/foxwork/docker/nginx/web/dist/
# 小程序 H5
rsync -az -e "ssh -i ~/.ssh/foxwork_prod -p 12211" frontend/app/dist/build/h5/ \
  ubuntu@118.24.244.36:/home/ubuntu/foxwork/docker/nginx/app/dist/build/h5/
```

### 3.3 上传后端源码 + 编排文件到服务器

服务器不跑构建（后端镜像本地构建见 3.4，也可在服务器 `docker compose build`）。
至少需要把以下内容放到服务器部署目录（如 `/home/ubuntu/foxwork`）：

- `backend/`（业务源码，Dockerfile 的 build context 根）
- `docker/backend/Dockerfile`、`docker/docker-compose.prod.pg.yaml`、`docker/Caddyfile`

### 3.4 准备环境变量

```bash
cd docker
cp .env.prod.pg.example .env.prod.pg
chmod 600 .env.prod.pg
# 编辑 .env.prod.pg：填入 POSTGRES_PASSWORD / REDIS_PASSWORD / SECRET_KEY 等真实值
#   SECRET_KEY=$(openssl rand -hex 32)
#   DATA_ENCRYPTION_KEY=$(openssl rand -hex 32)
```

### 3.5 启动

```bash
cd docker
# 上传目录需归 backend 运行用户（UID 1000）所有
mkdir -p backend/static/upload && sudo chown -R 1000:1000 backend/static/upload

docker compose --env-file .env.prod.pg -f docker-compose.prod.pg.yaml up -d --build
docker compose --env-file .env.prod.pg -f docker-compose.prod.pg.yaml ps
docker compose --env-file .env.prod.pg -f docker-compose.prod.pg.yaml logs -f backend
```

首次启动 backend 会自动建表 + 播种（菜单/角色/权限），随后健康检查转为 healthy。

## 4. 验证

```bash
# 容器状态
docker compose --env-file .env.prod.pg -f docker-compose.prod.pg.yaml ps

# 健康检查（本机）
curl -i -H 'Host: admin.xfoxlab.com.cn' http://127.0.0.1:8001/api/v1/monitor/health/check

# 公网（证书签发成功后）
curl -I https://admin.xfoxlab.com.cn/web/
curl -I https://wxh5.xfoxlab.com.cn/
```

## 5. 常用运维

```bash
cd docker
COMPOSE="docker compose --env-file .env.prod.pg -f docker-compose.prod.pg.yaml"

$COMPOSE logs -f backend          # 看后端日志
$COMPOSE restart backend          # 重启后端
$COMPOSE up -d --build backend    # 更新后端镜像并重建
$COMPOSE down                     # 停止全部（数据卷保留）
```

## 6. 注意事项

- **SSH**：服务器已改为密钥登录 + 端口 `12211`（密码登录已关闭）。连接：
  `ssh -i ~/.ssh/foxwork_prod -p 12211 ubuntu@118.24.244.36`
- **数据库迁移**：项目走「双轨制」，空库由 `create_all` 自动建表，存量升级靠 dev 自动迁移，
  不要手写 alembic migration（见 `DEVELOPMENT-LOG.md`）。
- **证书**：Caddy 自动申请/续期 Let's Encrypt 证书，无需手动维护；需保持 80/443 可达。
- **密钥轮换**：`SECRET_KEY` / `DATA_ENCRYPTION_KEY` 的轮换步骤见 `DEPLOYMENT.md` 第 3 节。
