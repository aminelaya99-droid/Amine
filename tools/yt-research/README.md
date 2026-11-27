# yt-research — بحث يوتيوب بلا vidIQ وبلا مفتاح API

يخدم على سيرفر GitHub (جهاز Claude ما يوصلش ليوتيوب). كل سطر في الطلب = أمر واحد:

| الأمر | شنو يدير |
|---|---|
| `outliers <قناة ولا @handle> [--limit 60] [--min-ratio 3] [--tab both\|videos\|shorts]` | الفيديوهات اللي فاتت 3 مرات الوسيط (median) تاع مشاهدات القناة، مع الوسوم (tags) إذا يوتيوب خلّا |
| `keywords <كلمات> [--gl DZ] [--hl ar] [--no-latin]` | الاقتراحات الحقيقية تاع البحث في يوتيوب (autocomplete) للجزائر |
| `transcript <فيديو> [--lang ar,en]` | النص الكامل تاع الفيديو بالتوقيت |
| `info <فيديو>` | العنوان، الوسوم، المشاهدات، اللايكات، الوصف، الفصول |

Claude يشغّلها هكذا:

```
tools/remote/job.sh yt-research 'outliers @channel --tab shorts' 'keywords قهوة'
```

النتيجة: ملف `.md` (تقرير) و`.json` (البيانات) لكل سطر، ومن بعد Claude يحلّلها ويحط
التقرير في Drive: `04 – تقارير وتحليلات`.

## حدود

يوتيوب يسدّ ساعات سيرفرات GitHub ("Sign in to confirm you're not a bot"). قائمة
فيديوهات القناة والـ autocomplete عادة يخدمو؛ الوسوم والنصوص ساعات لا. كي يصرا هكا
السطر يخرج `error` والسبب مكتوب في الملف.
