import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import axios from 'axios'
import type { DAGWorkflow, ExecutionInfo } from '@/types'
import {
  normalizeRole, projectNode, projectLog, projectBreaker,
  type Role
} from '@/policy/fields'

const ROLE_STORAGE_KEY = 'dag-view-role'

/**
 * 取数与字段可见范围只在这里收口：
 * 三条取数路径（创建工作流、执行明细、WebSocket 推送）拿到原始数据后，
 * 统一经 policy/fields 投影，组件不再各自判定字段可见性与脱敏。
 */
export const useDAGStore = defineStore('dag', () => {
  const loading = ref(false)
  const workflow = ref<DAGWorkflow | null>(null)
  const execution = ref<ExecutionInfo | null>(null)
  const wsConnected = ref(false)
  const workers = ref(3)
  const strategy = ref('fifo')
  const role = ref<Role>(normalizeRole(localStorage.getItem(ROLE_STORAGE_KEY)))

  let ws: WebSocket|null = null

  function applyWorkflow<T extends DAGWorkflow>(data: T): T {
    return { ...data, nodes: data.nodes.map(n => projectNode(n, role.value)) }
  }
  function applyExecution<T extends ExecutionInfo>(data: T): T {
    const wf = applyWorkflow(data.workflow)
    return {
      ...data,
      workflow: wf,
      logs: data.logs.map(l => projectLog(l, role.value)),
      circuitBreakers: data.circuitBreakers.map(cb => projectBreaker(cb, role.value)),
    }
  }

  function connectWS() {
    ws = new WebSocket(`ws://${location.hostname}:8000/ws?role=${encodeURIComponent(role.value)}`)
    ws.onopen = () => { wsConnected.value = true }
    ws.onmessage = (e) => {
      try { execution.value = applyExecution(JSON.parse(e.data)) }
      catch {}
    }
    ws.onclose = () => { wsConnected.value = false }
  }

  async function createWorkflow(name: string) {
    loading.value = true
    try {
      const { data } = await axios.post(`/api/workflow?role=${encodeURIComponent(role.value)}`, { name })
      workflow.value = applyWorkflow(data)
    }
    finally { loading.value = false }
  }

  async function run() {
    if (!workflow.value) return
    loading.value = true
    try {
      const { data } = await axios.post(`/api/run?role=${encodeURIComponent(role.value)}`,
        { workflowId: workflow.value.id, workers: workers.value, strategy: strategy.value })
      execution.value = applyExecution(data)
    }
    finally { loading.value = false }
  }

  function setRole(next: Role) {
    role.value = normalizeRole(next)
  }

  // 刷新后角色仍在；切换角色后重连 WS 并对已持有的数据重新投影，保证两侧字段立即对齐
  watch(role, (next, prev) => {
    localStorage.setItem(ROLE_STORAGE_KEY, next)
    if (next === prev) return
    if (workflow.value) workflow.value = applyWorkflow(workflow.value)
    if (execution.value) execution.value = applyExecution(execution.value)
    disconnectWS()
    connectWS()
  })

  function disconnectWS() { ws?.close(); ws = null }
  return {
    loading, workflow, execution, wsConnected, workers, strategy, role,
    connectWS, createWorkflow, run, setRole, disconnectWS
  }
})
