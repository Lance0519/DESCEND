import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import { ChoiceButtons } from '../components/ChoiceButtons'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { NumberInput } from '../components/NumberInput'
import { PageBackground } from '../components/PageBackground'
import { ProgressBar } from '../components/ProgressBar'
import { QuestionCard } from '../components/QuestionCard'
import { ReviewSummary } from '../components/ReviewSummary'
import { SkipButton } from '../components/SkipButton'
import { SpeakButton } from '../components/SpeakButton'
import { AppNavBar } from '../components/ui/AppNavBar'
import { useAssessment } from '../context/AssessmentContext'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { useAssessmentFlow } from '../hooks/useAssessmentFlow'
import { useSpeech } from '../hooks/useSpeech'
import { clearDraft } from '../lib/draftStorage'
import { buildReviewGroups, firstMissingIndex } from '../lib/answerSummary'
import { getVisibleQuestions } from '../data/questions'
import {
  isStrictNumberField,
  validateAnswersForSubmit,
  validateNumberField,
  type NumberFieldError,
} from '../lib/assessmentValidation'
import { computeBmi, type AnswerKey, type AssessmentAnswers } from '../types/assessment'
import { persistAssessmentRecord } from '../api/assessmentRecords'
import {
  PredictApiError,
  estimateAssessment,
  mapDiagnosedPayload,
  predictAssessment,
} from '../api/client'
import { mapPayload } from '../api/mapPayload'
import { mockScore } from '../utils/mockScore'
import { DiagnosisGate } from '../features/assessment/DiagnosisGate'
import { OnsetGate } from '../features/assessment/OnsetGate'
import { ResumeModal } from '../features/assessment/ResumeModal'
import './AssessmentPage.css'

type DiagnosisGate = 'diagnosis' | 'onset' | 'survey' | 'review'

function initialGate(answers: AssessmentAnswers): DiagnosisGate {
  if (answers.diagnosedT2dm === 'no') return 'survey'
  if (answers.diagnosedT2dm === 'yes') return 'onset'
  return 'diagnosis'
}

function AssessmentToolbar({ onHomeClick }: { onHomeClick: () => void }) {
  const { t } = useLanguage()
  const { user } = useAuth()

  return (
    <AppNavBar
      showHome={true}
      onHomeClick={onHomeClick}
      right={
        user ? (
          <>
            <Link to="/dashboard" className="app-nav__link">
              {t.dashboardNav}
            </Link>
            <Link to="/account" className="app-nav__link">
              {t.accountNav}
            </Link>
          </>
        ) : (
          <Link to="/access" className="app-nav__link">
            {t.accessSignIn}
          </Link>
        )
      }
    />
  )
}

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
  const [draftNumbers, setDraftNumbers] = useState<Record<string, number | ''>>({})
  const [showResume, setShowResume] = useState(hasDraft && Object.keys(answers).length > 0)
  const [predictError, setPredictError] = useState<string | null>(null)
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [attemptedNext, setAttemptedNext] = useState(false)
  const [gate, setGate] = useState<DiagnosisGate>(() => initialGate(answers))
  const [onsetAge, setOnsetAge] = useState<number | ''>(
    typeof answers.ageAtDiagnosis === 'number' ? answers.ageAtDiagnosis : '',
  )
  const [gateSubmitting, setGateSubmitting] = useState(false)
  const [returnToReview, setReturnToReview] = useState(false)
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false)

  const appliedUserPrefs = useRef(false)
  useEffect(() => {
    if (!user || appliedUserPrefs.current) return
    appliedUserPrefs.current = true
    if (answers.age == null && user.preferredAge != null) {
      setAnswer('age', user.preferredAge)
    }
    if (!answers.sex && (user.preferredSex === 'male' || user.preferredSex === 'female')) {
      setAnswer('sex', user.preferredSex)
    }
  }, [user, answers.age, answers.sex, setAnswer])

  const current = flow.current

  const currentDraft =
    current && (current.type === 'number' || current.type === 'optionalNumber')
      ? draftNumbers[current.id] !== undefined
        ? draftNumbers[current.id]
        : typeof answers[current.id as AnswerKey] === 'number'
          ? (answers[current.id as AnswerKey] as number)
          : ''
      : ''

  const optionLabel = (key: string) => (t.options as Record<string, string>)[key] ?? key
  const questionText = current ? t.questions[current.questionKey] : ''
  const sectionLabel = current ? t.section[current.section] : ''

  const speakText = useMemo(() => {
    if (!current) return ''
    const opts = current.options?.map((o) => optionLabel(String(o.labelKey))).join('. ') ?? ''
    return `${questionText}. ${opts}`
  }, [current, questionText, language]) // eslint-disable-line react-hooks/exhaustive-deps

  const reviewGroups = useMemo(
    () => buildReviewGroups(flow.visible, answers, t),
    [flow.visible, answers, t],
  )
  const reviewMissingIndex = useMemo(() => firstMissingIndex(reviewGroups), [reviewGroups])

  function rangeMessage(min?: number, max?: number) {
    return t.fieldOutOfRange
      .replace('{min}', min != null ? String(min) : '—')
      .replace('{max}', max != null ? String(max) : '—')
  }

  function messageForFieldError(code: NumberFieldError, min?: number, max?: number) {
    if (code === 'required') return t.fieldRequired
    if (code === 'range') return rangeMessage(min, max)
    return null
  }

  function messageForPredictError(err: unknown): string {
    if (err instanceof PredictApiError) {
      if (err.code === 'network') return t.predictErrorNetwork
      if (err.code === 'config') return t.predictErrorConfig
      if (err.code === 'invalid') return t.predictErrorInvalid
      if (err.code === 'http') {
        return err.message && err.message !== 'http' ? err.message : t.predictErrorText
      }
    }
    if (err instanceof Error && err.message) return err.message
    return t.predictErrorText
  }

  function onHomeRequest() {
    if (Object.keys(answers).length > 0) {
      setShowLeaveConfirm(true)
    } else {
      navigate('/')
    }
  }

  if (showResume) {
    return (
      <ResumeModal
        toolbar={<AssessmentToolbar onHomeClick={onHomeRequest} />}
        onResume={() => {
          setShowResume(false)
          if (answers.diagnosedT2dm === 'yes' && answers.ageAtDiagnosis != null) {
            navigate('/management', { replace: true })
            return
          }
          setGate(initialGate(answers))
        }}
        onStartOver={() => {
          resetAssessment()
          setGate('diagnosis')
          setOnsetAge('')
          setShowResume(false)
        }}
      />
    )
  }

  if (gate === 'diagnosis') {
    return (
      <DiagnosisGate
        toolbar={<AssessmentToolbar onHomeClick={onHomeRequest} />}
        onYes={() => {
          setAnswer('diagnosedT2dm', 'yes')
          setGate('onset')
        }}
        onNo={() => {
          setAnswer('diagnosedT2dm', 'no')
          setAnswer('ageAtDiagnosis', undefined as never)
          setQuestionIndex(0)
          setGate('survey')
        }}
      />
    )
  }

  if (gate === 'onset') {
    return (
      <OnsetGate
        toolbar={<AssessmentToolbar onHomeClick={onHomeRequest} />}
        initialAge={onsetAge}
        submitting={gateSubmitting}
        onBack={() => setGate('diagnosis')}
        onSubmit={async (age) => {
          setGateSubmitting(true)
          setOnsetAge(age)
          setAnswer('diagnosedT2dm', 'yes')
          setAnswer('ageAtDiagnosis', age)
          try {
            await estimateAssessment(mapDiagnosedPayload(age))
          } catch {
            // Local management path proceeds even if remote save fails
          }
          if (user) {
            void persistAssessmentRecord({
              userId: user.id,
              riskScore: null,
              riskTier: null,
              preDiagnosed: true,
            })
          }
          clearDraft()
          navigate('/management', { replace: true })
          setGateSubmitting(false)
        }}
      />
    )
  }

  if (gate === 'review') {
    return (
      <PageBackground>
        <div className="assessment-page">
          <ProgressBar current={flow.total - 1} total={flow.total} label={t.progress} />
          <AssessmentToolbar onHomeClick={onHomeRequest} />
          <div className="assessment-page__content">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
            >
              <ReviewSummary
                groups={reviewGroups}
                missingIndex={reviewMissingIndex}
                onEdit={handleEditAnswer}
              />
            </motion.div>

            <div className="assessment-page__nav">
              <button
                type="button"
                className="btn btn--ghost"
                disabled={submitting}
                onClick={() => {
                  setReturnToReview(false)
                  setQuestionIndex(Math.max(flow.total - 1, 0))
                  setGate('survey')
                }}
              >
                {t.reviewBackToQuestions}
              </button>
              <button
                type="button"
                className="btn btn--primary"
                disabled={submitting || reviewMissingIndex != null}
                onClick={() => void submitAssessment(answers)}
              >
                {submitting ? t.loading : t.reviewConfirm}
              </button>
            </div>

            {predictError ? (
              <div className="assessment-page__predict-error" role="alert">
                <h3>{t.predictErrorTitle}</h3>
                <p>{predictError}</p>
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={submitting}
                  onClick={() => void submitAssessment(answers)}
                >
                  {submitting ? t.loading : t.predictRetry}
                </button>
              </div>
            ) : null}
          </div>
        </div>
        {showLeaveConfirm ? (
          <ConfirmDialog
            title={t.confirmLeaveTitle}
            text={t.confirmLeaveText}
            confirmLabel={t.confirmLeaveYes}
            cancelLabel={t.confirmLeaveNo}
            onCancel={() => setShowLeaveConfirm(false)}
            onConfirm={() => {
              setShowLeaveConfirm(false)
              navigate('/')
            }}
          />
        ) : null}
      </PageBackground>
    )
  }

  if (!current) {
    return (
      <PageBackground>
        <div className="assessment-page assessment-page--resume">
          <div className="resume-card" role="alert">
            <h2>{t.flowErrorTitle}</h2>
            <p>{t.flowErrorText}</p>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => {
                resetAssessment()
                navigate('/assessment', { replace: true })
              }}
            >
              {t.flowErrorRestart}
            </button>
            <Link to="/" className="btn btn--ghost btn--link">
              {t.backHome}
            </Link>
          </div>
        </div>
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
        currentDraft !== '' ||
        answers.fastingGlucoseMgDl != null
      : current.id === 'hba1cPercent'
        ? answers.hba1cSkipped === true || currentDraft !== '' || answers.hba1cPercent != null
        : false

  const numberErrorCode =
    current.type === 'number' && isStrictNumberField(String(current.id))
      ? validateNumberField(current, currentDraft)
      : null

  const canProceed =
    current.type === 'bmiConfirm'
      ? answers.heightCm != null && answers.weightKg != null
      : current.type === 'choice'
        ? flow.isAnswered(current)
        : current.type === 'optionalNumber'
          ? optionalAnswered
          : current.type === 'number'
            ? currentDraft !== '' && numberErrorCode === null
            : false

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
    cancel()
    if (current!.id === 'fastingGlucoseMgDl') {
      setAnswer('fastingGlucoseMgDl', null)
      setAnswer('fastingGlucoseSkipped', true)
    }
    if (current!.id === 'hba1cPercent') {
      setAnswer('hba1cPercent', null)
      setAnswer('hba1cSkipped', true)
    }
    setDraftNumbers((prev) => ({ ...prev, [current!.id]: '' }))
    setFieldError(null)
    setAttemptedNext(false)

    if (returnToReview) {
      setReturnToReview(false)
      setGate('review')
      return
    }

    if (flow.isLast) {
      setGate('review')
      return
    }

    flow.goNext()
  }

  async function handleNext() {
    setAttemptedNext(true)
    setPredictError(null)

    if (current!.type === 'number' && isStrictNumberField(String(current!.id))) {
      const code = validateNumberField(current!, currentDraft)
      if (code) {
        setFieldError(messageForFieldError(code, current!.min, current!.max))
        return
      }
      setFieldError(null)
    }

    let latest = answers
    if (current!.type === 'number' || current!.type === 'optionalNumber') {
      const skipped =
        (current!.id === 'fastingGlucoseMgDl' && answers.fastingGlucoseSkipped) ||
        (current!.id === 'hba1cPercent' && answers.hba1cSkipped)
      if (currentDraft !== '' && !skipped) latest = commitNumber(currentDraft)
    }

    cancel()
    setFieldError(null)
    setAttemptedNext(false)

    if (returnToReview) {
      const missing = firstMissingIndex(buildReviewGroups(getVisibleQuestions(latest), latest, t))
      if (missing == null || missing === flow.index) {
        setReturnToReview(false)
        setGate('review')
        return
      }
      setQuestionIndex(missing)
      return
    }

    if (flow.isLast) {
      setGate('review')
      return
    }

    flow.goNext()
  }

  async function submitAssessment(latest: AssessmentAnswers) {
    setPredictError(null)

    if (!validateAnswersForSubmit(latest)) {
      setPredictError(t.submitIncomplete)
      return
    }

    const scoredAnswers: AssessmentAnswers = { ...latest, diagnosedT2dm: 'no' }

    setSubmitting(true)
    try {
      const payload = mapPayload(scoredAnswers)
      try {
        const apiResult = await predictAssessment(payload)
        setResult(apiResult)
        clearDraft()
        navigate('/results')
      } catch (err) {
        if (import.meta.env.DEV) {
          const localResult = mockScore(scoredAnswers)
          setResult(localResult)
          clearDraft()
          navigate('/results')
          return
        }
        setPredictError(messageForPredictError(err))
      }
    } catch (err) {
      setPredictError(messageForPredictError(err))
    } finally {
      setSubmitting(false)
    }
  }

  function handleEditAnswer(index: number) {
    cancel()
    setPredictError(null)
    setFieldError(null)
    setAttemptedNext(false)
    setReturnToReview(true)
    setQuestionIndex(index)
    setGate('survey')
  }

  const bmi =
    answers.heightCm != null && answers.weightKg != null
      ? computeBmi(answers.heightCm, answers.weightKg)
      : null

  const shownFieldError =
    isStrictNumberField(String(current.id)) && (attemptedNext || fieldError)
      ? fieldError ?? messageForFieldError(numberErrorCode, current.min, current.max)
      : null

  const questionTooltip =
    current.tooltipKey && t.tooltips[current.tooltipKey]
      ? {
          title: t.tooltips[current.tooltipKey].title,
          body: t.tooltips[current.tooltipKey].body,
          triggerLabel: t.tooltips.whatDoesThisMean,
          closeLabel: t.tooltips.closeTooltip,
          buttonAriaLabel: t.tooltips.whatDoesThisMean,
        }
      : undefined

  return (
    <PageBackground>
      <div className="assessment-page">
        <ProgressBar current={flow.index} total={flow.total} label={t.progress} />
        <AssessmentToolbar onHomeClick={onHomeRequest} />
        <div className="assessment-page__content">
          <motion.div
            key={current.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            {returnToReview ? (
              <div className="assessment-page__edit-banner">
                <Check size={16} aria-hidden />
                <span>{t.reviewEditingNotice}</span>
              </div>
            ) : null}

            <QuestionCard
              sectionLabel={sectionLabel}
              title={questionText}
              tooltip={questionTooltip}
              headerAction={
                <SpeakButton
                  speaking={speaking}
                  onSpeak={() => speak(speakText)}
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
                  value={currentDraft}
                  min={current.min}
                  max={current.max}
                  step={current.step}
                  unit={current.unit}
                  error={shownFieldError}
                  onChange={(v) => {
                    setDraftNumbers((prev) => ({ ...prev, [current.id]: v }))
                    if (isStrictNumberField(String(current.id))) {
                      const code = validateNumberField(current, v)
                      setFieldError(messageForFieldError(code, current.min, current.max))
                      if (v !== '' && code === null) commitNumber(v)
                    } else if (v !== '') {
                      setFieldError(null)
                      commitNumber(v)
                    }
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

              {current.type === 'bmiConfirm' && bmi == null ? (
                <p className="assessment-page__inline-error" role="alert">
                  {t.submitIncomplete}
                </p>
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
                setPredictError(null)
                setFieldError(null)
                setAttemptedNext(false)
                flow.goBack()
              }}
            >
              {t.back}
            </button>
            <button
              type="button"
              className="btn btn--primary"
              disabled={submitting || !canProceed}
              onClick={() => void handleNext()}
            >
              {submitting
                ? t.loading
                : returnToReview
                  ? t.reviewSaveAndReturn
                  : flow.isLast
                    ? t.reviewTitle
                    : t.next}
            </button>
          </div>

          {predictError ? (
            <div className="assessment-page__predict-error" role="alert">
              <h3>{t.predictErrorTitle}</h3>
              <p>{predictError}</p>
              <button
                type="button"
                className="btn btn--primary"
                disabled={submitting}
                onClick={() => void handleNext()}
              >
                {submitting ? t.loading : t.predictRetry}
              </button>
            </div>
          ) : null}
        </div>
      </div>
      {showLeaveConfirm ? (
        <ConfirmDialog
          title={t.confirmLeaveTitle}
          text={t.confirmLeaveText}
          confirmLabel={t.confirmLeaveYes}
          cancelLabel={t.confirmLeaveNo}
          onCancel={() => setShowLeaveConfirm(false)}
          onConfirm={() => {
            setShowLeaveConfirm(false)
            navigate('/')
          }}
        />
      ) : null}
    </PageBackground>
  )
}
