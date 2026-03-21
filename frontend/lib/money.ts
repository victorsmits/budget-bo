export function money(n: number, currency: string = "EUR", locale: string = "fr-FR") {
  return n.toLocaleString(locale, { style: "currency", currency })
}
