"use client"

import { useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Brain, Calendar, CreditCard, Loader2, Save, Tag } from "lucide-react"

import DashboardLayout from "@/app/dashboard-layout"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { QueryErrorBoundary } from "@/components/ui/query-error-boundary"
import { Separator } from "@/components/ui/separator"
import { useCorrectTransaction, useEnrichTransaction, useTransaction } from "@/hooks/api/useTransactions"
import { getCategoryLabel, getTransactionDisplayLabel, TRANSACTION_CATEGORY_OPTIONS } from "@/lib/transaction-presentation"
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

  const displayLabel = useMemo(() => (transaction ? getTransactionDisplayLabel(transaction) : ""), [transaction])

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
        <div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>
      </DashboardLayout>
    )
  }

  if (error || !transaction) {
    return (
      <DashboardLayout>
        <Card><CardContent className="p-6"><p>{error?.message || "Transaction non trouvée"}</p></CardContent></Card>
      </DashboardLayout>
    )
  }

  return (
    <QueryErrorBoundary>
      <DashboardLayout>
        <div className="space-y-6">
          <section className="glass-card rounded-3xl p-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-3">
                <Button variant="outline" onClick={() => router.back()}><ArrowLeft className="mr-2 h-4 w-4" />Retour</Button>
                <div>
                  <p className="text-sm text-muted-foreground">Fiche opération</p>
                  <h1 className="text-2xl font-semibold">{displayLabel}</h1>
                </div>
              </div>
              <Button onClick={handleEnrich} disabled={enrichMutation.isPending}><Brain className="mr-2 h-4 w-4" />{enrichMutation.isPending ? "Enrichissement..." : "Relancer l'IA"}</Button>
            </div>
          </section>

          <div className="grid gap-4 xl:grid-cols-5">
            <Card className="xl:col-span-2 rounded-3xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><CreditCard className="h-4 w-4" />Données de transaction</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Montant</p>
                  <p className={`text-2xl font-semibold ${transaction.is_expense ? "text-red-600" : "text-green-600"}`}>{transaction.is_expense ? "-" : "+"}{formatCurrency(transaction.amount)}</p>
                </div>
                <Separator />
                <p className="flex items-center gap-2 text-sm"><Calendar className="h-4 w-4" />{formatDate(transaction.date)}</p>
                <p className="flex items-center gap-2 text-sm"><Tag className="h-4 w-4" />{getCategoryLabel(transaction.category || "other")}</p>
                <Badge variant={transaction.is_expense ? "destructive" : "default"}>{transaction.is_expense ? "Dépense" : "Revenu"}</Badge>
                {displayLabel !== transaction.raw_label && <p className="text-xs text-muted-foreground">Libellé brut: {transaction.raw_label}</p>}
              </CardContent>
            </Card>

            <Card className="xl:col-span-3 rounded-3xl">
              <CardHeader>
                <CardTitle>Correction & apprentissage</CardTitle>
                <CardDescription>Modifiez les champs pour améliorer les futurs enrichissements.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="cleanedLabel">Libellé corrigé</Label>
                  <Input id="cleanedLabel" value={cleanedLabel} onChange={(event) => setCleanedLabel(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="merchantName">Marchand</Label>
                  <Input id="merchantName" value={merchantName} onChange={(event) => setMerchantName(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="category">Catégorie</Label>
                  <select id="category" className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm" value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value)}>
                    {TRANSACTION_CATEGORY_OPTIONS.map((category) => <option key={category} value={category}>{getCategoryLabel(category)}</option>)}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="transactionType">Type</Label>
                  <select id="transactionType" className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm" value={selectedType} onChange={(event) => setSelectedType(event.target.value === "income" ? "income" : "expense")}>
                    <option value="expense">Dépense</option>
                    <option value="income">Revenu</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <Button className="w-full" onClick={handleCorrectionSave} disabled={correctMutation.isPending}><Save className="mr-2 h-4 w-4" />{correctMutation.isPending ? "Enregistrement..." : "Enregistrer la correction"}</Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </DashboardLayout>
    </QueryErrorBoundary>
  )
}
