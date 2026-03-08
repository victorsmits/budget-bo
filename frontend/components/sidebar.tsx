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
} from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { useAuth, logout } from "@/lib/auth"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { ThemeToggle } from "@/components/theme-toggle"

interface NavItem {
  title: string
  href: string
  icon: React.ComponentType<{ className?: string }>
}

const navItems: NavItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    title: "Transactions",
    href: "/transactions",
    icon: CreditCard,
  },
  {
    title: "Récurrentes",
    href: "/recurring",
    icon: Repeat,
  },
  {
    title: "Comptes",
    href: "/credentials",
    icon: Building2,
  },
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
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {item.title}
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
    <div className="border-t p-4">
      <div className="flex items-center gap-3 rounded-lg bg-muted p-3">
        <Avatar className="h-9 w-9">
          <AvatarImage src={user?.profile_picture || ""} alt={user?.display_name || ""} />
          <AvatarFallback>{user?.display_name?.[0] || user?.email?.[0] || "U"}</AvatarFallback>
        </Avatar>
        <div className="flex-1 overflow-hidden">
          <p className="text-sm font-medium truncate">{user?.display_name || user?.email || "Utilisateur"}</p>
          <p className="text-xs text-muted-foreground truncate">{user?.email || ""}</p>
        </div>
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={logout}>
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 font-bold text-xl">
      <Wallet className="h-6 w-6 text-budget-500" />
      <span>Budget Bo</span>
    </Link>
  )
}

export function Sidebar() {
  const [open, setOpen] = React.useState(false)

  return (
    <>
      {/* Desktop Sidebar */}
      <div className="hidden md:flex h-full w-64 flex-col border-r bg-card">
        <div className="flex h-16 items-center border-b px-6">
          <Logo />
        </div>

        <div className="flex-1 py-4">
          <nav className="grid gap-1 px-2">
            <NavLinks />
          </nav>
        </div>

        <UserSection />
      </div>

      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 border-b bg-card z-50 flex items-center justify-between px-4">
        <Logo />
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0 flex flex-col">
            <div className="flex h-16 items-center border-b px-6">
              <Logo />
            </div>
            <div className="flex-1 py-4">
              <nav className="grid gap-1 px-2">
                <NavLinks onClick={() => setOpen(false)} />
              </nav>
            </div>
            <UserSection />
          </SheetContent>
        </Sheet>
      </div>
    </>
  )
}
