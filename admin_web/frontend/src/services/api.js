import axios from 'axios';

const API_BASE = 'http://localhost:8001/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle 401 — redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('admin_token');
      localStorage.removeItem('admin_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ─── AUTH ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  changePassword: (current_password, new_password) =>
    api.post('/auth/change-password', { current_password, new_password }),
  verifyEmail: (email) => api.post('/auth/verify-email', { email }),
  sendOtp: (email) => api.post('/auth/send-otp', { email }),
  verifyOtp: (email, otp) => api.post('/auth/verify-otp', { email, otp }),
  setupPassword: (email, otp, password) =>
    api.post('/auth/setup-password', { email, otp, password }),
};


// ─── DEPARTMENTS ──────────────────────────────────────────────────────────────
export const deptApi = {
  list: () => api.get('/departments/'),
  create: (data) => api.post('/departments/', data),
  update: (id, data) => api.put(`/departments/${id}`, data),
  delete: (id) => api.delete(`/departments/${id}`),
};

// ─── TEACHERS ─────────────────────────────────────────────────────────────────
export const teacherApi = {
  list: () => api.get('/teachers/'),
  create: (data) => api.post('/teachers/', data),
  update: (id, data) => api.put(`/teachers/${id}`, data),
  resetPassword: (id) => api.post(`/teachers/${id}/reset-password`),
  deactivate: (id) => api.delete(`/teachers/${id}`),
};

// ─── STUDENTS ─────────────────────────────────────────────────────────────────
export const studentApi = {
  list: () => api.get('/students/'),
  create: (data) => api.post('/students/', data),
  update: (id, data) => api.put(`/students/${id}`, data),
  resetPassword: (id) => api.post(`/students/${id}/reset-password`),
  delete: (id) => api.delete(`/students/${id}`),
  bulkUpload: (formData) =>
    api.post('/students/bulk-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};

// ─── SEMESTERS ────────────────────────────────────────────────────────────────
export const semesterApi = {
  list: () => api.get('/semesters/'),
  create: (data) => api.post('/semesters/', data),
  update: (id, data) => api.put(`/semesters/${id}`, data),
  delete: (id) => api.delete(`/semesters/${id}`),
  rollover: (id) => api.post(`/semesters/${id}/rollover`),
};

// ─── COURSES ──────────────────────────────────────────────────────────────────
export const courseApi = {
  list: () => api.get('/courses/'),
  create: (data) => api.post('/courses/', data),
  update: (id, data) => api.put(`/courses/${id}`, data),
  delete: (id) => api.delete(`/courses/${id}`),
};

// ─── SECTIONS ─────────────────────────────────────────────────────────────────
export const sectionApi = {
  list: () => api.get('/sections/'),
  create: (data) => api.post('/sections/', data),
  update: (id, data) => api.put(`/sections/${id}`, data),
  delete: (id) => api.delete(`/sections/${id}`),
};

// ─── ENROLLMENTS ──────────────────────────────────────────────────────────────
export const enrollmentApi = {
  list: () => api.get('/enrollments/'),
  enroll: (data) => api.post('/enrollments/', data),
  bulkUpload: (sectionId, formData) =>
    api.post(`/enrollments/bulk-upload/${sectionId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  deactivate: (id) => api.delete(`/enrollments/${id}`),
};

// ─── REPORTS ──────────────────────────────────────────────────────────────────
export const reportsApi = {
  stats: () => api.get('/reports/stats'),
  studentsPerSection: () => api.get('/reports/students-per-section'),
  teachersSummary: () => api.get('/reports/teachers-summary'),
  atRiskSummary: () => api.get('/reports/at-risk-summary'),
  departmentalKpis: () => api.get('/reports/departmental-kpis'),
  auditLogs: () => api.get('/reports/audit-logs'),
};

// ─── GLOBAL ANNOUNCEMENTS ─────────────────────────────────────────────────────
export const announcementApi = {
  list: () => api.get('/announcements/'),
  create: (data) => api.post('/announcements/', data),
  delete: (id) => api.delete(`/announcements/${id}`),
};

// ─── TEACHER PORTAL ────────────────────────────────────────────────────────────
export const teacherPortalApi = {
  dashboard: () => api.get('/teacher/dashboard'),
  sections: () => api.get('/teacher/sections'),
  listTopics: (courseId) => api.get(`/teacher/courses/${courseId}/topics`),
  createTopic: (courseId, data) => api.post(`/teacher/courses/${courseId}/topics`, data),
  deleteTopic: (topicId) => api.delete(`/teacher/topics/${topicId}`),
  uploadMaterial: (topicId, formData) => api.post(`/teacher/topics/${topicId}/materials`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  deleteMaterial: (materialId) => api.delete(`/teacher/materials/${materialId}`),
  uploadLectureVideo: (sectionId, formData) => api.post(`/teacher/sections/${sectionId}/lectures/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  listLectures: (sectionId) => api.get(`/teacher/sections/${sectionId}/lectures`),
  updateLecture: (lectureId, formData) => api.put(`/teacher/lectures/${lectureId}`, formData),
  deleteLecture: (lectureId) => api.delete(`/teacher/lectures/${lectureId}`),
  listQuizzes: () => api.get('/teacher/quizzes'),
  getQuiz: (quizId) => api.get(`/teacher/quizzes/${quizId}`),
  updateQuiz: (quizId, data) => api.put(`/teacher/quizzes/${quizId}`, data),
  getQuizSubmissions: (quizId) => api.get(`/teacher/quizzes/${quizId}/submissions`),
  getQuizAnalytics: (quizId) => api.get(`/teacher/quizzes/${quizId}/analytics`),
  getSectionAnalytics: (sectionId) => api.get(`/teacher/analytics/sections/${sectionId}`),
  getGradebook: (sectionId) => api.get(`/teacher/gradebook/${sectionId}`),
  overrideAttendance: (data) => api.post('/teacher/attendance/override', data),
  overrideGrade: (data) => api.post('/teacher/grades/override', data),
  getNotifications: () => api.get('/teacher/notifications'),
  markNotificationRead: (id) => api.post(`/teacher/notifications/${id}/read`),
  archiveCourse: (courseId) => api.post(`/teacher/courses/${courseId}/archive`),
  listAnnouncements: (sectionId) => api.get(`/teacher/sections/${sectionId}/announcements`),
  createAnnouncement: (sectionId, data) => api.post(`/teacher/sections/${sectionId}/announcements`, data),
  deleteAnnouncement: (announcementId) => api.delete(`/teacher/announcements/${announcementId}`),
};

export default api;

