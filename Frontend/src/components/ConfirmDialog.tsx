import type { ReactNode } from 'react'
import { Modal } from './ui/Modal'
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
    <Modal
      isOpen={true}
      onClose={onCancel}
      title={title}
      size="sm"
      ariaLabelledBy="confirm-dialog-title"
      actions={
        <>
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
        </>
      }
    >
      <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>{text}</p>
      {extra}
    </Modal>
  )
}
