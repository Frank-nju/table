import { useI18n } from 'vue-i18n'
import { ApiError } from '@/api/client'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'

const WEEKDAYS = {
  en: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
  zh: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
}

/** Turns API errors into friendly, translated messages. */
export function useErrors() {
  const { t, te, locale } = useI18n()
  const session = useSession()
  const ui = useUi()

  function weekdayName(index: number): string {
    return WEEKDAYS[locale.value === 'zh' ? 'zh' : 'en'][index] ?? ''
  }

  function message(err: unknown): string {
    if (err instanceof ApiError) {
      const key = `errors.${err.code}`
      if (te(key)) {
        const cfg = session.config
        return t(key, {
          weekday: cfg ? weekdayName(cfg.meetup_weekday) : '',
          start: cfg?.meetup_window[0] ?? '',
          end: cfg?.meetup_window[1] ?? '',
        })
      }
      return err.message
    }
    return t('common.somethingWrong')
  }

  function report(err: unknown): void {
    ui.toast(message(err), 'error', 6000)
  }

  return { message, report, weekdayName }
}
