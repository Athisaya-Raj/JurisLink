import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import { useAuth } from './context/AuthContext.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import RegisterUser from './pages/RegisterUser.jsx'
import RegisterLawyer from './pages/RegisterLawyer.jsx'
import UserDashboard from './pages/dashboard/UserDashboard.jsx'
import LawyerDashboard from './pages/dashboard/LawyerDashboard.jsx'
import NewCase from './pages/cases/NewCase.jsx'
import CaseDetails from './pages/cases/CaseDetails.jsx'
import LawyerCaseDetails from './pages/cases/LawyerCaseDetails.jsx'
import BookAppointment from './pages/appointments/BookAppointment.jsx'
import UserAppointments from './pages/appointments/UserAppointments.jsx'
import LawyerAppointments from './pages/appointments/LawyerAppointments.jsx'
import Invitations from './pages/lawyer/Invitations.jsx'
import InvitationDetails from './pages/lawyer/InvitationDetails.jsx'
import NotFound from './pages/NotFound.jsx'
import Unauthorized from './pages/Unauthorized.jsx'

function HomeRedirect() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={user.role === 'lawyer' ? '/lawyer' : '/dashboard'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/register/user" element={<RegisterUser />} />
      <Route path="/register/lawyer" element={<RegisterLawyer />} />
      <Route path="/unauthorized" element={<Unauthorized />} />
      <Route path="/" element={<HomeRedirect />} />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute roles={['user']}>
            <Layout>
              <UserDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/lawyer"
        element={
          <ProtectedRoute roles={['lawyer']}>
            <Layout>
              <LawyerDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/cases/new"
        element={
          <ProtectedRoute roles={['user']}>
            <Layout>
              <NewCase />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/cases/:id"
        element={
          <ProtectedRoute roles={['user']}>
            <Layout>
              <CaseDetails />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/cases/:id/book"
        element={
          <ProtectedRoute roles={['user']}>
            <Layout>
              <BookAppointment />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/appointments"
        element={
          <ProtectedRoute roles={['user']}>
            <Layout>
              <UserAppointments />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/lawyer/cases/:id"
        element={
          <ProtectedRoute roles={['lawyer']}>
            <Layout>
              <LawyerCaseDetails />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/lawyer/appointments"
        element={
          <ProtectedRoute roles={['lawyer']}>
            <Layout>
              <LawyerAppointments />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/lawyer/invitations"
        element={
          <ProtectedRoute roles={['lawyer']}>
            <Layout>
              <Invitations />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/lawyer/invitations/:id"
        element={
          <ProtectedRoute roles={['lawyer']}>
            <Layout>
              <InvitationDetails />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
