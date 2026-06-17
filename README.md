# نظام قاعدة البيانات الذكية للهيئة

نظام إلكتروني متكامل لإدارة شؤون هيئة دعم وتنمية الإنتاج المحلي والصادرات.

## التقنيات المستخدمة

- **Backend**: FastAPI + SQLAlchemy
- **Frontend**: Jinja2 + Bootstrap 5.3 (RTL)
- **Database**: SQLite (تطوير) / MySQL (إنتاج)
- **Auth**: JWT + bcrypt

## طريقة التشغيل

**المتطلبات**: Python 3.12+

```bash
# 1. تنزيل المشروع
git clone https://github.com/wiskunde4iedereen-ai/My-Syrian-Project.git
cd "My-Syrian-Project"

# 2. تثبيت الحزم
pip install -r requirements.txt

# 3. تشغيل السيرفر
uvicorn app.main:app --reload
```

ثم افتح المتصفح على: **http://127.0.0.1:8000**

## حسابات الاختبار

| البريد | كلمة السر | الصفة |
|---|---|---|
| admin@heya.gov.sy | admin123 | مدير عام |
| dev@heya.gov.sy | dev123 | مطور النظام |
| planning@heya.gov.sy | planning123 | مدير التخطيط |
| emp@heya.gov.sy | emp123 | موظف |

## الترحيل إلى MySQL (للإنتاج)

عدل ملف `.env`:
```
DATABASE_URL=mysql+pymysql://user:password@localhost/dbname
```

## الترخيص

جميع الحقوق محفوظة للهيئة.
