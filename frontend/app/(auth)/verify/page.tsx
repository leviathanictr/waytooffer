'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { auth } from '@/lib/api'
import { getUserId } from '@/lib/auth'
import { CheckCircle, Loader2 } from 'lucide-react'
import axios from 'axios'

export default function VerifyPage() {
  const router = useRouter()
  const [userId, setUserId] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [verified, setVerified] = useState(false)
  const [loading, setLoading] = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const id = getUserId()
    if (!id) { router.push('/register'); return }
    setUserId(id)
  }, [router])

  useEffect(() => {
    if (verified) {
      toast.success('Email подтверждён! Войдите в систему.')
      setTimeout(() => router.push('/login'), 1500)
    }
  }, [verified, router])

  function startCooldown() {
    setCooldown(60)
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setCooldown(prev => {
        if (prev <= 1) { if (timerRef.current) clearInterval(timerRef.current); return 0 }
        return prev - 1
      })
    }, 1000)
  }

  function apiError(err: unknown, fallback: string): string {
    if (axios.isAxiosError(err)) {
      if (!err.response) return 'Нет связи с сервером'
      return err.response.data?.detail || fallback
    }
    return fallback
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault()
    if (!userId || !code.trim()) return
    setLoading(true)
    try {
      await auth.verifyEmail({ user_id: userId, code: code.trim() })
      setVerified(true)
    } catch (err) {
      toast.error(apiError(err, 'Неверный код. Попробуйте ещё раз.'))
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    if (!userId || cooldown > 0) return
    try {
      await auth.resendVerification({ user_id: userId, type: 'email' })
      toast.success('Код отправлен повторно')
      startCooldown()
    } catch (err) {
      toast.error(apiError(err, 'Не удалось отправить код'))
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-muted/30">
      <div className="w-full max-w-sm space-y-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-primary mb-1">WayToOffer</div>
          <h1 className="text-xl font-semibold">Подтверждение email</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Мы отправили код подтверждения на ваш email
          </p>
          {process.env.NODE_ENV === 'development' && (
            <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-2">
              Dev-режим: код напечатан в консоли бэкенда
            </p>
          )}
        </div>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Код из письма</CardTitle>
              {verified && (
                <div className="flex items-center gap-1 text-green-600 text-sm font-medium">
                  <CheckCircle className="w-4 h-4" /> Подтверждён
                </div>
              )}
            </div>
            <CardDescription>Введите 6-значный код</CardDescription>
          </CardHeader>
          <CardContent>
            {!verified ? (
              <form onSubmit={handleVerify} className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="code">Код</Label>
                  <Input
                    id="code"
                    type="text"
                    inputMode="numeric"
                    placeholder="000000"
                    maxLength={6}
                    value={code}
                    onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
                    autoFocus
                  />
                </div>
                <div className="flex gap-2">
                  <Button type="submit" disabled={loading || code.length < 6} className="flex-1">
                    {loading ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Проверяем...</> : 'Подтвердить'}
                  </Button>
                  <Button type="button" variant="outline" disabled={cooldown > 0} onClick={handleResend}>
                    {cooldown > 0 ? `${cooldown}с` : 'Повторно'}
                  </Button>
                </div>
              </form>
            ) : (
              <div className="flex items-center gap-2 text-green-600 py-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Email успешно подтверждён</span>
              </div>
            )}
          </CardContent>
        </Card>

        <button
          onClick={() => router.push('/login')}
          className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors py-2 text-center"
        >
          Пропустить →
        </button>
      </div>
    </div>
  )
}
