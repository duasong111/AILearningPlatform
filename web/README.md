# AiTeach · Web

> 智能体教学平台前端 —— Vue 3 + Vite + TypeScript + Element Plus + Pinia + Vue Router
> 设计语言遵循 [`DESIGN-x.ai.md`](./DESIGN-x.ai.md),开发规范遵循 [`PROJECT-RULES.md`](./PROJECT-RULES.md)

---

## 目录

1. [快速开始](#1-快速开始)
2. [环境要求](#2-环境要求)
3. [配置说明](#3-配置说明)
4. [开发命令](#4-开发命令)
5. [项目结构](#5-项目结构)
6. [开发协同规范](#6-开发协同规范)
7. [新增功能模块的标准流程](#7-新增功能模块的标准流程)
8. [局域网联调](#8-局域网联调)
9. [常见问题](#9-常见问题)
10. [构建与部署](#10-构建与部署)

---

## 1. 快速开始

```bash
# 1. 进入前端目录
cd web

# 2. 复制环境变量模板,按需填值
cp .env.example .env

# 3. 安装依赖
npm install

# 4. 启动开发服务器
npm run dev
```

启动成功后控制台会打印两个地址:

```
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://<你的局域网 IP>:5173/    ← 同 WiFi 设备可访问
```

---

## 2. 环境要求

| 要求 | 版本 | 检查命令 |
|------|------|----------|
| Node.js | `^20.19.0` 或 `>=22.12.0` | `node -v` |
| npm | 跟随 Node 一起装即可 | `npm -v` |
| 推荐 IDE | VS Code + **Volar** 插件 | — |
| **必须禁用** | Vetur (与 Volar 冲突) | — |
| 浏览器调试 | Chrome / Edge + **Vue.js DevTools** 插件 | — |

> ⚠️ Node 版本过低会让 `vite` 直接报错。用 [`nvm`](https://github.com/nvm-sh/nvm) 管理 Node 版本最省事。

---

## 3. 配置说明

### 3.1 环境变量 (`.env`)

**位置**:`web/.env`(本地,不进 Git);`web/.env.example`(模板,进 Git)

**当前变量**:

| 变量名 | 必填 | 示例 | 说明 |
|--------|------|------|------|
| `VITE_BASE_URL` | ✅ | `127.0.0.1:8000` | 后端 API 地址,**不带协议** —— [`http.ts`](src/api/http.ts) 会自动拼上 `http://` |

**典型几套配置**:

```env
# 本机开发(后端跑在同一台机器)
VITE_BASE_URL=127.0.0.1:8000

# 局域网联调(后端跑在同事电脑/远程开发机)
VITE_BASE_URL=192.168.18.234:8000

# 用 mDNS 域名避免 IP 漂移(macOS 自带)
VITE_BASE_URL=duasong-mac.local:8000
```

> ⚠️ **改完 `.env` 必须重启 `npm run dev`**,Vite 只在启动时读一次。
> ⚠️ Vite 的环境变量**不做 shell 风格插值**,`VITE_BASE_URL=${window.location.host}` 这种写法会被当成字面量字符串,不要这么写。

### 3.2 类型声明 ([`env.d.ts`](env.d.ts))

新增 `VITE_*` 变量时,同步在 `env.d.ts` 的 `ImportMetaEnv` 接口里加一行:

```ts
interface ImportMetaEnv {
  readonly VITE_BASE_URL: string
  readonly VITE_NEW_VAR: string   // ← 新增字段
}
```

这样 `import.meta.env.VITE_NEW_VAR` 才有类型提示,拼错会被 TS 报错。

### 3.3 Vite 配置 ([`vite.config.ts`](vite.config.ts))

关键配置说明:

| 配置 | 值 | 作用 |
|------|-----|------|
| `resolve.alias['@']` | `./src` | 全局 `@/*` 别名,导入用 `@/api/http` 而不是相对路径 |
| `server.host` | `true` | 监听 `0.0.0.0`,**让局域网其他设备能访问** |
| `server.port` | `5173` | 固定端口,不随机切换 |
| `server.strictPort` | `true` | 端口被占直接报错,避免局域网设备打开旧端口的页面 |

### 3.4 TypeScript 配置

项目用 **strict 模式 + `noUncheckedIndexedAccess`**,代码内**禁止 `any`**:

- `tsconfig.json` —— 项目主入口,引用下面三个
- `tsconfig.app.json` —— 业务代码编译配置
- `tsconfig.node.json` —— `vite.config.ts` 等 Node 端配置编译
- `tsconfig.vitest.json` —— 单测编译配置

### 3.5 路由守卫配置

[`router/index.ts`](src/router/index.ts) 通过 route meta 控制访问权限:

```ts
{
  path: '/dashboard',
  meta: { requiresAuth: true, title: 'Dashboard — AiTeach' },
  // ⬆ 未登录会被 beforeEach 拦截到 /login?redirect=/dashboard
}

{
  path: '/login',
  meta: { guestOnly: true, title: 'Sign in — AiTeach' },
  // ⬆ 已登录会被弹回 /
}
```

登录态由 [`stores/user.ts`](src/stores/user.ts) 维护,通过 `pinia-plugin-persistedstate` 持久化到 `localStorage`(key=`aiteach.user`)。

---

## 4. 开发命令

| 命令 | 作用 | 何时用 |
|------|------|--------|
| `npm run dev` | 启动开发服务器(HMR) | 日常开发 |
| `npm run build` | 类型检查 + 生产构建 → `dist/` | 上线前 |
| `npm run preview` | 本地预览构建产物 | 验证产物 |
| `npm run type-check` | 仅做 `vue-tsc` 类型检查 | CI / 提交前 |
| `npm run test:unit` | 跑 Vitest 单测 | 改了 store / composable 后 |
| `npm run format` | Prettier 格式化 `src/` | 提交前 |

---

## 5. 项目结构

```
web/
├── public/                      静态资源(直接拷贝到 dist 根)
├── index.html                   入口 HTML,引入 Inter / JetBrains Mono 字体
├── .env / .env.example          环境变量
├── DESIGN-x.ai.md               设计规范(颜色 / 字号 / 间距 / 组件)
├── PROJECT-RULES.md             开发协同规范(必读)
│
└── src/
    ├── main.ts                  入口:注册 Pinia / Router / Element Plus / PrimeVue
    ├── App.vue                  根组件,只放 <router-view>
    │
    ├── router/
    │   └── index.ts             路由表 + beforeEach 守卫
    │
    ├── views/                   页面级组件(路由直接映射)
    │   ├── home/                每个功能模块一个子文件夹
    │   │   ├── HomeView.vue     主页 (xAI 风格 + 多种特效)
    │   │   ├── use_starfield.ts ↘ 页面级 composable
    │   │   ├── use_typewriter.ts  跟随该页面 → 跟 View 同级
    │   │   ├── use_count_up.ts
    │   │   └── use_reveal.ts
    │   ├── auth/
    │   │   ├── LoginView.vue
    │   │   └── RegisterView.vue
    │   └── about/
    │       └── AboutView.vue
    │
    ├── components/              通用可复用 UI 组件
    │   └── [模块名]/            (目前为空,新增组件时按模块建子目录)
    │
    ├── composables/             通用 composables(跨 2+ 页面复用)
    │                            (目前为空,详见 § 6)
    │
    ├── api/                     接口层
    │   ├── http.ts              axios 实例(唯一对外出口)
    │   ├── endpoints.ts         URL 常量集中管理
    │   └── user.ts              user 模块的 API 函数
    │
    ├── stores/                  Pinia 状态
    │   └── user.ts              登录态 store(持久化)
    │
    ├── types/                   TypeScript 类型声明
    │   ├── index.d.ts           表单类型
    │   └── response.d.ts        响应类型
    │
    └── assets/
        ├── base.css             设计 token(CSS 变量定义)
        ├── main.css             全局骨架,引入 base.css
        └── logo.svg
```

---

## 6. 开发协同规范

**🔴 在写任何代码前先读一遍 [`PROJECT-RULES.md`](./PROJECT-RULES.md)**。本节是几条最常踩坑的精简版。

### 6.1 永远不要在组件里直接发请求

```ts
// ❌ 禁止
import axios from 'axios'
axios.get('/api/user/profile')

// ✅ 必须走 api/ 层
import { fetchUserProfile } from '@/api/user'
const data = await fetchUserProfile()
```

### 6.2 永远不要硬编码 URL

```ts
// ❌ 禁止
http.post('/api/func/login/', form)

// ✅ 统一在 api/endpoints.ts 维护
import { ENDPOINTS } from './endpoints'
http.post(ENDPOINTS.LOGIN, form)
```

### 6.3 composable 放哪儿?

**判断标准:这个逻辑会不会在 2 个以上的页面用到?**

| 情况 | 位置 | 命名 |
|------|------|------|
| **只有一个页面用** | `views/[模块]/use_xxx.ts` | 跟 View 同级 |
| **多个页面用** | `src/composables/use_xxx.ts` | 通用层 |

例:`use_starfield.ts` 只有首页 Hero 在用 → 放 `views/home/`
而 `use_table.ts`(通用表格 CRUD)会被很多列表页用 → 放 `src/composables/`

### 6.4 永远不要硬编码颜色/字号

```css
/* ❌ 禁止 */
.x-card {
  background: #191919;
  color: #fff;
}

/* ✅ 用 base.css 里的 token */
.x-card {
  background: var(--x-canvas-card);
  color: var(--x-ink);
}
```

### 6.5 永远不要用 `any`

```ts
// ❌ 禁止
function handle(data: any) {}

// ✅ 用 unknown 再做类型收窄
function handle(data: unknown) {
  if (typeof data === 'string') { /* ... */ }
}
```

### 6.6 文件命名

| 类型 | 规则 | 示例 |
|------|------|------|
| `.vue` 组件 | PascalCase | `UserCard.vue` |
| `.ts` 单词 | 全小写 | `http.ts`、`user.ts` |
| `.ts` 多词 | 下划线 | `use_starfield.ts`、`course_detail.ts` |
| 文件夹 | 全小写 | `user_center/` |

### 6.7 不许引入技术栈白名单外的库

允许:Vue / TypeScript / Vite / Element Plus / PrimeVue / Pinia / Vue Router / Axios / Vitest / Prettier

禁止:Tailwind、Vuex、Redux、react-query、SCSS、Sass、Less、UnoCSS 等

需要引入新库时**先口头确认**,获批后再 `npm install`。

---

## 7. 新增功能模块的标准流程

以新增"课程"模块为例,按以下顺序创建文件:

```
① types/course.d.ts                              定义数据类型
② api/endpoints.ts                               追加 COURSE_LIST / COURSE_DETAIL 常量
③ api/course.ts                                  实现 fetchCourseList() / fetchCourseDetail()
④ stores/course.ts                               定义 useCourseStore (需要跨页面共享时)
⑤ composables/use_table.ts (通用)                  ┐
   或 views/course/use_course_list.ts (页面级)    ┘ 抽业务逻辑
⑥ components/course/CourseCard.vue (可选)         可复用子组件
⑦ views/course/CourseListView.vue                创建页面
⑧ router/index.ts                                注册新路由 + meta
```

> 💡 步骤 ⑤ 的判断:如果 `use_course_list` 的逻辑只服务于一个页面,放 `views/course/`;
> 如果是通用表格 CRUD/分页/搜索逻辑,放 `src/composables/`。

---

## 8. 局域网联调

让手机 / iPad / 同事的电脑都能访问到你跑的页面。

### 8.1 前端(已配好 ✅)

`vite.config.ts` 里 `server.host: true` 已经开启,运行 `npm run dev` 后:

```
  ➜  Network: http://192.168.18.234:5173/    ← 别的设备打开这个
```

### 8.2 后端(需要你手动改)

```bash
# Django 必须监听 0.0.0.0,不能只监听 127.0.0.1
python manage.py runserver 0.0.0.0:8000
```

并在 `settings.py`:

```python
ALLOWED_HOSTS = ['*']          # 开发期偷懒,生产改成具体域名/IP

# CORS
INSTALLED_APPS = [..., 'corsheaders']
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ← 必须放在第一个
    ...
]
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
```

### 8.3 防火墙

macOS 首次有外部设备访问时会弹"是否允许 node / python 接受网络连接",点**允许**。

### 8.4 验证步骤

| # | 操作 | 期望 |
|---|------|------|
| 1 | 本机 `http://localhost:5173/` | 主页正常加载 → 前端 ✅ |
| 2 | 本机 `http://192.168.x.x:8000/api/...` | 后端有响应(405 都行) → 后端监听 0.0.0.0 ✅ |
| 3 | 手机 `http://192.168.x.x:5173/` | 主页正常加载 → vite 局域网 ✅ |
| 4 | 手机 F12 / Safari 远程调试看 network | 请求成功无 CORS 报错 → CORS ✅ |

---

## 9. 常见问题

### 9.1 `npm install` 报 `EACCES: permission denied`

```
npm error EACCES: permission denied, rename '/Users/xxx/.npm/_cacache/...'
```

之前用 `sudo npm` 留下了 root 拥有的缓存文件。修复:

```bash
sudo chown -R $(whoami):staff ~/.npm
```

然后重新 `npm install`。

### 9.2 启动后字体抖动一下

首屏会从 Google CDN 下载 Inter 和 JetBrains Mono,1 秒后切换。这是预期行为 —— Universal Sans 和 Geist Mono 是商业字体,开源替身就是这两款。

国内访问慢的话可以考虑:
- 下载字体放本地 `public/fonts/`
- 改 `@font-face` 引用本地路径

### 9.3 Element Plus 的 Toast 弹出来是白色

`<style scoped>` 里写的样式不会影响 Element Plus 注入到 `body` 末尾的 toast 节点。需要用一个**不带 `scoped` 的 `<style>` 块**覆盖:

```vue
<style>
.x-toast {
  background: #0a0a0a !important;
  ...
}
</style>
```

然后调用时传入:`ElMessage({ message: '...', customClass: 'x-toast' })`。

### 9.4 路由变化但页面没刷新

检查浏览器 console 是否有 `[Vue Router warn]`。常见原因:
- meta 写了 `guestOnly: true` 又已登录 → 守卫弹回 `/`,正常行为
- 用 `router.push('/')` 跳到当前页 → 用 `router.replace('/')` 强制替换

### 9.5 改了 `.env` 没生效

Vite **只在启动时读一次环境变量**。改完必须 Ctrl+C 杀掉 `npm run dev` 重启。HMR 不会重新读取。

### 9.6 类型报错 `Property 'xxx' is possibly 'undefined'`

`tsconfig` 开了 `noUncheckedIndexedAccess`,数组下标访问返回 `T | undefined`:

```ts
// ❌
const word = words[i]   // word: string | undefined
word.slice(0)            // ❌ possibly undefined

// ✅ 三种解法之一
const word = words[i] ?? ''
const word = words[i]!         // 你确定 i 在范围内时
if (i < words.length) {
  const word = words[i]!
}
```

---

## 10. 构建与部署

### 10.1 生产构建

```bash
npm run build
```

产物输出到 `dist/`,包含:
- 入口 HTML
- JS chunks(按路由懒加载分割)
- CSS 文件
- 静态资源(带 hash 文件名)

### 10.2 本地验证构建结果

```bash
npm run preview
```

会启动一个静态服务器跑 `dist/`,**用来确认生产模式下没问题**(SSR / 路径 / 环境变量),开发跑得起来不代表生产能跑。

### 10.3 部署到服务器

`dist/` 是纯静态文件,扔到任何 web 服务器(Nginx / Caddy / Vercel / 阿里云 OSS)即可。

**Nginx 示例**(注意 SPA 必须把所有路径回退到 `index.html`):

```nginx
server {
    listen 80;
    server_name aiteach.example.com;
    root /var/www/aiteach/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;  # ← SPA 路由回退
    }

    location /api/ {
        proxy_pass http://localhost:8000;  # ← 反代到后端
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 10.4 生产环境的 BASE_URL

生产建议**不写死** `VITE_BASE_URL`,而是让前端用 `window.location.host` 读运行时域名,这样同一份构建产物可以部署到任意域名。

修改 [`src/api/http.ts`](src/api/http.ts),启用文件里被注释的"正式环境"代码段,删掉开发环境那段。

---

## 参考文档

- 🎨 [设计规范 DESIGN-x.ai.md](./DESIGN-x.ai.md) —— 颜色 / 字号 / 组件令牌
- 📐 [开发规范 PROJECT-RULES.md](./PROJECT-RULES.md) —— 技术栈 / 目录 / 命名 / 分层
- 📦 [Vue 3 文档](https://cn.vuejs.org/)
- ⚡ [Vite 文档](https://cn.vitejs.dev/)
- 🍍 [Pinia 文档](https://pinia.vuejs.org/zh/)
- 🛤️ [Vue Router 文档](https://router.vuejs.org/zh/)
- 🎯 [Element Plus 文档](https://element-plus.org/zh-CN/)

---

## 维护者

- 项目作者: duasong
- 后端项目: [`../backend/`](../backend/)
- 反馈: 在阿里云 Codeup 仓库提 Issue
