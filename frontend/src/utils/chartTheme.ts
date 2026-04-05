import type { EChartsOption } from 'echarts'

const fallbackPalette = {
  textPrimary: '#0f172a',
  textSecondary: '#475569',
  textTertiary: '#64748b',
  border: 'rgba(148, 163, 184, 0.28)',
  borderStrong: '#94a3b8',
  surface: '#ffffff',
}

const getThemeToken = (token: string, fallback: string): string => {
  if (typeof window === 'undefined') {
    return fallback
  }

  const value = getComputedStyle(document.documentElement).getPropertyValue(token).trim()
  return value || fallback
}

export const getChartThemeTokens = () => ({
  textPrimary: getThemeToken('--text-primary', fallbackPalette.textPrimary),
  textSecondary: getThemeToken('--text-secondary', fallbackPalette.textSecondary),
  textTertiary: getThemeToken('--text-tertiary', fallbackPalette.textTertiary),
  border: getThemeToken('--border-color-soft', fallbackPalette.border),
  borderStrong: getThemeToken('--text-disabled', fallbackPalette.borderStrong),
  surface: getThemeToken('--surface-2', fallbackPalette.surface),
})

export const buildBaseChartOption = (): Pick<EChartsOption, 'backgroundColor' | 'textStyle' | 'tooltip'> => {
  const tokens = getChartThemeTokens()
  return {
    backgroundColor: 'transparent',
    textStyle: {
      color: tokens.textSecondary,
    },
    tooltip: {
      backgroundColor: tokens.surface,
      borderColor: tokens.border,
      textStyle: {
        color: tokens.textPrimary,
      },
    },
  }
}
