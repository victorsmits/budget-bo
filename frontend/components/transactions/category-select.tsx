import { getCategoryLabel, TRANSACTION_CATEGORY_OPTIONS } from "@/lib/transaction-presentation"

interface CategorySelectProps {
  id?: string
  value: string
  onChange: (value: string) => void
  includeAllOption?: boolean
}

export function CategorySelect({ id, value, onChange, includeAllOption = false }: CategorySelectProps) {
  return (
    <select
      id={id}
      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      {includeAllOption && <option value="">Toutes</option>}
      {TRANSACTION_CATEGORY_OPTIONS.map((category) => (
        <option key={category} value={category}>
          {getCategoryLabel(category)}
        </option>
      ))}
    </select>
  )
}
