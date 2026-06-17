# PROJECT_MAP - نظام قاعدة البيانات الذكية للهيئة

## [TECH_STACK]
| الطبقة | التقنية | الإصدار |
|--------|---------|---------|
| Backend | FastAPI | 0.136.3 |
| ORM | SQLAlchemy (sync) | 2.0.50 |
| Database (dev) | SQLite | - |
| Database (prod) | MySQL | 8+ |
| Auth | JWT + bcrypt | - |
| Validation | Pydantic v2 | built-in |
| Frontend | Jinja2 + Bootstrap 5 (RTL) | - |
| Sidebar | Fixed right sidebar with logo, org name, nav links, logout. Hover: golden underline + icon scale + bg highlight | - |
| License Detail | Full view page with document attachment | - |
| Color Theme | Syrian gov: green (#0d5e2e), bronze (#8b6b2a), black (#1a1a1a), white (#fafaf5) | - |
| Excel Export | openpyxl | 3.1+ |
| Logging | structlog | latest |
| Server | Uvicorn | 0.48.0 |
| Language | Python | 3.12.10 |
| Encoding | UTF-8 (Arabic support) | - |

## [SYSTEM_FLOW]
```
Client → FastAPI → SQLAlchemy (sync) → SQLite/MySQL
                ↕
          Jinja2 Templates (RTL Arabic, Bootstrap 5, Syrian gov theme)
                ↕
          JWT Auth Middleware (Cookie + Header)
                ↕
          structlog Logger
                ↕
          AuditLog (all CRUD operations tracked)
```

## [UI THEME]
- Primary: Dark green (`#0d5e2e`, `#14803f`) — cards, buttons
- Secondary: Black (`#1a1a1a`) — navbar, table headers, card headers
- Accent: Bronze (`#8b6b2a`, `#b08838`) — gold buttons, badges, highlights
- Background: Off-white (`#f5f5f0`, `#fafaf5`)
- Logo: Syrian golden eagle emblem (الجمهورية العربية السورية) on login/register pages and navbar
- Organization header: "هيئة دعم وتنمية الإنتاج المحلي والصادرات" on all auth pages
- CSS classes: `bg-syria-green`, `bg-syria-gold`, `bg-syria-black`, `btn-gold`, `btn-gov`, `text-syria-gold`

## [AUTH & ROLES]
### Login
- صفحة الدخول: بريد إلكتروني + كلمة سر فقط (بلا اختيار الصفة)
- شعار الجمهورية العربية السورية (العقاب الذهبي) + عنوان هيئة دعم وتنمية الإنتاج المحلي والصادرات أعلى بطاقة الدخول
- إذا كان المستخدم مضطراً لتغيير كلمة السر (must_change_password=true) يتم توجيهه لصفحة تغيير كلمة السر

### Registration
- اسم كامل + بريد إلكتروني + كلمة سر + تأكيد كلمة السر
- التحقق من تطابق كلمة المرور قبل التسجيل
- المسجلون الجدد يصبحون بصفة "موظف"

### Profile & Password Management
- صفحة `/auth/profile` تعرض معلومات المستخدم مع نموذج تغيير كلمة السر
- إذا كان `must_change_password=true` يتم توجيه المستخدم إلى `/auth/profile/change-password` بعد تسجيل الدخول
- `/auth/change-password` POST: تغيير كلمة السر (يتطلب كلمة السر الحالية + الجديدة + التأكيد)

### Roles
| Role | Dashboard | Admin Nav | User Mgmt | Backup | Permissions | Audit View | CRUD |
|------|-----------|-----------|-----------|--------|-------------|------------|------|
| مدير عام | Full stats | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| مطور النظام | Full stats | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ (users/backup/permissions) |
| معاون مدير عام | Full stats | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| مدير مديرية | **Planning-specific** | ❌ | ❌ | ❌ | ❌ | ❌ | limited |
| رئيس دائرة | Partial | ❌ | ❌ | ❌ | ❌ | ❌ | limited |
| موظف | Employee | ❌ | ❌ | ❌ | ❌ | ❌ | requests only |

### Planning Director (مدير مديرية التخطيط والتعاون الدولي)
- يتم التعرف على مدير التخطيط عبر: `employee.department_id == 4` (مديرية التخطيط والتعاون الدولي) + `role.name == "مدير مديرية"`
- sidebar خاص يظهر فقط: لوحة التحكم، الملف الشخصي، الدوائر، التقارير، الشكاوى
- dashboard خاص: ترحيب باسم المدير، منطقة تنبيهات، تقويم (JavaScript)، إحصائيات سريعة
- `/planning/profile` — ملف شخصي موسّع بمعلومات المديرية والرقم الوظيفي
- `/planning/circles` — يعرض دائرتين: التخطيط والمتابعة (dept 15)، الإحصاء والدراسات (dept 16)
- `/planning/circles/{id}` — يعرض موظفي الدائرة + تقارير الدائرة مع زر تحميل
- `/planning/circles/{id}/employees/{user_id}` — تفاصيل الموظف + سجل التدقيق الكامل
- `/planning/reports` — ثلاث تبويبات: تقارير المدير، تقارير المديريات، تقارير خارجية
- `/planning/reports/create` — نموذج إنشاء تقرير مع اختيار النوع والدائرة والجهة
- `/planning/reports/{id}/tracking` — مسار تتبع التقرير (مثل تتبع الشحنة) مع تحديث الحالة والرد
- `/planning/reports/{id}/upload` — رفع ملف للتقرير
- `/planning/reports/{id}/download` — تحميل ملف التقرير
- `/planning/reports/{id}/respond` — الرد على تقارير المديريات
- نماذج جديدة: `PlanningReport` و `PlanningReportStatus` لتتبع حالة التقارير

## [ARCHITECTURE]
### Domain Modules
1. **auth** ✅ - تسجيل دخول، تسجيل، خروج، JWT، RBAC، إجبار تغيير كلمة السر، صفحة الملف الشخصي
2. **admin** ✅ - لوحة المدير: سجل التدقيق، إدارة الموظفين، تفاصيل الموظف، إدارة الأقسام، إضافة مستخدمين (لمطور النظام)، إعادة تعيين كلمات السر، النسخ الاحتياطي، إدارة الصلاحيات
3. **exporters** ✅ - إدارة المصدرين (إضافة/تعديل/حذف/بحث) + صفحة تفاصيل المصدر + تسجيل Audit
4. **products** ✅ - إدارة المنتجات (إضافة/تعديل/حذف/بحث) + تسجيل Audit
5. **markets** ✅ - إدارة الأسواق الخارجية (إضافة/تعديل/حذف) + تسجيل Audit
6. **licenses** ✅ - إدارة التراخيص (تقديم طلب، اعتماد، رفض) + صفحة تفاصيل + إرفاق مستندات + تسجيل Audit
7. **finance** ✅ - إدارة السجلات المالية (رسوم، تسديد) + تسجيل Audit
8. **documents** ✅ - رفع وتحميل المستندات + تسجيل Audit
9. **reports** ✅ - لوحة إحصائيات + تصدير CSV + تصدير Excel (XLSX)
10. **planning** ✅ - وحدة مدير مديرية التخطيط والتعاون الدولي: لوحة تحكم خاصة، دوائر، موظفين، تقارير مع تتبع الحالة، تقويم، تنبيهات

### New System User Management (مطور النظام)
- **إنشاء مستخدم**: `/admin/users/create` — نموذج إنشاء مستخدم جديد مع صلاحيات محددة (دون ربط بهيكل الهيئة)
- **إعادة تعيين كلمة السر**: `/admin/users/{id}/reset-password` — يولد كلمة سر عشوائية ويجبر المستخدم على تغييرها
- **النسخ الاحتياطي**: `/admin/backup` و `/admin/backup/export` — تصدير نسخة ZIP من قاعدة البيانات
- **إدارة الصلاحيات**: `/admin/permissions` و `/admin/permissions/update` — مصفوفة صلاحيات لكل دور

### Key Auth Behaviors
- `must_change_password` على User: يحول المستخدم لصفحة تغيير كلمة السر بعد تسجيل الدخول
- مطور النظام يمكنه إنشاء مستخدمين جدد وتعيين صلاحياتهم من خلال قائمة الصفات (roles)
- المستخدمون الجدد تكون `must_change_password=True` حتى يغيروا كلمة السر من صفحتهم الشخصية
- إعادة تعيين كلمة السر تحدث كلمة سر عشوائية وتعيد `must_change_password=True`

## [SEED USERS]
| Email | Password | Role |
|-------|----------|------|
| admin@heya.gov.sy | admin123 | مدير عام |
| dev@heya.gov.sy | dev123 | مطور النظام |
| emp@heya.gov.sy | emp123 | موظف |
| planning@heya.gov.sy | planning123 | مدير مديرية التخطيط (مضاف مسبقاً) |

## [ORPHANS & PENDING]
- AI Forecasting للتصدير
- Mobile Application
- تكامل دولي مباشر
- تكامل OCR للمستندات
- تكامل مع جهات حكومية (API خارجية)
- تقارير Word (docx) — النسخ التلقائي Word غير مطبّق (فقط رفع ملفات موجودة)
