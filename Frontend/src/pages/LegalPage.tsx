import { AuthNavBar } from '../components/AuthNavBar'
import { PageBackground } from '../components/PageBackground'
import { useLanguage } from '../context/LanguageContext'
import './LegalPage.css'

export function TermsPage() {
  const { t } = useLanguage()
  return (
    <PageBackground>
      <div className="legal-page">
        <AuthNavBar backTo="/register" />
        <article className="legal-page__card">
          <h1>{t.legalTermsTitle}</h1>
          <p className="legal-page__lead">{t.legalTermsLead}</p>
          <p className="legal-page__body">{t.legalTermsBody}</p>
        </article>
      </div>
    </PageBackground>
  )
}

export function PrivacyPage() {
  const { t } = useLanguage()
  return (
    <PageBackground>
      <div className="legal-page">
        <AuthNavBar backTo="/register" />
        <article className="legal-page__card">
          <h1>{t.legalPrivacyTitle}</h1>
          <p className="legal-page__lead">{t.legalPrivacyLead}</p>
          <p className="legal-page__body">{t.legalPrivacyBody}</p>
        </article>
      </div>
    </PageBackground>
  )
}
