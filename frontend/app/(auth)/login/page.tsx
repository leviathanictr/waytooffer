'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { auth } from '@/lib/api'
import { saveTokens } from '@/lib/auth'
import { Loader2 } from 'lucide-react'
import axios from 'axios'

export default function LoginPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ login: '', password: '' })
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!form.login.trim()) { setError('Введите телефон или email'); return }
    if (!form.password)     { setError('Введите пароль'); return }

    setLoading(true)
    try {
      const { data } = await auth.login(form)
      saveTokens(data.access_token, data.refresh_token)
      toast.success('Добро пожаловать!')
      const onboarded = localStorage.getItem('wto_onboarded')
      router.push(onboarded ? '/' : '/onboarding')
    } catch (err: unknown) {
      console.error('[login] error:', err)
      if (axios.isAxiosError(err)) {
        if (!err.response) {
          setError('Не удалось подключиться к серверу. Убедитесь что бэкенд запущен.')
        } else if (err.response.status === 401) {
          setError('Неверный логин или пароль')
        } else if (err.response.status === 403) {
          setError('Аккаунт не подтверждён. Пройдите верификацию email и телефона.')
        } else {
          setError(`Ошибка сервера: ${err.response.data?.detail || err.response.statusText}`)
        }
      } else {
        setError('Неожиданная ошибка. Откройте консоль браузера для деталей.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-muted/30">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center pb-2">
          <div className="text-2xl font-bold text-primary mb-1">WayToOffer</div>
          <CardTitle className="text-xl">Войти</CardTitle>
          <CardDescription>Войдите в свой аккаунт</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="login">Телефон или Email</Label>
              <Input
                id="login"
                type="text"
                placeholder="+7XXXXXXXXXX или you@example.com"
                value={form.login}
                onChange={e => setForm(f => ({ ...f, login: e.target.value }))}
                autoComplete="username"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Пароль</Label>
              <Input
                id="password"
                type="password"
                placeholder="Ваш пароль"
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                autoComplete="current-password"
              />
            </div>

            {error && (
              <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <Button type="submit" disabled={loading} className="w-full h-12 mt-2">
              {loading ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Входим...</> : 'Войти'}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-4">
            Нет аккаунта?{' '}
            <Link href="/register" className="text-primary font-medium hover:underline">
              Зарегистрироваться
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
