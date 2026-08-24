import { SpeechConfig, SpeechSynthesizer, ResultReason } from 'microsoft-cognitiveservices-speech-sdk'

// -----------------------------------------------------------------------------
// Paste your Azure Speech credentials here (do not commit real keys).
// You can also set VITE_AZURE_SPEECH_KEY and VITE_AZURE_SPEECH_REGION in .env.
// -----------------------------------------------------------------------------
const AZURE_SPEECH_KEY = ''
const AZURE_SPEECH_REGION = 'eastasia'
const AZURE_SPEECH_LANGUAGE = 'fil-PH'
const AZURE_SPEECH_VOICE = 'fil-PH-BlessicaNeural'

function resolveSpeechKey(): string {
  return (
    AZURE_SPEECH_KEY.trim() || String(import.meta.env.VITE_AZURE_SPEECH_KEY ?? '').trim()
  )
}

function resolveSpeechRegion(): string {
  return (
    AZURE_SPEECH_REGION.trim() ||
    String(import.meta.env.VITE_AZURE_SPEECH_REGION ?? 'eastasia').trim()
  )
}

export function isAzureSpeechConfigured(): boolean {
  return Boolean(resolveSpeechKey() && resolveSpeechRegion())
}

let activeSynthesizer: SpeechSynthesizer | null = null

export function stopAzureSpeech(): void {
  if (!activeSynthesizer) return
  try {
    activeSynthesizer.close()
  } catch {
    // Already closed.
  }
  activeSynthesizer = null
}

export function speakAzureText(text: string): Promise<void> {
  const trimmed = text.trim()
  if (!trimmed) return Promise.resolve()

  const key = resolveSpeechKey()
  const region = resolveSpeechRegion()
  if (!key || !region) {
    return Promise.reject(new Error('Azure Speech key or region is missing'))
  }

  stopAzureSpeech()

  const speechConfig = SpeechConfig.fromSubscription(key, region)
  speechConfig.speechSynthesisLanguage = AZURE_SPEECH_LANGUAGE
  speechConfig.speechSynthesisVoiceName = AZURE_SPEECH_VOICE

  const synthesizer = new SpeechSynthesizer(speechConfig)
  activeSynthesizer = synthesizer

  return new Promise((resolve, reject) => {
    synthesizer.speakTextAsync(
      trimmed,
      (result) => {
        if (activeSynthesizer === synthesizer) activeSynthesizer = null
        synthesizer.close()
        if (result.reason === ResultReason.SynthesizingAudioCompleted) {
          resolve()
          return
        }
        reject(new Error(result.errorDetails || 'Azure speech synthesis failed'))
      },
      (error) => {
        if (activeSynthesizer === synthesizer) activeSynthesizer = null
        synthesizer.close()
        reject(typeof error === 'string' ? new Error(error) : error)
      },
    )
  })
}
