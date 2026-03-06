import { Transaction } from "@/types/api"
import { Card, CardContent } from "@/components/ui/card"
import { ArrowUpRight, ArrowDownRight } from "lucide-react"
import { cn, formatCurrency } from "@/lib/utils"
import Link from "next/link"

interface TransactionCardProps {
  transaction: Transaction
  showLink?: boolean
}

export function TransactionCard({ transaction, showLink = true }: TransactionCardProps) {
  const content = (
    <Card className={cn("transition-colors", showLink && "hover:bg-muted/50 cursor-pointer")}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn(
              "h-9 w-9 rounded-full flex items-center justify-center",
              transaction.is_expense ? "bg-red-100 text-red-600" : "bg-green-100 text-green-600"
            )}>
              {transaction.is_expense ? <ArrowDownRight className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">{transaction.cleaned_label || transaction.raw_label}</p>
              <p className="text-xs text-muted-foreground">{transaction.date} • {transaction.category}</p>
            </div>
          </div>
          <div className={cn("font-medium", transaction.is_expense ? "text-red-600" : "text-green-600")}>
            {transaction.is_expense ? "-" : "+"}{formatCurrency(transaction.amount)}
          </div>
        </div>
      </CardContent>
    </Card>
  )

  if (showLink) {
    return (
      <Link href={`/transactions/${transaction.id}`}>
        {content}
      </Link>
    )
  }

  return content
}
