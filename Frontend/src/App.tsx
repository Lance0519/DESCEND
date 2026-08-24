import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AssessmentProvider } from './context/AssessmentContext'
import { AuthProvider } from './context/AuthContext'
import { LanguageProvider } from './context/LanguageContext'
import { AccessPage } from './pages/AccessPage'
import { AssessmentPage } from './pages/AssessmentPage'
import { AuthCallbackPage } from './pages/AuthCallbackPage'
import { HistoryPage } from './pages/HistoryPage'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { ManagementPage } from './pages/ManagementPage'
import { ProfilePage } from './pages/ProfilePage'
import { RegisterPage } from './pages/RegisterPage'
import { ResultsPage } from './pages/ResultsPage'
import { UserDashboard } from './pages/UserDashboard'

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <AssessmentProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/access" element={<AccessPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/auth/callback" element={<AuthCallbackPage />} />
              <Route path="/assessment" element={<AssessmentPage />} />
              <Route path="/management" element={<ManagementPage />} />
              <Route path="/results" element={<ResultsPage />} />
              <Route path="/account" element={<ProfilePage />} />
              <Route path="/dashboard" element={<UserDashboard />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AssessmentProvider>
      </AuthProvider>
    </LanguageProvider>
  )
}
