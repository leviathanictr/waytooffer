'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { auth } from '@/lib/api'
import { getUserId, saveTokens } from '@/lib/auth'
import { CheckCircle } from 'lucide-react'

export default function VerifyPage() {
  const router = useRouter()
  const [userId, setUserId] = useState<string | null>(null)
  const [emailCode, setEmailCode] = useState('')
  const [phoneCode, setPhoneCode] = useState('')
  const [emailVerified, setEmailVerified] = useState(false)
  const [phoneVerified, setPhoneVerified] = useState(false)
  const [emailLoading, setEmailLoading] = useState(false)
  const [phoneLoading, setPhoneLoading] = useState(false)
  const [emailCooldown, setEmailCooldown] = useState(0)
  const [phoneCooldown, setPhoneCooldown] = useState(0)
  const emailTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const phoneTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const id = getUserId()
    if (!id) {
      router.push('/register')
      return
    }
    setUserId(id)
  }, [router])

  useEffect(() => {
    if (emailVerified && phoneVerified) {
      toast.success('Аккаунт подтверждён!')
      setTimeout(() => router.push('/onboarding'), 1000)
    }
  }, [emailVerified, phoneVerified, router])

  function startCooldown(
    setter: React.Dispatch<React.SetStateAction<number>>,
    timerRef: React.MutableRefObject<ReturnType<typeof setInterval> | null>
  ) {
    setter(60)
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setter(prev => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current)
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }

  async function handleVerifyEmail(e: React.FormEvent) {
    e.preventDefault()
    if (!userId || !emailCode.trim()) return
    setEmailLoading(true)
    try {
      await auth.verifyEmail({ user_id: userId, code: emailCode.trim() })
      setEmailVerified(true)
      toast.success('Email подтверждён!')
    } catch {
      toast.error('Неверный код. Попробуйте ещё раз.')
    } finally {
      setEmailLoading(false)
    }
  }

  async function handleVerifyPhone(e: React.FormEvent) {
    e.preventDefault()
    if (!userId || !phoneCode.trim()) return
    setPhoneLoading(true)
    try {
      await auth.verifyPhone({ user_id: userId, code: phoneCode.trim() })
      setPhoneVerified(true)
      toast.success('Телефон подтверждён!')
    } catch {
      toast.error('Неверный код. Попробуйте ещё раз.')
    } finally {
      setPhoneLoading(false)
    }
  }

  async function handleResendEmail() {
    if (!userId || emailCooldown > 0) return
    try {
      await auth.resendVerification({ user_id: userId, type: 'email' })
      toast.success('Код отправлен на email')
      startCooldown(setEmailCooldown, emailTimerRef)
    } catch {
      toast.error('Не удалось отправить код')
    }
  }

  async function handleResendPhone() {
    if (!userId || phoneCooldown > 0) return
    try {
      await auth.resendVerification({ user_id: userId, type: 'phone' })
      toast.success('Код отправлен на телефон')
      startCooldown(setPhoneCooldown, phoneTimerRef)
    } catch {
      toast.error('Не удалось отправить код')
    }
  }

  async function handleSkip() {
    // Try to proceed even without verification — login may handle this
    router.push('/onboarding')
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-muted/30">
      <div className="w-full max-w-sm space-y-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-primary mb-1">WayToOffer</div>
          <h1 className="text-xl font-semibold">Подтверждение аккаунта</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Мы отправили коды подтверждения на ваш email и телефон
          </p>
        </div>

        {/* Email verification */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Подтверждение Email</CardTitle>
              {emailVerified && (
                <div className="flex items-center gap-1 text-green-600 text-sm font-medium">
                  <CheckCircle className="w-4 h-4" />
                  Подтверждён
                </div>
              )}
            </div>
            <CardDescription>Введите 6-значный код из письма</CardDescription>
          </CardHeader>
          <CardContent>
            {!emailVerified ? (
              <form onSubmit={handleVerifyEmail} className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="emailCode">Код из email</Label>
                  <Input
                    id="emailCode"
                    type="text"
                    inputMode="numeric"
                    placeholder="000000"
                    maxLength={6}
                    value={emailCode}
                    onChange={e => setEmailCode(e.target.value.replace(/\D/g, ''))}
                  />
                </div>
                <div className="flex gap-2">
                  <Button type="submit" disabled={emailLoading || emailCode.length < 6} className="flex-1">
                    {emailLoading ? 'Проверяем...' : 'Подтвердить'}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={emailCooldown > 0}
                    onClick={handleResendEmail}
                  >
                    {emailCooldown > 0 ? `${emailCooldown}с` : 'Повторно'}
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

        {/* Phone verification */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Подтверждение телефона</CardTitle>
              {phoneVerified && (
                <div className="flex items-center gap-1 text-green-600 text-sm font-medium">
                  <CheckCircle className="w-4 h-4" />
                  Подтверждён
                </div>
              )}
            </div>
            <CardDescription>Введите 6-значный код из SMS</CardDescription>
          </CardHeader>
          <CardContent>
            {!phoneVerified ? (
              <form onSubmit={handleVerifyPhone} className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="phoneCode">Код из SMS</Label>
                  <Input
                    id="phoneCode"
                    type="text"
                    inputMode="numeric"
                    placeholder="000000"
                    maxLength={6}
                    value={phoneCode}
                    onChange={e => setPhoneCode(e.target.value.replace(/\D/g, ''))}
                  />
                </div>
                <div className="flex gap-2">
                  <Button type="submit" disabled={phoneLoading || phoneCode.length < 6} className="flex-1">
                    {phoneLoading ? 'Проверяем...' : 'Подтвердить'}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={phoneCooldown > 0}
                    onClick={handleResendPhone}
                  >
                    {phoneCooldown > 0 ? `${phoneCooldown}с` : 'Повторно'}
                  </Button>
                </div>
              </form>
            ) : (
              <div className="flex items-center gap-2 text-green-600 py-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Телефон успешно подтверждён</span>
              </div>
            )}
          </CardContent>
        </Card>

        <button
          onClick={handleSkip}
          className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors py-2 text-center"
        >
          Пропустить подтверждение →
        </button>
      </div>
    </div>
  )
}
