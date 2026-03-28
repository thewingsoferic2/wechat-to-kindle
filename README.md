# 微信推Kindle

把微信公众号文章一键转换为 EPUB 并推送到 Kindle。

## 项目结构

```
wechat-to-kindle/
├── app/
│   ├── main.py          # FastAPI 路由
│   ├── fetcher.py       # 抓取微信文章
│   ├── converter.py     # 生成 EPUB
│   └── sender.py        # 发送邮件到 Kindle
├── static/
│   └── index.html       # 前端页面
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 部署步骤（Render.com，免费）

### 第一步：准备邮件服务

推荐使用 [Resend](https://resend.com)（每月 3000 封免费）：

1. 注册账号，添加并验证你的域名
2. 创建 API Key
3. 记下发件地址，例如 `kindle@yourdomain.com`

也可以用 Gmail：在 Google 账号设置中生成「应用专用密码」。

### 第二步：部署到 Render

1. 将本项目 push 到 GitHub
2. 登录 [render.com](https://render.com)，新建 **Web Service**
3. 连接你的 GitHub 仓库，选择 `wechat-to-kindle` 目录
4. 设置如下：
   - **Environment**: Docker
   - **Instance Type**: Free

5. 在 **Environment Variables** 中添加：

   | 变量名 | 说明 |
   |--------|------|
   | `SENDER_EMAIL` | 发件地址，如 `kindle@yourdomain.com` |
   | `RESEND_API_KEY` | Resend API Key（用 Resend 时填） |

6. 点击 Deploy，等待部署完成

### 第三步：配置 Amazon Kindle 白名单

用户使用前需要一次性设置：

1. 登录 Amazon 官网 → 账户与列表 → 管理内容和设备
2. 选择「首选项」→「个人文档设置」
3. 在「已批准的个人文档电子邮件列表」中添加你的 `SENDER_EMAIL`

完成后即可正常使用。

## 本地开发

```bash
cd wechat-to-kindle

# 复制环境变量
cp .env.example .env
# 编辑 .env 填入你的配置

# 使用 Docker
docker compose up

# 或直接用 Python
pip install -r requirements.txt
uvicorn app.main:app --reload
```

访问 http://localhost:8000

## 使用方法

1. 在微信中打开公众号文章，点击右上角「...」→「复制链接」
2. 打开网页，粘贴链接（每行一个，最多 20 篇）
3. 填入 Kindle 邮箱地址，点击「推送到 Kindle」
4. Kindle 联网后自动同步，在「文档」中查看

## 限制说明

- 仅支持 `mp.weixin.qq.com` 链接
- 需要设付费墙的文章无法抓取
- 每次最多推送 20 篇合并为一个 EPUB
