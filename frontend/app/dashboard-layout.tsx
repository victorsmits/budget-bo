import { Sidebar } from "@/components/sidebar"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-transparent">
      <Sidebar />
      <main className="md:pl-72">
        <div className="mx-auto max-w-7xl px-4 pb-8 pt-24 md:px-8 md:pt-8">{children}</div>
      </main>
    </div>
  )
}
