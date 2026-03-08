import { Badge } from "@/components/ui/badge"
import { getCategoryBadgeClass, getCategoryLabel } from "@/lib/transaction-presentation"

interface CategoryBadgeProps {
  category?: string | null
  className?: string
}

export function CategoryBadge({ category, className }: CategoryBadgeProps) {
  const normalizedCategory = category || "other"

  return (
    <Badge variant="secondary" className={[getCategoryBadgeClass(normalizedCategory), className].filter(Boolean).join(" ")}>
      {getCategoryLabel(normalizedCategory)}
    </Badge>
  )
}
