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

export default function RegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    phone: '+7',
    email: '',
    password: '',
    password_confirm: '',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  function validate() {
    const e: Record<string, string> = {}
    if (!form.phone.match(/^\+7\d{10}$/)) e.phone = 'Введите номер в формате +7XXXXXXXXXX'
    if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) e.email = 'Введите корректный email'
    if (form.password.length < 8) e.password = 'Минимум 8 символов'
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
      router.push('/verify')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (msg?.includes('Phone')) toast.error('Этот номер телефона уже зарегистрирован')
      else if (msg?.includes('Email')) toast.error('Этот email уже зарегистрирован')
      else toast.error('Ошибка регистрации. Попробуйте ещё раз.')
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
              <Label htmlFor="phone">Телефон</Label>
              <Input
                id="phone"
                type="tel"
                placeholder="+7XXXXXXXXXX"
                value={form.phone}
                onChange={e => {
                  let v = e.target.value
                  if (!v.startsWith('+7')) v = '+7' + v.replace(/^\+7?/, '')
                  setForm(f => ({ ...f, phone: v }))
                }}
                className={errors.phone ? 'border-destructive' : ''}
              />
              {errors.phone && <p className="text-xs text-destructive">{errors.phone}</p>}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className={errors.email ? 'border-destructive' : ''}
              />
              {errors.email && <p className="text-xs text-destructive">{errors.email}</p>}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Пароль</Label>
              <Input
                id="password"
                type="password"
                placeholder="Минимум 8 символов"
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
                value={form.password_confirm}
                onChange={e => setForm(f => ({ ...f, password_confirm: e.target.value }))}
                className={errors.password_confirm ? 'border-destructive' : ''}
              />
              {errors.password_confirm && <p className="text-xs text-destructive">{errors.password_confirm}</p>}
            </div>

            <Button type="submit" disabled={loading} className="w-full h-12 mt-2">
              {loading ? 'Создаём аккаунт...' : 'Зарегистрироваться'}
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
