"use client"

import { ArrowDown, ArrowUp, Landmark, Repeat2 } from "lucide-react"

import DashboardLayout from "./dashboard-layout"
import { ErrorCard } from "@/components/error"
import { PageHeader } from "@/components/page-header"
import { KpiCard } from "@/components/kpi-card"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useDashboardData } from "@/hooks/api"
import { useBankAccountsSummary } from "@/hooks/api/useAccounts"
import { getTransactionDisplayLabel } from "@/lib/transaction-presentation"

const money = (n: number) => n.toLocaleString("fr-FR", { style: "currency", currency: "EUR" })

export default function DashboardPage() {
  const { summary, recentTransactions, upcomingRecurring, credentials, syncCredential, error } = useDashboardData()
  const accounts = useBankAccountsSummary()

  if (error) {
    return (
      <DashboardLayout>
        <ErrorCard title="Erreur" description={error.message} retry={() => window.location.reload()} />
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <PageHeader
          title="Vue d'ensemble"
          subtitle="Une nouvelle expérience claire et actionnable, alimentée uniquement par l'API existante."
          action={() => credentials?.[0] && syncCredential.mutate(credentials[0].id)}
          actionLabel={syncCredential.isPending ? "Synchronisation..." : "Synchroniser ma banque"}
          actionLoading={syncCredential.isPending || !credentials?.length}
        />

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard title="Solde réel" value={money(accounts.data?.total_balance ?? summary?.net ?? 0)} icon={<Landmark className="size-4" />} />
          <KpiCard title="Dépenses" value={money(summary?.total_expenses ?? 0)} icon={<ArrowDown className="size-4 text-rose-600" />} />
          <KpiCard title="Revenus" value={money(summary?.total_income ?? 0)} icon={<ArrowUp className="size-4 text-emerald-600" />} />
          <KpiCard title="Récurrences" value={String(upcomingRecurring?.length ?? 0)} icon={<Repeat2 className="size-4" />} />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Dernières transactions</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {recentTransactions?.map((t) => (
                <div key={t.id} className="rounded-lg border p-3">
                  <p className="font-medium">{getTransactionDisplayLabel(t)}</p>
                  <p className="text-xs text-muted-foreground">{t.date} • {t.is_expense ? "Dépense" : "Revenu"}</p>
                </div>
              ))}
              {!recentTransactions?.length && <p className="text-sm text-muted-foreground">Aucune transaction récente.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Échéances à venir</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {upcomingRecurring?.map((item) => (
                <div key={item.id} className="rounded-lg border p-3">
                  <p className="font-medium">{item.pattern_name}</p>
                  <p className="text-xs text-muted-foreground">{money(item.average_amount)} • {item.next_expected_date || "Date inconnue"}</p>
                </div>
              ))}
              {!upcomingRecurring?.length && <p className="text-sm text-muted-foreground">Aucune échéance détectée.</p>}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}
