import type { Metadata } from "next"
import { Toaster } from "@/components/ui/sonner"
import { Navigation } from "@/components/navigation"
import "./globals.css"

export const metadata: Metadata = {
  title: "WayToOffer — Резюме под вакансию",
  description: "Создайте идеальное резюме за 5 минут с помощью AI",
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className="h-full dark" suppressHydrationWarning>
      <body className="min-h-full flex flex-col font-sans antialiased bg-background text-foreground">
        <Navigation />
        <main className="flex-1 flex flex-col pb-16 md:pb-0">
          {children}
        </main>
        <Toaster position="top-center" richColors />
      </body>
    </html>
  )
}
