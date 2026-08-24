import { Activity, Apple, CigaretteOff, Moon, Scale, Stethoscope } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useLanguage } from '../../context/LanguageContext'
import {
  matchesPreventionTip,
  PREVENTION_SOURCES,
  PREVENTION_TIP_IDS,
  type PreventionSourceId,
  type PreventionTipId,
} from '../../data/preventionTips'
import type { AssessmentAnswers } from '../../types/assessment'
import './PreventionPanel.css'

const TIP_ICONS: Record<PreventionTipId, LucideIcon> = {
  activity: Activity,
  weight: Scale,
  diet: Apple,
  smoking: CigaretteOff,
  sleep: Moon,
  screening: Stethoscope,
}

function tipCopy(
  id: PreventionTipId,
  t: ReturnType<typeof useLanguage>['t'],
): { title: string; text: string } {
  switch (id) {
    case 'activity':
      return { title: t.preventActivityTitle, text: t.preventActivityText }
    case 'weight':
      return { title: t.preventWeightTitle, text: t.preventWeightText }
    case 'diet':
      return { title: t.preventDietTitle, text: t.preventDietText }
    case 'smoking':
      return { title: t.preventSmokingTitle, text: t.preventSmokingText }
    case 'sleep':
      return { title: t.preventSleepTitle, text: t.preventSleepText }
    case 'screening':
      return { title: t.preventScreeningTitle, text: t.preventScreeningText }
  }
}

function sourceLabel(id: PreventionSourceId, t: ReturnType<typeof useLanguage>['t']): string {
  switch (id) {
    case 'ada':
      return t.preventSourceAda
    case 'dpp':
      return t.preventSourceDpp
    case 'cdc':
      return t.preventSourceCdc
    case 'who':
      return t.preventSourceWho
    case 'pinggang':
      return t.preventSourcePinggang
  }
}

interface PreventionPanelProps {
  answers: AssessmentAnswers
  bmi: number | null
}

export function PreventionPanel({ answers, bmi }: PreventionPanelProps) {
  const { t } = useLanguage()

  return (
    <section className="prevent" aria-labelledby="prevent-heading">
      <h2 id="prevent-heading" className="prevent__title">
        {t.preventTitle}
      </h2>
      <p className="prevent__lead">{t.preventLead}</p>
      <ul className="prevent__tips">
        {PREVENTION_TIP_IDS.map((id) => {
          const Icon = TIP_ICONS[id]
          const copy = tipCopy(id, t)
          const highlighted = matchesPreventionTip(id, answers, bmi)
          return (
            <li key={id} className={highlighted ? 'prevent__tip prevent__tip--highlight' : 'prevent__tip'}>
              <Icon size={22} aria-hidden className="prevent__icon" />
              <div>
                {highlighted ? <p className="prevent__badge">{t.preventBasedOnAnswers}</p> : null}
                <h3>{copy.title}</h3>
                <p>{copy.text}</p>
              </div>
            </li>
          )
        })}
      </ul>
      <h3 className="prevent__sources-title">{t.preventSourcesTitle}</h3>
      <ul className="prevent__sources">
        {PREVENTION_SOURCES.map((source) => (
          <li key={source.id}>
            <a href={source.href} target="_blank" rel="noreferrer">
              {sourceLabel(source.id, t)}
            </a>
          </li>
        ))}
      </ul>
      <p className="prevent__note">{t.preventClinicianNote}</p>
    </section>
  )
}
