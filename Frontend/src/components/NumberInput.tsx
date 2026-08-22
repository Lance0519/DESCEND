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
  error?: string | null
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
  error,
}: NumberInputProps) {
  const describedBy = error ? `${id}-error` : undefined

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
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          className={error ? 'number-input__field--error' : undefined}
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
      {error ? (
        <p id={describedBy} className="number-input__error" role="alert">
          {error}
        </p>
      ) : null}
    </label>
  )
}
