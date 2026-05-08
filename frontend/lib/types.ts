export interface Profile {
  name?: string
  city?: string
  phone?: string
  email?: string
  link_hh?: string
  link_portfolio?: string
  university?: string
  faculty?: string
  speciality?: string
  graduation_year?: string
  languages?: { language: string; level: string }[]
}

export interface Session {
  session_id: string
  vacancy_summary?: string
  created_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ResumeData {
  personal: {
    name: string
    city: string
    phone: string
    email: string
    links: string[]
    about: string
  }
  education: Array<{
    university: string
    faculty: string
    speciality: string
    year: string
    achievements: string
  }>
  experience: Array<{
    title: string
    role: string
    description: string
    result: string
  }>
  skills: { hard: string[]; soft: string[] }
  languages: Array<{ language: string; level: string }>
  extra: { projects: string[]; hobbies: string }
}

export interface Resume {
  resume_id: string
  session_id: string
  data: ResumeData
  pdf_url: string
  created_at: string
}

export interface ResumeListItem {
  resume_id: string
  vacancy_title?: string
  vacancy_preview?: string
  pdf_url: string
  created_at: string
}
