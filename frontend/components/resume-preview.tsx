'use client'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import type { ResumeData } from '@/lib/types'
import { MapPin, Phone, Mail, Link as LinkIcon, GraduationCap, Briefcase, Star, Globe, Layers } from 'lucide-react'

interface ResumePreviewProps {
  data: ResumeData
}

export function ResumePreview({ data }: ResumePreviewProps) {
  return (
    <div className="bg-white rounded-xl ring-1 ring-foreground/10 overflow-hidden">
      {/* Header */}
      <div className="bg-primary px-6 py-6 text-white">
        <h1 className="text-2xl font-bold">{data.personal.name || 'Имя не указано'}</h1>
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-white/80 text-sm">
          {data.personal.city && (
            <span className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" />
              {data.personal.city}
            </span>
          )}
          {data.personal.phone && (
            <span className="flex items-center gap-1">
              <Phone className="w-3.5 h-3.5" />
              {data.personal.phone}
            </span>
          )}
          {data.personal.email && (
            <span className="flex items-center gap-1">
              <Mail className="w-3.5 h-3.5" />
              {data.personal.email}
            </span>
          )}
        </div>
        {data.personal.links && data.personal.links.length > 0 && (
          <div className="flex flex-wrap gap-3 mt-2">
            {data.personal.links.map((link, i) => (
              <a
                key={i}
                href={link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-white/80 hover:text-white text-xs underline underline-offset-2 transition-colors"
              >
                <LinkIcon className="w-3 h-3" />
                {link.replace(/^https?:\/\//, '').replace(/\/$/, '')}
              </a>
            ))}
          </div>
        )}
      </div>

      <div className="p-6 space-y-6">
        {/* About */}
        {data.personal.about && (
          <section>
            <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-2">
              <Star className="w-4 h-4 text-primary" />
              О себе
            </h2>
            <p className="text-sm leading-relaxed">{data.personal.about}</p>
          </section>
        )}

        {data.personal.about && <Separator />}

        {/* Experience */}
        {data.experience && data.experience.length > 0 && (
          <section>
            <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide mb-3 flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-primary" />
              Опыт и проекты
            </h2>
            <div className="space-y-4">
              {data.experience.map((exp, i) => (
                <div key={i} className="border-l-2 border-primary/30 pl-4">
                  <div className="font-semibold text-sm">{exp.title}</div>
                  {exp.role && (
                    <div className="text-xs text-primary font-medium mt-0.5">{exp.role}</div>
                  )}
                  {exp.description && (
                    <p className="text-sm text-muted-foreground mt-1">{exp.description}</p>
                  )}
                  {exp.result && (
                    <div className="mt-1 text-sm font-medium text-foreground">
                      Результат: {exp.result}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {data.experience && data.experience.length > 0 && <Separator />}

        {/* Education */}
        {data.education && data.education.length > 0 && (
          <section>
            <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide mb-3 flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-primary" />
              Образование
            </h2>
            <div className="space-y-3">
              {data.education.map((edu, i) => (
                <div key={i}>
                  <div className="font-semibold text-sm">{edu.university}</div>
                  {edu.faculty && (
                    <div className="text-xs text-muted-foreground">{edu.faculty}</div>
                  )}
                  {edu.speciality && (
                    <div className="text-xs text-muted-foreground">{edu.speciality}</div>
                  )}
                  {edu.year && (
                    <div className="text-xs text-primary mt-0.5">Окончание: {edu.year}</div>
                  )}
                  {edu.achievements && (
                    <p className="text-sm text-muted-foreground mt-1">{edu.achievements}</p>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {data.education && data.education.length > 0 && <Separator />}

        {/* Skills */}
        {data.skills && (data.skills.hard?.length > 0 || data.skills.soft?.length > 0) && (
          <section>
            <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary" />
              Навыки
            </h2>
            {data.skills.hard && data.skills.hard.length > 0 && (
              <div className="mb-2">
                <div className="text-xs text-muted-foreground mb-1.5">Hard skills</div>
                <div className="flex flex-wrap gap-1.5">
                  {data.skills.hard.map((skill, i) => (
                    <Badge key={i} variant="default" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {data.skills.soft && data.skills.soft.length > 0 && (
              <div>
                <div className="text-xs text-muted-foreground mb-1.5">Soft skills</div>
                <div className="flex flex-wrap gap-1.5">
                  {data.skills.soft.map((skill, i) => (
                    <Badge key={i} variant="secondary" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* Languages */}
        {data.languages && data.languages.length > 0 && (
          <>
            <Separator />
            <section>
              <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide mb-3 flex items-center gap-2">
                <Globe className="w-4 h-4 text-primary" />
                Языки
              </h2>
              <div className="flex flex-wrap gap-2">
                {data.languages.map((lang, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-sm">
                    <span className="font-medium">{lang.language}</span>
                    <Badge variant="outline" className="text-xs">
                      {lang.level}
                    </Badge>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}

        {/* Extra */}
        {data.extra && (data.extra.projects?.length > 0 || data.extra.hobbies) && (
          <>
            <Separator />
            <section>
              <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide mb-3">
                Дополнительно
              </h2>
              {data.extra.projects && data.extra.projects.length > 0 && (
                <div className="mb-2">
                  <div className="text-xs text-muted-foreground mb-1.5">Проекты</div>
                  <div className="space-y-0.5">
                    {data.extra.projects.map((project, i) => (
                      <div key={i}>
                        {project.startsWith('http') ? (
                          <a
                            href={project}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary hover:underline flex items-center gap-1"
                          >
                            <LinkIcon className="w-3 h-3" />
                            {project.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                          </a>
                        ) : (
                          <span className="text-sm">{project}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {data.extra.hobbies && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1.5">Увлечения</div>
                  <p className="text-sm">{data.extra.hobbies}</p>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  )
}
