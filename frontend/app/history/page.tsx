'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { resume as resumeApi } from '@/lib/api'
import { isAuthenticated, getAccessToken } from '@/lib/auth'
import { Download, FileText, Plus } from 'lucide-react'
import type { ResumeListItem } from '@/lib/types'

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(dateStr))
}

async function downloadPdf(resumeId: string, fileName?: string) {
  const token = getAccessToken()
  const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/resume/${resumeId}/pdf`
  try {
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) throw new Error('Failed to fetch PDF')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = fileName ? `${fileName}.pdf` : 'resume.pdf'
    a.click()
    URL.revokeObjectURL(a.href)
  } catch {
    toast.error('Ошибка скачивания PDF')
  }
}

function SkeletonCard() {
  return (
    <Card>
      <CardContent className="pt-5 pb-5">
        <div className="space-y-3">
          <div className="h-4 bg-muted rounded w-3/4 animate-pulse" />
          <div className="h-3 bg-muted rounded w-full animate-pulse" />
          <div className="h-3 bg-muted rounded w-2/3 animate-pulse" />
          <div className="flex items-center justify-between mt-4">
            <div className="h-3 bg-muted rounded w-24 animate-pulse" />
            <div className="h-8 bg-muted rounded w-28 animate-pulse" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function HistoryPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [resumes, setResumes] = useState<ResumeListItem[]>([])
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    loadResumes()
  }, [router])

  async function loadResumes() {
    setLoading(true)
    try {
      const { data } = await resumeApi.list()
      setResumes(data)
    } catch {
      toast.error('Не удалось загрузить историю резюме')
    } finally {
      setLoading(false)
    }
  }

  async function handleDownload(item: ResumeListItem) {
    setDownloadingId(item.resume_id)
    await downloadPdf(item.resume_id, item.vacancy_title || 'resume')
    setDownloadingId(null)
  }

  return (
    <div className="flex-1 py-6 px-4">
      <div className="max-w-lg mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">История резюме</h1>
          <Link href="/">
            <Button size="sm" className="gap-1.5">
              <Plus className="w-3.5 h-3.5" />
              Новое
            </Button>
          </Link>
        </div>

        {loading ? (
          <div className="space-y-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : resumes.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
              <FileText className="w-8 h-8 text-muted-foreground" />
            </div>
            <h2 className="text-lg font-semibold mb-2">Резюме ещё нет</h2>
            <p className="text-muted-foreground mb-6">
              Создайте своё первое резюме под вакансию с помощью AI
            </p>
            <Link href="/">
              <Button className="gap-2">
                <Plus className="w-4 h-4" />
                Создать первое резюме
              </Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {resumes.map(item => (
              <Card key={item.resume_id}>
                <CardContent className="pt-5 pb-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-sm truncate">
                        {item.vacancy_title || 'Резюме'}
                      </h3>
                      {item.vacancy_preview && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {item.vacancy_preview.slice(0, 100)}
                          {item.vacancy_preview.length > 100 ? '...' : ''}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground mt-2">
                        {formatDate(item.created_at)}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleDownload(item)}
                      disabled={downloadingId === item.resume_id}
                      className="gap-1.5 shrink-0"
                    >
                      {downloadingId === item.resume_id ? (
                        <>
                          <span className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                          Загрузка...
                        </>
                      ) : (
                        <>
                          <Download className="w-3.5 h-3.5" />
                          Скачать PDF
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
