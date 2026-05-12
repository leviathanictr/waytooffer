'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ResumePreview } from '@/components/resume-preview'
import { session as sessionApi } from '@/lib/api'
import { isAuthenticated, getAccessToken } from '@/lib/auth'

async function sendAndPoll(
  sessionId: string,
  text: string,
  onContent: (content: string) => void,
): Promise<{ is_complete: boolean }> {
  const token = getAccessToken()
  const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }

  const postRes = await fetch(`${base}/session/${sessionId}/message`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ text }),
  })
  if (!postRes.ok) throw new Error(`HTTP ${postRes.status}`)
  const { job_id } = await postRes.json()

  return new Promise((resolve, reject) => {
    const interval = setInterval(async () => {
      try {
        const pollRes = await fetch(`${base}/session/${sessionId}/poll/${job_id}`, { headers })
        if (!pollRes.ok) { clearInterval(interval); reject(new Error(`Poll HTTP ${pollRes.status}`)); return }
        const data = await pollRes.json()
        // Never show intermediate content — only set message once when fully done
        // (prevents partial/full JSON from leaking into chat during streaming)
        if (data.status === 'done') {
          clearInterval(interval)
          // Only show content for normal replies (not JSON completion blobs)
          if (!data.is_complete && data.content) onContent(data.content)
          resolve({ is_complete: data.is_complete })
          return
        }
        if (data.status === 'error') { clearInterval(interval); reject(new Error(data.error || 'AI error')) }
      } catch (e) { clearInterval(interval); reject(e) }
    }, 600)
  })
}
import { Send, Download, RotateCcw, Loader2 } from 'lucide-react'
import type { Session, Resume, ChatMessage } from '@/lib/types'

type PageState = 'input' | 'chat' | 'done'

async function downloadPdf(resumeId: string) {
  const token = getAccessToken()
  const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/resume/${resumeId}/pdf`
  try {
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) throw new Error('Failed to fetch PDF')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'resume.pdf'
    a.click()
    URL.revokeObjectURL(a.href)
  } catch {
    toast.error('Ошибка скачивания PDF')
  }
}

export default function HomePage() {
  const router = useRouter()
  const [pageState, setPageState] = useState<PageState>('input')
  const [vacancyUrl, setVacancyUrl] = useState('')
  const [vacancyText, setVacancyText] = useState('')
  const [inputTab, setInputTab] = useState<string>('url')
  const [startLoading, setStartLoading] = useState(false)

  const [currentSession, setCurrentSession] = useState<Session | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [messageInput, setMessageInput] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [generating, setGenerating] = useState(false)

  const [resume, setResume] = useState<Resume | null>(null)

  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
    }
  }, [router])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, aiLoading])

  async function handleStart() {
    const url = vacancyUrl.trim()
    const text = vacancyText.trim()

    if (inputTab === 'url' && !url) {
      toast.error('Введите ссылку на вакансию')
      return
    }
    if (inputTab === 'text' && !text) {
      toast.error('Вставьте текст вакансии')
      return
    }

    setStartLoading(true)
    try {
      const payload = inputTab === 'url' ? { vacancy_url: url } : { vacancy_text: text }
      const { data } = await sessionApi.create(payload)
      setCurrentSession(data)
      setMessages([
        {
          role: 'assistant',
          content: data.vacancy_summary
            ? `Отлично! Я проанализировал вакансию: "${data.vacancy_summary}". Давай начнём собирать данные для резюме. Расскажи о своём опыте — какие проекты, стажировки или участие в чемпионатах у тебя были?`
            : 'Привет! Я проанализировал вакансию. Давай начнём составлять резюме. Расскажи о своём опыте — какие проекты, стажировки или участие в чемпионатах у тебя были?',
        },
      ])
      setPageState('chat')
    } catch {
      toast.error('Не удалось создать сессию. Проверьте ссылку или попробуйте ещё раз.')
    } finally {
      setStartLoading(false)
    }
  }

  async function triggerGenerate() {
    if (!currentSession) return
    setGenerating(true)
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const token = getAccessToken()
      const headers = { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }

      const startRes = await fetch(`${base}/session/${currentSession.session_id}/generate`, { method: 'POST', headers })
      if (!startRes.ok) throw new Error(`HTTP ${startRes.status}`)
      const { job_id } = await startRes.json()

      await new Promise<void>((resolve, reject) => {
        const deadline = Date.now() + 5 * 60 * 1000 // 5 min timeout
        const iv = setInterval(async () => {
          if (Date.now() > deadline) { clearInterval(iv); reject(new Error('Timeout')); return }
          try {
            const r = await fetch(`${base}/session/${currentSession.session_id}/generate-poll/${job_id}`, { headers })
            if (!r.ok) { clearInterval(iv); reject(new Error(`Poll ${r.status}`)); return }
            const d = await r.json()
            if (d.status === 'done') { clearInterval(iv); setResume(d.result); setPageState('done'); resolve() }
            if (d.status === 'error') { clearInterval(iv); reject(new Error(d.error || 'Generate error')) }
          } catch (e) { clearInterval(iv); reject(e) }
        }, 1000)
      })
    } catch {
      toast.error('Ошибка генерации резюме. Попробуйте ещё раз.')
    } finally {
      setGenerating(false)
    }
  }

  async function handleSendMessage() {
    if (!currentSession || !messageInput.trim() || aiLoading) return

    const text = messageInput.trim()
    setMessageInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }, { role: 'assistant', content: '' }])
    setAiLoading(true)

    try {
      const { is_complete } = await sendAndPoll(
        currentSession.session_id,
        text,
        (content) => setMessages(prev => {
          const next = [...prev]
          next[next.length - 1] = { role: 'assistant', content }
          return next
        }),
      )

      if (is_complete) {
        // Remove last assistant message entirely (contains raw JSON schema)
        setMessages(prev => {
          const next = [...prev]
          if (next.length > 0 && next[next.length - 1].role === 'assistant') {
            next.pop()
          }
          return next
        })
        setAiLoading(false)
        await triggerGenerate()
      }
    } catch {
      toast.error('Ошибка отправки сообщения')
      setMessages(prev => prev.slice(0, -2))
      setMessageInput(text)
    } finally {
      setAiLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  function handleReset() {
    setPageState('input')
    setVacancyUrl('')
    setVacancyText('')
    setCurrentSession(null)
    setMessages([])
    setResume(null)
  }

  // State 1 — Input
  if (pageState === 'input') {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-lg">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold tracking-tight">
              Создайте резюме под вакансию
            </h1>
            <p className="text-muted-foreground mt-3 text-base">
              AI-ассистент задаст несколько вопросов и составит идеальное резюме за 5 минут
            </p>
          </div>

          <div className="bg-card rounded-xl ring-1 ring-foreground/10 p-6">
            <Tabs value={inputTab} onValueChange={(v) => setInputTab(String(v))}>
              <TabsList className="w-full mb-4">
                <TabsTrigger value="url" className="flex-1">
                  По ссылке
                </TabsTrigger>
                <TabsTrigger value="text" className="flex-1">
                  Текст вакансии
                </TabsTrigger>
              </TabsList>

              <TabsContent value="url">
                <div className="space-y-3">
                  <Input
                    type="url"
                    placeholder="https://hh.ru/vacancy/..."
                    value={vacancyUrl}
                    onChange={e => setVacancyUrl(e.target.value)}
                    className="h-12 text-base"
                    onKeyDown={e => e.key === 'Enter' && handleStart()}
                  />
                  <p className="text-xs text-muted-foreground">
                    Поддерживаются ссылки с hh.ru и других сайтов с вакансиями
                  </p>
                </div>
              </TabsContent>

              <TabsContent value="text">
                <div className="space-y-3">
                  <textarea
                    placeholder="Вставьте текст описания вакансии..."
                    value={vacancyText}
                    onChange={e => setVacancyText(e.target.value)}
                    rows={6}
                    className="w-full rounded-lg border border-input bg-transparent px-3 py-2.5 text-sm outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50 resize-none"
                  />
                </div>
              </TabsContent>
            </Tabs>

            <Button
              onClick={handleStart}
              disabled={startLoading}
              className="w-full h-12 mt-4 text-base font-semibold"
            >
              {startLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Анализируем вакансию...
                </>
              ) : (
                'Начать подбор'
              )}
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Generating overlay
  if (generating) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
          <h2 className="text-xl font-semibold">Генерирую резюме...</h2>
          <p className="text-muted-foreground mt-2">
            AI составляет идеальное резюме под вашу вакансию
          </p>
        </div>
      </div>
    )
  }

  // State 2 — Chat
  if (pageState === 'chat') {
    return (
      <div className="flex-1 flex flex-col max-w-2xl mx-auto w-full">
        {/* Chat header */}
        <div className="px-4 py-3 sticky top-0 md:top-16 z-10 bg-background">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-sm">Идёт сбор данных</h2>
              {currentSession?.vacancy_summary && (
                <p className="text-xs text-muted-foreground truncate max-w-xs">
                  {currentSession.vacancy_summary}
                </p>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              className="text-muted-foreground gap-1"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Заново
            </Button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">
                  AI
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary text-white rounded-br-sm'
                    : 'bg-card ring-1 ring-foreground/10 rounded-bl-sm'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {aiLoading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold shrink-0">
                AI
              </div>
              <div className="bg-card ring-1 ring-foreground/10 rounded-2xl rounded-bl-sm px-4 py-3">
                <div className="flex gap-1 items-center">
                  <span className="text-sm text-muted-foreground">AI думает</span>
                  <span className="flex gap-1 ml-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: '300ms' }} />
                  </span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 sticky bottom-0 md:bottom-0 bg-background">
          <div className="flex justify-center mb-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setMessages(prev => [...prev, { role: 'assistant', content: 'Начинаю составлять резюме по собранным данным...' }])
                triggerGenerate()
              }}
              disabled={aiLoading || generating}
              className="text-sm gap-2 text-primary border-primary/40 hover:bg-primary/5"
            >
              <Download className="w-3.5 h-3.5" />
              Сгенерировать резюме
            </Button>
          </div>
          <div className="flex gap-2 items-end max-w-2xl mx-auto">
            <textarea
              ref={textareaRef}
              placeholder="Напишите ответ..."
              value={messageInput}
              onChange={e => setMessageInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={aiLoading}
              className="flex-1 rounded-xl border border-input bg-transparent px-3.5 py-2.5 text-sm outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50 resize-none disabled:opacity-50 min-h-[44px] max-h-32"
              style={{ height: 'auto' }}
              onInput={e => {
                const el = e.currentTarget
                el.style.height = 'auto'
                el.style.height = `${Math.min(el.scrollHeight, 128)}px`
              }}
            />
            <Button
              onClick={handleSendMessage}
              disabled={aiLoading || !messageInput.trim()}
              size="icon"
              className="w-11 h-11 rounded-xl shrink-0"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-1">
            Enter — отправить, Shift+Enter — новая строка
          </p>
        </div>
      </div>
    )
  }

  // State 3 — Done
  return (
    <div className="flex-1 py-6 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🎉</div>
          <h1 className="text-2xl font-bold">Резюме готово!</h1>
          <p className="text-muted-foreground mt-1">
            AI составил резюме специально под вашу вакансию
          </p>
        </div>

        <div className="flex gap-3 mb-6">
          <Button
            onClick={() => resume && downloadPdf(resume.resume_id)}
            className="flex-1 h-11 gap-2"
          >
            <Download className="w-4 h-4" />
            Скачать PDF
          </Button>
          <Button
            variant="outline"
            onClick={handleReset}
            className="flex-1 h-11 gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            Создать ещё одно
          </Button>
        </div>

        {resume?.data && <ResumePreview data={resume.data} />}
      </div>
    </div>
  )
}
