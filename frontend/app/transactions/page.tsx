import DashboardLayout from "../dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Search, Filter, Download } from "lucide-react"

const transactions = [
  { id: 1, label: "Netflix", rawLabel: "PRLVM SEPA NETFLIX.COM", amount: -15.99, date: "2024-03-05", category: "subscriptions", isRecurring: true, merchant: "Netflix" },
  { id: 2, label: "Carrefour Market", rawLabel: "CARTE CARREFOUR MARKET 04/03", amount: -78.30, date: "2024-03-04", category: "food", isRecurring: false, merchant: "Carrefour" },
  { id: 3, label: "Salaire ACME", rawLabel: "VIREMENT SALAIRE ACME CORP", amount: 2500.00, date: "2024-03-01", category: "income", isRecurring: true, merchant: "ACME Corp" },
  { id: 4, label: "EDF", rawLabel: "PRLVM SEPA EDF PARTICULIERS", amount: -120.00, date: "2024-03-01", category: "utilities", isRecurring: true, merchant: "EDF" },
  { id: 5, label: "Spotify", rawLabel: "CARTE SPOTIFY AB", amount: -9.99, date: "2024-03-01", category: "subscriptions", isRecurring: true, merchant: "Spotify" },
  { id: 6, label: "Shell Station", rawLabel: "CARTE SHELL STATION 28/02", amount: -65.00, date: "2024-02-28", category: "transportation", isRecurring: false, merchant: "Shell" },
  { id: 7, label: "Pharmacie Centrale", rawLabel: "CARTE PHARMACIE CENTRALE", amount: -23.45, date: "2024-02-27", category: "healthcare", isRecurring: false, merchant: "Pharmacie Centrale" },
  { id: 8, label: "Fnac.com", rawLabel: "ACHAT INTERNET FNAC.COM", amount: -129.99, date: "2024-02-25", category: "shopping", isRecurring: false, merchant: "Fnac" },
]

const categoryColors: Record<string, string> = {
  subscriptions: "bg-purple-100 text-purple-700",
  food: "bg-green-100 text-green-700",
  income: "bg-blue-100 text-blue-700",
  utilities: "bg-yellow-100 text-yellow-700",
  transportation: "bg-orange-100 text-orange-700",
  healthcare: "bg-red-100 text-red-700",
  shopping: "bg-pink-100 text-pink-700",
  other: "bg-gray-100 text-gray-700",
}

const categoryLabels: Record<string, string> = {
  subscriptions: "Abonnements",
  food: "Alimentation",
  income: "Revenus",
  utilities: "Factures",
  transportation: "Transport",
  healthcare: "Santé",
  shopping: "Achats",
  other: "Autre",
}

export default function TransactionsPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Transactions</h1>
            <p className="text-muted-foreground">
              Historique de vos opérations bancaires
            </p>
          </div>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4 flex-1">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input placeholder="Rechercher..." className="pl-9" />
                </div>
                <Button variant="outline" size="sm">
                  <Filter className="mr-2 h-4 w-4" />
                  Filtres
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="relative w-full overflow-auto">
              <table className="w-full caption-bottom text-sm">
                <thead className="[&_tr]:border-b">
                  <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Date</th>
                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Libellé</th>
                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Catégorie</th>
                    <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Montant</th>
                    <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">Récurrent</th>
                  </tr>
                </thead>
                <tbody className="[&_tr:last-child]:border-0">
                  {transactions.map((tx) => (
                    <tr
                      key={tx.id}
                      className="border-b transition-colors hover:bg-muted/50"
                    >
                      <td className="p-4 align-middle">{tx.date}</td>
                      <td className="p-4 align-middle">
                        <div>
                          <p className="font-medium">{tx.label}</p>
                          <p className="text-xs text-muted-foreground">{tx.rawLabel}</p>
                        </div>
                      </td>
                      <td className="p-4 align-middle">
                        <Badge variant="secondary" className={categoryColors[tx.category]}>
                          {categoryLabels[tx.category]}
                        </Badge>
                      </td>
                      <td className={cn("p-4 align-middle text-right font-medium", tx.amount > 0 ? "text-green-600" : "text-red-600")}>
                        {tx.amount > 0 ? "+" : ""}{tx.amount.toFixed(2)} €
                      </td>
                      <td className="p-4 align-middle text-center">
                        {tx.isRecurring && (
                          <Badge variant="outline" className="text-xs">
                            Récurrent
                          </Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ")
}
