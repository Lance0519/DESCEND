import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChoiceButtons } from '../components/ChoiceButtons'
import { LanguageToggle } from '../components/LanguageToggle'
import { NumberInput } from '../components/NumberInput'
import { PageBackground } from '../components/PageBackground'
import { ProgressBar } from '../components/ProgressBar'
import { QuestionCard } from '../components/QuestionCard'
import { SkipButton } from '../components/SkipButton'
import { SpeakButton } from '../components/SpeakButton'
import { useAssessment } from '../context/AssessmentContext'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { useAssessmentFlow } from '../hooks/useAssessmentFlow'
import { useSpeech } from '../hooks/useSpeech'
import { clearDraft } from '../lib/draftStorage'
import { computeBmi, type AnswerKey, type AssessmentAnswers } from '../types/assessment'
import { predictAssessment } from '../api/client'
import { mapPayload } from '../api/mapPayload'
import { mockScore } from '../utils/mockScore'
import './AssessmentPage.css'

export function AssessmentPage() {
  const { t, language } = useLanguage()
  const { user } = useAuth()
  const {
    answers,
    setAnswer,
    setResult,
    questionIndex,
    setQuestionIndex,
    hasDraft,
    resetAssessment,
  } = useAssessment()
  const flow = useAssessmentFlow(answers, questionIndex, setQuestionIndex)
  const { speak, cancel, speaking } = useSpeech(language)
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [draftNumber, setDraftNumber] = useState<number | ''>('')
  const [showResume, setShowResume] = useState(hasDraft && Object.keys(answers).length > 0)

  const current = flow.current

  useEffect(() => {
    if (!current) return
    if (current.type === 'number' || current.type === 'optionalNumber') {
      const key = current.id as AnswerKey
      const existing = answers[key]
      setDraftNumber(typeof existing === 'number' ? existing : '')
    } else {
      setDraftNumber('')
    }
  }, [current?.id])

  const optionLabel = (key: string) => (t.options as Record<string, string>)[key] ?? key
  const questionText = current ? t.questions[current.questionKey] : ''
  const sectionLabel = current ? t.section[current.section] : ''

  const speakText = useMemo(() => {
    if (!current) return ''
    const opts = current.options?.map((o) => optionLabel(String(o.labelKey))).join('. ') ?? ''
    return `${questionText}. ${opts}`
  }, [current, questionText, language])

  if (showResume) {
    return (
      <PageBackground>
        <div className="assessment-page assessment-page--resume">
          <div className="resume-card">
            <h2>{t.resumeTitle}</h2>
            <p>{t.resumeText}</p>
            <button type="button" className="btn btn--primary" onClick={() => setShowResume(false)}>
              {t.resumeContinue}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => {
                resetAssessment()
                setShowResume(false)
              }}
            >
              {t.resumeStartOver}
            </button>
          </div>
        </div>
      </PageBackground>
    )
  }

  if (!current) {
    return (
      <PageBackground>
        <div className="assessment-page">{t.errorRetry}</div>
      </PageBackground>
    )
  }

  const storedValue =
    current.id === 'bmiConfirm'
      ? undefined
      : (answers[current.id as AnswerKey] as string | number | null | undefined)

  const optionalAnswered =
    current.id === 'fastingGlucoseMgDl'
      ? answers.fastingGlucoseSkipped === true ||
        draftNumber !== '' ||
        answers.fastingGlucoseMgDl != null
      : current.id === 'hba1cPercent'
        ? answers.hba1cSkipped === true || draftNumber !== '' || answers.hba1cPercent != null
        : false

  const canProceed =
    current.type === 'bmiConfirm'
      ? answers.heightCm != null && answers.weightKg != null
      : current.type === 'choice'
        ? flow.isAnswered(current)
        : current.type === 'optionalNumber'
          ? optionalAnswered
          : draftNumber !== '' || flow.isAnswered(current)

  function commitNumber(value: number | '', into?: AssessmentAnswers): AssessmentAnswers {
    const next = { ...(into ?? answers) }
    if (value === '') return next
    const key = current!.id as AnswerKey
    ;(next as Record<string, unknown>)[key] = value
    if (key === 'fastingGlucoseMgDl') next.fastingGlucoseSkipped = false
    if (key === 'hba1cPercent') next.hba1cSkipped = false
    setAnswer(key, value as never)
    if (key === 'fastingGlucoseMgDl') setAnswer('fastingGlucoseSkipped', false)
    if (key === 'hba1cPercent') setAnswer('hba1cSkipped', false)
    return next
  }

  function handleSkip() {
    if (current!.id === 'fastingGlucoseMgDl') {
      setAnswer('fastingGlucoseMgDl', null)
      setAnswer('fastingGlucoseSkipped', true)
    }
    if (current!.id === 'hba1cPercent') {
      setAnswer('hba1cPercent', null)
      setAnswer('hba1cSkipped', true)
    }
  }

  async function handleNext() {
    let latest = answers
    if (current!.type === 'number' || current!.type === 'optionalNumber') {
      if (draftNumber !== '') latest = commitNumber(draftNumber)
    }

    if (!flow.isLast) {
      cancel()
      flow.goNext()
      return
    }

    setSubmitting(true)
    try {
      const payload = mapPayload(latest)
      try {
        const apiResult = await predictAssessment(payload)
        setResult(apiResult)
      } catch {
        setResult(mockScore(latest))
      }
      clearDraft()
      navigate('/results')
    } finally {
      setSubmitting(false)
    }
  }

  const bmi =
    answers.heightCm != null && answers.weightKg != null
      ? computeBmi(answers.heightCm, answers.weightKg)
      : null

  return (
    <PageBackground>
      <div className="assessment-page">
        <ProgressBar current={flow.index} total={flow.total} label={t.progress} />
        <div className="assessment-page__toolbar">
          <LanguageToggle />
          {user ? (
            <Link to="/account" className="assessment-page__account">
              {t.accountNav}
            </Link>
          ) : (
            <Link to="/access" className="assessment-page__account">
              {t.accessSignIn}
            </Link>
          )}
        </div>
        <div className="assessment-page__content">
          <motion.div
            key={current.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            <QuestionCard
              sectionLabel={sectionLabel}
              title={questionText}
              headerAction={
                <SpeakButton
                  speaking={speaking}
                  onSpeak={() => void speak(speakText)}
                  onStop={cancel}
                  speakLabel={t.speak}
                  stopLabel={t.stopSpeak}
                />
              }
            >
              {current.type === 'choice' && current.options ? (
                <ChoiceButtons
                  name={current.id}
                  value={typeof storedValue === 'string' ? storedValue : undefined}
                  onChange={(value) => setAnswer(current.id as AnswerKey, value as never)}
                  options={current.options.map((o) => ({
                    value: String(o.value),
                    label: optionLabel(String(o.labelKey)),
                  }))}
                />
              ) : null}

              {(current.type === 'number' || current.type === 'optionalNumber') && (
                <NumberInput
                  id={current.id}
                  value={draftNumber}
                  min={current.min}
                  max={current.max}
                  step={current.step}
                  unit={current.unit}
                  onChange={(v) => {
                    setDraftNumber(v)
                    if (v !== '') commitNumber(v)
                  }}
                />
              )}

              {current.type === 'optionalNumber' ? (
                <SkipButton label={t.skip} onClick={handleSkip} />
              ) : null}

              {current.type === 'bmiConfirm' && bmi != null ? (
                <div className="bmi-confirm">
                  <p className="bmi-confirm__value">
                    {t.bmiLabel}: {bmi.toFixed(1)}
                  </p>
                  <p className="bmi-confirm__helper">{t.bmiHelper}</p>
                </div>
              ) : null}
            </QuestionCard>
          </motion.div>

          <div className="assessment-page__nav">
            <button
              type="button"
              className="btn btn--ghost"
              disabled={flow.isFirst || submitting}
              onClick={() => {
                cancel()
                flow.goBack()
              }}
            >
              {t.back}
            </button>
            <button
              type="button"
              className="btn btn--primary"
              disabled={!canProceed || submitting}
              onClick={() => void handleNext()}
            >
              {submitting ? t.loading : flow.isLast ? t.seeResults : t.next}
            </button>
          </div>
        </div>
      </div>
    </PageBackground>
  )
}
