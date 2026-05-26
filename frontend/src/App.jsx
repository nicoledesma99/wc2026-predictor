import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { LanguageProvider } from './i18n/LanguageContext'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Groups from './pages/Groups'
import GroupDetail from './pages/GroupDetail'
import Predictions from './pages/Predictions'
import Favorites from './pages/Favorites'
import ModelInfo from './pages/ModelInfo'

export default function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <div className="min-h-screen" style={{ backgroundColor: '#0f0f0f' }}>
          <Navbar />
          <main
            style={{
              maxWidth: '1200px',
              margin: '0 auto',
              padding: '24px 24px 80px',
              width: '100%',
              boxSizing: 'border-box',
            }}
          >
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/groups" element={<Groups />} />
              <Route path="/groups/:groupId" element={<GroupDetail />} />
              <Route path="/predictions" element={<Predictions />} />
              <Route path="/favorites" element={<Favorites />} />
              <Route path="/model" element={<ModelInfo />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </LanguageProvider>
  )
}
