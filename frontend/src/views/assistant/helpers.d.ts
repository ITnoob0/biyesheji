import type { AssistantAnswerResponse, AssistantQuestionType } from '../../types/assistant'

export interface AssistantQuestionOption {
  label: string
  value: AssistantQuestionType
}

export declare const assistantQuestionOptions: AssistantQuestionOption[]
export declare const supportedQuestionTypes: AssistantQuestionType[]
export declare function buildAssistantFallbackAnswer(
  questionType: AssistantQuestionType,
  reason?: string,
): AssistantAnswerResponse
