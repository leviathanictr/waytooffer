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
import type { Profile, EducationItem } from '@/lib/types'

const LANGUAGE_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'Родной']
const emptyEdu = (): EducationItem => ({ university: '', faculty: '', speciality: '', year: '', achievements: '' })

export default function SettingsPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<string>('profile')
  const [profileLoading, setProfileLoading] = useState(true)
  const [profileSaving, setProfileSaving] = useState(false)
  const [form, setForm] = useState<Profile>({
    name: '', city: '', phone: '', email: '',
    link_hh: '', link_portfolio: '',
    university: '', faculty: '', speciality: '', graduation_year: '',
    languages: [], links: [], education_list: [],
  })
  const [passwordForm, setPasswordForm] = useState({ old_password: '', new_password: '', new_password_confirm: '' })
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordError, setPasswordError] = useState('')
  const [emailForm, setEmailForm] = useState({ new_email: '', password: '' })
  const [emailLoading, setEmailLoading] = useState(false)
  const [emailError, setEmailError] = useState('')
  const [phoneForm, setPhoneForm] = useState({ new_phone: '+7', password: '' })
  const [phoneLoading, setPhoneLoading] = useState(false)
  const [phoneError, setPhoneError] = useState('')

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    loadProfile()
  }, [router])

  async function loadProfile() {
    setProfileLoading(true)
    try {
      const { data } = await profileApi.get()
      setForm({
        name: data.name || '', city: data.city || '',
        phone: data.phone || '', email: data.email || '',
        link_hh: data.link_hh || '', link_portfolio: data.link_portfolio || '',
        university: data.university || '', faculty: data.faculty || '',
        speciality: data.speciality || '', graduation_year: data.graduation_year || '',
        languages: data.languages || [],
        links: data.links || [],
        education_list: data.education_list || [],
      })
    } catch { toast.error('Не удалось загрузить профиль') }
    finally { setProfileLoading(false) }
  }

  async function handleSaveProfile() {
    setProfileSaving(true)
    try { await profileApi.update(form); toast.success('Данные сохранены!') }
    catch { toast.error('Ошибка сохранения данных') }
    finally { setProfileSaving(false) }
  }

  const addLanguage = () => setForm(f => ({ ...f, languages: [...(f.languages || []), { language: '', level: 'B1' }] }))
  const removeLanguage = (i: number) => setForm(f => ({ ...f, languages: (f.languages || []).filter((_, idx) => idx !== i) }))
  const updateLanguage = (i: number, field: 'language' | 'level', val: string) =>
    setForm(f => ({ ...f, languages: (f.languages || []).map((l, idx) => idx === i ? { ...l, [field]: val } : l) }))

  const addLink = () => setForm(f => ({ ...f, links: [...(f.links || []), ''] }))
  const removeLink = (i: number) => setForm(f => ({ ...f, links: (f.links || []).filter((_, idx) => idx !== i) }))
  const updateLink = (i: number, val: string) => setForm(f => ({ ...f, links: (f.links || []).map((l, idx) => idx === i ? val : l) }))

  const addEdu = () => setForm(f => ({ ...f, education_list: [...(f.education_list || []), emptyEdu()] }))
  const removeEdu = (i: number) => setForm(f => ({ ...f, education_list: (f.education_list || []).filter((_, idx) => idx !== i) }))
  const updateEdu = (i: number, field: keyof EducationItem, val: string) =>
    setForm(f => ({ ...f, education_list: (f.education_list || []).map((e, idx) => idx === i ? { ...e, [field]: val } : e) }))

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault(); setPasswordError('')
    if (passwordForm.new_password.length < 8) { setPasswordError('Минимум 8 символов'); return }
    if (passwordForm.new_password !== passwordForm.new_password_confirm) { setPasswordError('Пароли не совпадают'); return }
    setPasswordLoading(true)
    try { await auth.changePassword(passwordForm); toast.success('Пароль изменён!'); setPasswordForm({ old_password: '', new_password: '', new_password_confirm: '' }) }
    catch (err: unknown) {
      const raw = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setPasswordError((Array.isArray(raw) ? raw[0]?.msg : raw as string) || 'Неверный текущий пароль')
    } finally { setPasswordLoading(false) }
  }

  async function handleChangeEmail(e: React.FormEvent) {
    e.preventDefault(); setEmailError('')
    if (!emailForm.new_email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) { setEmailError('Введите корректный email'); return }
    setEmailLoading(true)
    try { await auth.changeEmail(emailForm); toast.success('Email изменён!'); setEmailForm({ new_email: '', password: '' }) }
    catch (err: unknown) {
      const raw = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setEmailError((Array.isArray(raw) ? raw[0]?.msg : raw as string) || 'Ошибка')
    } finally { setEmailLoading(false) }
  }

  async function handleChangePhone(e: React.FormEvent) {
    e.preventDefault(); setPhoneError('')
    if (!phoneForm.new_phone.match(/^\+7\d{10}$/)) { setPhoneError('Формат: +7XXXXXXXXXX'); return }
    setPhoneLoading(true)
    try { await auth.changePhone(phoneForm); toast.success('Телефон изменён!'); setPhoneForm({ new_phone: '+7', password: '' }) }
    catch (err: unknown) {
      const raw = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setPhoneError((Array.isArray(raw) ? raw[0]?.msg : raw as string) || 'Ошибка')
    } finally { setPhoneLoading(false) }
  }

  return (
    <div className="flex-1 py-6 px-4">
      <div className="max-w-lg mx-auto">
        <h1 className="text-2xl font-bold mb-6">Настройки</h1>
        <Tabs value={activeTab} onValueChange={v => setActiveTab(String(v))}>
          <TabsList className="w-full mb-6">
            <TabsTrigger value="profile" className="flex-1">Личные данные</TabsTrigger>
            <TabsTrigger value="security" className="flex-1">Безопасность</TabsTrigger>
          </TabsList>

          <TabsContent value="profile">
            {profileLoading ? (
              <div className="flex items-center justify-center py-16"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>
            ) : (
              <Card>
                <CardContent className="pt-6 space-y-5">

                  {/* Personal */}
                  <div className="space-y-4">
                    <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Личные данные</h2>
                    {(['name', 'city'] as const).map(field => (
                      <div key={field} className="space-y-1.5">
                        <Label>{field === 'name' ? 'Имя и фамилия' : 'Город'}</Label>
                        <Input placeholder={field === 'name' ? 'Иван Иванов' : 'Москва'} value={form[field] || ''} onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))} />
                      </div>
                    ))}
                    <div className="space-y-1.5">
                      <Label>Телефон</Label>
                      <Input type="tel" placeholder="+7XXXXXXXXXX" value={form.phone || ''} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
                    </div>
                    <div className="space-y-1.5">
                      <Label>Email</Label>
                      <Input type="email" placeholder="you@example.com" value={form.email || ''} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
                    </div>
                  </div>

                  <Separator />

                  {/* Links */}
                  <div className="space-y-3">
                    <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Ссылки</h2>
                    <div className="space-y-1.5">
                      <Label>hh.ru</Label>
                      <Input type="url" placeholder="https://hh.ru/resume/..." value={form.link_hh || ''} onChange={e => setForm(f => ({ ...f, link_hh: e.target.value }))} />
                    </div>
                    <div className="space-y-1.5">
                      <Label>GitHub / Портфолио</Label>
                      <Input type="url" placeholder="https://github.com/..." value={form.link_portfolio || ''} onChange={e => setForm(f => ({ ...f, link_portfolio: e.target.value }))} />
                    </div>
                    {(form.links || []).map((link, i) => (
                      <div key={i} className="flex gap-2 items-center">
                        <Input type="url" placeholder="https://..." value={link} onChange={e => updateLink(i, e.target.value)} className="flex-1" />
                        <Button type="button" variant="ghost" size="icon" onClick={() => removeLink(i)} className="text-muted-foreground hover:text-destructive shrink-0">
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                    <Button type="button" variant="outline" size="sm" onClick={addLink} className="gap-1">
                      <Plus className="w-3 h-3" /> Ещё ссылка
                    </Button>
                  </div>

                  <Separator />

                  {/* Education */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Образование</h2>
                      <Button type="button" variant="outline" size="sm" onClick={addEdu} className="gap-1">
                        <Plus className="w-3 h-3" /> Добавить
                      </Button>
                    </div>

                    {/* Primary */}
                    <div className="space-y-3 p-3 border rounded-xl">
                      <p className="text-xs text-muted-foreground font-medium">Основное</p>
                      {([['university','Вуз','МГУ'],['faculty','Факультет','ВМК'],['speciality','Специальность','Прикладная математика'],['graduation_year','Год / курс','2026']] as const).map(([field, label, ph]) => (
                        <div key={field} className="space-y-1">
                          <Label className="text-xs">{label}</Label>
                          <Input placeholder={ph} value={form[field] || ''} onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))} className="h-8 text-sm" />
                        </div>
                      ))}
                    </div>

                    {/* Additional */}
                    {(form.education_list || []).map((edu, i) => (
                      <div key={i} className="space-y-3 p-3 border rounded-xl">
                        <div className="flex items-center justify-between">
                          <p className="text-xs text-muted-foreground font-medium">Доп. образование {i + 1}</p>
                          <Button type="button" variant="ghost" size="icon" onClick={() => removeEdu(i)} className="text-muted-foreground hover:text-destructive h-6 w-6">
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                        {([['university','Вуз','Название'],['faculty','Факультет','Факультет'],['speciality','Специальность','Специальность'],['year','Год / курс','2026'],['achievements','Достижения','Красный диплом...']] as const).map(([field, label, ph]) => (
                          <div key={field} className="space-y-1">
                            <Label className="text-xs">{label}</Label>
                            <Input placeholder={ph} value={edu[field]} onChange={e => updateEdu(i, field, e.target.value)} className="h-8 text-sm" />
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>

                  <Separator />

                  {/* Languages */}
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
                        <select className="h-8 w-24 rounded-lg border border-input bg-transparent px-2 py-1 text-sm outline-none" value={lang.level} onChange={e => updateLanguage(i, 'level', e.target.value)}>
                          {LANGUAGE_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                        </select>
                        <Button type="button" variant="ghost" size="icon" onClick={() => removeLanguage(i)} className="text-muted-foreground hover:text-destructive shrink-0">
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                    {(form.languages || []).length === 0 && <p className="text-sm text-muted-foreground">Нажмите «Добавить»</p>}
                  </div>

                  <Button onClick={handleSaveProfile} disabled={profileSaving} className="w-full h-11">
                    {profileSaving ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Сохраняем...</> : 'Сохранить'}
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="security">
            <div className="space-y-4">
              {/* Password */}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-base">Сменить пароль</CardTitle><CardDescription>Введите текущий пароль и придумайте новый</CardDescription></CardHeader>
                <CardContent>
                  <form onSubmit={handleChangePassword} className="space-y-4">
                    <div className="space-y-1.5"><Label>Старый пароль</Label><Input type="password" placeholder="Текущий пароль" value={passwordForm.old_password} onChange={e => setPasswordForm(f => ({ ...f, old_password: e.target.value }))} autoComplete="current-password" /></div>
                    <div className="space-y-1.5"><Label>Новый пароль</Label><Input type="password" placeholder="Минимум 8 символов" value={passwordForm.new_password} onChange={e => setPasswordForm(f => ({ ...f, new_password: e.target.value }))} autoComplete="new-password" /></div>
                    <div className="space-y-1.5"><Label>Повтор</Label><Input type="password" placeholder="Повторите" value={passwordForm.new_password_confirm} onChange={e => setPasswordForm(f => ({ ...f, new_password_confirm: e.target.value }))} autoComplete="new-password" /></div>
                    {passwordError && <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">{passwordError}</p>}
                    <Button type="submit" disabled={passwordLoading} className="w-full">{passwordLoading ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Меняем...</> : 'Сменить пароль'}</Button>
                  </form>
                </CardContent>
              </Card>

              {/* Email */}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-base">Сменить email</CardTitle><CardDescription>Потребуется текущий пароль</CardDescription></CardHeader>
                <CardContent>
                  <form onSubmit={handleChangeEmail} className="space-y-4">
                    <div className="space-y-1.5"><Label>Новый email</Label><Input type="email" placeholder="new@example.com" value={emailForm.new_email} onChange={e => setEmailForm(f => ({ ...f, new_email: e.target.value }))} /></div>
                    <div className="space-y-1.5"><Label>Текущий пароль</Label><Input type="password" placeholder="Пароль" value={emailForm.password} onChange={e => setEmailForm(f => ({ ...f, password: e.target.value }))} autoComplete="current-password" /></div>
                    {emailError && <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">{emailError}</p>}
                    <Button type="submit" disabled={emailLoading} className="w-full">{emailLoading ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Меняем...</> : 'Сменить email'}</Button>
                  </form>
                </CardContent>
              </Card>

              {/* Phone */}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-base">Сменить телефон</CardTitle><CardDescription>Потребуется текущий пароль</CardDescription></CardHeader>
                <CardContent>
                  <form onSubmit={handleChangePhone} className="space-y-4">
                    <div className="space-y-1.5"><Label>Новый телефон</Label><Input type="tel" placeholder="+7XXXXXXXXXX" value={phoneForm.new_phone} onChange={e => { let v = e.target.value.replace(/\s/g,''); if (!v.startsWith('+7')) v='+7'; setPhoneForm(f => ({ ...f, new_phone: v })) }} /></div>
                    <div className="space-y-1.5"><Label>Текущий пароль</Label><Input type="password" placeholder="Пароль" value={phoneForm.password} onChange={e => setPhoneForm(f => ({ ...f, password: e.target.value }))} autoComplete="current-password" /></div>
                    {phoneError && <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">{phoneError}</p>}
                    <Button type="submit" disabled={phoneLoading} className="w-full">{phoneLoading ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />Меняем...</> : 'Сменить телефон'}</Button>
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
