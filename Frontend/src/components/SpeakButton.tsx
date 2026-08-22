import { Volume2, VolumeX } from 'lucide-react'
import './SpeakButton.css'

interface SpeakButtonProps {
  speaking: boolean
  onSpeak: () => void
  onStop: () => void
  speakLabel: string
  stopLabel: string
}

export function SpeakButton({ speaking, onSpeak, onStop, speakLabel, stopLabel }: SpeakButtonProps) {
  return (
    <button
      type="button"
      className="speak-btn"
      onClick={speaking ? onStop : onSpeak}
      aria-label={speaking ? stopLabel : speakLabel}
    >
      {speaking ? <VolumeX size={20} /> : <Volume2 size={20} />}
      <span>{speaking ? stopLabel : speakLabel}</span>
    </button>
  )
}
