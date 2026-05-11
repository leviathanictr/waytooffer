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
import { saveUserId } from '@/lib/auth'
import { Loader2 } from 'lucide-react'
import axios from 'axios'

export default function RegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ email: '', password: '', password_confirm: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})

  function validate() {
    const e: Record<string, string> = {}
    if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) e.email = 'Введите корректный email'
    if (form.password.length < 8) e.password = 'Минимум 8 символов'
    if (form.password.length > 72) e.password = 'Максимум 72 символа'
    if (form.password !== form.password_confirm) e.password_confirm = 'Пароли не совпадают'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    try {
      const { data } = await auth.register(form)
      saveUserId(data.user_id)
      toast.success('Аккаунт создан! Подтвердите email.')
      router.push('/verify')
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        if (!err.response) {
          toast.error('Не удалось подключиться к серверу.')
        } else {
          const rawDetail = err.response.data?.detail
          const detail: string = Array.isArray(rawDetail)
            ? (rawDetail[0]?.msg ?? String(rawDetail[0]))
            : (rawDetail ?? '')
          if (detail.toLowerCase().includes('email')) {
            toast.error('Этот email уже зарегистрирован')
          } else {
            toast.error(`Ошибка: ${detail || err.response.statusText}`)
          }
        }
      } else {
        toast.error('Неожиданная ошибка.')
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
          <CardTitle className="text-xl">Создать аккаунт</CardTitle>
          <CardDescription>Создайте резюме под любую вакансию с AI</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className={errors.email ? 'border-destructive' : ''}
                autoFocus
              />
              {errors.email && <p className="text-xs text-destructive">{errors.email}</p>}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Пароль</Label>
              <Input
                id="password"
                type="password"
                placeholder="Минимум 8 символов"
                maxLength={72}
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                className={errors.password ? 'border-destructive' : ''}
              />
              {errors.password && <p className="text-xs text-destructive">{errors.password}</p>}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password_confirm">Повторите пароль</Label>
              <Input
                id="password_confirm"
                type="password"
                placeholder="Повторите пароль"
                maxLength={72}
                value={form.password_confirm}
                onChange={e => setForm(f => ({ ...f, password_confirm: e.target.value }))}
                className={errors.password_confirm ? 'border-destructive' : ''}
              />
              {errors.password_confirm && <p className="text-xs text-destructive">{errors.password_confirm}</p>}
            </div>

            <Button type="submit" disabled={loading} className="w-full h-12 mt-2">
              {loading ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Создаём аккаунт...</> : 'Зарегистрироваться'}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-4">
            Уже есть аккаунт?{' '}
            <Link href="/login" className="text-primary font-medium hover:underline">
              Войти
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
