"use client"

import Link from "next/link"
import { ArrowDown, ArrowUp, Landmark, Repeat2 } from "lucide-react"

import DashboardLayout from "./dashboard-layout"
import { ErrorCard } from "@/components/error"
import { CategoryBadge } from "@/components/transactions/category-badge"
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
      <div className="space-y-6 pb-6">
        <PageHeader
          title="Vue d'ensemble"
          subtitle="Synthèse de vos finances depuis l'API existante."
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

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Dernières transactions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {recentTransactions?.map((t) => (
                <Link key={t.id} href={`/transactions/${t.id}`} className="block rounded-lg border p-3 hover:bg-muted/40">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium">{getTransactionDisplayLabel(t)}</p>
                      <p className="text-xs text-muted-foreground">{t.date} • {t.is_expense ? "Dépense" : "Revenu"}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <CategoryBadge category={t.category} linkTo={`/transactions?category=${encodeURIComponent(t.category || "")}`} />
                      <p className={t.is_expense ? "font-semibold text-rose-600" : "font-semibold text-emerald-600"}>
                        {t.is_expense ? "-" : "+"}{money(t.amount)}
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
              {!recentTransactions?.length && <p className="text-sm text-muted-foreground">Aucune transaction récente.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Dépenses par catégorie</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {summary?.by_category?.slice(0, 8).map((c: { category: string; total: number; count: number }) => (
                <div key={c.category} className="flex items-center justify-between gap-2 rounded-lg border p-2">
                  <CategoryBadge category={c.category} linkTo={`/transactions?category=${encodeURIComponent(c.category)}`} />
                  <div className="text-right">
                    <p className="text-sm font-medium">{money(c.total)}</p>
                    <p className="text-xs text-muted-foreground">{c.count} opérations</p>
                  </div>
                </div>
              ))}
              {!summary?.by_category?.length && <p className="text-sm text-muted-foreground">Aucune donnée de catégorie.</p>}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}
