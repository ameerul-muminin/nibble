import type { ButtonHTMLAttributes } from 'react'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'accent'
}

/** The chunky press-down button. Every action in Nibble uses this. */
export function Button({ variant = 'primary', className = '', ...rest }: Props) {
  return <button className={`btn btn--${variant} ${className}`} {...rest} />
}
