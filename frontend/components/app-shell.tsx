"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { BarChart3, Building2, CreditCard, Home, LogOut, Menu, Repeat2, Wallet2 } from "lucide-react"

import { logout, useAuth } from "@/lib/auth"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { ThemeToggle } from "@/components/theme-toggle"

const links = [
  { href: "/", label: "Accueil", icon: Home },
  { href: "/analytics", label: "Analyse", icon: BarChart3 },
  { href: "/transactions", label: "Transactions", icon: CreditCard },
  { href: "/recurring", label: "Récurrentes", icon: Repeat2 },
  { href: "/credentials", label: "Comptes", icon: Building2 },
]

function Nav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()

  return (
    <nav className="space-y-1.5">
      {links.map((item) => {
        const Icon = item.icon
        const active = pathname === item.href || pathname?.startsWith(`${item.href}/`)
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
              active ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Icon className="size-4" />
            {item.label}
          </Link>
        )
      })}
    </nav>
  )
}

function UserFooter() {
  const { user } = useAuth()
  return (
    <div className="rounded-xl border bg-background p-3">
      <div className="mb-3 flex items-center gap-3">
        <Avatar className="size-9">
          <AvatarImage src={user?.profile_picture || ""} alt={user?.display_name || ""} />
          <AvatarFallback>{user?.display_name?.[0] || user?.email?.[0] || "U"}</AvatarFallback>
        </Avatar>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{user?.display_name || "Utilisateur"}</p>
          <p className="truncate text-xs text-muted-foreground">{user?.email || ""}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <Button variant="outline" size="sm" className="flex-1" onClick={logout}>
          <LogOut className="mr-1 size-4" /> Déconnexion
        </Button>
      </div>
    </div>
  )
}

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <span className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
        <Wallet2 className="size-5" />
      </span>
      <div>
        <p className="text-base font-semibold">Budget Bo</p>
        <p className="text-xs text-muted-foreground">Pilotage financier</p>
      </div>
    </Link>
  )
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-muted/20">
      <header className="fixed inset-x-0 top-0 z-40 border-b bg-background/95 backdrop-blur md:hidden">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
          <Brand />
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon">
                <Menu className="size-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80 p-4">
              <div className="space-y-6">
                <Brand />
                <Nav />
                <UserFooter />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <aside className="hidden w-72 border-r bg-background p-4 md:flex md:flex-col">
        <div className="mb-8"><Brand /></div>
        <div className="flex-1"><Nav /></div>
        <UserFooter />
      </aside>

      <main className="flex-1 px-4 pb-8 pt-20 md:px-8 md:pt-8">
        <div className="mx-auto w-full max-w-7xl">{children}</div>
      </main>
    </div>
  )
}
