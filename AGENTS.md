# AGENTS.md — Handover Document

## Project Identity
- **نظام قاعدة البيانات الذكية للهيئة** — Syrian gov HR/export system (FastAPI + SQLAlchemy)
- **Root**: `C:\Users\shlho\Desktop\New folder\project beta`
- **Server**: `uvicorn app.main:app --reload` (run from root)
- **DB**: SQLite → `data.db` (auto-created). Delete it to reseed.
- **Tests**: `pytest tests/ -v --tb=short` (19 tests: 11 pass, 4 fail, 4 error — all failures/errors are PRE-EXISTING test isolation issues, not regressions)

## Tech Stack
- FastAPI 0.136.3 / SQLAlchemy 2.0.50 (sync) / Jinja2 / Bootstrap 5.3 RTL / SQLite (dev) / JWT+bcrypt
- Theme: Syrian gov colors — green (#0d5e2e), bronze (#8b6b2a), black (#1a1a1a), off-white (#fafaf5)
- Sidebar: fixed right 223px, dark bg, gold border-left, box-shadow

## Architecture
```
app/
├── main.py              # FastAPI app, seed data, router includes, static mount
├── templates.py         # render() — auto-injects show_nav, user, user_role, employee, is_planning_director
├── core/                # database.py, config.py, security.py, exceptions.py, audit.py, logging_config.py
├── models/              # 22 SQLAlchemy models (user, employee, role, permission, notification, planning, etc.)
├── modules/             # 16 domain modules (auth, admin, exporters, products, markets, licenses, finance, documents, reports, planning, complaints, events, projects, requests, vacation, notifications)
├── static/
│   ├── css/style.css    # Custom sidebar + theme CSS. All sidebar selectors prefixed with `body` for Bootstrap override.
│   └── js/main.js       # Active link highlighting + notification badge fetch
└── templates/
    ├── layouts/base.html # Master layout: sidebar (3 variants), main-content, notification badge
    ├── auth/             # login.html, register.html, profile.html
    ├── admin/            # audit, employees, departments, user_management, backup, permissions
    ├── planning/         # dashboard, profile, circles, reports, report_form, report_tracking
    ├── notifications/    # list.html
    └── ... (other modules)
```

## Session History (completed work)

### Planning Director Account (مدير التخطيط والتعاون الدولي)
- Added `planning_reports` to `RESOURCE_LIST` in `app/main.py` seed + `app/modules/admin/router.py`
- Added `planning_reports` permissions for roles "مدير مديرية" (view/create/edit) and "مطور النظام" (full)
- Seeded `planning@heya.gov.sy` with `department_id=4`, role "مدير مديرية", employee_no="EMP004"
- Password: `planning123`
- Added notification creation in `planning/router.py` create_report endpoint (when non-director creates report, notifies director)
- Removed completed orphan items from PROJECT_MAP.md

### Sidebar & Design Fix (الأعمدة الجانبية والتصميم)
- **Root cause**: Bootstrap's `.nav-link` (specificity 0-1-0) was overriding custom `.sidebar-nav .nav-link` (0-2-0) in some contexts. Also `display: flex` on `.no-sidebar` with default `flex-direction: row` caused login page layout breakage.
- **CSS fixes**:
  - All sidebar selectors prefixed with `body` for max specificity (`body .sidebar`, `body .sidebar-nav .nav-link`, etc.)
  - Added `box-sizing: border-box` globally
  - Sidebar width: 220px → 223px (accounting for 3px border)
  - Added `box-shadow: -2px 0 12px rgba(0,0,0,0.15)` to sidebar
  - `.main-content` margin-right: 220px → 223px
  - `.main-content.no-sidebar`: added `flex-direction: column` so logo stacks above card
  - Nav-link text: brighter default color, explicit `background: transparent; border: none; font-weight: normal;`
  - Added `.badge-notif` style for notification badge
- **Template fixes**:
  - Added "الإشعارات" link with notification badge to all 3 sidebar variants
  - Changed `id="notif-count"` → `class="badge-notif"` (safer with conditionals)
  - Login/register pages: logo 60px → 50px, `width:100%` on row, `mb-0` on card-footer p
- **JS fix** (`main.js`):
  - Fetch `/notifications/count` on DOM load and update all `.badge-notif` elements
  - Hide badge when count is 0
  - Strip trailing slashes from `href` and `pathname` for active link matching
- **Defensive fix** (`templates.py`): Auto-inject `show_nav=True` when user is authenticated (even if route handler forgets)

## Key Conventions

### Code Style
- **NO comments** in code unless the original file had them
- Surgical edits only — touch only what's broken, match existing patterns
- Arabic UI text, RTL layout (`dir="rtl"` on `<html>`, `direction: rtl` on `body`)
- Import: `from sqlalchemy import select` (NOT `session.query`)
- Route params: use `Depends(get_db)`, `Depends(get_current_user)`
- Render: `return render("template.html", request=request, ...)`
- Exception style: `from app.core.exceptions import Forbidden, NotFound`

### Templates
- `base.html` loaded: Bootstrap 5.3 CDN → Bootstrap Icons CDN → custom `/static/css/style.css`
- Sidebar condition: `{% if show_nav %}` (auto-injected when user is logged in)
- Three sidebar variants: `مطور النظام` → admin panel; `is_planning_director` → planning panel; else → default user panel
- Notification badge: `<span class="badge-notif">0</span>` inside the notifications nav-link

### CSS Specificity
- ALL sidebar selectors MUST be prefixed with `body` to override Bootstrap: `body .sidebar`, `body .sidebar-nav .nav-link`, etc.
- Do NOT remove the `body` prefix, do NOT drop specificity

### Tests
- 11 pass, 8 pre-existing failures/errors (test isolation — duplicate data from non-isolated runs, NOT caused by changes)
- `conftest.py` deletes `data.db` before each test session
- Do NOT "fix" the pre-existing failing tests unless explicitly asked

## Seed Users
| Email | Password | Role | Notes |
|---|---|---|---|
| admin@heya.gov.sy | admin123 | مدير عام | Full access |
| dev@heya.gov.sy | dev123 | مطور النظام | Developer panel |
| emp@heya.gov.sy | emp123 | موظف | Basic employee |
| planning@heya.gov.sy | planning123 | مدير مديرية | Dept 4, planning director |

## Known Pitfalls
1. **Sidebar CSS**: Always use `body` prefix on sidebar selectors. Bootstrap's `.nav-link` will override without it.
2. **show_nav**: Don't rely on route handlers passing it — `templates.py` auto-injects `show_nav=True` when user is authenticated. Login/register pages pass `show_nav=False` explicitly.
3. **Notification creation**: When adding notification logic, verify the notifications router exists at `app/modules/notifications/router.py` with prefix `/notifications`.
4. **Test isolation**: Existing test failures are pre-existing (409 Conflict / MultipleResultsFound). Do not treat them as regressions.
5. **Project path**: Always use the full absolute path `C:\Users\shlho\Desktop\New folder\project beta`. Do not guess.

## Static Files
- Mounted at `/static` in `main.py` line 188
- CSS: `/static/css/style.css`
- JS: `/static/js/main.js`
- Logo: `/static/img/eagle.svg` (Syrian golden eagle)

## PROJECT_MAP.md
Located at root. Update it dynamically when features are completed or deprecated. Follow the same format.
