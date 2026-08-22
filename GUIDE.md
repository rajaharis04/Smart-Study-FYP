# SmartStudy — Chalane aur Use karne ki Poori Guide (Admin · Teacher · Student)

Yeh guide bilkul **isi project** ke code ke hisaab se likhi gayi hai. Ismein 4 cheezein
cover hain:
1. Sab kuch **kaise run** karna hai (DB, backend, admin/teacher web, student app)
2. **Admin** ko dashboard par kya-kya karna hai
3. **Teacher** apne students ko video kaise bhejta hai
4. **Student** video kaise dekhta hai + Attention (webcam) monitoring

---

## 0) Login Credentials (seeded)

| Role    | Email                                   | Password      |
|---------|-----------------------------------------|---------------|
| Admin   | `admin@smartstudy.edu`                  | `Admin@123`   |
| Teacher | `asif.minhas@smartstudy.edu`            | `Teacher@123` |
| Student | `student.fa22-bcs-001@smartstudy.edu`   | `Student@123` |

> 16 teachers `firstname.lastname@smartstudy.edu` pattern par, aur 65 students
> `student.<batch>-b<dept>-001@smartstudy.edu` pattern par mojood hain. Sab ka
> password upar wala shared password hai. **Naya account app se khud nahi banta** —
> accounts admin banata hai (ya seed script se aate hain).

---

## 1) System Kaise Run Karein

Char cheezein chalti hain: **PostgreSQL** → **Backend (8001)** → **Admin/Teacher Web (5173)** → **Student App (Flutter Chrome)**.

### (a) PostgreSQL Database
```powershell
cd "C:\Users\PMLS\Desktop\MY_FYP\Smart-Study-FYP\admin_web"
docker-compose up -d
```

### (b) Backend — 2 options

**Option A — CV/Attention ke SAATH (recommended, taake webcam attendance chale):**
```powershell
cd "C:\Users\PMLS\Desktop\MY_FYP\Smart-Study-FYP\admin_web\backend"
.\.venv-attention\Scripts\Activate.ps1
python -X utf8 -m uvicorn main:app --host 0.0.0.0 --port 8001
```

**Option B — lean/normal (bina CV, halka aur fast):**
```powershell
cd "C:\Users\PMLS\Desktop\MY_FYP\Smart-Study-FYP\admin_web\backend"
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8001
```

> **Pehli dafa** DB khali ho to (ek baar):
> ```powershell
> python init_db.py          # admin account + default departments/semester
> python seed_dummy_data.py  # 16 teachers, 65 students, courses, sections
> ```
> Check: browser mein `http://localhost:8001/docs` khulna chahiye.
> Attention check: `http://localhost:8001/api/attention/status` → `cv_available:true`
> (sirf Option A mein true aayega).

### (c) Admin + Teacher Web Panel (React)
```powershell
cd "C:\Users\PMLS\Desktop\MY_FYP\Smart-Study-FYP\admin_web\frontend"
npm install
npm run dev
```
Kholo: `http://localhost:5173` — yahan **Admin aur Teacher dono** login karte hain
(role ke hisaab se alag menu khud dikhta hai).

### (d) Student App (Flutter — Chrome)
```powershell
cd "C:\Users\PMLS\Desktop\MY_FYP\Smart-Study-FYP"
flutter run -d chrome
```
> Student app `http://localhost:8001/api` se baat karti hai. Agar attention chahiye to
> backend **Option A** (CV venv) se chal raha ho. Camera permission ke liye `localhost`
> theek hai (secure context).

---

## 2) RISHTA (Relationship) — Sab kuch aapas mein kaise juda hai

Poora system in cheezon ki **chain** par khada hai. Yehi "teacher ka student se taluq"
banata hai:

```
Department  (CS, SE, EE...)
   └── Semester (Active hona zaroori)          ← registration/courses isi se bandhe
   └── Teacher (department se linked)
   └── Student (department + Academic Section/"batch" se linked)
   └── Course  (department + semester se linked)
         └── Section  = Course + (assigned) Teacher + Semester   ← YEH hai asli PUL
                 └── Enrollment = Student  ↔  Section            ← student is class mein
                        └── Lecture (video)  ← teacher isi section mein upload karta hai
```

**Teacher ↔ Student ka taluq `Section` ke zariye banta hai:**
- `Section.teacher_id` = us class ka **teacher**.
- Us section ki `enrollments` = us class ke **students**.
- Jab teacher us section mein **video upload** karta hai, to wahi video **usi section ke
  enrolled students** ko dikhti hai. Bas — yehi connection hai.

---

## 3) ADMIN — Dashboard par kya karna hai (step-by-step)

Login `http://localhost:5173` par admin se. Left sidebar mein yeh pages hain:
Dashboard, Departments, Teachers, Students, Students & Sections, Courses, Sections,
Enrollments, Semesters, Registration Week, Grading Policy, Reports, Accounts.

Naya setup banane ka **sahi order**:

1. **Semesters** → ek semester ko **Active** karo (registration/courses isi se chalte hain).
   (Seed mein "Spring 2026" already active hai.)
2. **Departments** → department mojood ho (CS/SE/EE seeded hain; naya bhi bana sakte ho).
3. **Teachers** → "Add Teacher" — naam, email, employee-id, department. (Default password
   `Teacher@123` type set hota hai.)
4. **Students** (ya **Students & Sections**) → student banao — naam, email, reg-number,
   department, aur **Academic Section / batch** (jaise FA22-CS-A). Yeh batch aage kaam aata hai.
5. **Courses** → "Add Course" — course name, code, credit hours, department, **semester**.
6. **Sections** → "Create Section" — yahan **Course** + **Assigned Teacher** + **Semester**
   choose karte ho (schedule/room optional). **Yehi teacher ko us class ka maalik banata hai.**
7. **Enrollment** (student ko course/class mein daalna) — **YEH IMPORTANT hai, dhyan se
   parho**. Is app mein **"Enrollments" page par koi Add/Enroll button NAHI hai** — woh page
   sirf pehle se maujood enrollments ko dikhata/approve/drop karta hai. Is liye enrollment
   in mein se kisi ek tareeqe se hoti hai:

   ### Tareeqa A — Registration Week (app ka asli/intended flow)
   1. **Registration Week** page kholo (left sidebar).
   2. **"Offer Course"** button → Course choon + Target (Whole Batch Section jaise
      `FA22-BCS-A`, ya Single Student by reg-no) + Instructor assign → **Create & Offer**.
      (Yeh ek **Section** bana deta hai us batch/student ke liye.)
   3. Us offered course card par **"Hidden → Live"** toggle karo (taake student ko dikhe).
   4. **"Set Deadline"** → future ki date/time do (warna registration band rahegi).
   5. Ab **Student** apni Flutter app mein login kare → **My Courses** khud-ba-khud
      "Course Registration" screen dikhayegi → student us course ko **Register** kare
      (status **PENDING** ho jaata hai).
   6. Admin wapis **Registration Week → "Finalize"** dabaye (ya **Enrollments** page par us
      PENDING row ke saamne green ✓ se approve kare) → status **ACTIVE**.
   7. Ab woh course student ki **My Courses** mein aa gaya; teacher ki uploaded video bhi dikhegi.

   ### Tareeqa B — Sabse tezz (demo/testing ke liye) via Swagger `/docs`
   > Isme na Registration Week chahiye, na student ka wait — turant ACTIVE enrollment ban jaati hai.
   1. Pehle ek **Section** mojood ho (Sections page se banao: Course + Teacher + Semester),
      ya Registration Week se offer karke banao. Section ki **id** note karlo.
      (Section id dekhne ka aasan tareeqa: `GET /api/sections/` Swagger se.)
   2. Student ki **id** chahiye: Swagger `GET /api/students/` chala kar apne student ki `id` le lo.
   3. Browser mein kholo: `http://localhost:8001/docs` → upar **"Authorize"** → admin token
      (pehle `POST /api/auth/login` se `admin@smartstudy.edu` / `Admin@123` ka token lo).
   4. **`POST /api/enrollments/`** → "Try it out" → body:
      ```json
      { "section_id": 1, "student_ids": [18] }
      ```
      (yahan apni section_id aur student id daalo) → **Execute**.
   5. Response `{"enrolled":1,...}` → enrollment turant **ACTIVE**. Student ko foran dikhega.

   > **Note:** Backend mein direct-enroll ka endpoint mojood hai (Tareeqa B), lekin frontend
   > ke Enrollments page par uska button abhi banaya nahi gaya — is liye UI se sirf Tareeqa A
   > (Registration Week) chalti hai. Agar chaho to main Enrollments page par ek
   > **"Enroll Students"** button bhi bana sakta hoon (bolo to laga doon).

**Khulasa — student class mein 2 tarah aata hai:**
- **(i) Self-registration** (Registration Week open ho) → PENDING → Finalize/approve → ACTIVE.
- **(ii) Swagger `POST /enrollments/`** (admin) → turant ACTIVE (demo ke liye behtareen).


Baaki admin pages: **Reports** (at-risk students, department KPIs, audit logs),
**Grading Policy**, **Registration Week** (deadline set), **Accounts** (apna password).

---

## 4) TEACHER — Video apne students ko kaise bheje

Login `http://localhost:5173` par teacher email se (jaise `asif.minhas@smartstudy.edu` /
`Teacher@123`). Teacher ko alag menu milta hai: Dashboard, Topics & Objectives,
**Lectures & Videos**, Quiz Management, Assignments, Class Analytics, Attendance,
Exam Grades, Final Results.

**Video bhejne ka tareeqa:**
1. Left menu → **Lectures & Videos**.
2. Upar **"Active Class"** dropdown se apni section chuno (sirf woh sections dikhengi jo
   admin ne is teacher ko assign ki hain).
3. Do options:
   - **Upload Lecture Video** → Title, Duration (minutes), Description, (optional) Topic,
     **MP4 file** select karo, "**Publish immediately**" ✓ → **Upload Video**.
   - **AI Video Generator** → PDF/text do → AI script draft banata hai → edit → render →
     auto ek lecture bun kar register ho jaata hai.
4. Upload hote hi ek **Lecture** ban jaati hai (us section se bandhi, `is_published=true`),
   aur system auto **10 MCQ post-quiz** bhi bana deta hai.

> Jaise hi lecture publish hoti hai, **us section ke saare enrolled students** ki app
> mein woh course/lecture aa jaati hai. Teacher ko alag se "send" karne ki zaroorat nahi —
> section-membership hi delivery hai.

**Attendance (teacher):** "Attendance" page par teacher har student ka
present/absent dekh/override kar sakta hai — ismein webcam-attention wala natija bhi
reflect hota hai (agar student ne attention monitoring ke saath dekha ho).

---

## 5) STUDENT — Video kaise dekhe + Attention monitoring

Student app (Flutter Chrome) mein login karo (jaise
`student.fa22-bcs-001@smartstudy.edu` / `Student@123`).

1. **My Courses** tab → jitne courses mein enrolled ho, sab dikhenge (progress bar ke saath).
   - Agar **Registration Week** open ho to yahan pehle "Course Registration" screen aayegi
     jahan student khud apni batch ki offered sections register kar sakta hai.
2. Course card par **"View Lectures"** → us section ki published lectures ki list.
3. Kisi lecture par tap → **Lecture Player** khulta hai (video stream hota hai).
4. **Attention & Presence Monitor** dialog aata hai (system khud check karta hai ke aap
   pehle se enrolled hain ya nahi):
   - **"Enroll & Start"** (sirf pehli dafa): ek **guided wizard** khulta hai jismein aapko
     apna **live camera preview** dikhta hai aur 5 poses step-by-step guide hote hain
     (seedha dekho → thoda left → thoda right → thoda upar → smile). Har step par
     "Capture" dabao; aakhri par chehra register ho kar monitoring shuru ho jaati hai.
     (Photo camera ke saamne rakh ke dhoka nahi chalega — **anti-spoof** check lagta hai.)
   - **"Start"**: agar aap pehle se enrolled hain to seedha monitoring shuru.
   - **"Skip"**: bina attention ke normal video.
5. Video ke doran ek **live badge** (upar) + ek **live panel** (camera preview ke saath)
   chalta hai jo real-time batata hai: **Attentive / Looking away / Eyes closed /
   Drowsy / No face / Multiple faces / Not you / Spoof** + attention %.
   - Backend ~**3 fps** par frames leta hai (light checks har frame), aur bhaari models
     (face-recognition, precise **gaze**, anti-spoof) **throttled** chalte hain taake
     CPU par bojh na parre. Ek **jhapki (blink)** normal hai; **lambi aankh band** ya
     zyada band-time = **Drowsy** flag.
6. Video khatam / back par → **Present / Absent** verdict dialog aata hai
   (ratio ≥ 80% → Present), saath mein drowsy episodes / spoof frames / flags bhi, aur
   yeh **Attendance** mein save ho jaata hai.

> **Privacy:** koi video/photo server par save nahi hoti — sirf numbers/metrics store hote hain.
> **Note:** Attention tab hi chalega jab backend **CV venv (Option A)** se chal raha ho aur
> student **Chrome/Edge** par ho (webcam chahiye).
> **Gaze (optional, behtar accuracy):** precise L2CS-Net gaze on karne ke liye CV venv mein:
> `pip install torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cpu`
> phir `pip install git+https://github.com/Ahmednull/L2CS-Net.git` aur
> `python video-lecture/scripts/download_l2cs_weights.py` — backend restart par
> `/api/attention/status` mein `gaze_available:true` aa jayega. Na ho to bhi kaam chalta
> rahega (MediaPipe iris gaze fallback).


---

## 6) Quick End-to-End Test (5 minute)

1. `docker-compose up -d` → DB on.
2. Backend **Option A** (CV venv) on 8001.
3. `npm run dev` (5173) → **Teacher** login → Lectures & Videos → apni section →
   Upload ek chhoti MP4 → Publish. ✅
4. `flutter run -d chrome` → **usi section ka Student** login → My Courses → View Lectures →
   lecture tap → **Enroll & Start** → thodi der dekho → back → **Present/Absent** ✅.
5. Teacher panel → **Attendance** page par us student ka natija verify karo. ✅

---

## 7) Common Issues

- **"No internet" / login fail** → backend on nahi hai ya galat port. Backend 8001 par ho.
  (CORS already fix hai for localhost.)
- **"email is not registered"** → naya email nahi chalega; sirf seeded/admin-created emails.
- **Attention `cv_available:false`** → backend **Option B (lean)** par chal raha hai; **Option A
  (.venv-attention)** se chalao.
- **`cd /d ...` PowerShell error** → PowerShell mein `/d` mat likho; sirf `cd "path"`.
- **Student ko course nahi dikh raha** → (a) enrollment ACTIVE hai? (b) Section ka semester
  **Active** hai? (c) lecture **published** hai?
```
