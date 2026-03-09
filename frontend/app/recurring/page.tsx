"use client"

import { Radar, Sparkles } from "lucide-react"

import DashboardLayout from "../dashboard-layout"
import { KpiCard } from "@/components/kpi-card"
import { PageHeader } from "@/components/page-header"
import { CategoryBadge } from "@/components/transactions/category-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useDetectRecurring, useRecurringExpenses, useUpcomingRecurring } from "@/hooks/api/useRecurring"

export default function RecurringPage() {
  const recurring = useRecurringExpenses()
  const upcoming = useUpcomingRecurring(30)
  const detect = useDetectRecurring()

  return (
    <DashboardLayout>
      <div className="space-y-4">
        <PageHeader
          title="Dépenses récurrentes"
          subtitle="Prévisions automatiques basées sur vos historiques bancaires."
          action={() => detect.mutate(6)}
          actionLabel={detect.isPending ? "Détection en cours..." : "Détection IA"}
          actionLoading={detect.isPending}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <KpiCard title="Patterns" value={String(recurring.data?.length || 0)} icon={<Radar className="size-4" />} />
          <KpiCard title="À venir sur 30 jours" value={String(upcoming.data?.length || 0)} icon={<Sparkles className="size-4" />} />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Patterns détectés</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {(recurring.data || []).map((r: any) => (
                <div key={r.id} className="rounded-xl border p-3">
                  <p className="font-medium">{r.pattern_name}</p>
                  <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                    <span>{Number(r.average_amount || 0).toFixed(2)} €</span>
                    {r.category && <CategoryBadge category={r.category} />}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Prochaines échéances</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {(upcoming.data || []).map((u: any) => (
                <div key={u.id} className="rounded-xl border p-3">
                  <p className="font-medium">{u.pattern_name}</p>
                  <p className="text-xs text-muted-foreground">{u.next_expected_date || "Date inconnue"}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}
