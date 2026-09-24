# DESCEND - Survey Review & Confirmation Step (Implementation Plan)

Goal: after the user answers the last survey question, show a summary of every
response and require an explicit confirmation before the assessment is scored.
Today the survey submits silently on the final "See results" click, so a
mistyped weight or a mis-tapped family-history answer can only be discovered
after the score has already been computed and saved.

Decisions already taken (2026-09-24):

- The review is a **full page step**, and the page's own Confirm button is the
  confirmation. No extra modal dialog, no "I confirm" checkbox.
- The review stage is **not persisted** across a page reload. A refresh drops
  back into the survey at the last question, which is the behaviour today.

## 1. Current behaviour

`Frontend/src/pages/AssessmentPage.tsx` runs a small stage machine:

```ts
type DiagnosisGate = 'diagnosis' | 'onset' | 'survey'
```

`diagnosis` asks whether the user is already diagnosed, `onset` collects the age
at diagnosis and routes to `/management`, and `survey` renders one question at a
time via `useAssessmentFlow`.

Submission is inlined at the tail of `handleNext()`. When `flow.isLast` is true
it validates, maps the payload, calls the scorer and navigates away:

- `validateAnswersForSubmit(latest)` gate
- `mapPayload(scoredAnswers)` -> `predictAssessment(payload)`
- `setResult(...)`, `clearDraft()`, `navigate('/results')`
- on failure, `setPredictError(...)` and a retry button that re-enters
  `handleNext()`

There is no intermediate screen. That is the gap this plan closes.

## 2. Shape of the change

Add a fourth stage, `review`, between the last question and submission:

```
diagnosis -> onset -> /management
          -> survey -> review -> /results
```

Adding a stage reuses the machine already in the file rather than introducing a
second, parallel notion of "where am I". The review stage needs no new route;
`/assessment` keeps rendering it.

A full page is required rather than the existing `ConfirmDialog`. The survey
renders roughly 30-37 questions depending on branching, because `showIf`
predicates in `Frontend/src/data/questions.ts` hide follow-ups such as
`fatherAgeAtDx`. `ConfirmDialog` takes a single `text` string and is sized for
one short sentence.

## 3. Work items

### 3.1 Translation keys

Add to `Frontend/src/i18n/en.ts`, then mirror in `Frontend/src/i18n/tl.ts`:

| Key | Purpose |
| --- | --- |
| `reviewTitle` | Page heading |
| `reviewIntro` | "Check your answers before we compute your score." |
| `reviewEdit` | Per-row edit button label |
| `reviewConfirm` | Primary action, replaces `seeResults` on this screen |
| `reviewBackToQuestions` | Secondary action, returns to the last question |
| `reviewSkipped` | Shown for optional labs the user skipped |
| `reviewUnanswered` | Shown for a question with no answer |
| `reviewIncompleteWarning` | Banner text when at least one row is unanswered |

`tl.ts` is declared as `TranslationDict`, which is `DeepStringify<typeof en>`.
Any key added to `en.ts` and missing from `tl.ts` therefore fails `tsc -b`. The
type system enforces the Tagalog translation; it cannot be deferred.

### 3.2 `Frontend/src/lib/answerSummary.ts` (new)

A pure module with no React imports, so it stays trivially testable.

`formatAnswerValue(question, answers, t)` returns
`{ text: string; state: 'answered' | 'skipped' | 'missing' }`:

- `choice` -> look up `t.options[String(value)]`, never the raw enum
- `number` / `optionalNumber` -> the value plus `question.unit` when present
- `bmiConfirm` -> `computeBmi(answers.heightCm, answers.weightKg).toFixed(1)`;
  this is a computed pseudo-question whose `id` is not an `AnswerKey`
- `fastingGlucoseMgDl` / `hba1cPercent` -> `skipped` when the matching
  `fastingGlucoseSkipped` / `hba1cSkipped` flag is set, since a skipped lab and
  an unanswered lab must not read the same
- anything `null` / `undefined` -> `missing`

`buildReviewGroups(visible, answers, t)` groups the rows under the eight
`t.section` labels in `visible` order. Each row carries its index within
`flow.visible` so the edit action can jump directly to that question.

### 3.3 `Frontend/src/components/ReviewSummary.tsx` + `.css` (new)

Wrapped in the existing `QuestionCard` shell for visual consistency. Per
section: a heading, then a `<dl>` where each `<dt>` is the question text and
each `<dd>` holds the formatted answer plus an Edit button.

Props: `groups`, `onEdit(index)`, `onConfirm`, `onBack`, `submitting`,
`hasMissing`, `predictError`.

### 3.4 `AssessmentPage.tsx` edits

1. Extend the stage union with `'review'`.
2. Extract the submission tail of `handleNext()` into
   `submitAssessment(latest: AssessmentAnswers)`. Both the review's Confirm
   button and the existing error-retry button call it, so the retry path keeps
   working unchanged.
3. In `handleNext()`, when `flow.isLast`, commit any pending `draftNumber` and
   `setGate('review')` instead of submitting.
4. Render the review branch before the existing `if (!current)` guard.
5. `onEdit(i)` -> `setQuestionIndex(i)`, `setGate('survey')`, and record that
   the user came from the review (see section 4).
6. Show `ProgressBar` as complete on the review screen.

## 4. Editing an answer that changes the branching

The one subtle case. Editing an answer can change which questions exist, because
`getVisibleQuestions` re-evaluates every `showIf` against the current answers.
Changing `fatherT2dm` from `yes` to `no` removes `fatherAgeAtDx`; changing it
from `no` to `yes` *adds* `fatherAgeAtDx` with no answer in it.

So "return to the review after an edit" cannot be unconditional, or a
newly-revealed question gets silently skipped and submitted blank.

Rule to implement: after an edit, recompute the visible list. If every question
still satisfies `flow.isAnswered`, jump back to the review. If any question is
now unanswered, resume the normal one-at-a-time flow starting at the first gap,
and return to the review when the user reaches the end again.

Index-based edit targets also have to be resolved against the freshly computed
`visible` array, not a stale copy, since removing a question shifts every later
index down by one.

## 5. Completeness guard

`validateAnswersForSubmit` in `Frontend/src/lib/assessmentValidation.ts` only
checks `sex`, `age`, `heightCm` and `weightKg`. Every other answer - all of the
lifestyle and family-history questions - can be blank at submit time.

The review screen improves on this at no extra cost, because it is already
iterating each visible question:

- mark each row where `flow.isAnswered(q)` is false as `reviewUnanswered`
- disable Confirm while any row is unanswered
- show `reviewIncompleteWarning` with a link to the first gap

This closes a real hole. Reaching a branch via Back or Edit can currently leave
gaps that submit without complaint.

## 6. Accessibility

- Move focus to the review heading when the stage opens, so keyboard and screen
  reader users are not left on a detached Confirm button.
- `aria-live="polite"` on the incomplete warning.
- Each Edit button needs an accessible name that includes its question, not a
  bare "Edit" repeated 30 times.
- Optional: a `SpeakButton` that reads the summary aloud, consistent with the
  per-question text-to-speech already wired through `useSpeech`.

## 7. Out of scope

No change to `mapPayload`, `predictAssessment`, the Flask API or the model.
Scoring behaviour is identical; this is a pre-submission review only. No new npm
dependencies. `persistAssessmentRecord` still runs once, after confirmation.

## 8. Verification

Build: `cd Frontend && npm run build` (`tsc -b && vite build`). Missing Tagalog
keys surface here as type errors.

Manual passes:

1. Full not-diagnosed path to the end; confirm the review lists every answered
   question under the right section.
2. Edit a plain choice; confirm it returns straight to the review.
3. Edit `fatherT2dm` from `no` to `yes`; confirm `fatherAgeAtDx` appears and is
   collected before the review is reachable again.
4. Skip both optional labs; confirm they read "Skipped" and not "Not answered".
5. Force a prediction failure; confirm the error and retry render on the review
   screen rather than a blank page.
6. Switch language on the review screen; confirm every label and formatted
   answer follows.

There is no test runner in `Frontend` at present - the only `*.test.ts` files
are vendored inside `node_modules/zod` - so verification is build plus the
manual passes above. Adding Vitest would let sections 3.2 and 4 be covered by
unit tests, and is worth considering separately.

## 9. Estimated footprint

| File | Change |
| --- | --- |
| `Frontend/src/lib/answerSummary.ts` | new |
| `Frontend/src/components/ReviewSummary.tsx` | new |
| `Frontend/src/components/ReviewSummary.css` | new |
| `Frontend/src/pages/AssessmentPage.tsx` | stage union, extracted submit, review branch |
| `Frontend/src/i18n/en.ts` | 8 keys |
| `Frontend/src/i18n/tl.ts` | 8 keys |
| `Frontend/src/pages/AssessmentPage.css` | minor, if review styles are not self-contained |
