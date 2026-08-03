import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

/**
 * 知识点 mastery 覆盖层 —— per-subject 维度
 *
 *   后端有 KnowledgeNode.mastery, 但当前 *没有* HTTP GET 接口暴露出来.
 *   Practice agent 在练习时调 get_knowledge_map / assess_and_update_knowledge_score,
 *   返回的 tool_result 里 *会带* 当前真实 mastery (JSON 数组形式).
 *
 *   策略: PracticeView 把 tool_result 截下来 → 解析 → 写入本 store.
 *         GalaxyView 渲染时, 先读本 store, 缺失再 fall back 到 mocks/knowledgeGraph.ts.
 *         结果: 用户做完一轮练习 → 切回星图 → 看到对应节点颜色变化.
 *
 *   持久化: 'aiteach.mastery'. 同设备同账号刷新仍然看得见上次的进度.
 *   未来后端补 GET /api/knowledge/<subject>/<node>/ → 改成主动 fetch + 覆盖, store 形状不动.
 */

interface NodeMastery {
  mastery: number               // 0-100
  updated_at: number            // unix ms, 用于"最近"展示
}

/** Practice 期间的最近 mastery 跳变 —— 给 UI 弹通知 */
export interface MasteryDelta {
  ts: number
  subject_code: string
  node_id: string
  node_name: string
  prev: number
  new: number
}

export const useMasteryStore = defineStore(
  'mastery',
  () => {
    // ─── state ────────────────────────────────────────────
    //   subject_code → node_id → NodeMastery
    const masteryMap = ref<Record<string, Record<string, NodeMastery>>>({})
    // 最近 20 条 delta (FIFO), 仅运行时
    const recentDeltas = ref<MasteryDelta[]>([])

    // ─── getters ──────────────────────────────────────────
    /** 读某门学科的整张 mastery overlay (Galaxy 用) */
    function getOverlay(subjectCode: string): Record<string, number> {
      const sub = masteryMap.value[subjectCode]
      if (!sub) return {}
      const out: Record<string, number> = {}
      for (const [nodeId, m] of Object.entries(sub)) {
        out[nodeId] = m.mastery
      }
      return out
    }

    /** 单点查询, 没记录返 null (Galaxy fallback 到 mocks) */
    function getNodeMastery(subjectCode: string, nodeId: string): number | null {
      return masteryMap.value[subjectCode]?.[nodeId]?.mastery ?? null
    }

    const totalNodesTracked = computed<number>(() =>
      Object.values(masteryMap.value).reduce((acc, sub) => acc + Object.keys(sub).length, 0),
    )

    // ─── actions ──────────────────────────────────────────
    /** 内部 helper: 保证 subject 桶存在 */
    function bucket(subjectCode: string): Record<string, NodeMastery> {
      if (!masteryMap.value[subjectCode]) {
        masteryMap.value[subjectCode] = {}
      }
      return masteryMap.value[subjectCode]!
    }

    /**
     * 批量覆盖 —— Practice agent 调 get_knowledge_map 时, tool_result 是
     *   [{node_id, name, mastery, evidence_count}, ...]
     * 这是当前学科 mastery 的权威全量, 用它覆盖整桶.
     */
    function applyKnowledgeMap(
      subjectCode: string,
      rows: Array<{ node_id: string; mastery: number }>,
    ): void {
      const now = Date.now()
      const bk = bucket(subjectCode)
      for (const r of rows) {
        bk[r.node_id] = { mastery: r.mastery, updated_at: now }
      }
    }

    /**
     * 单点更新 —— 来自 assess_and_update_knowledge_score 的 tool_result.
     * 因为该 tool 返回字符串只带 node_name (没 node_id), 调用方需要先映射到 node_id.
     */
    function applyAssessment(
      subjectCode: string,
      nodeId: string,
      nodeName: string,
      prev: number,
      next: number,
    ): void {
      const bk = bucket(subjectCode)
      bk[nodeId] = { mastery: next, updated_at: Date.now() }
      recentDeltas.value.push({
        ts: Date.now(),
        subject_code: subjectCode,
        node_id: nodeId,
        node_name: nodeName,
        prev,
        new: next,
      })
      if (recentDeltas.value.length > 20) {
        recentDeltas.value.splice(0, recentDeltas.value.length - 20)
      }
    }

    function clearDeltas(): void {
      recentDeltas.value = []
    }

    /** 调试/手动清掉 */
    function reset(subjectCode?: string): void {
      if (subjectCode) {
        delete masteryMap.value[subjectCode]
      } else {
        masteryMap.value = {}
      }
      recentDeltas.value = []
    }

    return {
      masteryMap,
      recentDeltas,
      totalNodesTracked,
      getOverlay,
      getNodeMastery,
      applyKnowledgeMap,
      applyAssessment,
      clearDeltas,
      reset,
    }
  },
  {
    persist: {
      key: 'aiteach.mastery',
      // recentDeltas 不持久化 (运行时 UI 通知队列, 跨刷新没意义)
      pick: ['masteryMap'],
    },
  },
)
