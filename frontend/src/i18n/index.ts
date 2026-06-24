/**
 * i18n 国际化配置
 *
 * 使用方式：
 * - 模板中：{{ $t('common.save') }}
 * - 脚本中：import { useI18n } from 'vue-i18n'; const { t } = useI18n();
 */
import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import en from './locales/en'

export type MessageSchema = typeof zhCN

const i18n = createI18n<[MessageSchema], 'zh-CN' | 'en'>({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en': en,
  },
})

export default i18n
