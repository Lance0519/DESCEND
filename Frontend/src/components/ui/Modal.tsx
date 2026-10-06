import { useEffect, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'
import './Modal.css'

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: ReactNode
  children: ReactNode
  actions?: ReactNode
  size?: 'sm' | 'md' | 'lg'
  showCloseButton?: boolean
  closeLabel?: string
  ariaLabelledBy?: string
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  actions,
  size = 'md',
  showCloseButton = false,
  closeLabel = 'Close modal',
  ariaLabelledBy = 'app-modal-title',
}: ModalProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const closeBtnRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!isOpen) return

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    closeBtnRef.current?.focus()

    // Prevent background scrolling while modal is open
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = prevOverflow
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      className="app-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? ariaLabelledBy : undefined}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose()
        }
      }}
    >
      <div className={`app-modal__card app-modal__card--${size}`} ref={cardRef}>
        {(title || showCloseButton) && (
          <div className="app-modal__header">
            {title ? (
              <h2 id={ariaLabelledBy} className="app-modal__title">
                {title}
              </h2>
            ) : (
              <span />
            )}
            {showCloseButton && (
              <button
                type="button"
                ref={closeBtnRef}
                className="app-modal__close"
                aria-label={closeLabel}
                onClick={onClose}
              >
                <X size={18} aria-hidden />
              </button>
            )}
          </div>
        )}
        <div className="app-modal__body">{children}</div>
        {actions && <div className="app-modal__actions">{actions}</div>}
      </div>
    </div>
  )
}
