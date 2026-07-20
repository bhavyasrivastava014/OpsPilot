import type { HTMLAttributes } from 'react'

export function Spinner({
  size = 18,
  label = 'Loading',
  ...rest
}: { size?: number; label?: string } & Omit<HTMLAttributes<HTMLSpanElement>, 'role' | 'aria-label'>) {
  return (
    <span
      role="status"
      aria-label={label}
      {...rest}
      className={['inline-flex items-center justify-center', rest.className ?? ''].filter(Boolean).join(' ')}
      style={{ width: size, height: size, ...(rest.style ?? {}) }}
    >
      <span
        aria-hidden="true"
        className="bb-spinner"
        style={{ width: size, height: size }}
      />
    </span>
  )
}

