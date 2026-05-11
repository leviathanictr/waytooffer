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
    name: '', city: '', phone: '', telegram: '', email: '',
    link_hh: '', link_portfolio: '',
    university: '', faculty: '', speciality: '', graduation_year: '',
    languages: [],
  })

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    if (typeof window !== 'undefined' && localStorage.getItem('wto_onboarded') === '1') {
      router.push('/')
    }
  }, [router])

  function addLanguage() {
    setForm(f => ({ ...f, languages: [...(f.languages || []), { language: '', level: 'B1' }] }))
  }
  function removeLanguage(i: number) {
    setForm(f => ({ ...f, languages: (f.languages || []).filter((_, idx) => idx !== i) }))
  }
  function updateLanguage(i: number, field: 'language' | 'level', val: string) {
    setForm(f => ({ ...f, languages: (f.languages || []).map((l, idx) => idx === i ? { ...l, [field]: val } : l) }))
  }

  async function handleSave() {
    setLoading(true)
    try {
      await profileApi.update(form)
      localStorage.setItem('wto_onboarded', '1')
      toast.success('Данные сохранены!')
      router.push('/')
    } catch {
      toast.error('Ошибка сохранения. Попробуйте ещё раз.')
    } finally {
      setLoading(false)
    }
  }

  function handleSkip() {
    localStorage.setItem('wto_onboarded', '1')
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
              Заполни базовые данные — мы будем подставлять их в каждое резюме автоматически.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Button onClick={() => setStep('form')} className="w-full h-11">Заполнить анкету</Button>
            <Button variant="outline" onClick={handleSkip} className="w-full h-11">Пропустить</Button>
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
          <p className="text-sm text-muted-foreground mt-1">Автоматически подставляются в каждое резюме</p>
        </div>

        <Card>
          <CardContent className="pt-6 space-y-5">

            {/* Контактные данные */}
            <div className="space-y-4">
              <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Контактные данные</h2>

              <div className="space-y-1.5">
                <Label htmlFor="ob-name">Имя и фамилия</Label>
                <Input id="ob-name" placeholder="Иван Иванов" value={form.name || ''} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="ob-city">Город</Label>
                <Input id="ob-city" placeholder="Москва" value={form.city || ''} onChange={e => setForm(f => ({ ...f, city: e.target.value }))} />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="ob-phone">Телефон</Label>
                <Input
                  id="ob-phone"
                  type="tel"
                  placeholder="+7XXXXXXXXXX"
                  value={form.phone || ''}
                  onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="ob-telegram">Telegram</Label>
                <Input
                  id="ob-telegram"
                  placeholder="@username"
                  value={form.telegram || ''}
                  onChange={e => setForm(f => ({ ...f, telegram: e.target.value }))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="ob-email">Email для резюме</Label>
                <Input id="ob-email" type="email" placeholder="you@example.com" value={form.email || ''} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
              </div>
            </div>

            {/* Ссылки */}
            <div className="space-y-4">
              <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Ссылки</h2>
              <div className="space-y-1.5">
                <Label htmlFor="ob-hh">hh.ru</Label>
                <Input id="ob-hh" type="url" placeholder="https://hh.ru/resume/..." value={form.link_hh || ''} onChange={e => setForm(f => ({ ...f, link_hh: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ob-portfolio">GitHub / Портфолио</Label>
                <Input id="ob-portfolio" type="url" placeholder="https://github.com/..." value={form.link_portfolio || ''} onChange={e => setForm(f => ({ ...f, link_portfolio: e.target.value }))} />
              </div>
            </div>

            {/* Образование */}
            <div className="space-y-4">
              <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Образование</h2>
              {[
                { id: 'ob-uni',  label: 'Вуз',           field: 'university',      ph: 'МГУ' },
                { id: 'ob-fac',  label: 'Факультет',      field: 'faculty',         ph: 'ВМК' },
                { id: 'ob-spec', label: 'Специальность',  field: 'speciality',      ph: 'Прикладная математика' },
                { id: 'ob-year', label: 'Год / курс',     field: 'graduation_year', ph: '2026 или 3 курс' },
              ].map(({ id, label, field, ph }) => (
                <div key={id} className="space-y-1.5">
                  <Label htmlFor={id}>{label}</Label>
                  <Input id={id} placeholder={ph} value={(form as Record<string, unknown>)[field] as string || ''} onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))} />
                </div>
              ))}
            </div>

            {/* Языки */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Языки</h2>
                <Button type="button" variant="outline" size="sm" onClick={addLanguage} className="gap-1">
                  <Plus className="w-3 h-3" /> Добавить
                </Button>
              </div>
              {(form.languages || []).map((lang, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <Input placeholder="Английский" value={lang.language} onChange={e => updateLanguage(i, 'language', e.target.value)} className="flex-1" />
                  <select
                    className="h-8 w-24 rounded-lg border border-input bg-transparent px-2 py-1 text-sm outline-none"
                    value={lang.level}
                    onChange={e => updateLanguage(i, 'level', e.target.value)}
                  >
                    {LANGUAGE_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                  <Button type="button" variant="ghost" size="icon" onClick={() => removeLanguage(i)} className="text-muted-foreground hover:text-destructive shrink-0">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}
              {(form.languages || []).length === 0 && (
                <p className="text-sm text-muted-foreground">Нажмите «Добавить»</p>
              )}
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="button" variant="outline" onClick={handleSkip} className="flex-1 h-11">Пропустить</Button>
              <Button type="button" onClick={handleSave} disabled={loading} className="flex-1 h-11">
                {loading ? 'Сохраняем...' : 'Сохранить'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
