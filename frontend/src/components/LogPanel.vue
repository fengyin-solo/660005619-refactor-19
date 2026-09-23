<template>
  <div class="panel">
    <h4>📜 执行日志</h4>
    <div class="log-list">
      <div v-for="(l,i) in logs" :key="i" class="log-row" :class="statusClass(l.status)">
        <span v-for="col in columns" :key="col.key" :class="cellClass[col.key]">{{ l[col.key] }}</span>
      </div>
      <div v-if="!logs.length" class="empty">等待执行...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDAGStore } from '../store/dag'
import { LOG_COLUMNS, visibleColumns } from '../policy/fields'
const store = useDAGStore()
// 明细列来自统一字段策略，新增/调整字段时只改 policy/fields，大屏与明细自动对齐
const columns = computed(() => visibleColumns(LOG_COLUMNS, store.role))
const logs = computed(() => store.execution?.logs || [])
// 与原展示保持一致：状态直接转小写作为行样式类
const statusClass = (status: string) => status.toLowerCase()
// 各列对应的样式类（仅原有三种）
const cellClass: Record<string, string> = {
  taskId: 'l-task', status: 'l-status', message: 'l-msg'
}
</script>
<style scoped>
.panel{background:#1a1a2e;border-radius:8px;padding:10px;border:1px solid #2a2a4a;flex:1}
.panel h4{color:#bb86fc;font-size:12px;margin-bottom:6px}
.log-list{max-height:280px;overflow-y:auto;font-size:10px;font-family:monospace}
.log-row{display:flex;gap:6px;padding:2px 4px;border-radius:2px;margin:1px 0}
.log-row.running{background:#3182ce15}.log-row.success{color:#38a169}.log-row.failed{color:#e53e3e;background:#e53e3e10}
.l-status{font-weight:700;min-width:60px}.l-task{color:#888;min-width:70px}.l-msg{color:#ccc}.empty{color:#4a5568}
</style>
