import dynamic from 'next/dynamic'

export const RiskChart = dynamic(() => import('./RiskChart').then(m => ({ default: m.RiskChart })), { ssr: false })
export const WinProbGauge = dynamic(() => import('./WinProbGauge').then(m => ({ default: m.WinProbGauge })), { ssr: false })
export const SensitivityWaterfall = dynamic(() => import('./SensitivityWaterfall').then(m => ({ default: m.SensitivityWaterfall })), { ssr: false })
