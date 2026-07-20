import type { HTMLAttributes } from 'react'

export function Skeleton({
  className,
  ...rest
}: { className?: string } & HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...rest}
      className={['bb-skeleton', className ?? ''].filter(Boolean).join(' ')}
    />
  )
}

