import { ref, onMounted, onActivated } from 'vue'
import { listReports } from '@/api/learning'
import type { WeeklyReport } from '@/types/learning'

/**
 * 周报 list composable —— 与 useResourceHistory 同模式
 *   onMounted + onActivated 双 hook (配合 <keep-alive>)
 *
 * Mock fallback —— 后端返空 (用户没真实周报) 时, 用确定性 mock 数据填图,
 *   让"我的报告" tab 立刻有视觉. mock 引用 backend/users/knowledge_map.py
 *   里 7 门课的真实知识点, 跟 /app/home 雷达 + 环形图数据联动.
 */
export function useReports() {
  const items = ref<WeeklyReport[]>([])
  const loading = ref<boolean>(false)
  const error = ref<string>('')

  // 知识点池 —— 按 7 门课分组, 跟 /course-select + 雷达 + 环形图 共用同一份
  // 名字跟 backend/users/knowledge_map.py 严格对齐, 未来接真数据时不会错位
  const NODES_BY_SUBJECT: Record<string, string[]> = {
    data_structure:         ['数组', '链表', '栈', '队列', '哈希表', '树', '二叉树', 'B树', 'DFS', 'BFS', 'Dijkstra', '动态规划', '回溯算法', '时间复杂度'],
    cybersecurity:            ['对称加密', '非对称加密', '哈希函数', '数字签名', 'SSL/TLS', '防火墙', '入侵检测', 'WAF', '零信任', '渗透测试', 'SQL注入', 'XSS', 'CSRF', 'DDOS防护'],
    iot:                    ['传感器', '嵌入式系统', 'MCU', '边缘计算', '云平台', 'MQTT', 'CoAP', 'RFID', '实时操作系统', 'LoRa', 'NB-IoT', '数字孪生'],
    electrical_automation:  ['电路原理', '模拟电路', '数字电路', 'PLC编程', '变频器', '伺服系统', '传感器与检测', '电机学', '电力电子', 'PID控制', '工业以太网', 'SCADA'],
    mechanical_design:      ['机械制图', 'AutoCAD', 'SolidWorks', '材料力学', '热力学', '流体力学', '机械原理', '机械设计', '齿轮传动', '轴承', '公差配合', '有限元分析', '信号量与互斥锁', '进程调度'],
    advanced_math:          ['微积分', '极限', '导数', '微分', '积分', '重积分', '级数', '泰勒展开', '偏导数', '曲线积分', '曲面积分', '常微分方程', '拉普拉斯变换', '傅里叶变换'],
    artificial_intelligence:['机器学习', '深度学习', '监督学习', '无监督学习', '线性回归', '决策树', '支持向量机', '神经网络', 'CNN', 'RNN', 'LSTM', 'Transformer', '注意力机制'],
  }

  // SUBJECT_CHOICES 的 code → 中文名 映射, 给 mock summary 用
  // advanced_math 现在的显示名是"软件工程" (前端 SUBJECT_CHOICES 已对齐)
  const SUBJECT_DISPLAY: Record<string, string> = {
    data_structure:         '数据结构',
    cybersecurity:            '网络安全',
    iot:                    '物联网',
    electrical_automation:  '电气自动化',
    mechanical_design:      '机械设计',
    advanced_math:          '软件工程',
    artificial_intelligence:'人工智能',
  }

  function buildMockReports(): WeeklyReport[] {
    // 全部 seed 化, 每次刷新数据稳定
    let seed = 17
    const rand = () => {
      seed = (seed * 9301 + 49297) % 233280
      return seed / 233280
    }
    const sample = <T>(arr: T[], n: number): T[] => {
      const copy = [...arr]
      const out: T[] = []
      while (out.length < n && copy.length > 0) {
        const i = Math.floor(rand() * copy.length)
        out.push(copy.splice(i, 1)[0]!)
      }
      return out
    }
    const fmt = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

    const today = new Date()

    // ── 本周 (具体场景) ──
    // focus = advanced_math (显示名"软件工程") + iot
    // summary 提到巩固微积分 + IoT 协议, MQTT 已完成, 建议下周补信号量与互斥锁
    const thisWeekEnd = new Date(today)
    const thisWeekStart = new Date(thisWeekEnd)
    thisWeekStart.setDate(thisWeekEnd.getDate() - 6)
    const thisReport: WeeklyReport = {
      id: 1003,
      week_start: fmt(thisWeekStart),
      week_end: fmt(thisWeekEnd),
      summary: '本周主要在巩固 软件工程 的微积分与 IoT 协议. MQTT 章节已完成, 整体掌握扎实. 建议下周补一下信号量与互斥锁.',
      top_nodes: ['MQTT', '微积分', '积分'],
      weak_nodes: ['信号量与互斥锁', '进程调度', '拉普拉斯变换'],
      total_time_min: 320,
    }

    // ── 上周 (常规随机) ──
    const lastWeekEnd = new Date(today)
    lastWeekEnd.setDate(today.getDate() - 7)
    const lastWeekStart = new Date(lastWeekEnd)
    lastWeekStart.setDate(lastWeekEnd.getDate() - 6)
    const lastFocus = sample(Object.keys(NODES_BY_SUBJECT), 1 + Math.floor(rand() * 2))
    const lastReport: WeeklyReport = {
      id: 1002,
      week_start: fmt(lastWeekStart),
      week_end: fmt(lastWeekEnd),
      summary: `上周你主要在 ${lastFocus.map((s) => SUBJECT_DISPLAY[s] ?? s).join('、')} 上发力, 累计投入 ${180 + Math.floor(rand() * 200)} 分钟. 继续巩固, 节奏稳!`,
      top_nodes: sample(
        lastFocus.flatMap((s) => NODES_BY_SUBJECT[s] ?? []),
        3,
      ),
      weak_nodes: sample(
        Object.keys(NODES_BY_SUBJECT)
          .filter((s) => !lastFocus.includes(s))
          .flatMap((s) => NODES_BY_SUBJECT[s] ?? []),
        3,
      ),
      total_time_min: 180 + Math.floor(rand() * 200),
    }

    // ── 前两周 (常规随机) ──
    const twoWeeksAgoEnd = new Date(today)
    twoWeeksAgoEnd.setDate(today.getDate() - 14)
    const twoWeeksAgoStart = new Date(twoWeeksAgoEnd)
    twoWeeksAgoStart.setDate(twoWeeksAgoEnd.getDate() - 6)
    const twoWeeksAgoFocus = sample(Object.keys(NODES_BY_SUBJECT), 1 + Math.floor(rand() * 2))
    const twoWeeksAgoReport: WeeklyReport = {
      id: 1001,
      week_start: fmt(twoWeeksAgoStart),
      week_end: fmt(twoWeeksAgoEnd),
      summary: `前两周你主要在 ${twoWeeksAgoFocus.map((s) => SUBJECT_DISPLAY[s] ?? s).join('、')} 上发力, 累计投入 ${150 + Math.floor(rand() * 180)} 分钟. 继续保持!`,
      top_nodes: sample(
        twoWeeksAgoFocus.flatMap((s) => NODES_BY_SUBJECT[s] ?? []),
        3,
      ),
      weak_nodes: sample(
        Object.keys(NODES_BY_SUBJECT)
          .filter((s) => !twoWeeksAgoFocus.includes(s))
          .flatMap((s) => NODES_BY_SUBJECT[s] ?? []),
        3,
      ),
      total_time_min: 150 + Math.floor(rand() * 180),
    }

    // 本周 → 上周 → 前两周 (倒序)
    return [thisReport, lastReport, twoWeeksAgoReport]
  }

  async function reload(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const { data } = await listReports()
      // 真数据全 0 / 空 → 用 mock 填充, 跟 7 门课 / 雷达数据联动
      const hasReal = data.items.some((r) => r.total_time_min > 0 || r.top_nodes.length > 0)
      items.value = hasReal ? data.items : buildMockReports()
    } catch (err) {
      // 网络挂了: 用 mock, 不要让报告 tab 空白
      items.value = buildMockReports()
      error.value = err instanceof Error ? err.message : 'Load failed'
    } finally {
      loading.value = false
    }
  }

  onMounted(reload)
  onActivated(reload)
  return { items, loading, error, reload }
}
