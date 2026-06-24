/**
 * 统一图标系统
 * 提供一致的图标使用方式，统一图标库
 * 
 * 设计原则：
 * - 优先使用 lucide-vue-next (更现代、更一致)
 * - Element Plus Icons 仅作为备选
 * - 所有图标支持 size、color、strokeWidth 参数
 */
import {
  // 基础操作
  Search, Plus, X, Check, ChevronDown, ChevronLeft, ChevronRight, ChevronUp,
  MoreHorizontal, MoreVertical, Menu, Ellipsis,
  
  // 导航
  Home, LayoutDashboard, Settings, User, Users,
  
  // 文件操作
  FileText, Folder, FolderOpen, FilePlus, FolderPlus, FileEdit, Trash2,
  Copy, Clipboard, Download, Upload, Share,
  
  // API 相关
  Send, Save, Play, Pause, Square, RefreshCw, RotateCw,
  Plug, Link, ExternalLink, ArrowRight, ArrowLeft, ArrowUp, ArrowDown,
  
  // 状态
  CheckCircle, AlertCircle, AlertTriangle, Info, XCircle,
  Loader, Loader2, Clock, Timer,
  
  // 模式与视图
  Sun, Moon, Eye, EyeOff, Maximize2, Minimize2, ZoomIn, ZoomOut,
  
  // 环境与配置
  Globe, Server, Cpu, Database, HardDrive, Cloud,
  
  // 测试相关
  TestTube, FlaskConical, Activity, BarChart3, PieChart,
  TrendingUp, TrendingDown, LineChart,
  
  // 场景与步骤
  GitBranch, GitMerge, Layers, Component,
  
  // 排序与筛选
  SortAsc, SortDesc, Filter, SlidersHorizontal,
  
  // 其他
  Lock, Unlock, Key, Shield, Bell, BellOff,
  HelpCircle, MessageSquare, Mail,
  Calendar, Clock3, History,
  Tag, Label, Bookmark, Star, Flag,
  
  // 徽章与通知
  Badge, Award, Crown,
} from 'lucide-vue-next'

import {
  // Element Plus Icons (备选)
  Delete, Edit, Setting, Loading,
  Document, DocumentCopy,
  Close, Refresh, View,
  Hide, Show,
  Keys, Connection,
} from '@element-plus/icons-vue'

export {
  // 重新导出 lucide 图标作为默认
  Search, Plus, X, Check, ChevronDown, ChevronLeft, ChevronRight, ChevronUp,
  MoreHorizontal, MoreVertical, Menu, Ellipsis,
  Home, LayoutDashboard, Settings, User, Users,
  FileText, Folder, FolderOpen, FilePlus, FolderPlus, FileEdit, Trash2,
  Copy, Clipboard, Download, Upload, Share,
  Send, Save, Play, Pause, Square, RefreshCw, RotateCw,
  Plug, Link, ExternalLink, ArrowRight, ArrowLeft, ArrowUp, ArrowDown,
  CheckCircle, AlertCircle, AlertTriangle, Info, XCircle,
  Loader, Loader2, Clock, Timer,
  Sun, Moon, Eye, EyeOff, Maximize2, Minimize2, ZoomIn, ZoomOut,
  Globe, Server, Cpu, Database, HardDrive, Cloud,
  TestTube, FlaskConical, Activity, BarChart3, PieChart,
  TrendingUp, TrendingDown, LineChart,
  GitBranch, GitMerge, Layers, Component,
  SortAsc, SortDesc, Filter, SlidersHorizontal,
  Lock, Unlock, Key, Shield, Bell, BellOff,
  HelpCircle, MessageSquare, Mail,
  Calendar, Clock3, History,
  Tag, Label, Bookmark, Star, Flag,
  Badge, Award, Crown,
  
  // Element Plus Icons (备选)
  Delete, Edit, Setting, Loading,
  Document, DocumentCopy,
  Close, Refresh, View, Hide, Show,
  Keys, Connection,
}

// 图标映射表 - 用于动态图标
export const iconMap = {
  // 基础
  search: Search,
  plus: Plus,
  close: X,
  check: Check,
  menu: Menu,
  
  // 文件
  'file-text': FileText,
  folder: Folder,
  'folder-open': FolderOpen,
  trash: Trash2,
  copy: Copy,
  download: Download,
  upload: Upload,
  
  // 操作
  send: Send,
  save: Save,
  play: Play,
  pause: Pause,
  refresh: RefreshCw,
  
  // 状态
  'check-circle': CheckCircle,
  'alert-circle': AlertCircle,
  'alert-triangle': AlertTriangle,
  info: Info,
  
  // 导航
  home: Home,
  dashboard: LayoutDashboard,
  settings: Settings,
  user: User,
  
  // 其他
  sun: Sun,
  moon: Moon,
  globe: Globe,
  'bar-chart': BarChart3,
  
  // Element Plus 兼容
  delete: Delete,
  edit: Edit,
  loading: Loading,
}

// 常用图标集
export const iconSets = {
  // 动作类
  actions: ['play', 'pause', 'save', 'delete', 'edit', 'refresh', 'copy', 'download'],
  
  // 状态类
  status: ['check-circle', 'alert-circle', 'alert-triangle', 'info'],
  
  // 导航类
  navigation: ['home', 'dashboard', 'settings', 'user', 'menu'],
  
  // 文件类
  file: ['file-text', 'folder', 'folder-open', 'trash'],
}

// 预设图标尺寸 — 与 tokens.css --size-icon-* 对齐
export const iconSizes = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 20,
  xl: 32,
  '2xl': 48,
}

/**
 * 图标组件 Props 类型
 */
export interface IconProps {
  size?: number | string
  color?: string
  strokeWidth?: number
  class?: string
}

/**
 * 图标工具函数
 */
export function getIcon(name: string) {
  return iconMap[name as keyof typeof iconMap] || Search
}