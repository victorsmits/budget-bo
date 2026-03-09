"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Building2, CreditCard, LayoutDashboard, LogOut, Menu, Repeat2, Wallet } from "lucide-react"

import { logout, useAuth } from "@/lib/auth"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { ThemeToggle } from "@/components/theme-toggle"

const navItems = [
  { title: "Tableau de bord", href: "/", icon: LayoutDashboard },
  { title: "Transactions", href: "/transactions", icon: CreditCard },
  { title: "Récurrentes", href: "/recurring", icon: Repeat2 },
  { title: "Comptes", href: "/credentials", icon: Building2 },
]

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <span className="flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
        <Wallet className="size-5" />
      </span>
      <div>
        <p className="text-sm font-semibold">Budget Bo</p>
        <p className="text-xs text-muted-foreground">Finance personnelle</p>
      </div>
    </Link>
  )
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()

  return (
    <nav className="space-y-1">
      {navItems.map((item) => {
        const Icon = item.icon
        const active = pathname === item.href || pathname?.startsWith(`${item.href}/`)
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
              active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Icon className="size-4" />
            {item.title}
          </Link>
        )
      })}
    </nav>
  )
}

function UserCard() {
  const { user } = useAuth()

  return (
    <div className="rounded-xl border bg-background/70 p-3">
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
      <div className="flex gap-2">
        <ThemeToggle />
        <Button variant="outline" size="sm" className="flex-1" onClick={logout}>
          <LogOut className="mr-2 size-4" />
          Quitter
        </Button>
      </div>
    </div>
  )
}

export function Sidebar() {
  const [open, setOpen] = React.useState(false)

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-40 border-b bg-background/90 backdrop-blur md:hidden">
        <div className="flex h-16 items-center justify-between px-4">
          <Brand />
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon">
                <Menu className="size-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80 p-4">
              <div className="space-y-6">
                <Brand />
                <NavLinks onNavigate={() => setOpen(false)} />
                <UserCard />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <aside className="hidden h-full w-72 flex-col border-r bg-muted/30 p-4 md:flex">
        <div className="mb-8">
          <Brand />
        </div>
        <div className="flex-1">
          <NavLinks />
        </div>
        <UserCard />
      </aside>
    </>
  )
}
