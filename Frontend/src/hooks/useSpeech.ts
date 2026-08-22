import { useCallback, useEffect, useRef, useState } from 'react'
import type { Language } from '../types/assessment'

function pickVoice(language: Language): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !window.speechSynthesis) return null
  const voices = window.speechSynthesis.getVoices()
  if (!voices.length) return null

  if (language === 'tl') {
    const fil =
      voices.find((v) => v.lang.toLowerCase().startsWith('fil')) ??
      voices.find((v) => v.lang.toLowerCase().startsWith('tl')) ??
      voices.find((v) => {
        const name = v.name.toLowerCase()
        return (
          name.includes('filipino') ||
          name.includes('tagalog') ||
          name.includes('philippines') ||
          name.includes('fil-ph')
        )
      })
    return fil ?? null
  }

  return (
    voices.find((v) => v.lang.toLowerCase().startsWith('en-us')) ??
    voices.find((v) => v.lang.toLowerCase().startsWith('en')) ??
    null
  )
}

function waitForVoices(): Promise<SpeechSynthesisVoice[]> {
  return new Promise((resolve) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      resolve([])
      return
    }
    const existing = window.speechSynthesis.getVoices()
    if (existing.length) {
      resolve(existing)
      return
    }
    const onChange = () => {
      window.speechSynthesis.removeEventListener('voiceschanged', onChange)
      resolve(window.speechSynthesis.getVoices())
    }
    window.speechSynthesis.addEventListener('voiceschanged', onChange)
    // Safety timeout if voiceschanged never fires
    window.setTimeout(() => {
      window.speechSynthesis.removeEventListener('voiceschanged', onChange)
      resolve(window.speechSynthesis.getVoices())
    }, 750)
  })
}

export function useSpeech(language: Language) {
  const [speaking, setSpeaking] = useState(false)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  const cancel = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    utteranceRef.current = null
    setSpeaking(false)
  }, [])

  useEffect(() => {
    void waitForVoices()
    return () => cancel()
  }, [cancel])

  const speak = useCallback(
    async (text: string) => {
      if (!text.trim() || typeof window === 'undefined' || !window.speechSynthesis) return
      cancel()
      await waitForVoices()

      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = language === 'tl' ? 'fil-PH' : 'en-US'
      utterance.rate = language === 'tl' ? 0.9 : 1
      const preferred = pickVoice(language)
      if (preferred) utterance.voice = preferred

      utterance.onend = () => setSpeaking(false)
      utterance.onerror = () => setSpeaking(false)
      utteranceRef.current = utterance
      setSpeaking(true)
      window.speechSynthesis.speak(utterance)
    },
    [cancel, language],
  )

  return { speak, cancel, speaking }
}
