import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    guestOnly?: boolean
    skipOnboardingGuard?: boolean // 标记不走"无课程强制 onboarding"守卫
    title?: string
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'login',
      component: () => import('../views/auth/LoginView.vue'),
      meta: { guestOnly: true, title: '登录 — 学径' },
    },
    {
      path: '/welcome',
      name: 'welcome',
      component: () => import('../views/acquisition/AcquisitionView.vue'),
      meta: { requiresAuth: true, skipOnboardingGuard: true, title: '欢迎 — 学径' },
    },
    // {
    //   path: '/onboarding',
    //   name: 'onboarding',
    //   component: () => import('../views/onboarding/OnboardingView.vue'),
    //   meta: { requiresAuth: true, title: '入门引导 — 学径' },
    // },
    {
      path: '/course-select',
      name: 'course-select',
      component: () => import('../views/onboarding/CourseSelectView.vue'),
      meta: { requiresAuth: true, skipOnboardingGuard: true, title: '选择课程 — 学径' },
    },
    {
      path: '/course-onboarding/:code',
      name: 'course-onboarding',
      component: () => import('../views/onboarding/CourseOnboardingView.vue'),
      meta: { requiresAuth: true, skipOnboardingGuard: true, title: '课程画像 — 学径' },
    },
    {
      path: '/register',
      redirect: '/login',
    },

    // ── AppShell 布局 (所有 /app/* 页面) ──────────────────────────────
    //
    // 命名约定:
    //   - 路径段用名词单数 (galaxy / book / exam) —— 跟左上角 Nav 文案对齐
    //   - route name 全部 'app-*' —— 跟顶层 'login' / 'home' 区分开
    //   - 每个功能一个目录 (views/<feature>/<View>.vue), 不再共用 views/learning/
    //
    {
      path: '/app',
      component: () => import('../layouts/AppShell.vue'),
      meta: { requiresAuth: true },
      children: [
        // 默认进 "主页" (== 学习记录内容, 整个 LearningRecordsView)
        { path: '', redirect: '/app/home' },

        // 主 页 ← LearningRecordsView.vue (从原 /app/records 搬过来, /app/records 已删)
        {
          path: 'home',
          name: 'app-home',
          component: () => import('../views/learning/LearningRecordsView.vue'),
          meta: { title: '主页 — 学径' },
        },

        // 星 图
        {
          path: 'galaxy',
          name: 'app-galaxy',
          component: () => import('../views/galaxy/GalaxyView.vue'),
          meta: { title: '知识星图 — 学径' },
        },
        // 对 话
        {
          path: 'dialog',
          name: 'app-dialog',
          component: () => import('../views/tutor/TutorView.vue'),
          meta: { title: 'AI 对话 — 学径' },
        },
        // 计 划 (计划规划 + 课程详情 + 知识点详情)
        {
          path: 'plan',
          name: 'app-plan',
          component: () => import('../views/plan/PlanScheduleView.vue'),
          meta: { title: '计划规划 — 学径' },
        },
        {
          path: 'plan/courses',
          name: 'app-plan-courses',
          component: () => import('../views/plan/MyCoursesView.vue'),
          meta: { title: '我的课程 — 学径' },
        },
        {
          path: 'plan/course/:subjectCode',
          name: 'app-course-detail',
          component: () => import('../views/plan/CourseDetailView.vue'),
          meta: { title: '课程详情 — 学径' },
        },
        {
          path: 'plan/course/:subjectCode/node/:nodeId',
          name: 'app-knowledge-point',
          component: () => import('../views/plan/KnowledgePointView.vue'),
          meta: { title: '知识点 — 学径' },
        },
        // 书 架
        {
          path: 'book',
          name: 'app-book',
          component: () => import('../views/book/BookShelf.vue'),
          meta: { title: '书架 — 学径' },
        },
        // 视频课 —— app-video 无参数即未选中状态，app-video-detail 有 uuid 参数
        {
          path: 'video',
          name: 'app-video',
          component: () => import('../views/video/VideoPlayerView.vue'),
          meta: { title: '视频课 — 学径' },
        },
        {
          path: 'video/:id',
          name: 'app-video-detail',
          component: () => import('../views/video/VideoPlayerView.vue'),
          meta: { title: '视频课详情 — 学径' },
          props: true,
        },
        // 刷 题
        {
          path: 'exercise',
          name: 'app-exercise',
          component: () => import('../views/practice/ExerciseDetailView.vue'),
          meta: { title: '刷题 — 学径' },
        },
        {
          path: 'exercise/:taskId',
          name: 'app-exercise-detail',
          component: () => import('../views/practice/ExerciseDetailView.vue'),
          meta: { title: '刷题详情 — 学径' },
          props: true,
        },
        // 评 测
        {
          path: 'exam',
          name: 'app-exam',
          component: () => import('../views/exam/ExamView.vue'),
          meta: { title: '评测 — 学径' },
        },
        // 设计系统 Demo (开发用)
        {
          path: 'design-demo',
          name: 'app-design-demo',
          component: () => import('../views/design/DesignDemoView.vue'),
          meta: { title: 'Design System Demo — 学径' },
        },
        // 验证 Demo
        {
          path: 'demo',
          name: 'app-demo',
          component: () => import('../views/demo/DemoView.vue'),
          meta: { title: '验证 Demo — 学径' },
        },
        // 个人中心
        {
          path: 'profile',
          name: 'app-profile',
          component: () => import('../views/profile/ProfileView.vue'),
          meta: { title: '个人中心 — 学径' },
        },
        // 设置
        // {
        //   path: 'settings',
        //   name: 'app-settings',
        //   component: () => import('../views/settings/SettingsView.vue'),
        //   meta: { title: '设置 — 学径' },
        // },
      ],
    },

    // ── 独立页面 ──────────────────────────────────────
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/about/AboutView.vue'),
      meta: { title: '关于 — 学径' },
    },

    // ── 兜底 ──────────────────────────────────────────
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()

  // 1) 登录态守卫
  if (to.meta.requiresAuth && !userStore.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && userStore.isAuthenticated) {
    return { name: 'home' }
  }

  // 2) 标题
  if (to.meta.title) {
    document.title = to.meta.title
  }

  // 3) Onboarding 守卫 —— 已删除 (用户希望完全自由进入主界面, 不再强制选课)
  //    之前逻辑 ① : 登录后无课程 → 强制 /course-select
  //    之前逻辑 ② : /app/* 进入时若当前学科画像未完成 → 强制 /course-onboarding/:code
  //    现在: 任何 /app/* 路由都直接放行, 用户自己决定何时加课 / 完成画像

  return true
})

export default router
