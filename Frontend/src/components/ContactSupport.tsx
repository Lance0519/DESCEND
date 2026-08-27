import { useEffect, useRef, useState } from 'react'
import { Check, Copy, Mail, X } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext'
import './ContactSupport.css'

const SUPPORT_EMAIL =
  String(import.meta.env.VITE_SUPPORT_EMAIL ?? '').trim() || 'justinelance0067@gmail.com'

/** Clipboard API needs a secure context, so fall back to a hidden selection copy. */
async function copyText(value: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value)
      return true
    }
  } catch {
    // fall through to the legacy path
  }
  try {
    const field = document.createElement('textarea')
    field.value = value
    field.setAttribute('readonly', '')
    field.style.position = 'fixed'
    field.style.opacity = '0'
    document.body.appendChild(field)
    field.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(field)
    return ok
  } catch {
    return false
  }
}

export function ContactSupport() {
  const { t } = useLanguage()
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 2000)
    return () => window.clearTimeout(timer)
  }, [copied])

  const mailHref = `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(t.contactSupportSubject)}`

  return (
    <>
      <p className="contact-support">
        <Mail size={16} aria-hidden />
        <span>
          {t.contactSupportText}{' '}
          <button
            type="button"
            className="contact-support__link"
            onClick={() => {
              setCopied(false)
              setOpen(true)
            }}
          >
            {t.contactSupportCta}
          </button>
        </span>
      </p>

      {open ? (
        <div
          className="contact-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="contact-dialog-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpen(false)
          }}
        >
          <div className="contact-dialog__card">
            <button
              type="button"
              ref={closeRef}
              className="contact-dialog__close"
              aria-label={t.contactSupportClose}
              onClick={() => setOpen(false)}
            >
              <X size={18} aria-hidden />
            </button>
            <h2 id="contact-dialog-title">
              <Mail size={20} aria-hidden /> {t.contactSupportDialogTitle}
            </h2>
            <p className="contact-dialog__help">{t.contactSupportDialogHelp}</p>
            <p className="contact-dialog__address">{SUPPORT_EMAIL}</p>
            <div className="contact-dialog__actions">
              <button
                type="button"
                className="contact-dialog__copy"
                onClick={() => void copyText(SUPPORT_EMAIL).then(setCopied)}
              >
                {copied ? <Check size={16} aria-hidden /> : <Copy size={16} aria-hidden />}
                {copied ? t.contactSupportCopied : t.contactSupportCopy}
              </button>
              <a className="contact-dialog__mail" href={mailHref}>
                {t.contactSupportOpenMail}
              </a>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
