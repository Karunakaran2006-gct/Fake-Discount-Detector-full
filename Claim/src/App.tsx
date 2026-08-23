import { useState, useCallback } from 'react'

// ─── Types ─────────────────────────────────────────────────────────────────────

type Category = 'Travel' | 'Meals' | 'Supplies' | 'Software' | 'Conference'
type Status = 'Pending' | 'AwaitingFinance' | 'Rejected' | 'Completed'
type View = 'employee' | 'manager' | 'finance'
type ToastVariant = 'success' | 'error' | 'info'

interface HistoryEntry {
  action: string
  by: string
  at: string
  comment?: string
}

interface Expense {
  id: string
  employee: string
  amount: number
  category: Category
  date: string
  description: string
  status: Status
  approvalHistory: HistoryEntry[]
}

interface ToastItem {
  id: string
  message: string
  variant: ToastVariant
}

// ─── Mock Data ─────────────────────────────────────────────────────────────────

const INITIAL_EXPENSES: Expense[] = [
  {
    id: 'exp-001',
    employee: 'Jordan Chen',
    amount: 847.5,
    category: 'Travel',
    date: '2026-08-10',
    description: 'Round-trip flight to NYC for Q3 client strategy meeting with Meridian Corp.',
    status: 'Completed',
    approvalHistory: [
      { action: 'Submitted', by: 'Jordan Chen', at: 'Aug 10, 2026 · 9:15 AM' },
      {
        action: 'Approved',
        by: 'Sarah Mitchell',
        at: 'Aug 11, 2026 · 2:30 PM',
        comment: 'Approved. Travel was essential for the deal closure.',
      },
      { action: 'Reimbursed', by: 'Finance Team', at: 'Aug 14, 2026 · 10:00 AM' },
    ],
  },
  {
    id: 'exp-002',
    employee: 'Jordan Chen',
    amount: 124.3,
    category: 'Meals',
    date: '2026-08-15',
    description: 'Team lunch celebrating successful product launch v2.4 — 8 attendees.',
    status: 'AwaitingFinance',
    approvalHistory: [
      { action: 'Submitted', by: 'Jordan Chen', at: 'Aug 15, 2026 · 1:45 PM' },
      {
        action: 'Approved by Manager',
        by: 'Sarah Mitchell',
        at: 'Aug 16, 2026 · 9:00 AM',
        comment: 'Great milestone! Approved — forwarded to Finance.',
      },
    ],
  },
  {
    id: 'exp-006',
    employee: 'Alex Rivera',
    amount: 450.0,
    category: 'Software',
    date: '2026-08-19',
    description: 'JetBrains All Products Pack annual license for development team.',
    status: 'AwaitingFinance',
    approvalHistory: [
      { action: 'Submitted', by: 'Alex Rivera', at: 'Aug 19, 2026 · 10:00 AM' },
      {
        action: 'Approved by Manager',
        by: 'Sarah Mitchell',
        at: 'Aug 20, 2026 · 8:30 AM',
        comment: 'Essential for dev workflow. Approved — forwarded to Finance.',
      },
    ],
  },
  {
    id: 'exp-003',
    employee: 'Jordan Chen',
    amount: 599.99,
    category: 'Software',
    date: '2026-08-18',
    description: 'Adobe Creative Cloud annual subscription — design team license renewal.',
    status: 'Pending',
    approvalHistory: [
      { action: 'Submitted', by: 'Jordan Chen', at: 'Aug 18, 2026 · 11:20 AM' },
    ],
  },
  {
    id: 'exp-004',
    employee: 'Alex Rivera',
    amount: 312.0,
    category: 'Conference',
    date: '2026-08-05',
    description: 'Hotel stay (2 nights) for Chicago DevSummit 2026 conference attendance.',
    status: 'Rejected',
    approvalHistory: [
      { action: 'Submitted', by: 'Alex Rivera', at: 'Aug 5, 2026 · 3:00 PM' },
      {
        action: 'Rejected',
        by: 'Sarah Mitchell',
        at: 'Aug 6, 2026 · 11:00 AM',
        comment: 'Budget freeze on conference travel this quarter. Please resubmit in Q4.',
      },
    ],
  },
  {
    id: 'exp-005',
    employee: 'Jordan Chen',
    amount: 89.45,
    category: 'Supplies',
    date: '2026-08-20',
    description: 'Office supplies: printer paper (3 reams), black toner cartridge, sticky notes.',
    status: 'Pending',
    approvalHistory: [
      { action: 'Submitted', by: 'Jordan Chen', at: 'Aug 20, 2026 · 4:10 PM' },
    ],
  },
]

// ─── Config ────────────────────────────────────────────────────────────────────

const CATEGORY_CONFIG: Record<Category, { icon: string }> = {
  Travel: { icon: '✈️' },
  Meals: { icon: '🍽️' },
  Supplies: { icon: '📦' },
  Software: { icon: '💻' },
  Conference: { icon: '🎤' },
}

interface StatusStyle {
  bg: string
  text: string
  border: string
  dot: string
  label: string
}

const STATUS_STYLE: Record<Status, StatusStyle> = {
  Pending: {
    bg: '#fef3c7',
    text: '#92400e',
    border: '#fde68a',
    dot: '#f59e0b',
    label: 'Awaiting manager',
  },
  AwaitingFinance: {
    bg: '#dbeafe',
    text: '#1e40af',
    border: '#bfdbfe',
    dot: '#3b82f6',
    label: 'Awaiting finance',
  },
  Rejected: {
    bg: '#fee2e2',
    text: '#991b1b',
    border: '#fecaca',
    dot: '#ef4444',
    label: 'Rejected',
  },
  Completed: {
    bg: '#d1fae5',
    text: '#065f46',
    border: '#a7f3d0',
    dot: '#10b981',
    label: 'Reimbursed',
  },
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)

const fmtDate = (d: string) =>
  new Date(d + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

const nowStamp = () =>
  new Date().toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })

// ─── StatusBadge ───────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: Status }) {
  const s = STATUS_STYLE[status]
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '3px 10px',
        borderRadius: 99,
        fontSize: 12,
        fontWeight: 500,
        whiteSpace: 'nowrap',
        background: s.bg,
        color: s.text,
        border: `1px solid ${s.border}`,
        fontFamily: "'Inter', sans-serif",
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.dot, display: 'inline-block', flexShrink: 0 }} />
      {s.label}
    </span>
  )
}

// ─── ToastContainer ────────────────────────────────────────────────────────────

const TOAST_STYLE: Record<ToastVariant, { border: string; icon: string; iconBg: string; iconColor: string }> = {
  success: { border: 'rgba(16,185,129,0.35)', icon: '✓', iconBg: 'rgba(16,185,129,0.2)', iconColor: '#34D399' },
  error: { border: 'rgba(239,68,68,0.35)', icon: '✕', iconBg: 'rgba(239,68,68,0.2)', iconColor: '#F87171' },
  info: { border: 'rgba(99,102,241,0.35)', icon: 'i', iconBg: 'rgba(99,102,241,0.2)', iconColor: '#A5B4FC' },
}

function ToastContainer({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: string) => void }) {
  return (
    <div
      style={{
        position: 'fixed',
        top: 72,
        right: 20,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        pointerEvents: 'none',
      }}
    >
      {toasts.map((t) => {
        const ts = TOAST_STYLE[t.variant]
        return (
          <div
            key={t.id}
            className="toast-enter"
            style={{
              pointerEvents: 'all',
              background: 'rgba(15,23,42,0.95)',
              border: `1px solid ${ts.border}`,
              borderLeft: `3px solid ${ts.iconColor}`,
              borderRadius: 12,
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              minWidth: 290,
              boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
              backdropFilter: 'blur(16px)',
            }}
          >
            <span
              style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                background: ts.iconBg,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 13,
                fontWeight: 700,
                color: ts.iconColor,
                flexShrink: 0,
              }}
            >
              {ts.icon}
            </span>
            <span style={{ color: '#E2E8F0', fontSize: 14, fontWeight: 500, flex: 1 }}>{t.message}</span>
            <button
              onClick={() => onDismiss(t.id)}
              style={{
                color: '#6b7280',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: 18,
                lineHeight: 1,
                padding: '2px 4px',
                transition: 'color 0.15s',
              }}
              onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.color = '#94A3B8')}
              onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.color = '#475569')}
            >
              ×
            </button>
          </div>
        )
      })}
    </div>
  )
}

// ─── Navbar ────────────────────────────────────────────────────────────────────

function Navbar({ view, onViewChange }: { view: View; onViewChange: (v: View) => void }) {
  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        height: 60,
        background: '#ffffff',
        borderBottom: '1px solid #e8e4de',
        display: 'flex',
        alignItems: 'center',
        padding: '0 28px',
        gap: 24,
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: '#1e2d3d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 18,
          }}
        >
          🧾
        </div>
        <div>
          <span
            style={{
              fontFamily: "'Outfit', sans-serif",
              fontWeight: 700,
              fontSize: 16,
              color: '#1a1a1a',
              letterSpacing: '-0.02em',
              display: 'block',
            }}
          >
            ExpenseClaim
          </span>
          <span style={{ fontSize: 11, color: '#9ca3af' }}>Expense approval workflow</span>
        </div>
      </div>

      {/* Role switcher */}
      <div
        style={{
          margin: '0 auto',
          background: 'transparent',
          borderRadius: 11,
          padding: 4,
          display: 'flex',
          border: 'none',
          gap: 4,
        }}
      >
        {([
          { id: 'employee' as View, label: 'My Expenses' },
          { id: 'manager' as View, label: '⚡ Manager' },
          { id: 'finance' as View, label: '💰 Finance' },
        ]).map(({ id, label }) => (
          <button
            key={id}
            onClick={() => onViewChange(id)}
            style={{
              padding: '6px 18px',
              borderRadius: 8,
              border: 'none',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 600,
              fontFamily: "'Outfit', sans-serif",
              transition: 'all 0.2s ease',
              background: view === id ? '#1e2d3d' : 'transparent',
              color: view === id ? '#ffffff' : '#6b7280',
              boxShadow: 'none',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Avatar */}
      <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ textAlign: 'right' }}>
          <div style={{ color: '#1a1a1a', fontSize: 13, fontWeight: 600 }}>
            {view === 'employee' ? 'Jordan Chen' : view === 'manager' ? 'Sarah Mitchell' : 'Priya Nair'}
          </div>
          <div style={{ color: '#9ca3af', fontSize: 11 }}>
            {view === 'employee' ? 'Employee' : view === 'manager' ? 'Manager' : 'Finance Officer'}
          </div>
        </div>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            background:
              view === 'employee'
                ? 'linear-gradient(135deg, #6366F1, #8B5CF6)'
                : view === 'manager'
                  ? 'linear-gradient(135deg, #10B981, #059669)'
                  : 'linear-gradient(135deg, #06B6D4, #0891B2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 13,
            fontWeight: 700,
            color: '#fff',
            border: '2px solid rgba(255,255,255,0.1)',
          }}
        >
          {view === 'employee' ? 'JC' : view === 'manager' ? 'SM' : 'PN'}
        </div>
      </div>
    </nav>
  )
}

// ─── StatsCard ─────────────────────────────────────────────────────────────────

function StatsCard({
  label,
  value,
  sub,
  accentColor,
}: {
  label: string
  value: string
  sub: string
  accentColor: string
}) {
  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid #e8e4de',
        borderRadius: 16,
        padding: '22px 24px',
        flex: 1,
        minWidth: 0,
        position: 'relative',
        overflow: 'hidden',
        transition: 'border-color 0.2s',
      }}
      onMouseEnter={(e) =>
        ((e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.12)')
      }
      onMouseLeave={(e) =>
        ((e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.07)')
      }
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background: accentColor,
          borderRadius: '16px 16px 0 0',
        }}
      />
      <div
        style={{
          color: '#6b7280',
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: '0.09em',
          textTransform: 'uppercase',
          marginBottom: 10,
          fontFamily: "'Outfit', sans-serif",
        }}
      >
        {label}
      </div>
      <div
        style={{
          color: '#1a1a1a',
          fontSize: 30,
          fontWeight: 700,
          letterSpacing: '-0.03em',
          fontFamily: "'Outfit', sans-serif",
          marginBottom: 6,
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      <div style={{ color: '#334155', fontSize: 12 }}>{sub}</div>
    </div>
  )
}

// ─── Employee Dashboard ────────────────────────────────────────────────────────

function EmployeeDashboard({
  expenses,
  onSubmitNew,
  onViewDetail,
}: {
  expenses: Expense[]
  onSubmitNew: () => void
  onViewDetail: (id: string) => void
}) {
  const mine = expenses.filter((e) => e.employee === 'Jordan Chen')
  const pending = mine.filter((e) => e.status === 'Pending').length
  const approvedTotal = mine
    .filter((e) => e.status === 'AwaitingFinance' || e.status === 'Completed')
    .reduce((s, e) => s + e.amount, 0)

  return (
    <div style={{ padding: '80px 28px 56px', maxWidth: 1080, margin: '0 auto' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: 28,
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div>
          <h1
            style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: 32,
              fontWeight: 700,
              color: '#1a1a1a',
              letterSpacing: '-0.03em',
              margin: 0,
              lineHeight: 1.1,
            }}
          >
            My Expenses
          </h1>
          <p style={{ color: '#475569', marginTop: 8, fontSize: 14, margin: '8px 0 0' }}>
            Track and manage your expense claims
          </p>
        </div>
        <button
          onClick={onSubmitNew}
          style={{
            background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
            color: '#0A0F1E',
            border: 'none',
            borderRadius: 11,
            padding: '11px 24px',
            fontSize: 14,
            fontWeight: 700,
            fontFamily: "'Outfit', sans-serif",
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            boxShadow: '0 4px 20px rgba(245,158,11,0.28)',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLButtonElement
            el.style.transform = 'translateY(-2px)'
            el.style.boxShadow = '0 8px 28px rgba(245,158,11,0.4)'
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLButtonElement
            el.style.transform = 'translateY(0)'
            el.style.boxShadow = '0 4px 20px rgba(245,158,11,0.28)'
          }}
          onMouseDown={(e) => ((e.currentTarget as HTMLButtonElement).style.transform = 'scale(0.97)')}
          onMouseUp={(e) => ((e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-2px)')}
        >
          <span style={{ fontSize: 20, lineHeight: 1, marginTop: -1 }}>+</span>
          Submit New Expense
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 28, flexWrap: 'wrap' }}>
        <StatsCard
          label="Total Claims"
          value={String(mine.length)}
          sub="all-time submissions"
          accentColor="linear-gradient(90deg, #6366F1, #8B5CF6)"
        />
        <StatsCard
          label="Pending Review"
          value={String(pending)}
          sub="awaiting approval"
          accentColor="linear-gradient(90deg, #F59E0B, #FBBF24)"
        />
        <StatsCard
          label="Total Approved"
          value={fmt(approvedTotal)}
          sub="approved or reimbursed"
          accentColor="linear-gradient(90deg, #10B981, #34D399)"
        />
      </div>

      {/* Table */}
      <div
        style={{
          background: '#0f1724',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: 18,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid #ede9e3',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <h2
            style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: 15,
              fontWeight: 600,
              color: '#374151',
              margin: 0,
            }}
          >
            Expense Claims
          </h2>
          <span style={{ color: '#334155', fontSize: 13 }}>{mine.length} records</span>
        </div>

        {mine.length === 0 ? (
          <div style={{ padding: 72, textAlign: 'center', color: '#334155' }}>
            <div style={{ fontSize: 52, marginBottom: 16 }}>📋</div>
            <p style={{ fontSize: 16, margin: 0, color: '#475569' }}>
              No expenses yet. Submit your first claim above.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 680 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  {['Description', 'Category', 'Date', 'Amount', 'Status', ''].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: '12px 20px',
                        textAlign: 'left',
                        color: '#9ca3af',
                        fontSize: 11,
                        fontWeight: 600,
                        letterSpacing: '0.09em',
                        textTransform: 'uppercase',
                        fontFamily: "'Outfit', sans-serif",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {mine.map((exp, i) => (
                  <tr
                    key={exp.id}
                    onClick={() => onViewDetail(exp.id)}
                    style={{
                      borderBottom:
                        i < mine.length - 1 ? '1px solid #ede9e3' : 'none',
                      transition: 'background 0.15s ease',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={(e) =>
                      ((e.currentTarget as HTMLTableRowElement).style.background =
                        '#f8f7f4')
                    }
                    onMouseLeave={(e) =>
                      ((e.currentTarget as HTMLTableRowElement).style.background = 'transparent')
                    }
                  >
                    <td style={{ padding: '17px 20px', maxWidth: 280 }}>
                      <div
                        style={{
                          color: '#374151',
                          fontSize: 14,
                          fontWeight: 500,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {exp.description}
                      </div>
                    </td>
                    <td style={{ padding: '17px 20px' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 7, color: '#64748B', fontSize: 13 }}>
                        <span style={{ fontSize: 16 }}>{CATEGORY_CONFIG[exp.category].icon}</span>
                        {exp.category}
                      </span>
                    </td>
                    <td style={{ padding: '17px 20px', color: '#475569', fontSize: 13, whiteSpace: 'nowrap' }}>
                      {fmtDate(exp.date)}
                    </td>
                    <td style={{ padding: '17px 20px' }}>
                      <span
                        style={{
                          color: '#1a1a1a',
                          fontSize: 15,
                          fontWeight: 700,
                          fontFamily: "'Outfit', sans-serif",
                        }}
                      >
                        {fmt(exp.amount)}
                      </span>
                    </td>
                    <td style={{ padding: '17px 20px' }}>
                      <StatusBadge status={exp.status} />
                    </td>
                    <td style={{ padding: '17px 20px', textAlign: 'right' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onViewDetail(exp.id)
                        }}
                        style={{
                          color: '#F59E0B',
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          fontSize: 13,
                          fontWeight: 600,
                          fontFamily: "'Outfit', sans-serif",
                          opacity: 0.7,
                          transition: 'opacity 0.15s',
                          whiteSpace: 'nowrap',
                        }}
                        onMouseEnter={(e) =>
                          ((e.currentTarget as HTMLButtonElement).style.opacity = '1')
                        }
                        onMouseLeave={(e) =>
                          ((e.currentTarget as HTMLButtonElement).style.opacity = '0.7')
                        }
                      >
                        View →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Manager Dashboard ─────────────────────────────────────────────────────────

function ManagerDashboard({
  expenses,
  onViewDetail,
}: {
  expenses: Expense[]
  onViewDetail: (id: string) => void
}) {
  const [tab, setTab] = useState<'pending' | 'all'>('pending')
  const pending = expenses.filter((e) => e.status === 'Pending')
  const displayed = tab === 'pending' ? pending : [...expenses].sort((a, b) => {
    const order: Status[] = ['Pending', 'AwaitingFinance', 'Rejected', 'Completed']
    return order.indexOf(a.status) - order.indexOf(b.status)
  })

  const totalPendingValue = pending.reduce((s, e) => s + e.amount, 0)

  return (
    <div style={{ padding: '80px 28px 56px', maxWidth: 1080, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          <h1
            style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: 32,
              fontWeight: 700,
              color: '#1a1a1a',
              letterSpacing: '-0.03em',
              margin: 0,
              lineHeight: 1.1,
            }}
          >
            Approver Dashboard
          </h1>
          {pending.length > 0 && (
            <span
              style={{
                background: 'rgba(239,68,68,0.15)',
                color: '#EF4444',
                border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: 99,
                padding: '4px 14px',
                fontSize: 13,
                fontWeight: 700,
                fontFamily: "'Outfit', sans-serif",
              }}
            >
              {pending.length} action{pending.length !== 1 ? 's' : ''} required
            </span>
          )}
        </div>
        <p style={{ color: '#475569', marginTop: 8, fontSize: 14 }}>
          Review and act on pending expense submissions
        </p>
      </div>

      {/* Manager stats */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 28, flexWrap: 'wrap' }}>
        <StatsCard
          label="Pending Action"
          value={String(pending.length)}
          sub="require your review"
          accentColor="linear-gradient(90deg, #EF4444, #F87171)"
        />
        <StatsCard
          label="Pending Value"
          value={fmt(totalPendingValue)}
          sub="total awaiting approval"
          accentColor="linear-gradient(90deg, #F59E0B, #FBBF24)"
        />
        <StatsCard
          label="Total Submissions"
          value={String(expenses.length)}
          sub="across all employees"
          accentColor="linear-gradient(90deg, #6366F1, #8B5CF6)"
        />
      </div>

      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          gap: 4,
          marginBottom: 20,
          background: '#f1f0ee',
          borderRadius: 11,
          padding: 4,
          width: 'fit-content',
          border: '1px solid #e8e4de',
        }}
      >
        {[
          { id: 'pending', label: `Action Required (${pending.length})` },
          { id: 'all', label: 'All Submissions' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as 'pending' | 'all')}
            style={{
              padding: '7px 20px',
              borderRadius: 8,
              border: 'none',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 600,
              fontFamily: "'Outfit', sans-serif",
              transition: 'all 0.2s ease',
              background: tab === t.id ? '#ffffff' : 'transparent',
              color: tab === t.id ? '#1a1a1a' : '#64748b',
              boxShadow: tab === t.id ? '0 2px 4px rgba(0,0,0,0.05)' : 'none',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Expense cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {displayed.length === 0 ? (
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e8e4de',
              borderRadius: 18,
              padding: 72,
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 52, marginBottom: 16 }}>🎉</div>
            <p style={{ fontSize: 16, color: '#475569', margin: 0 }}>
              All caught up! No pending approvals.
            </p>
          </div>
        ) : (
          displayed.map((exp) => (
            <div
              key={exp.id}
              onClick={() => onViewDetail(exp.id)}
              style={{
                background: '#ffffff',
                border: `1px solid ${exp.status === 'Pending' ? '#fde68a' : '#e8e4de'}`,
                borderRadius: 16,
                padding: '18px 22px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                gap: 18,
              }}
              onMouseEnter={(e) => {
                const el = e.currentTarget as HTMLDivElement
                el.style.background = '#f8f7f4'
                el.style.transform = 'translateY(-2px)'
                el.style.boxShadow = '0 4px 16px rgba(0,0,0,0.08)'
              }}
              onMouseLeave={(e) => {
                const el = e.currentTarget as HTMLDivElement
                el.style.background = '#ffffff'
                el.style.transform = 'translateY(0)'
                el.style.boxShadow = 'none'
              }}
            >
              {/* Icon */}
              <div
                style={{
                  width: 50,
                  height: 50,
                  borderRadius: 14,
                  background: 'rgba(0,0,0,0.03)',
                  border: '1px solid rgba(0,0,0,0.05)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 24,
                  flexShrink: 0,
                }}
              >
                {CATEGORY_CONFIG[exp.category].icon}
              </div>

              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    color: '#1a1a1a',
                    fontSize: 14,
                    fontWeight: 600,
                    marginBottom: 5,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {exp.description}
                </div>
                <div style={{ color: '#475569', fontSize: 12, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span
                      style={{
                        width: 18,
                        height: 18,
                        borderRadius: '50%',
                        background: '#e0e7ff',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 9,
                        color: '#6366f1',
                        fontWeight: 700,
                      }}
                    >
                      {exp.employee.split(' ').map((n) => n[0]).join('')}
                    </span>
                    {exp.employee}
                  </span>
                  <span style={{ color: '#cbd5e1' }}>·</span>
                  <span>{exp.category}</span>
                  <span style={{ color: '#cbd5e1' }}>·</span>
                  <span>{fmtDate(exp.date)}</span>
                </div>
              </div>

              {/* Right side */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  flexShrink: 0,
                }}
              >
                <div style={{ textAlign: 'right' }}>
                  <div
                    style={{
                      color: '#1a1a1a',
                      fontSize: 20,
                      fontWeight: 700,
                      fontFamily: "'Outfit', sans-serif",
                      letterSpacing: '-0.02em',
                    }}
                  >
                    {fmt(exp.amount)}
                  </div>
                </div>
                <StatusBadge status={exp.status} />
                {exp.status === 'Pending' && (
                  <span
                    style={{
                      color: '#F59E0B',
                      fontSize: 13,
                      fontWeight: 700,
                      fontFamily: "'Outfit', sans-serif",
                    }}
                  >
                    Review →
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ─── Finance Dashboard ────────────────────────────────────────────────────────

function FinanceDashboard({
  expenses,
  onViewDetail,
}: {
  expenses: Expense[]
  onViewDetail: (id: string) => void
}) {
  const queue = expenses.filter((e) => e.status === 'AwaitingFinance')
  const logs = expenses.filter((e) => e.status === 'Completed')
  const totalQueue = queue.reduce((s, e) => s + e.amount, 0)

  const sectionLabel = (text: string): React.CSSProperties => ({
    color: '#334155', fontSize: 11, fontWeight: 600, textTransform: 'uppercase' as const,
    letterSpacing: '0.09em', marginBottom: 12, fontFamily: "'Outfit', sans-serif",
  })

  return (
    <div style={{ padding: '80px 28px 56px', maxWidth: 1080, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          <h1 style={{ fontFamily: "'Outfit', sans-serif", fontSize: 32, fontWeight: 700, color: '#1a1a1a', letterSpacing: '-0.03em', margin: 0 }}>
            Finance Dashboard
          </h1>
          {queue.length > 0 && (
            <span style={{ background: '#e0f7fa', color: '#0891b2', border: '1px solid #bae6fd', borderRadius: 99, padding: '4px 14px', fontSize: 13, fontWeight: 700, fontFamily: "'Outfit', sans-serif" }}>
              {queue.length} to process
            </span>
          )}
        </div>
        <p style={{ color: '#475569', marginTop: 8, fontSize: 14 }}>Process manager-approved expenses and save to audit log</p>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 32, flexWrap: 'wrap' }}>
        <StatsCard label="Queue" value={String(queue.length)} sub="approved by manager" accentColor="linear-gradient(90deg, #06B6D4, #0891B2)" />
        <StatsCard label="Queue Value" value={fmt(totalQueue)} sub="total to process" accentColor="linear-gradient(90deg, #F59E0B, #FBBF24)" />
        <StatsCard label="Processed" value={String(logs.length)} sub="saved to audit log" accentColor="linear-gradient(90deg, #6366F1, #8B5CF6)" />
      </div>

      {/* Approval Queue */}
      <div style={sectionLabel('Approval Queue · ' + queue.length + ' items')}>
        Approval Queue &middot; {queue.length} items
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 36 }}>
        {queue.length === 0 ? (
          <div style={{ background: '#ffffff', border: '1px solid #e8e4de', borderRadius: 18, padding: 60, textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🎉</div>
            <p style={{ fontSize: 15, color: '#475569', margin: 0 }}>All caught up! No expenses awaiting processing.</p>
          </div>
        ) : queue.map((exp) => (
          <div
            key={exp.id}
            onClick={() => onViewDetail(exp.id)}
            style={{ background: '#ffffff', border: '1px solid #bae6fd', borderRadius: 16, padding: '18px 22px', cursor: 'pointer', transition: 'all 0.2s ease', display: 'flex', alignItems: 'center', gap: 18 }}
            onMouseEnter={(e) => { const el = e.currentTarget as HTMLDivElement; el.style.background = '#f0f9ff'; el.style.transform = 'translateY(-2px)'; el.style.boxShadow = '0 4px 16px rgba(0,0,0,0.05)' }}
            onMouseLeave={(e) => { const el = e.currentTarget as HTMLDivElement; el.style.background = '#ffffff'; el.style.transform = 'translateY(0)'; el.style.boxShadow = 'none' }}
          >
            <div style={{ width: 50, height: 50, borderRadius: 14, background: '#f0f9ff', border: '1px solid #bae6fd', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, flexShrink: 0 }}>
              {CATEGORY_CONFIG[exp.category].icon}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: '#1a1a1a', fontSize: 14, fontWeight: 600, marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{exp.description}</div>
              <div style={{ color: '#475569', fontSize: 12 }}>{exp.employee} &middot; {exp.category} &middot; {fmtDate(exp.date)}</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexShrink: 0 }}>
              <span style={{ color: '#1a1a1a', fontSize: 18, fontWeight: 700, fontFamily: "'Outfit', sans-serif" }}>{fmt(exp.amount)}</span>
              <StatusBadge status={exp.status} />
              <span style={{ color: '#06B6D4', fontSize: 13, fontWeight: 700, fontFamily: "'Outfit', sans-serif" }}>Process →</span>
            </div>
          </div>
        ))}
      </div>

      {/* Audit Log */}
      <div style={sectionLabel('Audit Log · ' + logs.length + ' records')}>
        Audit Log &middot; {logs.length} records
      </div>
      <div style={{ background: '#ffffff', border: '1px solid #e8e4de', borderRadius: 18, overflow: 'hidden' }}>
        {logs.length === 0 ? (
          <div style={{ padding: 48, textAlign: 'center' }}>
            <div style={{ fontSize: 36, marginBottom: 10 }}>📋</div>
            <p style={{ color: '#475569', fontSize: 14, margin: 0 }}>No processed expenses yet.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 600 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #ede9e3' }}>
                  {['Description', 'Employee', 'Category', 'Amount', 'Status', 'Logged'].map((h) => (
                    <th key={h} style={{ padding: '12px 20px', textAlign: 'left', color: '#64748b', fontSize: 11, fontWeight: 600, letterSpacing: '0.09em', textTransform: 'uppercase', fontFamily: "'Outfit', sans-serif" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.map((exp, i) => (
                  <tr
                    key={exp.id}
                    onClick={() => onViewDetail(exp.id)}
                    style={{ borderBottom: i < logs.length - 1 ? '1px solid #ede9e3' : 'none', cursor: 'pointer', transition: 'background 0.15s' }}
                    onMouseEnter={(e) => ((e.currentTarget as HTMLTableRowElement).style.background = '#f8f7f4')}
                    onMouseLeave={(e) => ((e.currentTarget as HTMLTableRowElement).style.background = 'transparent')}
                  >
                    <td style={{ padding: '14px 20px', color: '#1a1a1a', fontSize: 13, maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{exp.description}</td>
                    <td style={{ padding: '14px 20px', color: '#475569', fontSize: 13 }}>{exp.employee}</td>
                    <td style={{ padding: '14px 20px', color: '#475569', fontSize: 13 }}>{CATEGORY_CONFIG[exp.category].icon} {exp.category}</td>
                    <td style={{ padding: '14px 20px', color: '#1a1a1a', fontSize: 14, fontWeight: 700, fontFamily: "'Outfit', sans-serif" }}>{fmt(exp.amount)}</td>
                    <td style={{ padding: '14px 20px' }}><StatusBadge status={exp.status} /></td>
                    <td style={{ padding: '14px 20px', color: '#475569', fontSize: 12 }}>
                      {exp.approvalHistory.find((h) => h.action === 'Processed & Logged')?.at ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── New Expense Modal ─────────────────────────────────────────────────────────

type ExpenseFormData = Omit<Expense, 'id' | 'employee' | 'status' | 'approvalHistory'>

function NewExpenseModal({
  onClose,
  onSubmit,
}: {
  onClose: () => void
  onSubmit: (data: ExpenseFormData) => void
}) {
  const today = new Date().toISOString().split('T')[0]
  const [form, setForm] = useState({
    amount: '',
    category: 'Travel' as Category,
    date: today,
    description: '',
  })
  const [dragOver, setDragOver] = useState(false)
  const [fileName, setFileName] = useState('')
  const [focused, setFocused] = useState('')

  const inputStyle = (name: string): React.CSSProperties => ({
    width: '100%',
    background: '#ffffff',
    border: `1px solid ${focused === name ? '#f59e0b' : '#e8e4de'}`,
    borderRadius: 11,
    padding: '12px 14px',
    color: '#1a1a1a',
    fontSize: 14,
    fontFamily: "'Inter', sans-serif",
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.2s',
  })

  const labelStyle: React.CSSProperties = {
    display: 'block',
    color: '#64748b',
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    marginBottom: 8,
    fontFamily: "'Outfit', sans-serif",
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.amount || !form.description.trim()) return
    onSubmit({
      amount: parseFloat(form.amount),
      category: form.category,
      date: form.date,
      description: form.description.trim(),
    })
  }

  const handleFileDrop = (file: File) => {
    setFileName(file.name)
  }

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 200,
        padding: 20,
      }}
    >
      <div
        className="modal-content"
        style={{
          background: '#ffffff',
          border: '1px solid #e8e4de',
          borderRadius: 22,
          width: '100%',
          maxWidth: 540,
          maxHeight: '92vh',
          overflowY: 'auto',
          boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '26px 28px 0',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            marginBottom: 24,
          }}
        >
          <div>
            <h2
              style={{
                fontFamily: "'Outfit', sans-serif",
                fontSize: 22,
                fontWeight: 700,
                color: '#1a1a1a',
                margin: '0 0 6px',
                letterSpacing: '-0.025em',
              }}
            >
              Submit Expense
            </h2>
            <p style={{ color: '#475569', fontSize: 13, margin: 0 }}>
              Fill in the details and attach your receipt
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              color: '#6b7280',
              background: '#f8f7f4',
              border: '1px solid #e8e4de',
              borderRadius: 9,
              width: 34,
              height: 34,
              cursor: 'pointer',
              fontSize: 20,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              lineHeight: 1,
              transition: 'all 0.15s',
              flexShrink: 0,
            }}
            onMouseEnter={(e) => {
              const el = e.currentTarget as HTMLButtonElement
              el.style.background = '#e8e4de'
              el.style.color = '#1a1a1a'
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLButtonElement
              el.style.background = '#f8f7f4'
              el.style.color = '#6b7280'
            }}
          >
            ×
          </button>
        </div>

        <form
          onSubmit={handleSubmit}
          style={{ padding: '0 28px 28px', display: 'flex', flexDirection: 'column', gap: 18 }}
        >
          {/* Amount + Category */}
          <div style={{ display: 'flex', gap: 14 }}>
            <div style={{ flex: 1 }}>
              <label style={labelStyle}>Amount (USD)</label>
              <div style={{ position: 'relative' }}>
                <span
                  style={{
                    position: 'absolute',
                    left: 14,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: '#94a3b8',
                    fontWeight: 600,
                    fontSize: 15,
                    pointerEvents: 'none',
                  }}
                >
                  $
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={form.amount}
                  onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                  onFocus={() => setFocused('amount')}
                  onBlur={() => setFocused('')}
                  placeholder="0.00"
                  style={{
                    ...inputStyle('amount'),
                    paddingLeft: 28,
                    fontWeight: 600,
                    fontFamily: "'Outfit', sans-serif",
                    fontSize: 15,
                  }}
                />
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <label style={labelStyle}>Category</label>
              <select
                value={form.category}
                onChange={(e) => setForm((f) => ({ ...f, category: e.target.value as Category }))}
                onFocus={() => setFocused('category')}
                onBlur={() => setFocused('')}
                style={{
                  ...inputStyle('category'),
                  background: '#ffffff',
                  cursor: 'pointer',
                  appearance: 'none',
                }}
              >
                {(['Travel', 'Meals', 'Supplies', 'Software', 'Conference'] as Category[]).map(
                  (c) => (
                    <option key={c} value={c}>
                      {CATEGORY_CONFIG[c].icon} {c}
                    </option>
                  ),
                )}
              </select>
            </div>
          </div>

          {/* Date */}
          <div>
            <label style={labelStyle}>Expense Date</label>
            <input
              type="date"
              required
              value={form.date}
              onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
              onFocus={() => setFocused('date')}
              onBlur={() => setFocused('')}
              style={{ ...inputStyle('date') }}
            />
          </div>

          {/* Description */}
          <div>
            <label style={labelStyle}>Description</label>
            <textarea
              required
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              onFocus={() => setFocused('description')}
              onBlur={() => setFocused('')}
              placeholder="What was this expense for? Please be specific..."
              rows={3}
              style={{
                ...inputStyle('description'),
                resize: 'vertical',
                lineHeight: 1.6,
              }}
            />
          </div>

          {/* Dropzone */}
          <div>
            <label style={labelStyle}>Receipt</label>
            <div
              onDragOver={(e) => {
                e.preventDefault()
                setDragOver(true)
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault()
                setDragOver(false)
                const f = e.dataTransfer.files[0]
                if (f) handleFileDrop(f)
              }}
              onClick={() => {
                const input = document.createElement('input')
                input.type = 'file'
                input.accept = 'image/*,.pdf'
                input.onchange = (e) => {
                  const f = (e.target as HTMLInputElement).files?.[0]
                  if (f) handleFileDrop(f)
                }
                input.click()
              }}
              style={{
                border: `2px dashed ${
                  dragOver
                    ? '#f59e0b'
                    : fileName
                      ? '#10b981'
                      : '#e8e4de'
                }`,
                borderRadius: 14,
                padding: '28px 20px',
                textAlign: 'center',
                transition: 'all 0.2s ease',
                background: '#f8f7f4',
                cursor: 'pointer',
              }}
            >
              <div style={{ fontSize: 36, marginBottom: 10 }}>
                {fileName ? '✅' : dragOver ? '📂' : '📎'}
              </div>
              <div
                style={{
                  color: fileName ? '#10b981' : '#64748B',
                  fontSize: 14,
                  fontWeight: 600,
                  fontFamily: "'Outfit', sans-serif",
                  marginBottom: 4,
                }}
              >
                {fileName || 'Drag & drop or click to browse'}
              </div>
              <div style={{ color: '#94a3b8', fontSize: 12 }}>
                {fileName ? fileName : 'PNG, JPG, PDF up to 10 MB'}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 12, marginTop: 6 }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                flex: 1,
                padding: '13px',
                border: '1px solid #e8e4de',
                borderRadius: 11,
                background: 'transparent',
                color: '#374151',
                fontSize: 14,
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: "'Outfit', sans-serif",
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                const el = e.currentTarget as HTMLButtonElement
                el.style.background = '#f8f7f4'
                el.style.color = '#1a1a1a'
              }}
              onMouseLeave={(e) => {
                const el = e.currentTarget as HTMLButtonElement
                el.style.background = 'transparent'
                el.style.color = '#374151'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              style={{
                flex: 2,
                padding: '13px',
                border: 'none',
                borderRadius: 11,
                background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
                color: '#ffffff',
                fontSize: 14,
                fontWeight: 700,
                cursor: 'pointer',
                fontFamily: "'Outfit', sans-serif",
                boxShadow: '0 4px 20px rgba(245,158,11,0.3)',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                const el = e.currentTarget as HTMLButtonElement
                el.style.transform = 'translateY(-1px)'
                el.style.boxShadow = '0 8px 24px rgba(245,158,11,0.42)'
              }}
              onMouseLeave={(e) => {
                const el = e.currentTarget as HTMLButtonElement
                el.style.transform = 'none'
                el.style.boxShadow = '0 4px 20px rgba(245,158,11,0.3)'
              }}
              onMouseDown={(e) =>
                ((e.currentTarget as HTMLButtonElement).style.transform = 'scale(0.97)')
              }
              onMouseUp={(e) =>
                ((e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)')
              }
            >
              Submit Expense Claim
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Expense Detail Modal ──────────────────────────────────────────────────────

function ExpenseDetailModal({
  expense,
  onClose,
  onApprove,
  onReject,
  onFinanceProcess,
  isManagerView,
  isFinanceView,
}: {
  expense: Expense
  onClose: () => void
  onApprove: (id: string, comment: string) => void
  onReject: (id: string, comment: string) => void
  onFinanceProcess: (id: string) => void
  isManagerView: boolean
  isFinanceView: boolean
}) {
  const [comment, setComment] = useState('')
  const [commentFocused, setCommentFocused] = useState(false)
  const canManagerAct = isManagerView && expense.status === 'Pending'
  const canFinanceAct = isFinanceView && expense.status === 'AwaitingFinance'
  const canAct = canManagerAct

  const historyDotColor = (i: number, total: number, status: Status): string => {
    if (i < total - 1) return '#6366F1'
    if (status === 'Rejected') return '#EF4444'
    if (status === 'AwaitingFinance') return '#06B6D4'
    if (status === 'Completed') return '#10B981'
    return '#F59E0B'
  }

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 200,
        padding: 20,
      }}
    >
      <div
        className="modal-content"
        style={{
          background: '#ffffff',
          border: '1px solid #e8e4de',
          borderRadius: 22,
          width: '100%',
          maxWidth: 620,
          maxHeight: '92vh',
          overflowY: 'auto',
          boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '26px 28px 22px',
            borderBottom: '1px solid #ede9e3',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 16,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 13,
                  background: '#f8f7f4',
                  border: '1px solid #e8e4de',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 22,
                  flexShrink: 0,
                }}
              >
                {CATEGORY_CONFIG[expense.category].icon}
              </div>
              <div>
                <h2
                  style={{
                    fontFamily: "'Outfit', sans-serif",
                    fontSize: 20,
                    fontWeight: 700,
                    color: '#1a1a1a',
                    margin: '0 0 4px',
                    letterSpacing: '-0.025em',
                  }}
                >
                  Expense Detail
                </h2>
                <div style={{ color: '#475569', fontSize: 12 }}>
                  Submitted by {expense.employee}
                </div>
              </div>
            </div>
            <StatusBadge status={expense.status} />
          </div>
          <button
            onClick={onClose}
            style={{
              color: '#6b7280',
              background: '#f8f7f4',
              border: '1px solid #e8e4de',
              borderRadius: 9,
              width: 34,
              height: 34,
              cursor: 'pointer',
              fontSize: 20,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              lineHeight: 1,
              transition: 'all 0.15s',
              flexShrink: 0,
            }}
            onMouseEnter={(e) => {
              const el = e.currentTarget as HTMLButtonElement
              el.style.background = '#e8e4de'
              el.style.color = '#1a1a1a'
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLButtonElement
              el.style.background = '#f8f7f4'
              el.style.color = '#6b7280'
            }}
          >
            ×
          </button>
        </div>

        <div style={{ padding: '22px 28px 28px', display: 'flex', flexDirection: 'column', gap: 22 }}>
          {/* Receipt placeholder */}
          <div
            style={{
              background: '#f8f7f4',
              border: '1px solid #e8e4de',
              borderRadius: 14,
              height: 130,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 16,
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background:
                  'repeating-linear-gradient(45deg, transparent, transparent 12px, #f1f0ee 12px, #f1f0ee 24px)',
              }}
            />
            <div style={{ textAlign: 'center', position: 'relative' }}>
              <div style={{ fontSize: 42, marginBottom: 8 }}>🧾</div>
              <div style={{ color: '#94a3b8', fontSize: 13 }}>Receipt · {expense.category}</div>
              <div style={{ color: '#cbd5e1', fontSize: 11, marginTop: 2 }}>
                Image preview would appear here
              </div>
            </div>
          </div>

          {/* Details grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { label: 'Employee', value: expense.employee },
              {
                label: 'Amount',
                value: fmt(expense.amount),
              },
              {
                label: 'Category',
                value: `${CATEGORY_CONFIG[expense.category].icon}  ${expense.category}`,
              },
              { label: 'Date', value: fmtDate(expense.date) },
            ].map((f) => (
              <div
                key={f.label}
                style={{
                  background: '#f8f7f4',
                  borderRadius: 12,
                  padding: '14px 16px',
                  border: '1px solid #e8e4de',
                }}
              >
                <div
                  style={{
                    color: '#94a3b8',
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.09em',
                    marginBottom: 6,
                    fontFamily: "'Outfit', sans-serif",
                  }}
                >
                  {f.label}
                </div>
                <div
                  style={{
                    color: '#1a1a1a',
                    fontSize: 15,
                    fontWeight: 600,
                    fontFamily: "'Outfit', sans-serif",
                  }}
                >
                  {f.value}
                </div>
              </div>
            ))}
          </div>

          {/* Description */}
          <div
            style={{
              background: '#f8f7f4',
              borderRadius: 12,
              padding: '16px 18px',
              border: '1px solid #e8e4de',
            }}
          >
            <div
              style={{
                color: '#94a3b8',
                fontSize: 11,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.09em',
                marginBottom: 10,
                fontFamily: "'Outfit', sans-serif",
              }}
            >
              Description
            </div>
            <div style={{ color: '#475569', fontSize: 14, lineHeight: 1.7 }}>
              {expense.description}
            </div>
          </div>

          {/* Approval history */}
          <div>
            <div
              style={{
                color: '#94a3b8',
                fontSize: 11,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.09em',
                marginBottom: 18,
                fontFamily: "'Outfit', sans-serif",
              }}
            >
              Approval Timeline
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {expense.approvalHistory.map((h, i) => {
                const dotColor = historyDotColor(i, expense.approvalHistory.length, expense.status)
                return (
                  <div key={i} style={{ display: 'flex', gap: 16, position: 'relative' }}>
                    {i < expense.approvalHistory.length - 1 && (
                      <div
                        style={{
                          position: 'absolute',
                          left: 11,
                          top: 28,
                          bottom: -14,
                          width: 1,
                          background: '#e8e4de',
                        }}
                      />
                    )}
                    <div
                      style={{
                        width: 24,
                        height: 24,
                        borderRadius: '50%',
                        background: `${dotColor}22`,
                        border: `2px solid ${dotColor}`,
                        flexShrink: 0,
                        marginTop: 2,
                      }}
                    />
                    <div style={{ paddingBottom: i < expense.approvalHistory.length - 1 ? 22 : 0 }}>
                      <div style={{ color: '#1a1a1a', fontSize: 14, fontWeight: 600 }}>
                        {h.action}
                      </div>
                      <div style={{ color: '#64748b', fontSize: 12, marginTop: 2 }}>
                        {h.by} · {h.at}
                      </div>
                      {h.comment && (
                        <div
                          style={{
                            background: '#f8f7f4',
                            borderRadius: 9,
                            padding: '10px 14px',
                            marginTop: 10,
                            color: '#475569',
                            fontSize: 13,
                            fontStyle: 'italic',
                            borderLeft: '2px solid #e8e4de',
                            lineHeight: 1.6,
                          }}
                        >
                          "{h.comment}"
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Approval actions (manager only, pending only) */}
          {canAct && (
            <div
              style={{
                borderTop: '1px solid #ede9e3',
                paddingTop: 22,
                display: 'flex',
                flexDirection: 'column',
                gap: 14,
              }}
            >
              <div>
                <label
                  style={{
                    display: 'block',
                    color: '#64748b',
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    marginBottom: 10,
                    fontFamily: "'Outfit', sans-serif",
                  }}
                >
                  Reviewer Comment (optional)
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  onFocus={() => setCommentFocused(true)}
                  onBlur={() => setCommentFocused(false)}
                  placeholder="Add a note for the employee..."
                  rows={3}
                  style={{
                    width: '100%',
                    background: '#f8f7f4',
                    border: `1px solid ${commentFocused ? '#f59e0b' : '#e8e4de'}`,
                    borderRadius: 11,
                    padding: '12px 14px',
                    color: '#1a1a1a',
                    fontSize: 14,
                    fontFamily: "'Inter', sans-serif",
                    outline: 'none',
                    resize: 'vertical',
                    boxSizing: 'border-box',
                    transition: 'border-color 0.2s',
                    lineHeight: 1.6,
                  }}
                />
              </div>
              <div style={{ display: 'flex', gap: 12 }}>
                <button
                  onClick={() => onReject(expense.id, comment)}
                  style={{
                    flex: 1,
                    padding: '13px',
                    border: '1px solid rgba(239,68,68,0.35)',
                    borderRadius: 11,
                    background: 'rgba(239,68,68,0.08)',
                    color: '#F87171',
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: 'pointer',
                    fontFamily: "'Outfit', sans-serif",
                    transition: 'all 0.2s',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                  }}
                  onMouseEnter={(e) => {
                    const el = e.currentTarget as HTMLButtonElement
                    el.style.background = 'rgba(239,68,68,0.18)'
                    el.style.transform = 'translateY(-1px)'
                  }}
                  onMouseLeave={(e) => {
                    const el = e.currentTarget as HTMLButtonElement
                    el.style.background = 'rgba(239,68,68,0.08)'
                    el.style.transform = 'none'
                  }}
                >
                  <span>✕</span> Reject
                </button>
                <button
                  onClick={() => onApprove(expense.id, comment)}
                  style={{
                    flex: 2,
                    padding: '13px',
                    border: 'none',
                    borderRadius: 11,
                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                    color: '#fff',
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: 'pointer',
                    fontFamily: "'Outfit', sans-serif",
                    boxShadow: '0 4px 20px rgba(16,185,129,0.28)',
                    transition: 'all 0.2s',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                  }}
                  onMouseEnter={(e) => {
                    const el = e.currentTarget as HTMLButtonElement
                    el.style.transform = 'translateY(-1px)'
                    el.style.boxShadow = '0 8px 28px rgba(16,185,129,0.4)'
                  }}
                  onMouseLeave={(e) => {
                    const el = e.currentTarget as HTMLButtonElement
                    el.style.transform = 'none'
                    el.style.boxShadow = '0 4px 20px rgba(16,185,129,0.28)'
                  }}
                  onMouseDown={(e) =>
                    ((e.currentTarget as HTMLButtonElement).style.transform = 'scale(0.97)')
                  }
                  onMouseUp={(e) =>
                    ((e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)')
                  }
                >
                  <span>✓</span> Approve Expense
                </button>
              </div>
            </div>
          )}

          {/* Finance action */}
          {canFinanceAct && (
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)', paddingTop: 22, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ background: 'rgba(6,182,212,0.08)', border: '1px solid rgba(6,182,212,0.2)', borderRadius: 12, padding: '14px 18px' }}>
                <div style={{ color: '#67E8F9', fontSize: 13, fontWeight: 600, marginBottom: 4, fontFamily: "'Outfit', sans-serif" }}>Finance Action Required</div>
                <div style={{ color: '#475569', fontSize: 13 }}>This expense has been approved by the manager. Process it to save to the audit log and mark as Completed.</div>
              </div>
              <button
                onClick={() => onFinanceProcess(expense.id)}
                style={{ padding: '14px', border: 'none', borderRadius: 11, background: 'linear-gradient(135deg, #06B6D4 0%, #0891B2 100%)', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: "'Outfit', sans-serif", boxShadow: '0 4px 20px rgba(6,182,212,0.28)', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
                onMouseEnter={(e) => { const el = e.currentTarget as HTMLButtonElement; el.style.transform = 'translateY(-1px)'; el.style.boxShadow = '0 8px 28px rgba(6,182,212,0.4)' }}
                onMouseLeave={(e) => { const el = e.currentTarget as HTMLButtonElement; el.style.transform = 'none'; el.style.boxShadow = '0 4px 20px rgba(6,182,212,0.28)' }}
              >
                <span>💰</span> Process &amp; Save Log
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [expenses, setExpenses] = useState<Expense[]>(INITIAL_EXPENSES)
  const [view, setView] = useState<View>('employee')
  const [modal, setModal] = useState<'none' | 'new' | string>('none')
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const addToast = useCallback((message: string, variant: ToastVariant = 'success') => {
    const id = `toast-${Date.now()}`
    setToasts((ts) => [...ts, { id, message, variant }])
    setTimeout(() => setToasts((ts) => ts.filter((t) => t.id !== id)), 3800)
  }, [])

  const dismissToast = useCallback(
    (id: string) => setToasts((ts) => ts.filter((t) => t.id !== id)),
    [],
  )

  const handleSubmitExpense = useCallback(
    (data: ExpenseFormData) => {
      const newExp: Expense = {
        id: `exp-${Date.now()}`,
        employee: 'Jordan Chen',
        status: 'Pending',
        approvalHistory: [
          { action: 'Submitted', by: 'Jordan Chen', at: nowStamp() },
        ],
        ...data,
      }
      setExpenses((es) => [newExp, ...es])
      setModal('none')
      addToast('Expense submitted successfully!', 'success')
    },
    [addToast],
  )

  const handleApprove = useCallback(
    (id: string, comment: string) => {
      setExpenses((es) =>
        es.map((e) =>
          e.id !== id
            ? e
            : {
                ...e,
                status: 'AwaitingFinance',
                approvalHistory: [
                  ...e.approvalHistory,
                  {
                    action: 'Approved by Manager',
                    by: 'Sarah Mitchell',
                    at: nowStamp(),
                    comment: (comment.trim() || 'Approved — forwarded to Finance.'),
                  },
                ],
              },
        ),
      )
      setModal('none')
      addToast('Expense approved — forwarded to Finance.', 'success')
    },
    [addToast],
  )

  const handleFinanceProcess = useCallback(
    (id: string) => {
      setExpenses((es) =>
        es.map((e) =>
          e.id !== id
            ? e
            : {
                ...e,
                status: 'Completed',
                approvalHistory: [
                  ...e.approvalHistory,
                  {
                    action: 'Processed & Logged',
                    by: 'Priya Nair',
                    at: nowStamp(),
                  },
                ],
              },
        ),
      )
      setModal('none')
      addToast('Expense processed and saved to audit log.', 'info')
    },
    [addToast],
  )

  const handleReject = useCallback(
    (id: string, comment: string) => {
      setExpenses((es) =>
        es.map((e) =>
          e.id !== id
            ? e
            : {
                ...e,
                status: 'Rejected',
                approvalHistory: [
                  ...e.approvalHistory,
                  {
                    action: 'Rejected',
                    by: 'Sarah Mitchell',
                    at: nowStamp(),
                    comment: comment.trim() || undefined,
                  },
                ],
              },
        ),
      )
      setModal('none')
      addToast('Expense has been rejected.', 'error')
    },
    [addToast],
  )

  const selectedExpense =
    modal !== 'none' && modal !== 'new' ? expenses.find((e) => e.id === modal) : null

  return (
    <div style={{ minHeight: '100vh', background: '#f4f1ec', fontFamily: "'Inter', sans-serif" }}>
      <Navbar view={view} onViewChange={setView} />

      {view === 'employee' ? (
        <EmployeeDashboard
          expenses={expenses}
          onSubmitNew={() => setModal('new')}
          onViewDetail={(id) => setModal(id)}
        />
      ) : view === 'manager' ? (
        <ManagerDashboard expenses={expenses} onViewDetail={(id) => setModal(id)} />
      ) : (
        <FinanceDashboard expenses={expenses} onViewDetail={(id) => setModal(id)} />
      )}

      {modal === 'new' && (
        <NewExpenseModal onClose={() => setModal('none')} onSubmit={handleSubmitExpense} />
      )}

      {selectedExpense && (
        <ExpenseDetailModal
          expense={selectedExpense}
          onClose={() => setModal('none')}
          onApprove={handleApprove}
          onReject={handleReject}
          onFinanceProcess={handleFinanceProcess}
          isManagerView={view === 'manager'}
          isFinanceView={view === 'finance'}
        />
      )}

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}
