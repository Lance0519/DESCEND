import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchTtsAudio } from '../api/client'
import type { Language } from '../types/assessment'

const audioCache = new Map<string, string>()

export function useSpeech(language: Language) {
  const [speaking, setSpeaking] = useState(false)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const cancel = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    utteranceRef.current = null
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    setSpeaking(false)
  }, [])

  useEffect(() => () => cancel(), [cancel])

  const speakWeb = useCallback(
    (text: string) => {
      if (typeof window === 'undefined' || !window.speechSynthesis || !text.trim()) return
      cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = language === 'tl' ? 'fil-PH' : 'en-US'
      const voices = window.speechSynthesis.getVoices()
      const preferred =
        voices.find((v) =>
          language === 'tl'
            ? v.lang.toLowerCase().startsWith('fil') || v.lang.toLowerCase().startsWith('tl')
            : v.lang.toLowerCase().startsWith('en'),
        ) ?? null
      if (preferred) utterance.voice = preferred
      utterance.onend = () => setSpeaking(false)
      utterance.onerror = () => setSpeaking(false)
      utteranceRef.current = utterance
      setSpeaking(true)
      window.speechSynthesis.speak(utterance)
    },
    [cancel, language],
  )

  const speak = useCallback(
    async (text: string) => {
      if (!text.trim()) return
      cancel()
      const cacheKey = `${language}:${text}`
      try {
        let url = audioCache.get(cacheKey)
        if (!url) {
          const blob = await fetchTtsAudio(text, language)
          if (blob && blob.size > 0) {
            url = URL.createObjectURL(blob)
            audioCache.set(cacheKey, url)
          }
        }
        if (url) {
          const audio = new Audio(url)
          audioRef.current = audio
          setSpeaking(true)
          audio.onended = () => setSpeaking(false)
          audio.onerror = () => {
            setSpeaking(false)
            speakWeb(text)
          }
          await audio.play()
          return
        }
      } catch {
        /* fall through */
      }
      speakWeb(text)
    },
    [cancel, language, speakWeb],
  )

  return { speak, cancel, speaking }
}
