# Plan: Employee Expense Approval Workflow Prototype

## Context
Employees lack visibility into their expense claim statuses, and managers lack a clear queue of what needs action. This prototype demonstrates the full end-to-end expense journey — submission, review, approval/rejection — entirely in local React state with no backend. The goal is a "lovable," highly interactive UI that feels polished and production-ready.

---

## Aesthetic Stance
**Minimalist with a dark-ground twist.** Deep slate/navy page background, white card surfaces floating on top. Warm amber primary accent (`#F59E0B`) for approve/submit actions. Crisp status badge colors: yellow (Pending), green (Approved), red (Rejected), steel blue (Completed). This avoids the clichéd gray-card-on-white SaaS look while remaining professional.

**Fonts (Google Fonts via CSS @import in src/index.css):**
- Display: **Outfit** (headings, nav, labels — clean modern sans with personality)
- Body: **Inter** (readable body copy, table cells, form inputs)

---

## Architecture

Single-page app in `src/App.tsx` — no router. View switching via React state. All data lives in a top-level `useState` array.

### State shape
```ts
type Expense = {
  id: string
  employee: string
  amount: number
  category: 'Travel' | 'Meals' | 'Supplies' | 'Software' | 'Conference'
  date: string
  description: string
  status: 'Pending' | 'Approved' | 'Rejected' | 'Completed'
  reviewerComment?: string
  approvalHistory: { action: string; by: string; at: string; comment?: string }[]
}

type View = 'employee' | 'manager'
type Modal = 'none' | 'new-expense' | { type: 'detail'; expenseId: string }
```

Top-level state:
- `expenses: Expense[]` — initialized with 5 realistic mock entries
- `currentView: View`
- `modal: Modal`
- `toasts: Toast[]`

---

## Mock Data (5 entries, varied statuses)
1. Flight to NYC client meeting — $847.50 — Travel — **Completed**
2. Team lunch after product launch — $124.30 — Meals — **Approved**
3. Adobe Creative Cloud annual — $599.99 — Software — **Pending**
4. Hotel for Chicago conference — $312.00 — Conference — **Rejected** (with comment)
5. Office printer paper & toner — $89.45 — Supplies — **Pending**

---

## Files to Create / Modify

### `src/index.css`
- Add Google Fonts `@import` for Outfit and Inter (before `@import 'tailwindcss'`)
- Add CSS custom properties for design tokens: `--background`, `--foreground`, `--card`, `--primary`, `--border`, etc.
- Set `font-family` defaults on `body`
- Hide scrollbars by default, reveal on hover

### `src/App.tsx`
Full rewrite. Contains all state and renders:
- `<Navbar>` — role switcher toggle (Employee / Manager)
- `<EmployeeDashboard>` or `<ManagerDashboard>` based on `currentView`
- `<NewExpenseModal>` — conditionally rendered
- `<ExpenseDetailModal>` — conditionally rendered  
- `<ToastContainer>` — portal-free fixed overlay

### Component structure (all inline in App.tsx or extracted to `src/components/` if complex):

**Navbar**
- Logo + app name ("ExpenseFlow")
- Role switcher: two tabs "My Expenses" / "Approver View" with smooth active indicator
- Avatar placeholder

**EmployeeDashboard**
- Header: "My Expenses" + stats row (total submitted, pending count, approved total amount)
- "Submit New Expense" CTA button (amber, prominent)
- Expense table/card list with columns: Description, Category, Date, Amount, Status badge, Action
- Status badges: color-coded pill chips
- Empty state if no expenses

**ManagerDashboard**
- Header: "Pending Approvals" with count badge
- Priority list: cards for each Pending expense showing employee name, amount, category, date, urgency indicator
- Tabs: "Action Required" | "All Submissions" 
- Clicking any card opens ExpenseDetailModal

**NewExpenseModal**
- Slide-up or fade-in modal with backdrop
- Fields: Amount (number input), Category (select), Date (date input), Description (textarea)
- Mock "Upload Receipt" dropzone: dashed border, cloud-upload icon, "Drag & drop or click to browse" text, visual only
- Submit button → adds expense as Pending, shows success toast, closes modal

**ExpenseDetailModal**
- Receipt placeholder: gray image block with receipt icon
- Expense metadata: all fields displayed
- Approval history timeline (visual steps)
- For Pending items: "Approve" (green) + "Reject" (red) buttons + reviewer comment textarea
- For non-Pending: status banner, history only
- Clicking Approve/Reject → updates expense status in state, shows toast, closes modal

**ToastContainer**
- Fixed top-right
- Auto-dismiss after 3.5s
- Slide-in from right animation
- Variants: success (green), error (red), info (blue)

---

## Micro-interactions
- Table rows: subtle hover background lift
- Buttons: scale(0.97) on active, smooth color transitions
- Status badges: shimmer on Pending
- Modal: backdrop fade + content slide-up (CSS transition)
- Toast: slide-in from right, fade-out on dismiss
- Role switcher: animated underline/pill indicator

---

## CSS approach
Use Tailwind utility classes for layout and spacing. Use CSS custom properties (`--primary`, `--card`, etc.) defined in `src/index.css` for the color system, referenced via arbitrary Tailwind values `bg-[var(--card)]` or explicit inline style where Tailwind can't reach. Animations via `@keyframes` in `src/index.css`.

---

## Verification
1. Run dev server (already running at `$PORT`)
2. Confirm Employee Dashboard renders with 5 mock entries and correct status badges
3. Click "Submit New Expense" → fill form → submit → new Pending row appears + toast fires
4. Switch to "Approver View" → see pending expenses listed
5. Click a Pending expense → modal opens with full detail
6. Click "Approve" → status updates to Approved, toast fires, modal closes
7. Click "Reject" + add comment → status updates to Rejected, comment visible in history
8. Verify no console errors
