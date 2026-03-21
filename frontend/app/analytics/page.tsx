"use client"

import { useMemo, useState } from "react"
import DashboardLayout from "../dashboard-layout"
import { PageHeader } from "@/components/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { money } from "@/lib/money"
import { CategorySelect } from "@/components/transactions/category-select"
import { api } from "@/lib/api"
import { useQuery } from "@tanstack/react-query"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts"

type Granularity = "day" | "month" | "year"

type TimeseriesResponse = {
  granularity: Granularity
  items: { date: string; expenses: number; income: number; net: number; count: number }[]
  totals: { total_expenses: number; total_income: number; net: number; count: number }
}

type GroupedResponse = {
  group_by: "category" | "merchant"
  items: { group: string; total: number; expenses: number; income: number; count: number }[]
}

type TopResponse = {
  kind: "expenses" | "income" | "all"
  limit: number
  items: any[]
}

type AnomaliesResponse = {
  scope: "global" | "category" | "merchant"
  threshold: number
  items: any[]
}

type AnalyticsQueryGroupBy = "none" | "day" | "month" | "year" | "category" | "merchant" | "label"

type AnalyticsQueryResponse =
  | {
      group_by: "none"
      result: { total: number; count: number; avg: number; min: number; max: number }
    }
  | {
      group_by: Exclude<AnalyticsQueryGroupBy, "none">
      items: { group: string; total: number; count: number; avg: number; min: number; max: number }[]
    }

function isoDate(d: Date) {
  return d.toISOString().slice(0, 10)
}

const COLORS = ["#0ea5e9", "#22c55e", "#f97316", "#a855f7", "#ef4444", "#14b8a6", "#eab308", "#64748b"]

export default function AnalyticsPage() {
  const today = useMemo(() => new Date(), [])
  const [granularity, setGranularity] = useState<Granularity>("month")
  const [dateFrom, setDateFrom] = useState<string>(isoDate(new Date(today.getFullYear(), today.getMonth(), 1)))
  const [dateTo, setDateTo] = useState<string>(isoDate(today))
  const [category, setCategory] = useState<string>("")

  const [customLabel, setCustomLabel] = useState<string>("")
  const [customLabelMatch, setCustomLabelMatch] = useState<"exact" | "contains" | "icontains">("icontains")
  const [customMerchant, setCustomMerchant] = useState<string>("")
  const [customMerchantMatch, setCustomMerchantMatch] = useState<"exact" | "contains" | "icontains">("icontains")
  const [customIsExpense, setCustomIsExpense] = useState<"all" | "expenses" | "income">("all")
  const [customGroupBy, setCustomGroupBy] = useState<AnalyticsQueryGroupBy>("none")
  const [customLimit, setCustomLimit] = useState<number>(50)

  const commonParams = useMemo(() => {
    return {
      granularity,
      date_from: dateFrom,
      date_to: dateTo,
      ...(category ? { category } : {}),
    }
  }, [granularity, dateFrom, dateTo, category])

  const timeseries = useQuery({
    queryKey: ["analytics", "timeseries", commonParams],
    queryFn: async () => {
      const sp = new URLSearchParams()
      sp.set("granularity", commonParams.granularity)
      sp.set("date_from", commonParams.date_from)
      sp.set("date_to", commonParams.date_to)
      if (category) sp.set("category", category)
      return apiClientRaw(`/transactions/analytics/timeseries?${sp.toString()}`)
    },
  })

  const byCategory = useQuery({
    queryKey: ["analytics", "grouped", "category", dateFrom, dateTo, category],
    queryFn: async () => {
      const sp = new URLSearchParams()
      sp.set("group_by", "category")
      sp.set("date_from", dateFrom)
      sp.set("date_to", dateTo)
      if (category) sp.set("category", category)
      return apiClientRaw(`/transactions/analytics/grouped?${sp.toString()}`)
    },
  })

  const topExpenses = useQuery({
    queryKey: ["analytics", "top", dateFrom, dateTo, category],
    queryFn: async () => {
      const sp = new URLSearchParams()
      sp.set("kind", "expenses")
      sp.set("limit", "20")
      sp.set("date_from", dateFrom)
      sp.set("date_to", dateTo)
      if (category) sp.set("category", category)
      return apiClientRaw(`/transactions/analytics/top?${sp.toString()}`)
    },
  })

  const anomalies = useQuery({
    queryKey: ["analytics", "anomalies", dateFrom, dateTo, category],
    queryFn: async () => {
      const sp = new URLSearchParams()
      sp.set("scope", "global")
      sp.set("threshold", "3.5")
      sp.set("limit", "30")
      sp.set("date_from", dateFrom)
      sp.set("date_to", dateTo)
      if (category) sp.set("category", category)
      return apiClientRaw(`/transactions/analytics/anomalies?${sp.toString()}`)
    },
  })

  const ts: TimeseriesResponse | undefined = timeseries.data
  const grouped: GroupedResponse | undefined = byCategory.data
  const tops: TopResponse | undefined = topExpenses.data
  const outliers: AnomaliesResponse | undefined = anomalies.data

  const customQueryParams = useMemo(() => {
    const is_expense =
      customIsExpense === "all" ? undefined : customIsExpense === "expenses" ? true : false
    return {
      date_from: dateFrom,
      date_to: dateTo,
      ...(category ? { category } : {}),
      ...(customLabel ? { label: customLabel, label_match: customLabelMatch } : {}),
      ...(customMerchant ? { merchant: customMerchant, merchant_match: customMerchantMatch } : {}),
      ...(typeof is_expense === "boolean" ? { is_expense } : {}),
      group_by: customGroupBy,
      limit: customLimit,
    }
  }, [dateFrom, dateTo, category, customLabel, customLabelMatch, customMerchant, customMerchantMatch, customIsExpense, customGroupBy, customLimit])

  const customQuery = useQuery({
    queryKey: ["analytics", "custom-query", customQueryParams],
    queryFn: () => api.transactions.analyticsQuery(customQueryParams as any) as Promise<AnalyticsQueryResponse>,
    enabled: false,
  })

  const pieData = useMemo(() => {
    const items = grouped?.items || []
    return items
      .filter((x) => x.expenses > 0)
      .sort((a, b) => b.expenses - a.expenses)
      .slice(0, 8)
      .map((x) => ({ name: x.group || "(sans catégorie)", value: x.expenses }))
  }, [grouped])

  return (
    <DashboardLayout>
      <div className="space-y-4 pb-6">
        <PageHeader title="Analyse" subtitle="Analyse avancée de votre budget (période, comparaisons, anomalies, gros postes)." />

        <Card>
          <CardHeader>
            <CardTitle>Filtres</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Du</label>
              <input className="h-10 w-full rounded-md border bg-background px-3 text-sm" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Au</label>
              <input className="h-10 w-full rounded-md border bg-background px-3 text-sm" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Granularité</label>
              <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={granularity} onChange={(e) => setGranularity(e.target.value as Granularity)}>
                <option value="day">Jour</option>
                <option value="month">Mois</option>
                <option value="year">Année</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Catégorie</label>
              <CategorySelect value={category} onChange={setCategory} includeAllOption />
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4 lg:grid-cols-4">
          <Card>
            <CardHeader><CardTitle>Dépenses</CardTitle></CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold text-rose-600">{money(ts?.totals?.total_expenses || 0)}</p>
              <p className="text-xs text-muted-foreground">Sur la période</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Revenus</CardTitle></CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold text-emerald-600">{money(ts?.totals?.total_income || 0)}</p>
              <p className="text-xs text-muted-foreground">Sur la période</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Net</CardTitle></CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{money(ts?.totals?.net || 0)}</p>
              <p className="text-xs text-muted-foreground">Revenus - Dépenses</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Transactions</CardTitle></CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{String(ts?.totals?.count || 0)}</p>
              <p className="text-xs text-muted-foreground">Nombre d’opérations</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle>Évolution (net / dépenses / revenus)</CardTitle></CardHeader>
            <CardContent className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={ts?.items || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip formatter={(v: any) => money(Number(v || 0))} />
                  <Legend />
                  <Line type="monotone" dataKey="expenses" name="Dépenses" stroke="#e11d48" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="income" name="Revenus" stroke="#10b981" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="net" name="Net" stroke="#0ea5e9" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Dépenses par catégorie (Top)</CardTitle></CardHeader>
            <CardContent className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={110}>
                    {pieData.map((_, idx) => (
                      <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: any) => money(Number(v || 0))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Top dépenses</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {(tops?.items || []).slice(0, 12).map((t: any) => (
                <div key={t.id} className="flex items-center justify-between gap-2 rounded-lg border p-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{t.cleaned_label || t.raw_label}</p>
                    <p className="truncate text-xs text-muted-foreground">{t.date} • {t.category || "other"}</p>
                  </div>
                  <p className="shrink-0 font-semibold text-rose-600">-{money(Number(t.amount || 0))}</p>
                </div>
              ))}
              {!tops?.items?.length && <p className="text-sm text-muted-foreground">Aucune donnée.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Anomalies (dépenses atypiques)</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {(outliers?.items || []).slice(0, 12).map((t: any) => (
                <div key={t.id} className="flex items-center justify-between gap-2 rounded-lg border p-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{t.cleaned_label || t.raw_label}</p>
                    <p className="truncate text-xs text-muted-foreground">{t.date} • score {Number(t.anomaly_score || 0).toFixed(2)}</p>
                  </div>
                  <p className="shrink-0 font-semibold text-rose-600">-{money(Number(t.amount || 0))}</p>
                </div>
              ))}
              {!outliers?.items?.length && <p className="text-sm text-muted-foreground">Aucune anomalie détectée sur la période.</p>}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Analyse personnalisée</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Libellé</label>
                <Input value={customLabel} onChange={(e) => setCustomLabel(e.target.value)} placeholder="Ex: NETFLIX" />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Match libellé</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={customLabelMatch} onChange={(e) => setCustomLabelMatch(e.target.value as any)}>
                  <option value="icontains">Contient (insensible)</option>
                  <option value="contains">Contient</option>
                  <option value="exact">Exact</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Type</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={customIsExpense} onChange={(e) => setCustomIsExpense(e.target.value as any)}>
                  <option value="all">Tout</option>
                  <option value="expenses">Dépenses</option>
                  <option value="income">Revenus</option>
                </select>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Marchand</label>
                <Input value={customMerchant} onChange={(e) => setCustomMerchant(e.target.value)} placeholder="Ex: AMAZON" />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Match marchand</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={customMerchantMatch} onChange={(e) => setCustomMerchantMatch(e.target.value as any)}>
                  <option value="icontains">Contient (insensible)</option>
                  <option value="contains">Contient</option>
                  <option value="exact">Exact</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Grouper par</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={customGroupBy} onChange={(e) => setCustomGroupBy(e.target.value as any)}>
                  <option value="none">Aucun</option>
                  <option value="day">Jour</option>
                  <option value="month">Mois</option>
                  <option value="year">Année</option>
                  <option value="category">Catégorie</option>
                  <option value="merchant">Marchand</option>
                  <option value="label">Libellé</option>
                </select>
              </div>
            </div>

            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="w-40 space-y-1">
                <label className="text-xs text-muted-foreground">Limite groupes</label>
                <Input type="number" value={String(customLimit)} onChange={(e) => setCustomLimit(Number(e.target.value || 0))} />
              </div>
              <Button onClick={() => customQuery.refetch()} disabled={customQuery.isFetching}>
                {customQuery.isFetching ? "Calcul..." : "Exécuter"}
              </Button>
            </div>

            {customQuery.error && (
              <p className="text-sm text-rose-600">{(customQuery.error as any)?.message || "Erreur"}</p>
            )}

            {customQuery.data && customGroupBy === "none" && "result" in customQuery.data && (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <div className="rounded-xl border p-3">
                  <p className="text-xs text-muted-foreground">Total</p>
                  <p className="text-lg font-semibold">{money(customQuery.data.result.total || 0)}</p>
                </div>
                <div className="rounded-xl border p-3">
                  <p className="text-xs text-muted-foreground">Count</p>
                  <p className="text-lg font-semibold">{String(customQuery.data.result.count || 0)}</p>
                </div>
                <div className="rounded-xl border p-3">
                  <p className="text-xs text-muted-foreground">Moyenne</p>
                  <p className="text-lg font-semibold">{money(customQuery.data.result.avg || 0)}</p>
                </div>
                <div className="rounded-xl border p-3">
                  <p className="text-xs text-muted-foreground">Min</p>
                  <p className="text-lg font-semibold">{money(customQuery.data.result.min || 0)}</p>
                </div>
                <div className="rounded-xl border p-3">
                  <p className="text-xs text-muted-foreground">Max</p>
                  <p className="text-lg font-semibold">{money(customQuery.data.result.max || 0)}</p>
                </div>
              </div>
            )}

            {customQuery.data && customGroupBy !== "none" && "items" in customQuery.data && (
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="h-[320px] rounded-xl border p-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={customQuery.data.items.slice(0, 20)}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="group" hide />
                      <YAxis />
                      <Tooltip formatter={(v: any) => money(Number(v || 0))} />
                      <Bar dataKey="total" name="Total" fill="#0ea5e9" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-2">
                  {customQuery.data.items.slice(0, 20).map((row) => (
                    <div key={`${row.group}`} className="flex items-center justify-between gap-3 rounded-xl border p-2">
                      <p className="min-w-0 truncate text-sm">{row.group || "(vide)"}</p>
                      <div className="shrink-0 text-right">
                        <p className="text-sm font-semibold">{money(row.total || 0)}</p>
                        <p className="text-xs text-muted-foreground">{row.count} tx</p>
                      </div>
                    </div>
                  ))}
                  {!customQuery.data.items.length && <p className="text-sm text-muted-foreground">Aucun résultat.</p>}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}

async function apiClientRaw(path: string) {
  // Reuse the same base URL behavior as apiClient in lib/api.ts by calling fetch directly.
  // We keep this local to avoid changing shared API helpers in this first iteration.
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  const res = await fetch(`${base}${path}`, { credentials: "include" })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json()
}
