import { Button } from "@/components/ui/button"

export function PageHeader({
  title,
  subtitle,
  action,
  actionLabel,
  actionLoading,
}: {
  title: string
  subtitle: string
  action?: () => void
  actionLabel?: string
  actionLoading?: boolean
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{title}</h1>
        <p className="text-sm text-muted-foreground">{subtitle}</p>
      </div>
      {action && actionLabel && (
        <Button onClick={action} disabled={actionLoading}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
