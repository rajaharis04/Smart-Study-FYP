// ╔══════════════════════════════════════════════════════════════════╗
// ║              MODELS — DATA CLASSES                               ║
// ║  Backend ke JSON responses ko type-safe Dart objects mein        ║
// ║  convert karne ke liye                                           ║
// ╚══════════════════════════════════════════════════════════════════╝

// ════════════════════════════════════════════════════════════════════
//
//  CONCEPT: JSON → MODEL kaise kaam karta hai?
//
//  Backend bhejta hai (raw JSON string):
//  {"access_token": "eyJ...", "full_name": "Ali Hassan", ...}
//
//  fromJson() method isse Dart object mein convert karta hai:
//  loginResponse.fullName → "Ali Hassan" ✅
//  loginResponse.accessToken → "eyJ..." ✅
//
//  Type safety ka faida:
//  loginResponse.fullName = 42;  ← Compile error! (String chahiye tha)
//
// ════════════════════════════════════════════════════════════════════

// ──────────────────────────────────────────────────────────────────
//  MODEL 1: LoginResponse
//  Login API se aane wala response
//  Backend endpoint: POST /api/auth/login
// ──────────────────────────────────────────────────────────────────

/// Login ke baad backend se mila response store karta hai.
///
/// Backend JSON example:
/// ```json
/// {
///   "access_token": "eyJhbGciOiJIUzI1NiIs...",
///   "token_type": "bearer",
///   "role": "student",
///   "full_name": "Ali Hassan",
///   "must_change_password": true
/// }
/// ```
class LoginResponse {
  // ── Fields ──────────────────────────────────────────────────────
  final String accessToken;       // JWT token — StorageService mein save hoga
  final String tokenType;         // "bearer" — Authorization header mein lagta hai
  final String role;              // "student" ya "instructor"
  final String fullName;          // User ka naam — UI mein dikhane ke liye
  final bool mustChangePassword;  // true → Change Password screen dikhao

  // ── Constructor ─────────────────────────────────────────────────
  const LoginResponse({
    required this.accessToken,
    required this.tokenType,
    required this.role,
    required this.fullName,
    required this.mustChangePassword,
  });

  // ── fromJson() — JSON Map ko LoginResponse object mein convert karo ──
  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    return LoginResponse(
      // json['access_token'] se value lo, String mein convert karo
      accessToken:        json['access_token'] as String,
      tokenType:          json['token_type']   as String,
      role:               json['role']         as String,
      fullName:           json['full_name']    as String,
      mustChangePassword: json['must_change_password'] as bool,
    );
  }

  // ── toJson() — Debug ya testing ke liye ─────────────────────────
  Map<String, dynamic> toJson() => {
    'access_token':         accessToken,
    'token_type':           tokenType,
    'role':                 role,
    'full_name':            fullName,
    'must_change_password': mustChangePassword,
  };

  @override
  String toString() =>
      'LoginResponse(role: $role, fullName: $fullName, mustChange: $mustChangePassword)';
}

// ──────────────────────────────────────────────────────────────────
//  MODEL 2: Lecture
//  Lecture list se har ek lecture ka data
//  Backend endpoint: GET /api/lectures/
// ──────────────────────────────────────────────────────────────────

/// Ek lecture ki saari information store karta hai.
///
/// Backend JSON example:
/// ```json
/// {
///   "id": 1,
///   "title": "Introduction to Algebra",
///   "video_url": "https://storage.example.com/lecture1.mp4",
///   "duration": 3600,
///   "publish_date": "2025-01-15T10:00:00",
///   "status": "published"
/// }
/// ```
class Lecture {
  // ── Fields ──────────────────────────────────────────────────────
  final int id;              // Database primary key
  final String title;        // Lecture ka naam
  final String videoUrl;     // Video file ka URL (video_player package use karega)
  final int duration;        // Duration in seconds (3600 = 1 hour)
  final DateTime publishDate; // Kab publish hua
  final String status;       // "published" | "draft" | "upcoming"

  const Lecture({
    required this.id,
    required this.title,
    required this.videoUrl,
    required this.duration,
    required this.publishDate,
    required this.status,
  });

  // ── fromJson() ──────────────────────────────────────────────────
  factory Lecture.fromJson(Map<String, dynamic> json) {
    return Lecture(
      id:          json['id']          as int,
      title:       json['title']       as String,
      videoUrl:    json['video_url']   as String? ?? '',
      duration:    json['duration']    as int,
      // String se DateTime mein convert karo
      publishDate: DateTime.parse(json['publish_date'] as String),
      status:      json['status']      as String? ?? 'published',
    );
  }

  // ── Computed properties — directly calculate karo ───────────────

  /// Duration ko human-readable format mein convert karo
  /// Example: 3661 seconds → "1h 1m 1s"
  String get durationFormatted {
    final h = duration ~/ 3600;
    final m = (duration % 3600) ~/ 60;
    final s = duration % 60;
    if (h > 0) return '${h}h ${m}m';
    if (m > 0) return '${m}m ${s}s';
    return '${s}s';
  }

  /// Lecture published hai ya nahi
  bool get isPublished => status == 'published';

  Map<String, dynamic> toJson() => {
    'id':           id,
    'title':        title,
    'video_url':    videoUrl,
    'duration':     duration,
    'publish_date': publishDate.toIso8601String(),
    'status':       status,
  };

  @override
  String toString() => 'Lecture(id: $id, title: $title, status: $status)';
}

// ──────────────────────────────────────────────────────────────────
//  MODEL 3: QuizQuestion
//  Quiz ke ek question ka data (Pre-assessment aur Post-quiz dono ke liye)
//  Backend endpoint: POST /api/quiz/generate-pre/
// ──────────────────────────────────────────────────────────────────

/// Ek quiz question aur uske 4 options store karta hai.
///
/// Backend JSON example:
/// ```json
/// {
///   "id": 101,
///   "question_text": "What is 2 + 2?",
///   "option_a": "3",
///   "option_b": "4",
///   "option_c": "5",
///   "option_d": "6",
///   "difficulty": "easy"
/// }
/// ```
class QuizQuestion {
  // ── Fields ──────────────────────────────────────────────────────
  final int id;             // Question ID
  final String questionText; // Actual question
  final String optionA;      // Option A
  final String optionB;      // Option B
  final String optionC;      // Option C
  final String optionD;      // Option D
  final String difficulty;   // "easy" | "medium" | "hard"

  const QuizQuestion({
    required this.id,
    required this.questionText,
    required this.optionA,
    required this.optionB,
    required this.optionC,
    required this.optionD,
    required this.difficulty,
  });

  // ── fromJson() ──────────────────────────────────────────────────
  factory QuizQuestion.fromJson(Map<String, dynamic> json) {
    return QuizQuestion(
      id:           json['id']            as int,
      questionText: json['question_text'] as String,
      optionA:      json['option_a']      as String,
      optionB:      json['option_b']      as String,
      optionC:      json['option_c']      as String,
      optionD:      json['option_d']      as String,
      difficulty:   json['difficulty']    as String,
    );
  }

  /// Options ko list mein convert karo — UI mein loop lagane ke liye
  /// Returns: [('A', 'option text'), ('B', 'option text'), ...]
  List<MapEntry<String, String>> get optionsList => [
    MapEntry('A', optionA),
    MapEntry('B', optionB),
    MapEntry('C', optionC),
    MapEntry('D', optionD),
  ];

  Map<String, dynamic> toJson() => {
    'id':            id,
    'question_text': questionText,
    'option_a':      optionA,
    'option_b':      optionB,
    'option_c':      optionC,
    'option_d':      optionD,
    'difficulty':    difficulty,
  };

  @override
  String toString() => 'QuizQuestion(id: $id, difficulty: $difficulty)';
}

// ──────────────────────────────────────────────────────────────────
//  MODEL 4: Dashboard
//  Dashboard screen ke liye overall stats
//  Backend endpoint: GET /api/dashboard/
// ──────────────────────────────────────────────────────────────────

/// Student ka overall progress aur stats store karta hai.
///
/// Backend JSON example:
/// ```json
/// {
///   "overall_progress": 65.5,
///   "total_courses": 4,
///   "attendance_percentage": 80.0,
///   "active_quizzes_count": 2
/// }
/// ```
class Dashboard {
  // ── Fields ──────────────────────────────────────────────────────
  final double overallProgress;     // 0.0 to 100.0 — percentage
  final int totalCourses;           // Total enrolled courses
  final double attendancePercentage; // Attendance %
  final int activeQuizzesCount;      // Kitne quizzes abhi active hain

  const Dashboard({
    required this.overallProgress,
    required this.totalCourses,
    required this.attendancePercentage,
    required this.activeQuizzesCount,
  });

  // ── fromJson() ──────────────────────────────────────────────────
  factory Dashboard.fromJson(Map<String, dynamic> json) {
    return Dashboard(
      // num.toDouble() use karo — backend int ya double bhej sakta hai
      overallProgress:      (json['overall_progress']      as num).toDouble(),
      totalCourses:          json['total_courses']          as int,
      attendancePercentage: (json['attendance_percentage'] as num).toDouble(),
      activeQuizzesCount:    json['active_quizzes_count']  as int,
    );
  }

  /// Progress 0.0–1.0 range mein (LinearProgressIndicator ke liye)
  double get progressFraction => overallProgress / 100.0;

  Map<String, dynamic> toJson() => {
    'overall_progress':      overallProgress,
    'total_courses':         totalCourses,
    'attendance_percentage': attendancePercentage,
    'active_quizzes_count':  activeQuizzesCount,
  };

  @override
  String toString() =>
      'Dashboard(progress: $overallProgress%, courses: $totalCourses)';
}

// ──────────────────────────────────────────────────────────────────
//  MODEL 5: Course
//  Enrolled courses ki list
//  Backend endpoint: GET /api/courses/
// ──────────────────────────────────────────────────────────────────

/// Ek enrolled course ka data store karta hai.
///
/// Backend JSON example:
/// ```json
/// {
///   "id": 1,
///   "name": "Mathematics Grade 10",
///   "code": "MATH-10",
///   "instructor": "Dr. Ahmed Khan"
/// }
/// ```
class Course {
  // ── Fields ──────────────────────────────────────────────────────
  final int id;           // Database primary key
  final String name;      // Course ka poora naam
  final String code;      // Short code (e.g., "MATH-10")
  final String instructor; // Instructor ka naam
  final int? creditHours;
  final double? progress;
  final int? sectionId;

  const Course({
    required this.id,
    required this.name,
    required this.code,
    required this.instructor,
    this.creditHours,
    this.progress,
    this.sectionId,
  });

  // ── fromJson() ──────────────────────────────────────────────────
  factory Course.fromJson(Map<String, dynamic> json) {
    return Course(
      id:         json['id']         as int,
      name:       json['name']       as String,
      code:       json['code']       as String,
      instructor: json['instructor'] as String,
      creditHours: json['credit_hours'] as int?,
      progress:   json['progress'] != null ? (json['progress'] as num).toDouble() : null,
      sectionId:   json['section_id'] as int?,
    );
  }

  Map<String, dynamic> toJson() => {
    'id':         id,
    'name':       name,
    'code':       code,
    'instructor': instructor,
    'credit_hours': creditHours,
    'progress': progress,
    'section_id': sectionId,
  };

  @override
  String toString() => 'Course(id: $id, code: $code, name: $name)';
}

// ──────────────────────────────────────────────────────────────────
//  MODEL 6: Student
//  Logged-in student ka profile
//  Backend endpoint: GET /api/students/me/
// ──────────────────────────────────────────────────────────────────

/// Student ka profile data store karta hai.
///
/// Backend JSON example:
/// ```json
/// {
///   "id": 42,
///   "full_name": "Ali Hassan",
///   "email": "ali.hassan@school.edu",
///   "role": "student"
/// }
/// ```
class Student {
  // ── Fields ──────────────────────────────────────────────────────
  final int id;         // Student ID
  final String fullName; // Display name
  final String email;   // Email address
  final String role;    // "student" ya "instructor"
  final String? regNumber;
  final String? department;
  final String? batch;
  final String? profilePicture;

  const Student({
    required this.id,
    required this.fullName,
    required this.email,
    required this.role,
    this.regNumber,
    this.department,
    this.batch,
    this.profilePicture,
  });

  // ── fromJson() ──────────────────────────────────────────────────
  factory Student.fromJson(Map<String, dynamic> json) {
    return Student(
      id:          json['id']          as int,
      fullName:    json['full_name']   as String,
      email:       json['email']       as String,
      role:        json['role']        as String,
      regNumber:   json['reg_number']  as String?,
      department:  json['department']  as String?,
      batch:       json['batch']       as String?,
      profilePicture: json['profile_picture'] as String?,
    );
  }


  /// First name nikalo (display ke liye)
  String get firstName => fullName.split(' ').first;

  Map<String, dynamic> toJson() => {
    'id':        id,
    'full_name': fullName,
    'email':     email,
    'role':      role,
  };

  @override
  String toString() => 'Student(id: $id, fullName: $fullName, role: $role)';
}

// ──────────────────────────────────────────────────────────────────
//  MODEL 7: TodayLecture
//  Aaj ki lecture schedule
//  Backend endpoint: GET /api/dashboard/today-lectures/
// ──────────────────────────────────────────────────────────────────

/// Aaj ki ek scheduled lecture ka data.
///
/// Backend JSON example:
/// ```json
/// {
///   "lecture_id": 5,
///   "title": "Quadratic Equations",
///   "course_name": "Mathematics Grade 10",
///   "scheduled_time": "2025-01-15T09:00:00",
///   "is_completed": false
/// }
/// ```
class TodayLecture {
  final int lectureId;       // Lecture ID
  final String title;        // Lecture ka naam
  final String courseName;   // Kis course ka lecture hai
  final DateTime scheduledTime; // Kab hai
  final bool isCompleted;    // Dekha ja chuka hai ya nahi

  const TodayLecture({
    required this.lectureId,
    required this.title,
    required this.courseName,
    required this.scheduledTime,
    required this.isCompleted,
  });

  factory TodayLecture.fromJson(Map<String, dynamic> json) {
    return TodayLecture(
      lectureId:     json['lecture_id']   as int,
      title:         json['title']        as String,
      courseName:    json['course_name']  as String,
      scheduledTime: DateTime.parse(json['scheduled_time'] as String),
      isCompleted:   json['is_completed'] as bool,
    );
  }

  @override
  String toString() =>
      'TodayLecture(id: $lectureId, title: $title, done: $isCompleted)';
}

// ──────────────────────────────────────────────────────────────────
//  MODEL 8: ActiveQuiz
//  Abhi available quizzes
//  Backend endpoint: GET /api/dashboard/active-quizzes/
// ──────────────────────────────────────────────────────────────────

/// Ek active (available) quiz ka data.
///
/// Backend JSON example:
/// ```json
/// {
///   "quiz_id": 10,
///   "quiz_type": "post",
///   "lecture_title": "Introduction to Algebra",
///   "due_date": "2025-01-20T23:59:59",
///   "is_attempted": false
/// }
/// ```
class ActiveQuiz {
  final int quizId;         // Quiz ID
  final String quizType;    // "pre" ya "post"
  final String lectureTitle; // Kis lecture se related
  final DateTime? dueDate;  // Deadline (null ho sakti hai)
  final bool isAttempted;   // Attempt kiya ja chuka hai?
  final int? lectureId;     // Lecture ID link

  const ActiveQuiz({
    required this.quizId,
    required this.quizType,
    required this.lectureTitle,
    this.dueDate,            // Optional — nullable
    required this.isAttempted,
    this.lectureId,
  });

  factory ActiveQuiz.fromJson(Map<String, dynamic> json) {
    return ActiveQuiz(
      quizId:       json['quiz_id']      as int,
      quizType:     json['quiz_type']    as String,
      lectureTitle: json['lecture_title'] as String,
      // dueDate optional hai — null check karo
      dueDate: json['due_date'] != null
          ? DateTime.parse(json['due_date'] as String)
          : null,
      isAttempted: json['is_attempted'] as bool,
      lectureId:    json['lecture_id']   as int?,
    );
  }

  /// Quiz type human-readable format mein
  String get quizTypeLabel =>
      quizType == 'pre' ? 'Pre-Assessment' : 'Post Quiz';

  @override
  String toString() =>
      'ActiveQuiz(id: $quizId, type: $quizType, attempted: $isAttempted)';
}

// ──────────────────────────────────────────────────────────────────
//  MODEL 9: QuizResult
//  Quiz submit karne ke baad aane wala result
//  Backend endpoint: POST /api/quiz/submit-pre/ ya /api/quiz/submit-post/
// ──────────────────────────────────────────────────────────────────

/// Quiz submit karne ke baad backend se aaya result.
///
/// Backend JSON example:
/// ```json
/// {
///   "quiz_id": 10,
///   "score": 2,
///   "total": 3,
///   "percentage": 66.7,
///   "feedback": "Good attempt! Review topic X."
/// }
/// ```
class QuizResult {
  final int quizId;       // Quiz ID
  final int score;        // Kitne sahi jawab
  final int total;        // Total questions
  final double percentage; // Percentage score
  final String? feedback;  // Optional feedback message

  const QuizResult({
    required this.quizId,
    required this.score,
    required this.total,
    required this.percentage,
    this.feedback,
  });

  factory QuizResult.fromJson(Map<String, dynamic> json) {
    return QuizResult(
      quizId:     json['quiz_id']   as int,
      score:      json['score']     as int,
      total:      json['total']     as int,
      percentage: (json['percentage'] as num).toDouble(),
      feedback:   json['feedback']  as String?,
    );
  }

  /// Pass/fail check (50% se upar = pass)
  bool get isPassed => percentage >= 50.0;

  @override
  String toString() =>
      'QuizResult(quizId: $quizId, score: $score/$total, %: $percentage)';
}

// ──────────────────────────────────────────────────────────────────
//  MODEL 10: QaResponse
//  Q&A se mila RAG-based answer
//  Backend endpoint: POST /api/qa/ask/
// ──────────────────────────────────────────────────────────────────

/// Student ke question ka AI-generated answer.
///
/// Backend JSON example:
/// ```json
/// {
///   "question": "What is Newton's 2nd law?",
///   "answer": "Force equals mass times acceleration (F = ma).",
///   "sources": ["Physics Chapter 3", "Newton's Laws PDF"]
/// }
/// ```
class QaResponse {
  final String question;        // Student ka original question
  final String answer;          // RAG-generated answer
  final List<String> sources;   // References / sources

  const QaResponse({
    required this.question,
    required this.answer,
    required this.sources,
  });

  factory QaResponse.fromJson(Map<String, dynamic> json) {
    return QaResponse(
      question: json['question'] as String,
      answer:   json['answer']   as String,
      // List<dynamic> ko List<String> mein convert karo
      sources: (json['sources'] as List<dynamic>)
          .map((s) => s as String)
          .toList(),
    );
  }

  @override
  String toString() => 'QaResponse(question: $question, sources: ${sources.length})';
}


// ──────────────────────────────────────────────────────────────────
//  STUDENT ATTENDANCE MODELS
// ──────────────────────────────────────────────────────────────────

class AttendanceItem {
  final String date;
  final String lectureName;
  final int courseId;
  final String courseCode;
  final double watchPercentage;
  final String status; // ✓ | ✗ | P

  const AttendanceItem({
    required this.date,
    required this.lectureName,
    required this.courseId,
    required this.courseCode,
    required this.watchPercentage,
    required this.status,
  });

  factory AttendanceItem.fromJson(Map<String, dynamic> json) {
    return AttendanceItem(
      date: json['date'] as String,
      lectureName: json['lecture_name'] as String,
      courseId: json['course_id'] as int,
      courseCode: json['course_code'] as String,
      watchPercentage: (json['watch_percentage'] as num).toDouble(),
      status: json['status'] as String,
    );
  }
}

class MyAttendanceResponse {
  final List<Course> courses;
  final List<AttendanceItem> attendanceList;
  final double overallAttendance;
  final int presentCount;
  final int absentCount;
  final int partialCount;

  const MyAttendanceResponse({
    required this.courses,
    required this.attendanceList,
    required this.overallAttendance,
    required this.presentCount,
    required this.absentCount,
    required this.partialCount,
  });

  factory MyAttendanceResponse.fromJson(Map<String, dynamic> json) {
    final rawCourses = json['courses'] as List<dynamic>? ?? [];
    final rawAttendance = json['attendance_list'] as List<dynamic>? ?? [];
    return MyAttendanceResponse(
      courses: rawCourses.map((c) => Course.fromJson(c as Map<String, dynamic>)).toList(),
      attendanceList: rawAttendance.map((a) => AttendanceItem.fromJson(a as Map<String, dynamic>)).toList(),
      overallAttendance: (json['overall_attendance'] as num).toDouble(),
      presentCount: json['present_count'] as int,
      absentCount: json['absent_count'] as int,
      partialCount: json['partial_count'] as int,
    );
  }
}


// ──────────────────────────────────────────────────────────────────
//  PROFILE PROGRESS / TOPIC MASTERY MODELS
// ──────────────────────────────────────────────────────────────────

class TopicProgress {
  final int topicId;
  final String title;
  final double mastery;
  final String statusLabel; // Strong, Working, Weak, Very Weak
  final String statusSymbol; // ✓, →, ⚠️, ⚠️⚠️
  final double confidence;
  final double learningPace;
  final double engagement;
  final double hintDependency;
  final double learningScore;

  const TopicProgress({
    required this.topicId,
    required this.title,
    required this.mastery,
    required this.statusLabel,
    required this.statusSymbol,
    this.confidence = 0.0,
    this.learningPace = 30.0,
    this.engagement = 0.0,
    this.hintDependency = 0.0,
    this.learningScore = 0.0,
  });

  factory TopicProgress.fromJson(Map<String, dynamic> json) {
    return TopicProgress(
      topicId: json['topic_id'] as int,
      title: json['title'] as String,
      mastery: (json['mastery'] as num).toDouble(),
      statusLabel: json['status_label'] as String,
      statusSymbol: json['status_symbol'] as String,
      confidence: (json['confidence'] as num? ?? 0.0).toDouble(),
      learningPace: (json['learning_pace'] as num? ?? 30.0).toDouble(),
      engagement: (json['engagement'] as num? ?? 0.0).toDouble(),
      hintDependency: (json['hint_dependency'] as num? ?? 0.0).toDouble(),
      learningScore: (json['learning_score'] as num? ?? 0.0).toDouble(),
    );
  }
}

class CourseProgress {
  final int courseId;
  final String courseCode;
  final String courseName;
  final List<TopicProgress> topics;

  const CourseProgress({
    required this.courseId,
    required this.courseCode,
    required this.courseName,
    required this.topics,
  });

  factory CourseProgress.fromJson(Map<String, dynamic> json) {
    final rawTopics = json['topics'] as List<dynamic>? ?? [];
    return CourseProgress(
      courseId: json['course_id'] as int,
      courseCode: json['course_code'] as String,
      courseName: json['course_name'] as String,
      topics: rawTopics.map((t) => TopicProgress.fromJson(t as Map<String, dynamic>)).toList(),
    );
  }
}

class ProfileProgressResponse {
  final List<CourseProgress> courseProgress;
  final List<Map<String, dynamic>> recommendations;
  final List<Map<String, dynamic>> insights;

  const ProfileProgressResponse({
    required this.courseProgress,
    required this.recommendations,
    required this.insights,
  });

  factory ProfileProgressResponse.fromJson(Map<String, dynamic> json) {
    final rawProgress = json['course_progress'] as List<dynamic>? ?? [];
    final rawRecs = json['recommendations'] as List<dynamic>? ?? [];
    final rawInsights = json['insights'] as List<dynamic>? ?? [];
    return ProfileProgressResponse(
      courseProgress: rawProgress.map((p) => CourseProgress.fromJson(p as Map<String, dynamic>)).toList(),
      recommendations: rawRecs.map((r) => Map<String, dynamic>.from(r as Map)).toList(),
      insights: rawInsights.map((i) => Map<String, dynamic>.from(i as Map)).toList(),
    );
  }
}


// ──────────────────────────────────────────────────────────────────
//  QUESTION BANK PRACTICE MODELS
// ──────────────────────────────────────────────────────────────────

class QuestionBankItem {
  final int id;
  final String questionText;
  final String optionA;
  final String optionB;
  final String optionC;
  final String optionD;
  final String yourAnswer;
  final String correctAnswer;
  final String topicTitle;
  final String courseCode;

  const QuestionBankItem({
    required this.id,
    required this.questionText,
    required this.optionA,
    required this.optionB,
    required this.optionC,
    required this.optionD,
    required this.yourAnswer,
    required this.correctAnswer,
    required this.topicTitle,
    required this.courseCode,
  });

  factory QuestionBankItem.fromJson(Map<String, dynamic> json) {
    return QuestionBankItem(
      id: json['id'] as int,
      questionText: json['question_text'] as String,
      optionA: json['option_a'] as String,
      optionB: json['option_b'] as String,
      optionC: json['option_c'] as String,
      optionD: json['option_d'] as String,
      yourAnswer: json['your_answer'] as String,
      correctAnswer: json['correct_answer'] as String,
      topicTitle: json['topic_title'] as String,
      courseCode: json['course_code'] as String,
    );
  }
}
