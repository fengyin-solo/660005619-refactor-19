<template>
  <div class="panel">
    <h4>⚡ 熔断器状态</h4>
    <div v-for="cb in breakers" :key="cb.taskId" class="cb-row" :class="stateClass(cb.state)">
      <span v-for="col in columns" :key="col.key" :class="cellClass[col.key]">{{ formatCell(col.key, cb) }}</span>
    </div>
    <div v-if="!breakers.length" class="empty">无熔断保护激活</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDAGStore } from '../store/dag'
import { BREAKER_COLUMNS, visibleColumns } from '../policy/fields'
import type { CircuitBreaker } from '../types'
const store = useDAGStore()
// 明细列来自统一字段策略，与日志明细、大屏字段列表同源
const columns = computed(() => visibleColumns(BREAKER_COLUMNS, store.role))
const breakers = computed(() => store.execution?.circuitBreakers || [])
// 与原展示保持一致：状态直接转小写作为行样式类
const stateClass = (state: string) => state.toLowerCase()
const cellClass: Record<string, string> = { taskId: 'cb-task', state: 'cb-state', failureCount: 'cb-count' }
// 失败次数列保留原有的“N 次失败”文案
type BreakerCellKey = (typeof BREAKER_COLUMNS)[number]['key']
function formatCell(key: BreakerCellKey, cb: CircuitBreaker): string | number {
  return key === 'failureCount' ? `${cb.failureCount} 次失败` : cb[key]
}
</script>
<style scoped>
.panel{background:#1a1a2e;border-radius:8px;padding:10px;border:1px solid #2a2a4a}
.panel h4{color:#f87171;font-size:12px;margin-bottom:6px}
.cb-row{display:flex;gap:8px;padding:4px 6px;border-radius:4px;font-size:11px;margin:2px 0}
.cb-row.open{background:#ef444415}
.cb-task{color:#ccc;font-weight:600}.cb-state{font-weight:700}.cb-count{color:#888;font-size:10px}
.open .cb-state{color:#ef4444}.closed .cb-state{color:#22c55e}.half_open .cb-state{color:#fbbf24}
.empty{color:#4a5568;font-size:11px}
</style>
