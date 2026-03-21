import type { BibtexImportResponse, PaperFormState, PaperRecord, PaperSummaryResponse } from '../../types/achievements'

export function buildPaperDuplicateWarnings(
  form: PaperFormState,
  papers: PaperRecord[],
  editingId: number | null,
): string[]

export function buildPaperMetadataHints(form: PaperFormState): string[]

export function buildPaperYearOptions(summary: PaperSummaryResponse | null): Array<{ label: string; value: string }>

export function buildImportFeedbackLines(payload: BibtexImportResponse): string[]
