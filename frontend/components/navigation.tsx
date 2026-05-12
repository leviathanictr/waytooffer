'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { FileText, History, Settings, LogOut } from 'lucide-react'
import { clearTokens } from '@/lib/auth'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { href: '/', label: 'Главная', icon: FileText },
  { href: '/history', label: 'История', icon: History },
  { href: '/settings', label: 'Настройки', icon: Settings },
]

export function Navigation() {
  const pathname = usePathname()
  const router = useRouter()

  const showNav = ['/', '/history', '/settings'].some(
    p => pathname === p || pathname.startsWith(p + '/')
  )
  if (!showNav) return null

  function handleLogout() {
    clearTokens()
    router.push('/login')
  }

  return (
    <>
      {/* Desktop top nav */}
      <nav className="hidden md:flex items-center justify-between px-6 h-16 border-b border-border bg-card sticky top-0 z-10">
        <Link href="/" className="font-bold text-lg text-primary">WayToOffer</Link>
        <div className="flex items-center gap-6">
          {NAV_ITEMS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                'text-sm font-medium transition-colors',
                pathname === href ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {label}
            </Link>
          ))}
          <button
            onClick={handleLogout}
            className="text-sm font-medium text-muted-foreground hover:text-destructive transition-colors flex items-center gap-1"
          >
            <LogOut className="w-4 h-4" />
            Выйти
          </button>
        </div>
      </nav>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-10 bg-card border-t border-border">
        <div className="flex items-center justify-around h-16 max-w-lg mx-auto">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-colors',
                pathname === href ? 'text-primary' : 'text-muted-foreground'
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="text-xs font-medium">{label}</span>
            </Link>
          ))}
          <button
            onClick={handleLogout}
            className="flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-colors text-muted-foreground hover:text-destructive"
          >
            <LogOut className="w-5 h-5" />
            <span className="text-xs font-medium">Выйти</span>
          </button>
        </div>
      </nav>
    </>
  )
}
