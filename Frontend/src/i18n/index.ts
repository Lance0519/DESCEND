import { en, type TranslationDict } from './en'
import { tl } from './tl'
import type { Language } from '../types/assessment'

const dictionaries: Record<Language, TranslationDict> = { en, tl }

export function getDictionary(lang: Language): TranslationDict {
  return dictionaries[lang]
}

export type { TranslationDict }
