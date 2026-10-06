import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import './Button.css'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  block?: boolean
  children: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      block = false,
      className = '',
      type = 'button',
      children,
      ...props
    },
    ref,
  ) => {
    const classes = [
      'app-btn',
      `app-btn--${variant}`,
      `app-btn--${size}`,
      block ? 'app-btn--block' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ')

    return (
      <button ref={ref} type={type} className={classes} {...props}>
        {children}
      </button>
    )
  },
)

Button.displayName = 'Button'
