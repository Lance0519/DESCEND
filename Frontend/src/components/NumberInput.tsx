import './NumberInput.css'

interface NumberInputProps {
  id: string
  value: number | ''
  onChange: (value: number | '') => void
  min?: number
  max?: number
  step?: number
  unit?: string
  label?: string
}

export function NumberInput({
  id,
  value,
  onChange,
  min,
  max,
  step = 1,
  unit,
  label,
}: NumberInputProps) {
  return (
    <label className="number-input" htmlFor={id}>
      {label ? <span className="number-input__label">{label}</span> : null}
      <div className="number-input__row">
        <input
          id={id}
          type="number"
          inputMode="decimal"
          min={min}
          max={max}
          step={step}
          value={value === '' ? '' : value}
          onChange={(e) => {
            const raw = e.target.value
            if (raw === '') {
              onChange('')
              return
            }
            const n = Number(raw)
            if (!Number.isNaN(n)) onChange(n)
          }}
        />
        {unit ? <span className="number-input__unit">{unit}</span> : null}
      </div>
    </label>
  )
}
