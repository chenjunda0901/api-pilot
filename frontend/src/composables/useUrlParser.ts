export function parseUrl(input: string): { method: string; path: string } | null {
  const trimmed = input.trim()
  const match = trimmed.match(/^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(\/\S+)/i)
  if (match) return { method: match[1].toUpperCase(), path: match[2] }
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    try {
      const url = new URL(trimmed)
      return { method: 'GET', path: url.pathname + url.search }
    } catch { return null }
  }
  if (trimmed.startsWith('/')) return { method: 'GET', path: trimmed }
  return null
}
