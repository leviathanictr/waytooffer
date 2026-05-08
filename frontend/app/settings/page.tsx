'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { profile as profileApi, auth } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import { Plus, Trash2, Loader2 } from 'lucide-react'
import type { Profile } from '@/lib/types'

const LANGUAGE_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'Родной']

export default function SettingsPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<string>('profile')

  // Profile state
  const [profileLoading, setProfileLoading] = useState(true)
  const [profileSaving, setProfileSaving] = useState(false)
  const [form, setForm] = useState<Profile>({
    name: '', city: '', phone: '', email: '',
    link_hh: '', link_portfolio: '',
    university: '', faculty: '', speciality: '', graduation_year: '',
    languages: [],
  })

  // Password state
  const [passwordForm, setPasswordForm] = useState({
    old_password: '', new_password: '', new_password_confirm: '',
  })
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordError, setPasswordError] = useState('')

  // Email state
  const [emailForm, setEmailForm] = useState({ new_email: '', password: '' })
  const [emailLoading, setEmailLoading] = useState(false)
  const [emailError, setEmailError] = useState('')

  // Phone state
  const [phoneForm, setPhoneForm] = useState({ new_phone: '+7', password: '' })
  const [phoneLoading, setPhoneLoading] = useState(false)
  const [phoneError, setPhoneError] = useState('')

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    loadProfile()
  }, [router])

  async function loadProfile() {
    setProfileLoading(true)
    try {
      const { data } = await profileApi.get()
      setForm({
        name: data.name || '',
        city: data.city || '',
        phone: data.phone || '',
        email: data.email || '',
        link_hh: data.link_hh || '',
        link_portfolio: data.link_portfolio || '',
        university: data.university || '',
        faculty: data.faculty || '',
        speciality: data.speciality || '',
        graduation_year: data.graduation_year || '',
        languages: data.languages || [],
      })
    } catch {
      toast.error('Не удалось загрузить профиль')
    } finally {
      setProfileLoading(false)
    }
  }

  async function handleSaveProfile() {
    setProfileSaving(true)
    try {
      await profileApi.update(form)
      toast.success('Данные сохранены!')
    } catch {
      toast.error('Ошибка сохранения данных')
    } finally {
      setProfileSaving(false)
    }
  }

  function addLanguage() {
    setForm(f => ({ ...f, languages: [...(f.languages || []), { language: '', level: 'B1' }] }))
  }

  function removeLanguage(index: number) {
    setForm(f => ({ ...f, languages: (f.languages || []).filter((_, i) => i !== index) }))
  }

  function updateLanguage(index: number, field: 'language' | 'level', value: string) {
    setForm(f => ({
      ...f,
      languages: (f.languages || []).map((lang, i) => i === index ? { ...lang, [field]: value } : lang),
    }))
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    setPasswordError('')
    if (passwordForm.new_password.length < 8) {
      setPasswordError('Новый пароль должен содержать минимум 8 символов')
      return
    }
    if (passwordForm.new_password !== passwordForm.new_password_confirm) {
      setPasswordError('Пароли не совпадают')
      return
    }
    setPasswordLoading(true)
    try {
      await auth.changePassword(passwordForm)
      toast.success('Пароль успешно изменён!')
      setPasswordForm({ old_password: '', new_password: '', new_password_confirm: '' })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setPasswordError(detail || 'Неверный текущий пароль')
    } finally {
      setPasswordLoading(false)
    }
  }

  async function handleChangeEmail(e: React.FormEvent) {
    e.preventDefault()
    setEmailError('')
    if (!emailForm.new_email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      setEmailError('Введите корректный email')
      return
    }
    setEmailLoading(true)
    try {
      await auth.changeEmail(emailForm)
      toast.success('Email успешно изменён!')
      setEmailForm({ new_email: '', password: '' })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setEmailError(detail || 'Ошибка изменения email')
    } finally {
      setEmailLoading(false)
    }
  }

  async function handleChangePhone(e: React.FormEvent) {
    e.preventDefault()
    setPhoneError('')
    if (!phoneForm.new_phone.match(/^\+7\d{10}$/)) {
      setPhoneError('Введите номер в формате +7XXXXXXXXXX')
      return
    }
    setPhoneLoading(true)
    try {
      await auth.changePhone(phoneForm)
      toast.success('Телефон успешно изменён!')
      setPhoneForm({ new_phone: '+7', password: '' })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setPhoneError(detail || 'Ошибка изменения телефона')
    } finally {
      setPhoneLoading(false)
    }
  }

  return (
    <div className="flex-1 py-6 px-4">
      <div className="max-w-lg mx-auto">
        <h1 className="text-2xl font-bold mb-6">Настройки</h1>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(String(v))}>
          <TabsList className="w-full mb-6">
            <TabsTrigger value="profile" className="flex-1">Личные данные</TabsTrigger>
            <TabsTrigger value="security" className="flex-1">Безопасность</TabsTrigger>
          </TabsList>

          {/* Profile tab */}
          <TabsContent value="profile">
            {profileLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
              </div>
            ) : (
              <Card>
                <CardContent className="pt-6 space-y-5">
                  {/* Personal */}
                  <div className="space-y-4">
                    <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                      Личные данные
                    </h2>

                    <div className="space-y-1.5">
                      <Label htmlFor="s-name">Имя и фамилия</Label>
                      <Input
                        id="s-name"
                        placeholder="Иван Иванов"
                        value={form.name || ''}
                        onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="s-city">Город</Label>
                      <Input
                        id="s-city"
                        placeholder="Москва"
                        value={form.city || ''}
                        onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="s-phone">Телефон</Label>
                      <Input
                        id="s-phone"
                        type="tel"
                        placeholder="+7XXXXXXXXXX"
                        value={form.phone || ''}
                        onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="s-email">Email</Label>
                      <Input
                        id="s-email"
                        type="email"
                        placeholder="you@example.com"
                        value={form.email || ''}
                        onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                      />
                    </div>
                  </div>

                  <Separator />

                  {/* Links */}
                  <div className="space-y-4">
                    <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                      Ссылки
                    </h2>

                    <div className="space-y-1.5">
                      <Label htmlFor="s-hh">Ссылка на hh.ru</Label>
                      <Input
                        id="s-hh"
                        type="url"
                        placeholder="https://hh.ru/resume/..."
                        value={form.link_hh || ''}
                        onChange={e => setForm(f => ({ ...f, link_hh: e.target.value }))}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="s-portfolio">Ссылка на GitHub / портфолио</Label>
                      <Input
                        id="s-portfolio"
                        type="url"
                        placeholder="https://github.com/..."
                        value={form.link_portfolio || ''}
                        onChange={e => setForm(f => ({ ...f, link_portfolio: e.target.value }))}
                      />
                    </div>
                  </div>

                  <Separator />

                  {/* Education */}
                  <div className="space-y-4">
                    <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                      Образование
                    </h2>

                    <div className="space-y-1.5">
                      <Label htmlFor="s-uni">Вуз</Label>
                      <Input
                        id="s-uni"
                        placeholder="МГУ им. М.В. Ломоносова"
                        value={form.university || ''}
                        onChange={e => setForm(f => ({ ...f, university: e.target.value }))}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="s-faculty">Факультет</Label>
                      <Input
                        id="s-faculty"
                        placeholder="Факультет вычислительной математики"
                        value={form.faculty || ''}
                        onChange={e => setForm(f => ({ ...f, faculty: e.target.value }))}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="s-spec">Специальность</Label>
                      <Input
                        id="s-spec"
                        placeholder="Прикладная математика"
                        value={form.speciality || ''}
                        onChange={e => setForm(f => ({ ...f, speciality: e.target.value }))}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="s-year">Год окончания / курс</Label>
                      <Input
                        id="s-year"
                        placeholder="2026 или 3 курс"
                        value={form.graduation_year || ''}
                        onChange={e => setForm(f => ({ ...f, graduation_year: e.target.value }))}
                      />
                    </div>
                  </div>

                  <Separator />

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
                      <div key={index} className="flex gap-2 items-center">
                        <Input
                          placeholder="Английский"
                          value={lang.language}
                          onChange={e => updateLanguage(index, 'language', e.target.value)}
                          className="flex-1"
                        />
                        <select
                          className="h-8 w-24 rounded-lg border border-input bg-transparent px-2 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50"
                          value={lang.level}
                          onChange={e => updateLanguage(index, 'level', e.target.value)}
                        >
                          {LANGUAGE_LEVELS.map(level => (
                            <option key={level} value={level}>{level}</option>
                          ))}
                        </select>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeLanguage(index)}
                          className="text-muted-foreground hover:text-destructive shrink-0"
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

                  <Button
                    onClick={handleSaveProfile}
                    disabled={profileSaving}
                    className="w-full h-11"
                  >
                    {profileSaving ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        Сохраняем...
                      </>
                    ) : (
                      'Сохранить'
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Security tab */}
          <TabsContent value="security">
            <div className="space-y-4">
              {/* Change password */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Сменить пароль</CardTitle>
                  <CardDescription>Введите текущий пароль и придумайте новый</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleChangePassword} className="space-y-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="old-password">Старый пароль</Label>
                      <Input
                        id="old-password"
                        type="password"
                        placeholder="Текущий пароль"
                        value={passwordForm.old_password}
                        onChange={e => setPasswordForm(f => ({ ...f, old_password: e.target.value }))}
                        autoComplete="current-password"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="new-password">Новый пароль</Label>
                      <Input
                        id="new-password"
                        type="password"
                        placeholder="Минимум 8 символов"
                        value={passwordForm.new_password}
                        onChange={e => setPasswordForm(f => ({ ...f, new_password: e.target.value }))}
                        autoComplete="new-password"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="confirm-password">Повтор нового пароля</Label>
                      <Input
                        id="confirm-password"
                        type="password"
                        placeholder="Повторите новый пароль"
                        value={passwordForm.new_password_confirm}
                        onChange={e => setPasswordForm(f => ({ ...f, new_password_confirm: e.target.value }))}
                        autoComplete="new-password"
                      />
                    </div>
                    {passwordError && (
                      <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                        {passwordError}
                      </p>
                    )}
                    <Button type="submit" disabled={passwordLoading} className="w-full">
                      {passwordLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                          Меняем...
                        </>
                      ) : (
                        'Сменить пароль'
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>

              {/* Change email */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Сменить email</CardTitle>
                  <CardDescription>Для смены email потребуется текущий пароль</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleChangeEmail} className="space-y-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="new-email">Новый email</Label>
                      <Input
                        id="new-email"
                        type="email"
                        placeholder="new@example.com"
                        value={emailForm.new_email}
                        onChange={e => setEmailForm(f => ({ ...f, new_email: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="email-password">Текущий пароль</Label>
                      <Input
                        id="email-password"
                        type="password"
                        placeholder="Текущий пароль"
                        value={emailForm.password}
                        onChange={e => setEmailForm(f => ({ ...f, password: e.target.value }))}
                        autoComplete="current-password"
                      />
                    </div>
                    {emailError && (
                      <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                        {emailError}
                      </p>
                    )}
                    <Button type="submit" disabled={emailLoading} className="w-full">
                      {emailLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                          Меняем...
                        </>
                      ) : (
                        'Сменить email'
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>

              {/* Change phone */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Сменить телефон</CardTitle>
                  <CardDescription>Для смены телефона потребуется текущий пароль</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleChangePhone} className="space-y-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="new-phone">Новый телефон</Label>
                      <Input
                        id="new-phone"
                        type="tel"
                        placeholder="+7XXXXXXXXXX"
                        value={phoneForm.new_phone}
                        onChange={e => {
                          let v = e.target.value
                          if (!v.startsWith('+7')) v = '+7' + v.replace(/^\+7?/, '')
                          setPhoneForm(f => ({ ...f, new_phone: v }))
                        }}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="phone-password">Текущий пароль</Label>
                      <Input
                        id="phone-password"
                        type="password"
                        placeholder="Текущий пароль"
                        value={phoneForm.password}
                        onChange={e => setPhoneForm(f => ({ ...f, password: e.target.value }))}
                        autoComplete="current-password"
                      />
                    </div>
                    {phoneError && (
                      <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                        {phoneError}
                      </p>
                    )}
                    <Button type="submit" disabled={phoneLoading} className="w-full">
                      {phoneLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                          Меняем...
                        </>
                      ) : (
                        'Сменить телефон'
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
