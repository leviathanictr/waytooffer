'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { profile as profileApi } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import { Plus, Trash2 } from 'lucide-react'
import type { Profile } from '@/lib/types'

const LANGUAGE_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'Родной']

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState<'welcome' | 'form'>('welcome')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState<Profile>({
    name: '',
    city: '',
    phone: '',
    email: '',
    link_hh: '',
    link_portfolio: '',
    university: '',
    faculty: '',
    speciality: '',
    graduation_year: '',
    languages: [],
  })

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    if (typeof window !== 'undefined') {
      const onboarded = localStorage.getItem('wto_onboarded')
      if (onboarded === '1') {
        router.push('/')
      }
    }
  }, [router])

  function addLanguage() {
    setForm(f => ({
      ...f,
      languages: [...(f.languages || []), { language: '', level: 'B1' }],
    }))
  }

  function removeLanguage(index: number) {
    setForm(f => ({
      ...f,
      languages: (f.languages || []).filter((_, i) => i !== index),
    }))
  }

  function updateLanguage(index: number, field: 'language' | 'level', value: string) {
    setForm(f => ({
      ...f,
      languages: (f.languages || []).map((lang, i) =>
        i === index ? { ...lang, [field]: value } : lang
      ),
    }))
  }

  async function handleSave() {
    setLoading(true)
    try {
      await profileApi.update(form)
      if (typeof window !== 'undefined') {
        localStorage.setItem('wto_onboarded', '1')
      }
      toast.success('Данные сохранены!')
      router.push('/')
    } catch {
      toast.error('Ошибка сохранения. Попробуйте ещё раз.')
    } finally {
      setLoading(false)
    }
  }

  function handleSkip() {
    if (typeof window !== 'undefined') {
      localStorage.setItem('wto_onboarded', '1')
    }
    router.push('/')
  }

  if (step === 'welcome') {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-muted/30">
        <Card className="w-full max-w-sm">
          <CardHeader className="text-center">
            <div className="text-4xl mb-3">👋</div>
            <CardTitle className="text-xl">Привет!</CardTitle>
            <CardDescription className="text-base mt-2">
              Хочешь заполнить базовые данные? Мы будем подставлять их в каждое резюме автоматически — тебе не придётся вводить их заново.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Button
              onClick={() => setStep('form')}
              className="w-full h-11"
            >
              Заполнить анкету
            </Button>
            <Button
              variant="outline"
              onClick={handleSkip}
              className="w-full h-11"
            >
              Пропустить
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-muted/30 py-8 px-4">
      <div className="max-w-lg mx-auto">
        <div className="mb-6 text-center">
          <div className="text-2xl font-bold text-primary">WayToOffer</div>
          <h1 className="text-xl font-semibold mt-2">Базовые данные</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Эти данные будут автоматически подставляться в каждое резюме
          </p>
        </div>

        <Card>
          <CardContent className="pt-6 space-y-5">
            {/* Personal */}
            <div className="space-y-4">
              <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                Личные данные
              </h2>

              <div className="space-y-1.5">
                <Label htmlFor="name">Имя и фамилия</Label>
                <Input
                  id="name"
                  placeholder="Иван Иванов"
                  value={form.name || ''}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="city">Город</Label>
                <Input
                  id="city"
                  placeholder="Москва"
                  value={form.city || ''}
                  onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="phone">Телефон</Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="+7XXXXXXXXXX"
                  value={form.phone || ''}
                  onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={form.email || ''}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                />
              </div>
            </div>

            {/* Links */}
            <div className="space-y-4">
              <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                Ссылки
              </h2>

              <div className="space-y-1.5">
                <Label htmlFor="link_hh">Ссылка на hh.ru</Label>
                <Input
                  id="link_hh"
                  type="url"
                  placeholder="https://hh.ru/resume/..."
                  value={form.link_hh || ''}
                  onChange={e => setForm(f => ({ ...f, link_hh: e.target.value }))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="link_portfolio">Ссылка на GitHub / портфолио</Label>
                <Input
                  id="link_portfolio"
                  type="url"
                  placeholder="https://github.com/..."
                  value={form.link_portfolio || ''}
                  onChange={e => setForm(f => ({ ...f, link_portfolio: e.target.value }))}
                />
              </div>
            </div>

            {/* Education */}
            <div className="space-y-4">
              <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                Образование
              </h2>

              <div className="space-y-1.5">
                <Label htmlFor="university">Вуз</Label>
                <Input
                  id="university"
                  placeholder="МГУ им. М.В. Ломоносова"
                  value={form.university || ''}
                  onChange={e => setForm(f => ({ ...f, university: e.target.value }))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="faculty">Факультет</Label>
                <Input
                  id="faculty"
                  placeholder="Факультет вычислительной математики"
                  value={form.faculty || ''}
                  onChange={e => setForm(f => ({ ...f, faculty: e.target.value }))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="speciality">Специальность</Label>
                <Input
                  id="speciality"
                  placeholder="Прикладная математика"
                  value={form.speciality || ''}
                  onChange={e => setForm(f => ({ ...f, speciality: e.target.value }))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="graduation_year">Год окончания / курс</Label>
                <Input
                  id="graduation_year"
                  placeholder="2026 или 3 курс"
                  value={form.graduation_year || ''}
                  onChange={e => setForm(f => ({ ...f, graduation_year: e.target.value }))}
                />
              </div>
            </div>

            {/* Languages */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                  Языки
                </h2>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addLanguage}
                  className="gap-1"
                >
                  <Plus className="w-3 h-3" />
                  Добавить
                </Button>
              </div>

              {(form.languages || []).map((lang, index) => (
                <div key={index} className="flex gap-2 items-start">
                  <div className="flex-1 space-y-1.5">
                    <Input
                      placeholder="Английский"
                      value={lang.language}
                      onChange={e => updateLanguage(index, 'language', e.target.value)}
                    />
                  </div>
                  <div className="w-28 space-y-1.5">
                    <select
                      className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50"
                      value={lang.level}
                      onChange={e => updateLanguage(index, 'level', e.target.value)}
                    >
                      {LANGUAGE_LEVELS.map(level => (
                        <option key={level} value={level}>{level}</option>
                      ))}
                    </select>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeLanguage(index)}
                    className="text-muted-foreground hover:text-destructive mt-0"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}

              {(form.languages || []).length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Нажмите «Добавить» чтобы указать языки
                </p>
              )}
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleSkip}
                className="flex-1 h-11"
              >
                Пропустить
              </Button>
              <Button
                type="button"
                onClick={handleSave}
                disabled={loading}
                className="flex-1 h-11"
              >
                {loading ? 'Сохраняем...' : 'Сохранить'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
