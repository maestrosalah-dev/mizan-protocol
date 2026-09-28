# ميزان — Mizan

**بروتوكول مفتوح لمراجعة الأقران العلمية، وأدوات تشغيله.**
مشروع غير ربحي. الكود بترخيص MIT، والنصوص والنماذج بترخيص CC BY 4.0.

> *English summary at the end.*

## الفكرة

المجلة العلمية اليوم تجمع ثلاث وظائف في يد واحدة: حفظ البحث، وتقييمه، ومنح الاعتراف المهني. ميزان يفصلها: الورقة تُودَع في مستودع مفتوح (Zenodo)، ثم تُقيَّم علنًا وفق بروتوكول مكتوب يستطيع أي شخص التحقق من تطبيقه. الثقة تُبنى على أدلة قابلة للتتبع، لا على اسم مجلة.

نص البروتوكول الكامل: [`protocol/`](protocol/README.md) (معرّف DOI على Zenodo).

## ما في هذا المستودع

| المسار | المحتوى |
| --- | --- |
| `mizan/draw.py` | القرعة القابلة للتحقق: التثبيت، والسحب، والتحقق، والقرعة الموزونة |
| `mizan/oplog.py` | سجل المشغل المتسلسل بالبصمات: أي تعديل أو حذف يُكشف |
| `mizan/coi.py` | فحص تضارب المصالح على بيانات خاصة، وإخراج أسماء مستعارة فقط |
| `mizan/pseudonym.py` | إسناد أسماء مستعارة ثابتة، والربط بالهوية يبقى في `private/` |
| `mizan/schedule.py` | مواعيد حق التقييم (م0 إلى م3، وضمان 35 يومًا) |
| `templates/` | نماذج التجربة الأولى |
| `docs/HOW_IT_WORKS.md` | شرح آلية العمل بالتفصيل |
| `examples/demo/` | مثال كامل يعمل دون اتصال |
| `tests/` | اختبارات، تعمل تلقائيًا مع كل تعديل (GitHub Actions) |

## التثبيت

يكفي Python 3.9 أو أحدث. لا مكتبات خارجية، ليستطيع أي شخص قراءة الكود كله والتحقق منه.

```bash
git clone https://github.com/<account>/mizan-protocol.git
cd mizan-protocol
python -m unittest discover -s tests      # يجب أن تنجح كل الاختبارات
python -m mizan --help
```

## الاستعمال في دورة ورقة واحدة

```bash
# 1. مواعيد الطلب
python -m mizan schedule --submitted 2026-11-01

# 2. فحص التضارب (بيانات خاصة) -> قائمة مرشحين علنية بأسماء مستعارة
python -m mizan coi --reviewers private/reviewers.csv --author private/author_P00-01.json --out public/candidates_P00-01.txt

# 3. التثبيت: تجميد القائمة وربطها بجولة drand مستقبلية. انشر الملف فورًا.
python -m mizan commit --list public/candidates_P00-01.txt --request P00-01 --out public/commit_P00-01.json

# 4. السحب بعد صدور الجولة (يجلب العشوائية من drand تلقائيًا)
python -m mizan draw --commit public/commit_P00-01.json --list public/candidates_P00-01.txt --k 3 --out public/draw_P00-01.json

# 5. أي شخص يتحقق
python -m mizan verify --draw public/draw_P00-01.json --list public/candidates_P00-01.txt --check-beacon

# 6. تسجيل كل فعل، وكل انحراف عن النص
python -m mizan log add --request P00-01 --action draw --rule "S5 lottery" --output public/draw_P00-01.json
python -m mizan log add --kind deviation --request P00-01 --action "extend deadline 3d" --manual --reason "documented illness"
python -m mizan log verify
```

## القرعة في ثلاثة أسطر

1. قائمة المرشحين تُجمَّد ببصمة SHA-256 **قبل** وجود الرقم العشوائي.
2. الرقم العشوائي يأتي من منارة عامة عالمية ([drand](https://drand.love)) لا يتحكم فيها أحد منا.
3. الترتيب = فرز المرشحين بقيمة `SHA-256(العشوائية | رقم الطلب | الاسم المستعار)`، وأي شخص يعيد الحساب.

التفاصيل، وحدود ما تضمنه القرعة وما لا تضمنه: [`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md).

## الخصوصية

المجلد `private/` مستثنى من git بالكامل، وفيه الربط بين الأسماء المستعارة والحقيقية. احفظه داخل حاوية مشفّرة. لا يُرفع إلى المستودع أي اسم حقيقي أو بريد.

## الحالة

أدوات التجربة الأولى (Pilot-00): 10 أوراق، تشغيل يدوي، قياس الجدوى لا الصحة. النتائج تُنشر كاملة بما فيها الفشل.

## التواصل

عثماني صالح (Athmani Salah) — باحث مستقل — ORCID [0009-0004-9350-9216](https://orcid.org/0009-0004-9350-9216)
maestro.salah@gmail.com — والنقد مرحّب به أكثر من المديح: [CONTRIBUTING.md](CONTRIBUTING.md).

---

## English summary

Mizan separates the three functions journals bundle (archiving, evaluation, career signal). Papers are deposited on an open repository, then reviewed in public under a written protocol anyone can audit. This repo holds the tooling: a **verifiable reviewer lottery** (candidate list hash-committed before a future [drand](https://drand.love) round; ranking by `SHA-256(randomness|request_id|pseudonym)`; anyone can recompute), a **hash-chained operator log** where edits or deletions are detectable, **conflict-of-interest screening** that outputs pseudonyms only, **stable pseudonyms** with a git-ignored identity map, and the **Right-to-Evaluation schedule** (two reviews guaranteed within 35 days). Pure Python standard library, MIT licensed, non-profit. See `docs/HOW_IT_WORKS.md`.
