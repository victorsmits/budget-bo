import Link from "next/link"
import { ArrowDownRight, ArrowUpRight } from "lucide-react"

import { CategoryBadge } from "@/components/transactions/category-badge"
import { Card, CardContent } from "@/components/ui/card"
import { getTransactionDisplayLabel } from "@/lib/transaction-presentation"
import { cn, formatCurrency } from "@/lib/utils"
import { Transaction } from "@/types/api"

interface TransactionCardProps {
  transaction: Transaction
  showLink?: boolean
}

export function TransactionCard({ transaction, showLink = true }: TransactionCardProps) {
  const content = (
    <Card className={cn("transition-colors", showLink && "cursor-pointer hover:bg-muted/50")}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-full",
                transaction.is_expense ? "bg-red-100 text-red-600" : "bg-green-100 text-green-600",
              )}
            >
              {transaction.is_expense ? (
                <ArrowDownRight className="h-4 w-4" />
              ) : (
                <ArrowUpRight className="h-4 w-4" />
              )}
            </div>
            <div>
              <p className="text-sm font-medium">{getTransactionDisplayLabel(transaction)}</p>
              <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                <span>{transaction.date}</span>
                <CategoryBadge category={transaction.category} />
              </div>
            </div>
          </div>
          <div className={cn("font-medium", transaction.is_expense ? "text-red-600" : "text-green-600")}>
            {transaction.is_expense ? "-" : "+"}
            {formatCurrency(transaction.amount)}
          </div>
        </div>
      </CardContent>
    </Card>
  )

  if (!showLink) return content

  return <Link href={`/transactions/${transaction.id}`}>{content}</Link>
}
