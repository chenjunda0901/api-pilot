/**
 * 内置动态变量系统
 * 支持 Postman/Apifox 风格的动态变量
 * 使用方式：{{ $timestamp }}, {{ $randomInt }}, {{ $guid }} 等
 */

export interface BuiltinVarDef {
  name: string           // 变量名（如 $timestamp）
  label: string          // 显示标签（如 "当前时间戳"）
  description: string    // 描述
  category: 'time' | 'random' | 'string' | 'other'
  example: string        // 示例输出
  fn: (...args: string[]) => string  // 生成函数
  isRuntimeOnly?: boolean // 是否仅在运行时可解析
}

// 内置变量注册表
export const BUILTIN_VARS: Record<string, BuiltinVarDef> = {
  // ===== 时间类 =====
  '$timestamp': {
    name: '$timestamp',
    label: '时间戳',
    description: '当前 Unix 时间戳（秒）',
    category: 'time',
    example: '1740000000',
    fn: () => Math.floor(Date.now() / 1000).toString(),
  },
  '$timestampMs': {
    name: '$timestampMs',
    label: '毫秒时间戳',
    description: '当前 Unix 时间戳（毫秒）',
    category: 'time',
    example: '1740000000000',
    fn: () => Date.now().toString(),
  },
  '$date': {
    name: '$date',
    label: '格式化日期',
    description: '当前日期，默认 yyyy-MM-dd，可指定格式：{{ $date(yyyy/MM/dd) }}',
    category: 'time',
    example: '2026-06-11',
    fn: (format = 'yyyy-MM-dd') => formatDate(format),
  },
  '$time': {
    name: '$time',
    label: '格式化时间',
    description: '当前时间，默认 HH:mm:ss',
    category: 'time',
    example: '14:30:00',
    fn: (format = 'HH:mm:ss') => formatDate(format),
  },
  '$datetime': {
    name: '$datetime',
    label: '日期时间',
    description: '当前日期和时间',
    category: 'time',
    example: '2026-06-11 14:30:00',
    fn: (format = 'yyyy-MM-dd HH:mm:ss') => formatDate(format),
  },
  '$isoDateTime': {
    name: '$isoDateTime',
    label: 'ISO 日期时间',
    description: 'ISO 8601 格式日期时间',
    category: 'time',
    example: '2026-06-11T14:30:00.000Z',
    fn: () => new Date().toISOString(),
  },

  // ===== 随机数类 =====
  '$randomInt': {
    name: '$randomInt',
    label: '随机整数',
    description: '0-1000 随机整数，可指定范围：{{ $randomInt(1,100) }}',
    category: 'random',
    example: '42',
    fn: (min = '0', max = '1000') =>
      Math.floor(Math.random() * (parseInt(max, 10) - parseInt(min, 10) + 1) + parseInt(min, 10)).toString(),
  },
  '$randomFloat': {
    name: '$randomFloat',
    label: '随机浮点数',
    description: '0-1 随机浮点数',
    category: 'random',
    example: '0.723',
    fn: () => Math.random().toFixed(6),
  },
  '$randomBool': {
    name: '$randomBool',
    label: '随机布尔值',
    description: 'true 或 false',
    category: 'random',
    example: 'true',
    fn: () => Math.random() > 0.5 ? 'true' : 'false',
  },

  // ===== 字符串/标识符类 =====
  '$guid': {
    name: '$guid',
    label: 'GUID/UUID',
    description: '生成 UUID v4 格式字符串',
    category: 'string',
    example: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    fn: () => crypto.randomUUID?.() ?? generateFakeUuid(),
  },
  '$uuid': {
    name: '$uuid',
    label: 'UUID',
    description: '同 $guid',
    category: 'string',
    example: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    fn: () => crypto.randomUUID?.() ?? generateFakeUuid(),
  },
  '$randomString': {
    name: '$randomString',
    label: '随机字符串',
    description: '指定长度的随机字母数字字符串，默认 16 位',
    category: 'string',
    example: 'Kj9xM2nPqR7vBwT1',
    fn: (length = '16') => generateRandomString(parseInt(length, 10)),
  },
  '$randomName': {
    name: '$randomName',
    label: '随机姓名',
    description: '中文或英文随机姓名',
    category: 'string',
    example: '张三',
    fn: () => RANDOM_NAMES[Math.floor(Math.random() * RANDOM_NAMES.length)],
  },
  '$randomEmail': {
    name: '$randomEmail',
    label: '随机邮箱',
    description: '随机邮箱地址',
    category: 'string',
    example: 'user_abc123@example.com',
    fn: () => `user_${generateRandomString(8)}@example.com`,
  },
  '$randomPhone': {
    name: '$randomPhone',
    label: '随机手机号',
    description: '随机中国手机号',
    category: 'string',
    example: '13800138000',
    fn: () =>
      `1${3 + Math.floor(Math.random() * 8)}${Array.from({ length: 9 }, () =>
        Math.floor(Math.random() * 10).toString(),
      ).join('')}`,
  },

  // ===== 其他 =====
  '$now': {
    name: '$now',
    label: '当前时刻',
    description: '当前日期时间的友好描述',
    category: 'other',
    example: '刚刚',
    fn: () => new Date().toLocaleString('zh-CN'),
  },
  '$index': {
    name: '$index',
    label: '循环索引',
    description: '数据驱动执行时的当前行索引（从 1 开始）',
    category: 'other',
    example: '1',
    fn: () => '1',
    isRuntimeOnly: true,
  },
}

// 辅助函数
function formatDate(format: string): string {
  const d = new Date()
  const map: Record<string, string> = {
    yyyy: d.getFullYear().toString(),
    MM: String(d.getMonth() + 1).padStart(2, '0'),
    dd: String(d.getDate()).padStart(2, '0'),
    HH: String(d.getHours()).padStart(2, '0'),
    mm: String(d.getMinutes()).padStart(2, '0'),
    ss: String(d.getSeconds()).padStart(2, '0'),
  }
  let result = format
  for (const [k, v] of Object.entries(map)) {
    result = result.replaceAll(k, v)
  }
  return result
}

function generateRandomString(length: number): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  return Array.from({ length }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
}

function generateFakeUuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

const RANDOM_NAMES = [
  '张三', '李四', '王五', '赵六', '钱七', '孙八', '周九', '吴十',
  'John Doe', 'Jane Smith', 'Alice Johnson', 'Bob Brown',
]

/**
 * 核心函数：解析并替换模板字符串中的内置变量引用
 * {{ $timestamp }} → "1740000000"
 * {{ $randomInt(1,100) }} → "42"
 * {{ $date(yyyy/MM/dd) }} → "2026/06/11"
 */
export function resolveBuiltinVars(template: string, context?: Record<string, string>): string {
  if (!template) return template

  return template.replace(
    /\{\{\s*(\$[\w]+)(?:\(([^)]*)\))?\s*\}\}/g,
    (match, varName, args) => {
      const def = BUILTIN_VARS[varName]
      if (!def) return match

      if (context && context[varName]) return context[varName]

      if (args) {
        const parsedArgs = args.split(',').map((a) => a.trim())
        return def.fn(...parsedArgs)
      }
      return def.fn()
    },
  )
}

/**
 * 获取所有内置变量的列表（用于 UI 展示提示）
 */
export function getBuiltinVarList(): BuiltinVarDef[] {
  return Object.values(BUILTIN_VARS)
}

/**
 * 获取分类后的内置变量
 */
export function getBuiltinVarsByCategory(): Record<string, BuiltinVarDef[]> {
  const grouped: Record<string, BuiltinVarDef[]> = {}
  for (const v of Object.values(BUILTIN_VARS)) {
    if (!grouped[v.category]) grouped[v.category] = []
    grouped[v.category].push(v)
  }
  return grouped
}

/** 分类标签映射 */
export const CATEGORY_LABELS: Record<string, string> = {
  time: '\u23F0 \u65F6\u95F4',
  random: '\u{1F3B2} \u968F\u673A',
  string: '\u{1F524} \u5B57\u7B26\u4E32',
  other: '\u2699 \u5176\u4ED6',
}
