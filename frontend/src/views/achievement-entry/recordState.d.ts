export function upsertAchievementRecord<T extends { id: number }>(records: T[], nextRecord: T): T[]
export function removeAchievementRecord<T extends { id: number }>(records: T[], recordId: number): T[]
