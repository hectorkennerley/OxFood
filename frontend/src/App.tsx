import {
  BarChart3, Boxes, CalendarDays, ChefHat, Network, ShoppingCart, Smartphone, Store, Tablet, Trash2, Truck,
} from 'lucide-react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { useApi } from './api'
import Catalogue from './routes/Catalogue'
import Dashboard from './routes/Dashboard'
import Forecast from './routes/Forecast'
import Inventory from './routes/Inventory'
import Journey from './routes/Journey'
import Marketplace from './routes/Marketplace'
import Menu from './routes/Menu'
import SmartBin from './routes/SmartBin'
import Student from './routes/Student'
import Suppliers from './routes/Suppliers'
import TabletApp from './routes/Tablet'

const NAV = [
  { to: '/', label: 'Dashboard', icon: BarChart3 },
  { to: '/forecast', label: 'Bookings & covers', icon: CalendarDays },
  { to: '/catalogue', label: 'Order', icon: ShoppingCart },
  { to: '/suppliers', label: 'Suppliers', icon: Truck },
  { to: '/inventory', label: 'Stock & storage', icon: Boxes },
  { to: '/marketplace', label: 'College marketplace', icon: Store },
  { to: '/menu', label: 'Menu planner', icon: ChefHat },
  { to: '/journey', label: 'Food journey', icon: Network },
]

const DEVICES = [
  { to: '/tablet', label: 'Kitchen tablet', icon: Tablet },
  { to: '/bin', label: 'Smart bin', icon: Trash2 },
  { to: '/student', label: 'Student app', icon: Smartphone },
]

function Shell({ children }: { children: React.ReactNode }) {
  const { data: ctx } = useApi('/context', 10000)
  const home = ctx?.colleges?.find((c: any) => c.id === ctx.home_college_id)
  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 bg-ox text-white flex flex-col">
        <div className="px-5 py-5">
          <div className="text-2xl font-extrabold tracking-tight">🌱 OxFood</div>
          <div className="text-xs text-ox-100/80 mt-1">Distributor → kitchen → student</div>
        </div>
        <div className="px-5 pb-3">
          <div className="rounded-xl bg-white/10 px-3 py-2 text-sm">
            <div className="font-semibold">{home?.name ?? '…'}</div>
            <div className="text-xs text-white/70">Catering manager view</div>
          </div>
        </div>
        <nav className="flex-1 px-3 space-y-0.5">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'}
              className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-white text-ox' : 'text-white/85 hover:bg-white/10'}`}>
              <Icon size={17} /> {label}
            </NavLink>
          ))}
          <div className="label !text-white/50 px-3 pt-5 pb-1">Open on a device</div>
          {DEVICES.map(({ to, label, icon: Icon }) => (
            <a key={to} href={to} target="_blank" rel="noreferrer"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-white/85 hover:bg-white/10">
              <Icon size={17} /> {label} ↗
            </a>
          ))}
        </nav>
        <div className="p-4 text-[11px] text-white/60 space-y-1">
          <div className="chip bg-amber-400/90 text-amber-950">Simulated data</div>
          <div>AI: {ctx?.ai?.mode === 'live' ? `Claude Haiku · ${ctx.ai.calls} calls · $${ctx.ai.cost_usd}` : 'off (rule-based)'}</div>
        </div>
      </aside>
      <main className="flex-1 min-w-0 p-6 lg:p-8">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/tablet" element={<TabletApp />} />
      <Route path="/student" element={<Student />} />
      <Route path="/bin" element={<SmartBin />} />
      <Route path="*" element={
        <Shell>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/catalogue" element={<Catalogue />} />
            <Route path="/suppliers" element={<Suppliers />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/marketplace" element={<Marketplace />} />
            <Route path="/menu" element={<Menu />} />
            <Route path="/journey" element={<Journey />} />
            <Route path="/journey/:lotId" element={<Journey />} />
          </Routes>
        </Shell>
      } />
    </Routes>
  )
}
