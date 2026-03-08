import { Transaction } from "@/types/api"

export const TRANSACTION_CATEGORY_COLORS: Record<string, string> = {
  subscriptions: "bg-purple-100 text-purple-700",
  food: "bg-green-100 text-green-700",
  groceries: "bg-emerald-100 text-emerald-700",
  dining: "bg-lime-100 text-lime-700",
  income: "bg-blue-100 text-blue-700",
  utilities: "bg-yellow-100 text-yellow-700",
  transportation: "bg-orange-100 text-orange-700",
  healthcare: "bg-red-100 text-red-700",
  shopping: "bg-pink-100 text-pink-700",
  home_improvement: "bg-violet-100 text-violet-700",
  housing: "bg-indigo-100 text-indigo-700",
  insurance: "bg-cyan-100 text-cyan-700",
  entertainment: "bg-fuchsia-100 text-fuchsia-700",
  education: "bg-teal-100 text-teal-700",
  travel: "bg-amber-100 text-amber-700",
  other: "bg-gray-100 text-gray-700",
}

export const TRANSACTION_CATEGORY_LABELS: Record<string, string> = {
  subscriptions: "Abonnements",
  food: "Alimentation",
  groceries: "Courses",
  dining: "Restauration",
  income: "Revenus",
  utilities: "Factures",
  transportation: "Transport",
  healthcare: "Santé",
  shopping: "Achats",
  home_improvement: "Maison & Bricolage",
  housing: "Logement",
  insurance: "Assurance",
  entertainment: "Divertissement",
  education: "Éducation",
  travel: "Voyage",
  other: "Autre",
}

export const TRANSACTION_CATEGORY_OPTIONS = Object.keys(
  TRANSACTION_CATEGORY_LABELS,
)

export function getTransactionDisplayLabel(transaction: Transaction): string {
  return transaction.cleaned_label || transaction.merchant_name || transaction.raw_label
}

export function getCategoryLabel(category: string): string {
  return TRANSACTION_CATEGORY_LABELS[category] || category
}

export function getCategoryBadgeClass(category: string): string {
  return TRANSACTION_CATEGORY_COLORS[category] || TRANSACTION_CATEGORY_COLORS.other
}
