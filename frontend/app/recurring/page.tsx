"use client"

import { Radar, Sparkles, Trash2 } from "lucide-react"

import DashboardLayout from "../dashboard-layout"
import { KpiCard } from "@/components/kpi-card"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useDeleteRecurring, useDetectRecurring, useRecurringExpenses, useRecurringSummary, useUpcomingRecurring } from "@/hooks/api/useRecurring"
import { formatCurrency, formatDate } from "@/lib/utils"

export default function RecurringPage() {
  const recurring = useRecurringExpenses()
  const recurringSummary = useRecurringSummary()
  const upcoming = useUpcomingRecurring()
  const detect = useDetectRecurring()
  const deleteRecurring = useDeleteRecurring()

  const handleDelete = (id: string) => {
    if (!id || deleteRecurring.isPending) return
    if (window.confirm("Supprimer cette récurrence ?")) {
      deleteRecurring.mutate(id)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-5">
        <PageHeader
          title="Dépenses récurrentes"
          subtitle="Analyse statistique des 6 derniers mois avec prévisions automatiques."
          action={() => detect.mutate()}
          actionLabel={detect.isPending ? "Analyse en cours..." : "Analyser les 6 derniers mois"}
          actionLoading={detect.isPending}
        />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard title="Patterns" value={String(recurringSummary.data?.active_count || 0)} icon={<Radar className="size-4" />} />
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
            title="Mensuel estimé"
            value={formatCurrency(Number(recurringSummary.data?.estimated_monthly_total || 0))}
            hint="Selon les patterns actifs"
          />
        </div>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle>Abonnements détectés</CardTitle>
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
                          <span className="text-left font-medium">{expense.pattern_name}</span>
                          <span className="text-xs text-muted-foreground">
                            {expense.is_active ? "Actif" : "Inactif"} · {expense.matched_transaction_count} occurrences
                          </span>
                        </div>
                      </td>
                      <td className="py-3 font-semibold">{formatCurrency(Number(expense.average_amount || 0))}</td>
                      <td className="py-3">{expense.pattern || "unknown"}</td>
                      <td className="py-3">{expense.next_expected_date ? formatDate(expense.next_expected_date) : "—"}</td>
                      <td className="py-3">{Math.round(Number(expense.confidence_score || 0) * 100)}%</td>
                      <td className="py-3">
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(expense.id)} disabled={deleteRecurring.isPending}>
                          <Trash2 className="size-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {!recurring.data?.length && (
                    <tr>
                      <td colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                        Aucune dépense récurrente détectée.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
