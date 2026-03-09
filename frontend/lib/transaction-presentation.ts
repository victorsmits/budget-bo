import { Transaction } from "@/types/api"

export const TRANSACTION_CATEGORY_COLORS: Record<string, string> = {
  subscriptions: "bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-500/20 dark:text-purple-200 dark:border-purple-400/30",
  food: "bg-green-100 text-green-800 border-green-200 dark:bg-green-500/20 dark:text-green-200 dark:border-green-400/30",
  groceries: "bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-200 dark:border-emerald-400/30",
  dining: "bg-lime-100 text-lime-800 border-lime-200 dark:bg-lime-500/20 dark:text-lime-200 dark:border-lime-400/30",
  income: "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-500/20 dark:text-blue-200 dark:border-blue-400/30",
  utilities: "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-500/20 dark:text-yellow-200 dark:border-yellow-400/30",
  transportation: "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-500/20 dark:text-orange-200 dark:border-orange-400/30",
  healthcare: "bg-red-100 text-red-800 border-red-200 dark:bg-red-500/20 dark:text-red-200 dark:border-red-400/30",
  shopping: "bg-pink-100 text-pink-800 border-pink-200 dark:bg-pink-500/20 dark:text-pink-200 dark:border-pink-400/30",
  home_improvement: "bg-violet-100 text-violet-800 border-violet-200 dark:bg-violet-500/20 dark:text-violet-200 dark:border-violet-400/30",
  housing: "bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-500/20 dark:text-indigo-200 dark:border-indigo-400/30",
  insurance: "bg-cyan-100 text-cyan-800 border-cyan-200 dark:bg-cyan-500/20 dark:text-cyan-200 dark:border-cyan-400/30",
  entertainment: "bg-fuchsia-100 text-fuchsia-800 border-fuchsia-200 dark:bg-fuchsia-500/20 dark:text-fuchsia-200 dark:border-fuchsia-400/30",
  education: "bg-teal-100 text-teal-800 border-teal-200 dark:bg-teal-500/20 dark:text-teal-200 dark:border-teal-400/30",
  travel: "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-500/20 dark:text-amber-200 dark:border-amber-400/30",
  other: "bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-500/20 dark:text-slate-200 dark:border-slate-400/30",
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

export const TRANSACTION_CATEGORY_OPTIONS = Object.keys(TRANSACTION_CATEGORY_LABELS)

export function getTransactionDisplayLabel(transaction: Transaction): string {
  return transaction.cleaned_label || transaction.merchant_name || transaction.raw_label
}

export function getCategoryLabel(category: string): string {
  return TRANSACTION_CATEGORY_LABELS[category?.toLowerCase?.() || ""] || category
}

export function getCategoryBadgeClass(category: string): string {
  const normalized = category?.toLowerCase?.() || "other"
  return TRANSACTION_CATEGORY_COLORS[normalized] || TRANSACTION_CATEGORY_COLORS.other
}
