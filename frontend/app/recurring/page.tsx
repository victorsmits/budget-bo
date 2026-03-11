"use client"

import { useMemo, useState } from "react"
import { CalendarIcon, Loader2, Radar, Sparkles, Trash2, XCircle } from "lucide-react"

import DashboardLayout from "../dashboard-layout"
import { KpiCard } from "@/components/kpi-card"
import { PageHeader } from "@/components/page-header"
import { CategoryBadge } from "@/components/transactions/category-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import {
  useCancelRecurring,
  useDeleteRecurring,
  useDetectRecurring,
  useRecurringDetail,
  useRecurringExpenses,
  useRenameRecurring,
  useUpcomingRecurring,
} from "@/hooks/api/useRecurring"
import { formatCurrency, formatDate } from "@/lib/utils"

export default function RecurringPage() {
  const recurring = useRecurringExpenses()
  const upcoming = useUpcomingRecurring(30)
  const detect = useDetectRecurring()
  const cancelRecurring = useCancelRecurring()
  const deleteRecurring = useDeleteRecurring()
  const renameRecurring = useRenameRecurring()

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState("")

  const detail = useRecurringDetail(selectedId || undefined)

  const selectedExpense = detail.data

  useMemo(() => {
    if (selectedExpense) {
      setRenameValue(selectedExpense.pattern_name)
    }
  }, [selectedExpense])

  const handleCancel = (id: string) => {
    if (!id || cancelRecurring.isPending) return
    if (window.confirm("Annuler cette récurrence ?")) {
      cancelRecurring.mutate(id)
    }
  }

  const handleDelete = (id: string) => {
    if (!id || deleteRecurring.isPending) return
    if (window.confirm("Supprimer définitivement cette récurrence ?")) {
      deleteRecurring.mutate(id)
      if (selectedId === id) setSelectedId(null)
    }
  }

  const handleRename = () => {
    if (!selectedId || !renameValue.trim()) return
    renameRecurring.mutate({ expenseId: selectedId, newName: renameValue.trim() })
  }

  return (
    <DashboardLayout>
      <div className="space-y-5">
        <PageHeader
          title="Dépenses récurrentes"
          subtitle="Analyse statistique des 6 derniers mois avec prévisions automatiques."
          action={() => detect.mutate(6)}
          actionLabel={detect.isPending ? "Analyse en cours..." : "Analyser les 6 derniers mois"}
          actionLoading={detect.isPending}
        />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard title="Patterns" value={String(recurring.data?.length || 0)} icon={<Radar className="size-4" />} />
          <KpiCard
            title="À venir (30j)"
            value={String(upcoming.data?.length || 0)}
            icon={<Sparkles className="size-4" />}
            hint="Paiements attendus"
          />
          <KpiCard
            title="Montant moyen"
            value={formatCurrency(
              (recurring.data || []).reduce((sum, r) => sum + Number(r.average_amount || 0), 0),
            )}
            hint="Somme des abonnements"
          />
          <KpiCard
            title="Confiance moyenne"
            value={`${Math.round(
              (recurring.data || []).reduce((sum, r) => sum + Number(r.confidence_score || 0), 0) /
                Math.max(recurring.data?.length || 1, 1) /
                0.01,
            )}%`}
            hint="Basée sur le pattern détecté"
          />
        </div>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle>Abonnements détectés</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Cliquer sur une ligne pour afficher le calendrier et les transactions sources.
                </p>
              </div>
              <Button variant="outline" onClick={() => recurring.refetch()} disabled={recurring.isFetching}>
                Rafraîchir
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-muted-foreground">
                    <th className="pb-2">Nom</th>
                    <th className="pb-2">Montant moyen</th>
                    <th className="pb-2">Fréquence</th>
                    <th className="pb-2">Prochaine échéance</th>
                    <th className="pb-2">Confiance</th>
                    <th className="pb-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(recurring.data || []).map((expense) => (
                    <tr key={expense.id} className="border-t last:border-b hover:bg-muted/40">
                      <td className="py-3">
                        <div className="flex flex-col">
                          <button
                            className="text-left font-medium hover:underline"
                            onClick={() => setSelectedId(expense.id)}
                          >
                            {expense.pattern_name}
                          </button>
                          <span className="text-xs text-muted-foreground">
                            {expense.is_active ? "Actif" : "Inactif"} · {expense.matched_transaction_count} occurrences
                          </span>
                        </div>
                      </td>
                      <td className="py-3 font-semibold">{formatCurrency(Number(expense.average_amount || 0))}</td>
                      <td className="py-3 capitalize">{expense.pattern || "?"}</td>
                      <td className="py-3 text-sm text-muted-foreground">
                        {expense.next_expected_date ? formatDate(expense.next_expected_date) : "—"}
                      </td>
                      <td className="py-3">
                        <div className="text-xs font-semibold">
                          {Math.round(Number(expense.confidence_score || 0) * 100)}%
                        </div>
                      </td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button variant="secondary" size="sm" onClick={() => setSelectedId(expense.id)}>
                            Détails
                          </Button>
                          {expense.is_active ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleCancel(expense.id)}
                              disabled={cancelRecurring.isPending}
                            >
                              <XCircle className="mr-1 size-4" />
                              Annuler
                            </Button>
                          ) : (
                            <span className="text-xs text-muted-foreground">Annulé</span>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive"
                            onClick={() => handleDelete(expense.id)}
                            disabled={deleteRecurring.isPending}
                          >
                            <Trash2 className="mr-1 size-4" />
                            Supprimer
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!recurring.data?.length && !recurring.isLoading && (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-sm text-muted-foreground">
                        Aucun abonnement détecté. Lancez une analyse pour commencer.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {recurring.isLoading && (
              <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
                <Loader2 className="mr-2 size-4 animate-spin" /> Chargement des récurrences...
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Prochaines échéances (30 jours)</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {(upcoming.data || []).map((item) => (
              <div key={item.id} className="rounded-xl border p-3">
                <p className="font-medium">{item.pattern_name}</p>
                <p className="text-xs text-muted-foreground">
                  {item.next_expected_date ? formatDate(item.next_expected_date) : "Date inconnue"}
                </p>
                <p className="text-sm font-semibold">{formatCurrency(Number(item.average_amount || 0))}</p>
              </div>
            ))}
            {!upcoming.data?.length && (
              <p className="text-sm text-muted-foreground">Aucun paiement attendu sur les 30 prochains jours.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Sheet open={Boolean(selectedId)} onOpenChange={(open) => !open && setSelectedId(null)}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
          {detail.isLoading && (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="size-6 animate-spin" />
            </div>
          )}

          {!detail.isLoading && selectedExpense && (
            <div className="space-y-5">
              <div>
                <h2 className="text-2xl font-semibold">{selectedExpense.pattern_name}</h2>
                <p className="text-sm text-muted-foreground">
                  {selectedExpense.pattern?.toUpperCase()} • {selectedExpense.matched_transaction_count} occurrences •{" "}
                  {selectedExpense.is_active ? "Actif" : "Annulé"}
                </p>
              </div>

              <div className="grid gap-3 rounded-xl border p-4 text-sm">
                <p>
                  <span className="text-muted-foreground">Montant moyen :</span> {" "}
                  <span className="font-semibold">{formatCurrency(Number(selectedExpense.average_amount || 0))}</span>
                </p>
                <p>
                  <span className="text-muted-foreground">Variation :</span> {" "}
                  ±{Math.round(Number(selectedExpense.amount_variation_pct || 0) * 100)}%
                </p>
                <p>
                  <span className="text-muted-foreground">Prochaine échéance :</span> {" "}
                  {selectedExpense.next_expected_date ? formatDate(selectedExpense.next_expected_date) : "—"}
                </p>
                <p>
                  <span className="text-muted-foreground">Confiance :</span> {" "}
                  {Math.round(Number(selectedExpense.confidence_score || 0) * 100)}%
                </p>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium">Renommer cet abonnement</p>
                <div className="flex gap-2">
                  <Input value={renameValue} onChange={(e) => setRenameValue(e.target.value)} placeholder="Nom personnalisé" />
                  <Button onClick={handleRename} disabled={!renameValue.trim() || renameRecurring.isPending}>
                    Enregistrer
                  </Button>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <CalendarIcon className="size-4" />
                  <p className="font-medium">Calendrier des prochaines échéances</p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {selectedExpense.payment_schedule.slice(0, 12).map((date) => (
                    <div key={date} className="rounded-lg border px-3 py-2">
                      <p className="font-semibold">{formatDate(date)}</p>
                      <p className="text-xs text-muted-foreground">Prévision</p>
                    </div>
                  ))}
                  {!selectedExpense.payment_schedule.length && (
                    <p className="text-sm text-muted-foreground">Aucune échéance future.</p>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <p className="font-medium">Transactions associées</p>
                  <p className="text-xs text-muted-foreground">
                    Historique utilisé pour détecter ce pattern.
                  </p>
                </div>
                <div className="space-y-2">
                  {selectedExpense.transactions.map((tx) => (
                    <div key={tx.transaction_id} className="rounded-xl border p-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{tx.cleaned_label || tx.merchant_name || "Transaction"}</p>
                          <p className="text-xs text-muted-foreground">{formatDate(tx.date)}</p>
                        </div>
                        <p className="font-semibold">{formatCurrency(Number(tx.amount || 0))}</p>
                      </div>
                      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                        <CategoryBadge category={tx.category} />
                        <Separator orientation="vertical" className="h-4" />
                        <span>ID: {tx.transaction_id}</span>
                      </div>
                    </div>
                  ))}
                  {!selectedExpense.transactions.length && (
                    <p className="text-sm text-muted-foreground">
                      Aucune transaction attachée pour cette récurrence.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {!detail.isLoading && !selectedExpense && (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Récurrence introuvable ou supprimée.
            </div>
          )}
        </SheetContent>
      </Sheet>
    </DashboardLayout>
  )
}
