"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  LayoutDashboard,
  CreditCard,
  Repeat,
  LogOut,
  Wallet,
  Loader2,
  Building2,
  Menu,
  Sparkles,
} from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { useAuth, logout } from "@/lib/auth"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { ThemeToggle } from "@/components/theme-toggle"

interface NavItem {
  title: string
  subtitle: string
  href: string
  icon: React.ComponentType<{ className?: string }>
}

const navItems: NavItem[] = [
  { title: "Pilotage", subtitle: "Vue globale", href: "/", icon: LayoutDashboard },
  { title: "Flux", subtitle: "Transactions", href: "/transactions", icon: CreditCard },
  { title: "Abonnements", subtitle: "Récurrences", href: "/recurring", icon: Repeat },
  { title: "Connexions", subtitle: "Comptes", href: "/credentials", icon: Building2 },
]

function NavLinks({ onClick }: { onClick?: () => void }) {
  const pathname = usePathname()

  return (
    <>
      {navItems.map((item) => {
        const Icon = item.icon
        const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`)

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onClick}
            className={cn(
              "group flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all",
              isActive
                ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground",
            )}
          >
            <span
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-lg",
                isActive ? "bg-white/20" : "bg-muted/80 group-hover:bg-background",
              )}
            >
              <Icon className="h-4 w-4" />
            </span>
            <span className="flex flex-col leading-tight">
              <span className="text-sm font-medium">{item.title}</span>
              <span className={cn("text-xs", isActive ? "text-primary-foreground/80" : "text-muted-foreground")}>
                {item.subtitle}
              </span>
            </span>
          </Link>
        )
      })}
    </>
  )
}

function UserSection() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="glass-card rounded-2xl p-3">
      <div className="flex items-center gap-3">
        <Avatar className="h-10 w-10">
          <AvatarImage src={user?.profile_picture || ""} alt={user?.display_name || ""} />
          <AvatarFallback>{user?.display_name?.[0] || user?.email?.[0] || "U"}</AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{user?.display_name || user?.email || "Utilisateur"}</p>
          <p className="truncate text-xs text-muted-foreground">{user?.email || ""}</p>
        </div>
        <ThemeToggle />
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={logout}>
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/35">
        <Wallet className="h-5 w-5" />
      </div>
      <div>
        <p className="text-base font-semibold">Budget Bo</p>
        <p className="text-xs text-muted-foreground">Finance OS</p>
      </div>
    </Link>
  )
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-6 p-4">
      <div className="space-y-4">
        <Brand />
        <div className="glass-card rounded-2xl p-3">
          <p className="mb-2 flex items-center gap-1 text-xs uppercase tracking-wide text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5" /> Navigation
          </p>
          <nav className="grid gap-2">
            <NavLinks onClick={onNavigate} />
          </nav>
        </div>
      </div>

      <div className="mt-auto">
        <UserSection />
      </div>
    </div>
  )
}

export function Sidebar() {
  const [open, setOpen] = React.useState(false)

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-72 border-r bg-background/70 backdrop-blur-xl md:block">
        <SidebarContent />
      </aside>

      <header className="fixed left-0 right-0 top-0 z-50 border-b bg-background/90 backdrop-blur-xl md:hidden">
        <div className="flex h-16 items-center justify-between px-4">
          <Brand />
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80 p-0">
              <SidebarContent onNavigate={() => setOpen(false)} />
            </SheetContent>
          </Sheet>
        </div>
      </header>
    </>
  )
}
