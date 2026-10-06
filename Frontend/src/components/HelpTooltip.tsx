import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { Info, X } from 'lucide-react'
import './HelpTooltip.css'

export interface HelpTooltipProps {
  title: string
  body: string
  triggerLabel?: string
  closeLabel?: string
  buttonAriaLabel?: string
}

export function HelpTooltip({
  title,
  body,
  triggerLabel = 'What does this mean?',
  closeLabel = 'Close explanation',
  buttonAriaLabel,
}: HelpTooltipProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  function toggle(e: MouseEvent<HTMLButtonElement>) {
    e.preventDefault()
    e.stopPropagation()
    setOpen((prev) => !prev)
  }

  function handleClose(e?: MouseEvent<HTMLButtonElement>) {
    if (e) {
      e.preventDefault()
      e.stopPropagation()
    }
    setOpen(false)
  }

  useEffect(() => {
    if (!open) return

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false)
      }
    }

    function onPointerDown(e: PointerEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('pointerdown', onPointerDown)
    closeButtonRef.current?.focus()

    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('pointerdown', onPointerDown)
    }
  }, [open])

  return (
    <div className="help-tooltip" ref={containerRef}>
      <button
        type="button"
        className={`help-tooltip__trigger ${open ? 'help-tooltip__trigger--active' : ''}`}
        onClick={toggle}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={buttonAriaLabel || `${title}: ${body}`}
      >
        <Info size={16} aria-hidden />
        <span className="help-tooltip__trigger-label">{triggerLabel}</span>
      </button>

      {open ? (
        <div
          className="help-tooltip__popover"
          role="dialog"
          aria-modal="false"
          aria-label={title}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="help-tooltip__header">
            <h4 className="help-tooltip__title">{title}</h4>
            <button
              type="button"
              ref={closeButtonRef}
              className="help-tooltip__close"
              onClick={handleClose}
              aria-label={closeLabel}
            >
              <X size={16} aria-hidden />
            </button>
          </div>
          <p className="help-tooltip__body">{body}</p>
        </div>
      ) : null}
    </div>
  )
}
