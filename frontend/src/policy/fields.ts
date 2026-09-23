/**
 * 大屏与普通页面共享的唯一字段可见范围策略（与后端 app/field_policy.py 对齐）。
 *
 * 字段要不要脱敏、只读成员（viewer）能看到哪些列，只在本文件的字段目录里
 * 维护一份；调整范围或新增字段时只改这里。明细列定义（*_COLUMNS）与数据
 * 投影（projectXxx）都从同一份目录派生，刷新后大屏与主界面明细字段保持一致。
 */

export type Role = 'operator' | 'viewer'
export const ROLE_OPERATOR: Role = 'operator'
export const ROLE_VIEWER: Role = 'viewer'
export const DEFAULT_ROLE: Role = ROLE_OPERATOR

/** 字段目录条目：key 为字段名，sensitive 表示需脱敏，viewerVisible 表示只读成员可见 */
export interface FieldDef<K extends string = string> { key: K; sensitive: boolean; viewerVisible: boolean }
/** 明细列：字段目录条目 + 展示标题 */
export interface ColumnDef<K extends string = string> extends FieldDef<K> { label: string }

const field = <K extends string>(key: K, sensitive: boolean, viewerVisible: boolean): FieldDef<K> =>
  ({ key, sensitive, viewerVisible })
const column = <K extends string>(key: K, label: string, sensitive = false, viewerVisible = true): ColumnDef<K> =>
  ({ key, label, sensitive, viewerVisible })

// ---- 工作流节点字段（大屏 DAG 画布与明细共用目录）----
export const NODE_FIELDS: FieldDef<'id' | 'name' | 'deps' | 'x' | 'y' | 'status' | 'startTime' | 'endTime' | 'retries'>[] = [
  field('id', false, true),
  field('name', true, true),
  field('deps', false, true),
  field('x', false, true),
  field('y', false, true),
  field('status', false, true),
  field('startTime', false, true),
  field('endTime', false, true),
  field('retries', false, true),
]

// ---- 主界面取数字段（与后端 LOG_FIELDS / BREAKER_FIELDS 对齐，用于数据投影）----
export const LOG_FIELDS: FieldDef<'taskId' | 'status' | 'timestamp' | 'message'>[] = [
  field('taskId', false, true),
  field('status', false, true),
  field('timestamp', false, true),
  field('message', true, true),
]
export const BREAKER_FIELDS: FieldDef<'taskId' | 'failureCount' | 'state' | 'cooldownUntil'>[] = [
  field('taskId', false, true),
  field('failureCount', false, true),
  field('state', false, true),
  field('cooldownUntil', false, true),
]

// ---- 主界面明细列（组件渲染用的列，是取数字段的子集）----
// timestamp 属于取数字段但不在明细列中展示
export const LOG_COLUMNS: ColumnDef<'taskId' | 'status' | 'message'>[] = [
  column('taskId', '任务'),
  column('status', '状态'),
  column('message', '消息', true),
]
export const BREAKER_COLUMNS: ColumnDef<'taskId' | 'state' | 'failureCount'>[] = [
  column('taskId', '任务'),
  column('state', '状态'),
  column('failureCount', '失败次数'),
]

/** 未知角色按可读写成员处理，与后端保持一致，保证旧调用方结果不变 */
export function normalizeRole(role: string | null | undefined): Role {
  return role === ROLE_VIEWER ? ROLE_VIEWER : ROLE_OPERATOR
}

/** 统一脱敏规则：保留首尾，其余以 * 代替（与后端 mask_value 一致） */
export function maskValue(value: unknown): unknown {
  if (value === null || value === undefined) return value
  const text = String(value)
  if (text.length <= 2) return '*'.repeat(text.length)
  return text[0] + '*'.repeat(text.length - 2) + text[text.length - 1]
}

/** 按字段目录投影一条记录：裁剪只读成员不可见列并对敏感列脱敏 */
function projectRecord<T extends object>(record: T, fields: FieldDef[], role: Role): T {
  const source = record as Record<string, unknown>
  const out: Record<string, unknown> = {}
  for (const { key, sensitive, viewerVisible } of fields) {
    if (role === ROLE_VIEWER && !viewerVisible) continue
    const value = source[key]
    out[key] = sensitive && role === ROLE_VIEWER ? maskValue(value) : value
  }
  return out as T
}

/** 当前角色在明细里可见的列（大屏与普通页面字段列表的唯一来源） */
export function visibleColumns<K extends string>(columns: ColumnDef<K>[], role: Role): ColumnDef<K>[] {
  return columns.filter(c => role !== ROLE_VIEWER || c.viewerVisible)
}

export function projectNode<T extends object>(node: T, role: Role): T {
  return projectRecord(node, NODE_FIELDS, role)
}
export function projectLog<T extends object>(log: T, role: Role): T {
  return projectRecord(log, LOG_FIELDS, role)
}
export function projectBreaker<T extends object>(breaker: T, role: Role): T {
  return projectRecord(breaker, BREAKER_FIELDS, role)
}
