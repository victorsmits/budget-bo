import Link from "next/link"

import { Badge } from "@/components/ui/badge"
import { getCategoryBadgeClass, getCategoryLabel } from "@/lib/transaction-presentation"

interface CategoryBadgeProps {
  category?: string | null
  className?: string
  linkTo?: string
}

export function CategoryBadge({ category, className, linkTo }: CategoryBadgeProps) {
  const normalizedCategory = (category || "other").toLowerCase()

  const badge = (
    <Badge
      variant="outline"
      className={[
        "border",
        getCategoryBadgeClass(normalizedCategory),
        linkTo ? "cursor-pointer hover:opacity-80" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {getCategoryLabel(normalizedCategory)}
    </Badge>
  )

  if (!linkTo) return badge

  return <Link href={linkTo}>{badge}</Link>
}
