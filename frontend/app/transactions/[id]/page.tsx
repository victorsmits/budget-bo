"use client"

import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Brain, Calendar, Tag, CreditCard, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import DashboardLayout from "@/app/dashboard-layout"
import { useTransaction, useEnrichTransaction } from "@/hooks/api/useTransactions"
import { formatCurrency, formatDate } from "@/lib/utils"
import { QueryErrorBoundary } from "@/components/ui/query-error-boundary"
import { toast } from "sonner"

export default function TransactionDetailPage() {
  const params = useParams()
  const router = useRouter()
  const transactionId = params.id as string

  const { data: transaction, isLoading, error } = useTransaction(transactionId)
  const enrichMutation = useEnrichTransaction()

  const handleEnrich = async () => {
    if (!transaction) return
    
    try {
      await enrichMutation.mutateAsync(transaction.id)
      toast.success("Transaction enrichie avec succès")
    } catch (error) {
      // L'erreur est déjà gérée dans le hook
    }
  }

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
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
              <p className="text-muted-foreground">
                {error?.message || "Transaction non trouvée"}
              </p>
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
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" onClick={() => router.back()}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Retour
              </Button>
              <h1 className="text-2xl font-bold">Détail de la transaction</h1>
            </div>
            <Button 
              onClick={handleEnrich}
              disabled={enrichMutation.isPending}
              className="gap-2"
            >
              <Brain className="h-4 w-4" />
              {enrichMutation.isPending ? "Enrichissement..." : "Enrichir"}
            </Button>
          </div>

          {/* Transaction Details */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Main Info */}
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
                  <p className="text-base">{transaction.cleaned_label || transaction.raw_label}</p>
                  {transaction.cleaned_label && transaction.cleaned_label !== transaction.raw_label && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Original: {transaction.raw_label}
                    </p>
                  )}
                </div>
                
                <Separator />
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Montant</p>
                    <p className={`text-lg font-bold ${
                      transaction.is_expense ? "text-red-600" : "text-green-600"
                    }`}>
                      {transaction.is_expense ? "-" : "+"}{formatCurrency(transaction.amount)}
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
                    <p className="flex items-center gap-1">
                      <Tag className="h-4 w-4" />
                      {transaction.category || "Non catégorisé"}
                    </p>
                  </div>
                </div>

                {transaction.is_recurring && (
                  <>
                    <Separator />
                    <div>
                      <Badge variant="secondary">Transaction récurrente</Badge>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Additional Info */}
            <Card>
              <CardHeader>
                <CardTitle>Informations supplémentaires</CardTitle>
                <CardDescription>
                  ID: {transaction.id}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Statut</p>
                  <div className="mt-1">
                    {transaction.cleaned_label ? (
                      <Badge variant="default">Enrichie</Badge>
                    ) : (
                      <Badge variant="outline">Non enrichie</Badge>
                    )}
                  </div>
                </div>

                {transaction.is_recurring && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Fréquence</p>
                    <p className="text-sm">Récurrente</p>
                  </div>
                )}

                <div>
                  <p className="text-sm font-medium text-muted-foreground">Actions</p>
                  <div className="mt-2 space-y-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="w-full"
                      onClick={handleEnrich}
                      disabled={enrichMutation.isPending}
                    >
                      <Brain className="mr-2 h-4 w-4" />
                      {enrichMutation.isPending ? "Enrichissement..." : "Enrichir avec l'IA"}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </DashboardLayout>
    </QueryErrorBoundary>
  )
}
