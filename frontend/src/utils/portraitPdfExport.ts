import type {
  CalculationSummary,
  PortraitReportResponse,
  StageComparison,
  WeightSpecItem,
} from '../views/dashboard/portrait'

type PortraitPdfPayload = {
  teacherName: string
  report: PortraitReportResponse
  calculationSummary: CalculationSummary | null
  weightSpec: WeightSpecItem[]
  stageComparison: StageComparison | null
}

type ReportLine = {
  text: string
  font: string
  color: string
  marginTop: number
}

const A4_WIDTH_PT = 595.28
const A4_HEIGHT_PT = 841.89
const CANVAS_WIDTH = 1240
const CANVAS_HEIGHT = 1754
const PAGE_PADDING_X = 96
const PAGE_PADDING_Y = 92
const CONTENT_WIDTH = CANVAS_WIDTH - PAGE_PADDING_X * 2
const FONT_FAMILY = '"Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif'
const LINE_HEIGHT = 34

const toDataUrlBytes = (dataUrl: string): Uint8Array => {
  const base64 = dataUrl.split(',')[1] || ''
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }
  return bytes
}

const escapePdfText = (value: string): string =>
  value.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)')

const splitText = (ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] => {
  if (!text) return ['']
  const lines: string[] = []
  let current = ''
  for (const char of text) {
    const candidate = `${current}${char}`
    if (current && ctx.measureText(candidate).width > maxWidth) {
      lines.push(current)
      current = char
      continue
    }
    current = candidate
  }
  if (current) {
    lines.push(current)
  }
  return lines
}

const drawReportLines = async (lines: ReportLine[]): Promise<string[]> => {
  const canvases: HTMLCanvasElement[] = []
  let canvas = document.createElement('canvas')
  canvas.width = CANVAS_WIDTH
  canvas.height = CANVAS_HEIGHT
  let ctx = canvas.getContext('2d')
  if (!ctx) {
    throw new Error('无法初始化 PDF 画布。')
  }

  const resetPage = (targetCtx: CanvasRenderingContext2D) => {
    targetCtx.fillStyle = '#ffffff'
    targetCtx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
  }

  resetPage(ctx)
  let cursorY = PAGE_PADDING_Y

  const pushPage = () => {
    canvases.push(canvas)
    canvas = document.createElement('canvas')
    canvas.width = CANVAS_WIDTH
    canvas.height = CANVAS_HEIGHT
    ctx = canvas.getContext('2d')
    if (!ctx) {
      throw new Error('无法初始化 PDF 画布。')
    }
    resetPage(ctx)
    cursorY = PAGE_PADDING_Y
  }

  for (const line of lines) {
    ctx.font = line.font
    const wrapped = splitText(ctx, line.text, CONTENT_WIDTH)
    const blockHeight = line.marginTop + wrapped.length * LINE_HEIGHT
    if (cursorY + blockHeight > CANVAS_HEIGHT - PAGE_PADDING_Y) {
      pushPage()
      ctx.font = line.font
    }

    cursorY += line.marginTop
    ctx.fillStyle = line.color
    ctx.textBaseline = 'top'
    for (const textLine of wrapped) {
      ctx.fillText(textLine, PAGE_PADDING_X, cursorY)
      cursorY += LINE_HEIGHT
    }
  }

  canvases.push(canvas)
  return canvases.map(item => item.toDataURL('image/jpeg', 0.92))
}

const buildPdfBlob = (pageDataUrls: string[]): Blob => {
  const objectParts: Array<string | Uint8Array> = []
  const offsets: number[] = [0]
  let length = 0

  const push = (part: string | Uint8Array) => {
    objectParts.push(part)
    length += typeof part === 'string' ? new TextEncoder().encode(part).length : part.length
  }

  push('%PDF-1.4\n%\xFF\xFF\xFF\xFF\n')

  const imageObjectNumbers: number[] = []
  const contentObjectNumbers: number[] = []
  const pageObjectNumbers: number[] = []
  const pagesObjectNumber = pageDataUrls.length * 3 + 1
  const catalogObjectNumber = pagesObjectNumber + 1

  pageDataUrls.forEach((dataUrl, index) => {
    const imageObjectNumber = index * 3 + 1
    const contentObjectNumber = index * 3 + 2
    const pageObjectNumber = index * 3 + 3
    imageObjectNumbers.push(imageObjectNumber)
    contentObjectNumbers.push(contentObjectNumber)
    pageObjectNumbers.push(pageObjectNumber)

    const imageBytes = toDataUrlBytes(dataUrl)
    offsets.push(length)
    push(`${imageObjectNumber} 0 obj\n<< /Type /XObject /Subtype /Image /Width ${CANVAS_WIDTH} /Height ${CANVAS_HEIGHT} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${imageBytes.length} >>\nstream\n`)
    push(imageBytes)
    push('\nendstream\nendobj\n')

    const contentStream = `q\n${A4_WIDTH_PT.toFixed(2)} 0 0 ${A4_HEIGHT_PT.toFixed(2)} 0 0 cm\n/Im${index + 1} Do\nQ`
    const contentBytes = new TextEncoder().encode(contentStream)
    offsets.push(length)
    push(`${contentObjectNumber} 0 obj\n<< /Length ${contentBytes.length} >>\nstream\n${contentStream}\nendstream\nendobj\n`)

    offsets.push(length)
    push(
      `${pageObjectNumber} 0 obj\n<< /Type /Page /Parent ${pagesObjectNumber} 0 R /MediaBox [0 0 ${A4_WIDTH_PT.toFixed(2)} ${A4_HEIGHT_PT.toFixed(2)}] /Resources << /XObject << /Im${index + 1} ${imageObjectNumber} 0 R >> >> /Contents ${contentObjectNumber} 0 R >>\nendobj\n`,
    )
  })

  offsets.push(length)
  push(`${pagesObjectNumber} 0 obj\n<< /Type /Pages /Count ${pageObjectNumbers.length} /Kids [${pageObjectNumbers.map(item => `${item} 0 R`).join(' ')}] >>\nendobj\n`)
  offsets.push(length)
  push(`${catalogObjectNumber} 0 obj\n<< /Type /Catalog /Pages ${pagesObjectNumber} 0 R >>\nendobj\n`)

  const xrefOffset = length
  const totalObjects = catalogObjectNumber
  push(`xref\n0 ${totalObjects + 1}\n`)
  push('0000000000 65535 f \n')
  for (let index = 1; index <= totalObjects; index += 1) {
    const offset = offsets[index] || 0
    push(`${offset.toString().padStart(10, '0')} 00000 n \n`)
  }
  push(`trailer\n<< /Size ${totalObjects + 1} /Root ${catalogObjectNumber} 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`)

  const normalizedParts = objectParts.map(part => {
    if (typeof part === 'string') {
      return part
    }
    const normalized = Uint8Array.from(part)
    return normalized.buffer as ArrayBuffer
  })
  return new Blob(normalizedParts, { type: 'application/pdf' })
}

const buildReportLines = (payload: PortraitPdfPayload): ReportLine[] => {
  const { report, teacherName, calculationSummary, weightSpec, stageComparison } = payload
  const lines: ReportLine[] = [
    {
      text: report.report_title || `${teacherName} 教师画像分析报告`,
      font: `700 40px ${FONT_FAMILY}`,
      color: '#0f172a',
      marginTop: 0,
    },
    {
      text: `生成时间：${new Date(report.generated_at).toLocaleString('zh-CN', { hour12: false })}`,
      font: `400 22px ${FONT_FAMILY}`,
      color: '#475569',
      marginTop: 18,
    },
    {
      text: report.summary,
      font: `400 24px ${FONT_FAMILY}`,
      color: '#334155',
      marginTop: 22,
    },
    {
      text: '画像摘要',
      font: `700 30px ${FONT_FAMILY}`,
      color: '#0f172a',
      marginTop: 30,
    },
  ]

  report.highlights.forEach(item => {
    lines.push({
      text: `• ${item}`,
      font: `400 24px ${FONT_FAMILY}`,
      color: '#1e293b',
      marginTop: 12,
    })
  })

  if (calculationSummary) {
    lines.push(
      {
        text: '科研积分总分',
        font: `700 30px ${FONT_FAMILY}`,
        color: '#0f172a',
        marginTop: 28,
      },
      {
        text: `总分 ${calculationSummary.total_score} 分；积分最高维度 ${calculationSummary.strongest_dimension.name}；待补维度 ${calculationSummary.weakest_dimension.name}`,
        font: `400 24px ${FONT_FAMILY}`,
        color: '#334155',
        marginTop: 12,
      },
    )
  }

  lines.push({
    text: '维度积分结构',
    font: `700 30px ${FONT_FAMILY}`,
    color: '#0f172a',
    marginTop: 28,
  })

  weightSpec.forEach(item => {
    lines.push(
      {
        text: `${item.name}（原始积分 ${item.raw_score ?? 0} 分）`,
        font: `700 24px ${FONT_FAMILY}`,
        color: '#1e293b',
        marginTop: 14,
      },
      {
        text: `雷达展示分 ${item.current_value}，说明：${item.formula_short}`,
        font: `400 22px ${FONT_FAMILY}`,
        color: '#475569',
        marginTop: 8,
      },
      {
        text: `主要输入：${item.main_inputs.join('、') || '暂无'}`,
        font: `400 22px ${FONT_FAMILY}`,
        color: '#64748b',
        marginTop: 6,
      },
      {
        text: item.aggregation_note || item.rationale,
        font: `400 22px ${FONT_FAMILY}`,
        color: '#475569',
        marginTop: 6,
      },
    )
  })

  if (stageComparison) {
    lines.push(
      {
        text: '阶段对比',
        font: `700 30px ${FONT_FAMILY}`,
        color: '#0f172a',
        marginTop: 28,
      },
      {
        text: stageComparison.summary || '当前阶段暂无足够样本形成阶段对比。',
        font: `400 24px ${FONT_FAMILY}`,
        color: '#334155',
        marginTop: 12,
      },
      {
        text: stageComparison.structured_summary || stageComparison.coverage_note || '当前仅保留阶段对比接口边界。',
        font: `400 22px ${FONT_FAMILY}`,
        color: '#64748b',
        marginTop: 10,
      },
    )

    ;(stageComparison.changed_dimensions || []).forEach(item => {
      lines.push(
        {
          text: `${item.name}：${item.baseline_value} → ${item.current_value}（${item.delta > 0 ? '+' : ''}${item.delta}）`,
          font: `700 24px ${FONT_FAMILY}`,
          color: '#1e293b',
          marginTop: 14,
        },
        {
          text: item.change_summary || '当前未形成更细的变化说明。',
          font: `400 22px ${FONT_FAMILY}`,
          color: '#475569',
          marginTop: 8,
        },
      )
      if (item.drivers?.length) {
        lines.push({
          text: `驱动因素：${item.drivers.join('、')}`,
          font: `400 22px ${FONT_FAMILY}`,
          color: '#64748b',
          marginTop: 6,
        })
      }
      if (item.interpretation) {
        lines.push({
          text: item.interpretation,
          font: `400 22px ${FONT_FAMILY}`,
          color: '#475569',
          marginTop: 6,
        })
      }
    })
  }

  const filteredSections = (report.sections || []).filter(
    section => !['阶段对比', '快照摘要', '快照边界'].includes(section.title),
  )

  filteredSections.forEach(section => {
    lines.push(
      {
        text: section.title,
        font: `700 30px ${FONT_FAMILY}`,
        color: '#0f172a',
        marginTop: 28,
      },
      {
        text: section.summary,
        font: `400 24px ${FONT_FAMILY}`,
        color: '#334155',
        marginTop: 12,
      },
    )

    section.bullets.forEach(bullet => {
      lines.push({
        text: `• ${bullet}`,
        font: `400 22px ${FONT_FAMILY}`,
        color: '#475569',
        marginTop: 8,
      })
    })
  })

  return lines
}

export const exportPortraitReportPdf = async (payload: PortraitPdfPayload): Promise<Blob> => {
  const pageImages = await drawReportLines(buildReportLines(payload))
  return buildPdfBlob(pageImages)
}
