# aiteach 前端项目结构约束

## 一、技术栈（禁止引入未列出的替代库）

| 用途 | 库 / 工具 |
|------|-----------|
| 框架 | Vue 3（Composition API，`<script setup>` 语法） |
| 语言 | TypeScript（严格模式，禁止使用 `any`） |
| 构建 | Vite |
| UI 组件库 | Element Plus | PrimeVue ｜
| 状态管理 | Pinia |
| 路由 | Vue Router |
| HTTP 请求 | Axios（只能通过 `api/http.ts` 封装的实例发请求） |
| 样式 | 原生 CSS + CSS 变量（设计 token 定义在 `assets/base.css`） |
| 代码格式 | Prettier（配置见 `.prettierrc.json`） |
| 单元测试 | Vitest |

##  以下类型的库 AI 可以主动推荐更合适的选择，
##  但必须说明理由，等用户确认后再写进代码：

- 动画 / 交互增强
- 工具函数
- 图表 / 可视化
- 功能型 UI 组件（富文本、拖拽、日历等）

**禁止事项：**
- 不引入 Redux、Vuex、react-query 等替代状态/请求管理库
- 不使用 Tailwind、UnoCSS、SCSS 等替代样式方案
- 不在组件内直接调用 `axios` 或 `fetch`，必须走 `api/` 层
- 不使用 `any` 类型，用 `unknown` 代替后再做类型收窄

---

## 二、目录结构

```
web/src/
├── main.ts                  # 入口：注册 Pinia / Router / Element Plus
├── App.vue                  # 根组件，只保留 <router-view>
│
├── router/
│   └── index.ts             # 路由表，每新增页面在此注册
│
├── views/                   # 页面级组件（路由直接映射的页面）
│   ├── home/
│   │   └── HomeView.vue
│   └── [功能模块名]/        # 每个功能模块一个子文件夹
│       ├── [PageName]View.vue
│       └── use_[page_name].ts   # 该页面专属的 composable（仅此页面使用）
│
├── components/              # 可复用组件（非页面级）
│   └── [功能模块名]/        # 按功能模块分子文件夹
│       └── [ComponentName].vue
│
├── composables/             # 通用 composables（跨两个以上页面复用）
│   ├── use_table.ts         # 表格增删改查通用逻辑
│   ├── use_pagination.ts    # 分页
│   ├── use_search.ts        # 搜索条件
│   ├── use_form.ts          # 表单提交
│   ├── use_request.ts       # 请求状态封装（loading / error）
│   ├── use_websocket.ts     # WebSocket 连接
│   ├── use_camera.ts        # 摄像头
│   ├── use_device.ts        # 设备管理
│   └── use_mqtt.ts          # MQTT 连接
│
│   # ⚠️ 只属于某一个页面的逻辑，不放这里
│   # 放到对应 views/[模块]/ 目录下，与 View 文件并列
│
├── api/                     # 接口层
│   ├── http.ts              # axios 实例（唯一出口，读 .env 的 VITE_BASE_URL）
│   ├── endpoints.ts         # 所有 URL 常量，禁止在其他文件硬编码 URL
│   └── [模块名].ts          # 每个业务模块一个文件，例：user.ts、course.ts
│
├── stores/                  # Pinia 状态
│   └── [模块名].ts          # 每个业务模块一个 store，例：user.ts、course.ts
│
├── types/                   # TypeScript 类型声明
│   ├── index.d.ts           # 通用类型
│   └── [模块名].d.ts        # 每个业务模块的类型，例：course.d.ts
│
└── assets/
    ├── base.css             # 设计 token（CSS 变量定义，禁止在此写组件样式）
    ├── main.css             # 全局骨架样式，引入 base.css
    └── logo.svg
```

---

## 三、命名规范

### 文件命名

| 文件类型 | 规则 | 示例 |
|----------|------|------|
| `.vue` 组件 | PascalCase | `UserCard.vue`、`CourseList.vue` |
| `.ts` 单词短 | 全小写 | `http.ts`、`user.ts`、`index.ts` |
| `.ts` 多单词 | 下划线分隔 | `user_info.ts`、`use_auth.ts`、`course_detail.ts` |
| `.d.ts` 类型 | 同 `.ts` 规则 | `response.d.ts`、`course_item.d.ts` |
| `.json` | 同 `.ts` 规则 | `settings.json` |
| 文件夹 | 全小写，多词用下划线 | `user_center/`、`course_list/` |

### 代码内命名

| 对象 | 规则 | 示例 |
|------|------|------|
| 组件名 | PascalCase | `UserCard`、`CourseTable` |
| 变量 / 函数 | camelCase | `userInfo`、`fetchCourseList` |
| Pinia store | camelCase，`use` 前缀 | `useUserStore`、`useCourseStore` |
| composable | camelCase，`use` 前缀 | `useAuth`、`usePagination` |
| 类型 / 接口 | PascalCase | `LoginForm`、`CourseItem` |
| CSS 变量 | kebab-case，`--` 前缀 | `--color-bg`、`--font-size-base` |
| URL 常量 | 全大写下划线 | `LOGIN`、`COURSE_LIST` |

---

## 四、分层规则

### views/ — 页面层
- 只负责页面布局和组装，不写复杂业务逻辑
- 业务逻辑抽到 `composables/`，数据请求走 `api/`，状态走 `stores/`
- 文件名必须以 `View` 结尾：`HomeView.vue`、`CourseDetailView.vue`

### components/ — 组件层
- 只放可被多处复用的 UI 组件
- 仅属于某一页面的子组件，放在 `views/[模块]/` 下，不放进 `components/`
- 组件不直接调用 API，数据通过 props 或 store 传入

### composables/ — 逻辑层

composables 分为两种，**放置位置不同**：

**① 通用 composables → 放 `src/composables/`**

会在两个及以上页面中复用的逻辑，与具体业务无关：

```
composables/
├── use_table.ts       // 任何页面的表格都能用
├── use_pagination.ts  // 任何列表页都能用
├── use_form.ts        // 任何表单都能用
├── use_websocket.ts   // 任何需要 WS 的页面都能用
├── use_camera.ts      // 摄像头
├── use_device.ts      // 设备管理
└── use_mqtt.ts        // MQTT 连接
```

**② 页面级 composables → 放 `views/[模块]/` 下，与 View 文件并列**

只属于某一个页面的业务逻辑，不应放入全局 composables 目录：

```
views/course/
├── CourseListView.vue     // 页面组件
└── use_course_list.ts     // 只有这个页面用的逻辑
```

在 `.vue` 文件中按相对路径引入：
```ts
import { useCourseList } from './use_course_list'
const { courses, loading, fetchCourses } = useCourseList()
```

**判断标准：这个逻辑会不会在两个以上的页面用到？**
- 会 → `src/composables/`（通用层）
- 不会 → `views/[模块]/` 旁边（页面级）

**通用规则：**
- 文件名和导出函数名均以 `use` 开头
- 返回值用对象解构，不用数组（方便按需取值）
- 禁止在 composable 内直接调用 `axios`，请求统一走 `api/` 层

### api/ — 接口层
- `http.ts`：只做 axios 实例配置（baseURL、拦截器），不写业务逻辑
- `endpoints.ts`：集中管理所有 URL 字符串常量，**全项目禁止硬编码 URL**
- 业务文件（如 `user.ts`）：只导出异步函数，函数内使用 `http.ts` 实例

### stores/ — 状态层
- 每个业务模块一个 store 文件，与 `api/` 的业务文件一一对应
- store 只存"需要跨组件共享"的状态，局部状态用组件内 `ref`
- 使用 `defineStore` 的 Setup 写法（与 `<script setup>` 风格一致）

### types/ — 类型层
- 所有接口请求/响应的数据结构必须在此定义
- 禁止在组件或 API 文件内内联定义复杂类型

---

## 五、样式规范

- **所有颜色、字号、间距必须使用 `assets/base.css` 中定义的 CSS 变量**
- 禁止在组件 `<style>` 中硬编码颜色值（如 `#000000`、`rgba(...)`）
- 组件样式使用 `<style scoped>`
- 全局样式只写在 `assets/main.css`，组件内不写全局选择器
- 动画效果优先使用 CSS transition / animation，复杂交互再考虑 JS

---

## 六、新增功能模块时的标准步骤

新增一个业务模块（例如"课程管理"）时，AI 应按以下顺序生成文件：

1. `types/course.d.ts` — 定义数据类型
2. `api/endpoints.ts` — 追加该模块的 URL 常量
3. `api/course.ts` — 实现 API 调用函数
4. `stores/course.ts` — 创建 Pinia store
5. `composables/use_[name].ts` — 封装**通用**逻辑（如有，需跨页面复用）
   或 `views/course/use_course_list.ts` — 封装**页面级**逻辑（仅本页使用）
6. `components/course/` — 创建可复用子组件（如有）
7. `views/course/CourseListView.vue` — 创建页面
8. `router/index.ts` — 注册新路由

---

## 七、禁止行为清单

- ❌ 在 `<script setup>` 外写业务代码
- ❌ 组件内直接调用 `axios` / `fetch`
- ❌ 硬编码任何 API URL 字符串
- ❌ 使用 `any` 类型
- ❌ 在 `components/` 下放只属于某一个页面的子组件
- ❌ 在 `base.css` 中写组件级样式
- ❌ 在组件 `<style>` 中硬编码颜色 / 字号值
- ❌ 引入技术栈表以外的第三方库（需事先确认）
- ❌ 删除或修改 `api/http.ts` 的拦截器逻辑（如需改动请说明）