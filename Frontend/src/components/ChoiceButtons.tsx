import './ChoiceButtons.css'

interface ChoiceOption {
  value: string
  label: string
}

interface ChoiceButtonsProps {
  options: ChoiceOption[]
  value?: string
  onChange: (value: string) => void
  name: string
}

export function ChoiceButtons({ options, value, onChange, name }: ChoiceButtonsProps) {
  return (
    <div className="choice-buttons" role="radiogroup" aria-label={name}>
      {options.map((opt) => {
        const selected = value === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={selected}
            className={`choice-btn${selected ? ' choice-btn--selected' : ''}`}
            onClick={() => onChange(opt.value)}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
