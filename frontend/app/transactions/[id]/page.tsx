"use client"

import { useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Brain, Calendar, CreditCard, Loader2, Save } from "lucide-react"

import DashboardLayout from "@/app/dashboard-layout"
import { Badge } from "@/components/ui/badge"
import { CategoryBadge } from "@/components/transactions/category-badge"
import { CategorySelect } from "@/components/transactions/category-select"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { QueryErrorBoundary } from "@/components/ui/query-error-boundary"
import { Separator } from "@/components/ui/separator"
import {
  useCorrectTransaction,
  useEnrichTransaction,
  useTransaction,
} from "@/hooks/api/useTransactions"
import {
  getTransactionDisplayLabel,
} from "@/lib/transaction-presentation"
import { formatCurrency, formatDate } from "@/lib/utils"

export default function TransactionDetailPage() {
  const params = useParams()
  const router = useRouter()
  const transactionId = params.id as string

  const { data: transaction, isLoading, error } = useTransaction(transactionId)
  const enrichMutation = useEnrichTransaction()
  const correctMutation = useCorrectTransaction()

  const [cleanedLabel, setCleanedLabel] = useState("")
  const [merchantName, setMerchantName] = useState("")
  const [selectedCategory, setSelectedCategory] = useState("other")
  const [selectedType, setSelectedType] = useState<"expense" | "income">("expense")

  useEffect(() => {
    if (!transaction) return

    setCleanedLabel(transaction.cleaned_label || transaction.merchant_name || "")
    setMerchantName(transaction.merchant_name || "")
    setSelectedCategory(transaction.category || "other")
    setSelectedType(transaction.is_expense ? "expense" : "income")
  }, [transaction])

  const displayLabel = useMemo(() => {
    return transaction ? getTransactionDisplayLabel(transaction) : ""
  }, [transaction])

  const handleEnrich = async () => {
    if (!transaction) return
    await enrichMutation.mutateAsync(transaction.id)
  }

  const handleCorrectionSave = async () => {
    if (!transaction) return

    await correctMutation.mutateAsync({
      transactionId: transaction.id,
      payload: {
        cleaned_label: cleanedLabel.trim() || null,
        merchant_name: merchantName.trim() || null,
        category: selectedCategory,
        is_expense: selectedType === "expense",
      },
    })
  }

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </DashboardLayout>
    )
  }

  if (error || !transaction) {
    return (
      <DashboardLayout>
        <div className="space-y-4">
          <Button variant="ghost" onClick={() => router.back()} className="mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Retour
          </Button>
          <Card>
            <CardContent className="pt-6">
              <p className="text-muted-foreground">{error?.message || "Transaction non trouvée"}</p>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <QueryErrorBoundary>
      <DashboardLayout>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" onClick={() => router.back()}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Retour
              </Button>
              <h1 className="text-2xl font-bold">Détail de la transaction</h1>
            </div>
            <Button onClick={handleEnrich} disabled={enrichMutation.isPending} className="gap-2">
              <Brain className="h-4 w-4" />
              {enrichMutation.isPending ? "Enrichissement..." : "Enrichir"}
            </Button>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5" />
                  Informations
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Libellé</p>
                  <p className="text-base">{displayLabel}</p>
                  {displayLabel !== transaction.raw_label && (
                    <p className="mt-1 text-sm text-muted-foreground">Original: {transaction.raw_label}</p>
                  )}
                </div>

                <Separator />

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Montant</p>
                    <p className={`text-lg font-bold ${transaction.is_expense ? "text-red-600" : "text-green-600"}`}>
                      {transaction.is_expense ? "-" : "+"}
                      {formatCurrency(transaction.amount)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Type</p>
                    <Badge variant={transaction.is_expense ? "destructive" : "default"}>
                      {transaction.is_expense ? "Dépense" : "Revenu"}
                    </Badge>
                  </div>
                </div>

                <Separator />

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Date</p>
                    <p className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      {formatDate(transaction.date)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Catégorie</p>
                    <CategoryBadge category={transaction.category || "other"} className="mt-1" linkTo={`/transactions?category=${encodeURIComponent(transaction.category || "")}`} />
                  </div>
                </div>

                {transaction.is_recurring && (
                  <>
                    <Separator />
                    <Badge variant="secondary">Transaction récurrente</Badge>
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Correction & apprentissage</CardTitle>
                <CardDescription>
                  Corrigez les champs puis enregistrez pour entraîner les futurs enrichissements.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="cleanedLabel">Libellé corrigé</Label>
                  <Input
                    id="cleanedLabel"
                    value={cleanedLabel}
                    onChange={(event) => setCleanedLabel(event.target.value)}
                    placeholder="Ex: Netflix"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="merchantName">Marchand</Label>
                  <Input
                    id="merchantName"
                    value={merchantName}
                    onChange={(event) => setMerchantName(event.target.value)}
                    placeholder="Ex: Netflix"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="category">Catégorie</Label>
                  <CategorySelect
                    id="category"
                    value={selectedCategory}
                    onChange={setSelectedCategory}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="transactionType">Type</Label>
                  <select
                    id="transactionType"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={selectedType}
                    onChange={(event) =>
                      setSelectedType(event.target.value === "income" ? "income" : "expense")
                    }
                  >
                    <option value="expense">Dépense</option>
                    <option value="income">Revenu</option>
                  </select>
                </div>

                <Button className="w-full" onClick={handleCorrectionSave} disabled={correctMutation.isPending}>
                  <Save className="mr-2 h-4 w-4" />
                  {correctMutation.isPending ? "Enregistrement..." : "Enregistrer la correction"}
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </DashboardLayout>
    </QueryErrorBoundary>
  )
}
