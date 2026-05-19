'use client'
import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { auth } from '@/lib/api'
import { Loader2 } from 'lucide-react'
import axios from 'axios'

type Step = 'request' | 'confirm'

export default function ForgotPasswordPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>('request')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  function apiError(err: unknown, fallback: string): string {
    if (axios.isAxiosError(err)) {
      if (!err.response) return 'Нет связи с сервером'
      const detail = err.response.data?.detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) return detail[0]?.msg ?? fallback
      return fallback
    }
    return fallback
  }

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

  async function handleRequest(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    try {
      const { data } = await auth.passwordResetRequest({ email: email.trim() })
      toast.success(data.message)
      setStep('confirm')
      startCooldown()
    } catch (err) {
      toast.error(apiError(err, 'Не удалось отправить код'))
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    if (cooldown > 0 || !email.trim()) return
    try {
      await auth.passwordResetRequest({ email: email.trim() })
      toast.success('Код отправлен повторно')
      startCooldown()
    } catch (err) {
      toast.error(apiError(err, 'Не удалось отправить код'))
    }
  }

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault()
    if (code.length < 6) { toast.error('Введите 6-значный код'); return }
    if (newPassword.length < 8) { toast.error('Пароль минимум 8 символов'); return }
    if (newPassword !== newPasswordConfirm) { toast.error('Пароли не совпадают'); return }
    setLoading(true)
    try {
      await auth.passwordResetConfirm({
        email: email.trim(),
        code: code.trim(),
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      })
      toast.success('Пароль изменён — войдите с новым')
      setTimeout(() => router.push('/login'), 1200)
    } catch (err) {
      toast.error(apiError(err, 'Неверный или просроченный код'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-muted/30">
      <div className="w-full max-w-sm space-y-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-primary mb-1">WayToOffer</div>
          <h1 className="text-xl font-semibold">Восстановление пароля</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {step === 'request'
              ? 'Введите email, на который зарегистрировались'
              : 'Введите код из письма и новый пароль'}
          </p>
        </div>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              {step === 'request' ? 'Запросить код' : 'Новый пароль'}
            </CardTitle>
            <CardDescription>
              {step === 'request'
                ? 'Пришлём 6-значный код'
                : `Код выслан на ${email}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === 'request' ? (
              <form onSubmit={handleRequest} className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    autoFocus
                  />
                </div>
                <Button type="submit" disabled={loading || !email.trim()} className="w-full h-12">
                  {loading
                    ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Отправляем...</>
                    : 'Прислать код'}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleConfirm} className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="code">Код из письма</Label>
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
                <div className="space-y-1.5">
                  <Label htmlFor="new_password">Новый пароль</Label>
                  <Input
                    id="new_password"
                    type="password"
                    placeholder="Минимум 8 символов"
                    maxLength={72}
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="new_password_confirm">Повторите пароль</Label>
                  <Input
                    id="new_password_confirm"
                    type="password"
                    placeholder="Повторите новый пароль"
                    maxLength={72}
                    value={newPasswordConfirm}
                    onChange={e => setNewPasswordConfirm(e.target.value)}
                  />
                </div>
                <div className="flex gap-2 pt-1">
                  <Button type="submit" disabled={loading} className="flex-1">
                    {loading ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Сохраняем...</> : 'Сменить пароль'}
                  </Button>
                  <Button type="button" variant="outline" disabled={cooldown > 0} onClick={handleResend}>
                    {cooldown > 0 ? `${cooldown}с` : 'Повторно'}
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>

        <p className="text-center text-sm text-muted-foreground">
          Вспомнили пароль?{' '}
          <Link href="/login" className="text-primary font-medium hover:underline">
            Вернуться ко входу
          </Link>
        </p>
      </div>
    </div>
  )
}
