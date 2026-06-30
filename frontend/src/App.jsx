// HealthChecker/frontend/src/App.jsx
import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage.jsx'
import ApplicationFormPage from './pages/ApplicationFormPage.jsx'
import ApplicationViewPage from './pages/ApplicationViewPage.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/new" element={<ApplicationFormPage mode="create" />} />
      <Route path="/edit/:id" element={<ApplicationFormPage mode="edit" />} />
      <Route path="/view/:id" element={<ApplicationViewPage />} />
    </Routes>
  )
}
