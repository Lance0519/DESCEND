import type { ReactNode } from 'react'
import './ConfirmDialog.css'

interface ConfirmDialogProps {
  title: string
  text: string
  confirmLabel: string
  cancelLabel: string
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
  extra?: ReactNode
}

export function ConfirmDialog({
  title,
  text,
  confirmLabel,
  cancelLabel,
  danger,
  onConfirm,
  onCancel,
  extra,
}: ConfirmDialogProps) {
  return (
    <div className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title">
      <div className="confirm-dialog__card">
        <h2 id="confirm-dialog-title">{title}</h2>
        <p>{text}</p>
        {extra}
        <div className="confirm-dialog__actions">
          <button type="button" className="confirm-dialog__cancel" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={danger ? 'confirm-dialog__confirm confirm-dialog__confirm--danger' : 'confirm-dialog__confirm'}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
