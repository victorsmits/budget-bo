import DashboardLayout from "../dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Calendar, Repeat, TrendingUp, AlertCircle, Play } from "lucide-react"

const recurringExpenses = [
  {
    id: 1,
    name: "Loyer",
    pattern: "monthly",
    averageAmount: 850.00,
    nextDate: "2024-04-01",
    daysUntil: 26,
    confidence: 0.98,
    transactions: 12,
    category: "housing",
  },
  {
    id: 2,
    name: "Netflix",
    pattern: "monthly",
    averageAmount: 15.99,
    nextDate: "2024-03-10",
    daysUntil: 5,
    confidence: 0.95,
    transactions: 8,
    category: "subscriptions",
  },
  {
    id: 3,
    name: "EDF",
    pattern: "monthly",
    averageAmount: 120.00,
    nextDate: "2024-03-15",
    daysUntil: 10,
    confidence: 0.92,
    transactions: 6,
    category: "utilities",
  },
  {
    id: 4,
    name: "Spotify",
    pattern: "monthly",
    averageAmount: 9.99,
    nextDate: "2024-03-01",
    daysUntil: 0,
    confidence: 0.94,
    transactions: 10,
    category: "subscriptions",
  },
  {
    id: 5,
    name: "Assurance Habitation",
    pattern: "quarterly",
    averageAmount: 180.00,
    nextDate: "2024-04-15",
    daysUntil: 40,
    confidence: 0.88,
    transactions: 4,
    category: "insurance",
  },
]

const patternLabels: Record<string, string> = {
  weekly: "Hebdomadaire",
  monthly: "Mensuel",
  quarterly: "Trimestriel",
  annually: "Annuel",
}

const categoryColors: Record<string, string> = {
  housing: "bg-blue-100 text-blue-700",
  subscriptions: "bg-purple-100 text-purple-700",
  utilities: "bg-yellow-100 text-yellow-700",
  insurance: "bg-orange-100 text-orange-700",
}

const categoryLabels: Record<string, string> = {
  housing: "Logement",
  subscriptions: "Abonnements",
  utilities: "Factures",
  insurance: "Assurance",
}

export default function RecurringPage() {
  const totalMonthly = recurringExpenses
    .filter(e => e.pattern === "monthly")
    .reduce((sum, e) => sum + e.averageAmount, 0)

  const upcomingTotal = recurringExpenses
    .filter(e => e.daysUntil <= 30)
    .reduce((sum, e) => sum + e.averageAmount, 0)

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dépenses Récurrentes</h1>
            <p className="text-muted-foreground">
              Suivi et détection automatique des paiements récurrents
            </p>
          </div>
          <Button>
            <Play className="mr-2 h-4 w-4" />
            Détection IA
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total mensuel
              </CardTitle>
              <Repeat className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalMonthly.toFixed(2)} €</div>
              <p className="text-xs text-muted-foreground">
                {recurringExpenses.filter(e => e.pattern === "monthly").length} paiements mensuels
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                À venir (30j)
              </CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">-{upcomingTotal.toFixed(2)} €</div>
              <p className="text-xs text-muted-foreground">
                {recurringExpenses.filter(e => e.daysUntil <= 30).length} paiements attendus
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Taux de confiance moyen
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(recurringExpenses.reduce((sum, e) => sum + e.confidence, 0) / recurringExpenses.length * 100).toFixed(0)}%
              </div>
              <p className="text-xs text-muted-foreground">
                Basé sur {recurringExpenses.reduce((sum, e) => sum + e.transactions, 0)} transactions
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Patterns détectés</CardTitle>
              <CardDescription>
                Détectés automatiquement par l&apos;IA basée sur votre historique
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recurringExpenses.map((expense) => (
                  <div
                    key={expense.id}
                    className="flex items-center justify-between p-4 rounded-lg border"
                  >
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "h-10 w-10 rounded-full flex items-center justify-center",
                        categoryColors[expense.category] || "bg-gray-100 text-gray-700"
                      )}>
                        <Repeat className="h-5 w-5" />
                      </div>
                      <div>
                        <p className="font-medium">{expense.name}</p>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Badge variant="secondary" className={categoryColors[expense.category]}>
                            {categoryLabels[expense.category] || expense.category}
                          </Badge>
                          <span>•</span>
                          <span>{patternLabels[expense.pattern]}</span>
                          <span>•</span>
                          <span>{expense.transactions} transactions</span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-medium text-red-600">
                        -{expense.averageAmount.toFixed(2)} €
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        {expense.daysUntil === 0 ? (
                          <Badge variant="destructive" className="text-xs">
                            Aujourd&apos;hui
                          </Badge>
                        ) : expense.daysUntil <= 7 ? (
                          <Badge variant="outline" className="text-xs border-orange-300 text-orange-700">
                            Dans {expense.daysUntil} jours
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            Dans {expense.daysUntil} jours
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Calendrier</CardTitle>
              <CardDescription>Vue mensuelle des paiements</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-orange-50 border border-orange-200">
                  <AlertCircle className="h-5 w-5 text-orange-600" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-orange-900">
                      Paiement imminent
                    </p>
                    <p className="text-xs text-orange-700">
                      Netflix (15.99 €) dans 5 jours
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-sm font-medium">Ce mois</p>
                  {recurringExpenses
                    .filter(e => e.daysUntil <= 30)
                    .sort((a, b) => a.daysUntil - b.daysUntil)
                    .map((expense) => (
                      <div key={expense.id} className="flex items-center justify-between text-sm">
                        <span>{expense.name}</span>
                        <span className="text-muted-foreground">
                          {expense.daysUntil === 0 ? "Aujourd'hui" : `J+${expense.daysUntil}`}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ")
}
