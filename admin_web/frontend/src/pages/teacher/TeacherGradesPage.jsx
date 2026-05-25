import { useState, useEffect } from 'react';
import { teacherPortalApi } from '../../services/api';
import { FileSpreadsheet, Check, X, ShieldAlert, Archive, Award, HelpCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TeacherGradesPage() {
  const [sections, setSections] = useState([]);
  const [selectedSection, setSelectedSection] = useState(null);
  const [gradebook, setGradebook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingGrades, setLoadingGrades] = useState(false);

  // Edit grade modal/inline states
  const [activeOverrideCell, setActiveOverrideCell] = useState(null); // { studentId, quizId, currentScore }
  const [overrideScoreVal, setOverrideScoreVal] = useState('');

  const fetchSections = async () => {
    try {
      const res = await teacherPortalApi.sections();
      setSections(res.data);
      if (res.data.length > 0) {
        setSelectedSection(res.data[0]);
      }
    } catch (err) {
      toast.error('Failed to load courses.');
    } finally {
      setLoading(false);
    }
  };

  const fetchGradebookData = async (sectId) => {
    setLoadingGrades(true);
    try {
      const res = await teacherPortalApi.getGradebook(sectId);
      setGradebook(res.data);
    } catch (err) {
      toast.error('Failed to fetch class gradebook.');
    } finally {
      setLoadingGrades(false);
    }
  };

  useEffect(() => {
    fetchSections();
  }, []);

  useEffect(() => {
    if (selectedSection) {
      fetchGradebookData(selectedSection.id);
    }
  }, [selectedSection]);

  const handleToggleAttendance = async (studentId, lectureId, currentVal) => {
    const newVal = !currentVal;
    try {
      await teacherPortalApi.overrideAttendance({
        student_id: studentId,
        lecture_id: lectureId,
        is_present: newVal
      });
      
      // Update local state immediately
      setGradebook(prev => {
        const copy = { ...prev };
        copy.rows = copy.rows.map(row => {
          if (row.student_id === studentId) {
            row.lectures = row.lectures.map(lec => {
              if (lec.lecture_id === lectureId) {
                lec.is_present = newVal;
              }
              return lec;
            });
          }
          return row;
        });
        return copy;
      });
      
      toast.success('Attendance overridden successfully.');
    } catch (err) {
      toast.error('Failed to override attendance.');
    }
  };

  const handleSaveGradeOverride = async (studentId, quizId) => {
    const parsedScore = parseInt(overrideScoreVal);
    if (isNaN(parsedScore) || parsedScore < 0) {
      toast.error('Please enter a valid numeric score.');
      return;
    }

    try {
      await teacherPortalApi.overrideGrade({
        student_id: studentId,
        quiz_id: quizId,
        correct_count: parsedScore
      });

      // Update local state immediately
      setGradebook(prev => {
        const copy = { ...prev };
        copy.rows = copy.rows.map(row => {
          if (row.student_id === studentId) {
            row.lectures = row.lectures.map(lec => {
              if (lec.quiz_id === quizId) {
                lec.quiz_score = parsedScore;
              }
              return lec;
            });
          }
          return row;
        });
        return copy;
      });

      toast.success('Quiz grade overridden successfully.');
      setActiveOverrideCell(null);
      setOverrideScoreVal('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to override grade.');
    }
  };

  const handleArchiveCourse = async () => {
    if (!window.confirm('WARNING: Concluding the semester will calculate final grades, deactivate all student enrollments, and archive this course. Students will lose active access to slides and videos. Proceed?')) return;
    
    try {
      await teacherPortalApi.archiveCourse(selectedSection.course_id);
      toast.success('Semester concluded! Course archived and student enrollments finalized.');
      fetchGradebookData(selectedSection.id);
    } catch (err) {
      toast.error('Failed to conclude semester.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: '60vh' }}>
        <div className="loading" style={{ fontSize: '18px' }}>Loading Grade Book...</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Selection and Concluding Actions */}
      <div className="card" style={{ padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="form-label" style={{ margin: 0, fontWeight: '600' }}>Active Section:</span>
            <select 
              className="form-control" 
              style={{ width: '280px', background: 'var(--bg-primary)' }}
              value={selectedSection ? selectedSection.id : ''}
              onChange={(e) => {
                const sec = sections.find(s => s.id === parseInt(e.target.value));
                setSelectedSection(sec);
              }}
            >
              {sections.map(s => (
                <option key={s.id} value={s.id}>
                  {s.course_code} - {s.course_name} (Sec {s.section_label})
                </option>
              ))}
            </select>
          </div>
          
          <button 
            className="btn btn-danger"
            onClick={handleArchiveCourse}
            style={{ background: 'rgba(239,68,68,0.15)', borderColor: 'rgba(239,68,68,0.3)', color: 'var(--danger)' }}
          >
            <Archive size={16} />
            Conclude Semester & Archive
          </button>
        </div>
      </div>

      {/* Grade Book Grid Card */}
      <div className="card" style={{ padding: '24px' }}>
        <div className="card-header" style={{ padding: '0 0 16px', borderBottom: '1px solid var(--border)', marginBottom: '20px' }}>
          <h3 className="card-title flex items-center gap-2">
            <FileSpreadsheet size={18} className="text-success" />
            Class Gradebook Grid
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            💡 Quicktip: Click Attendance badges to toggle. Click Quiz marks to override.
          </span>
        </div>

        {loadingGrades || !gradebook ? (
          <div className="flex justify-center padding-32">
            <div className="loading" style={{ color: 'var(--text-secondary)' }}>Compiling grid...</div>
          </div>
        ) : gradebook.lectures.length === 0 ? (
          <div className="empty-state">
            <FileSpreadsheet size={36} className="text-muted" style={{ margin: '0 auto 12px' }} />
            <h3>No lecture modules live</h3>
            <p>Upload a video lecture and students will begin showing attendance and scores in this grid.</p>
          </div>
        ) : (
          <div className="table-wrapper" style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ minWidth: '800px' }}>
              <thead>
                <tr>
                  <th style={{ width: '160px', position: 'sticky', left: 0, background: 'var(--bg-secondary)', zIndex: 10 }}>Student Name</th>
                  <th style={{ width: '110px' }}>Reg Number</th>
                  {gradebook.lectures.map((lec) => (
                    <th key={lec.id} style={{ textAlign: 'center', minWidth: '130px' }}>
                      <div style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: '600' }}>
                        {lec.title.length > 25 ? lec.title.substring(0, 25) + '...' : lec.title}
                      </div>
                      <div style={{ fontSize: '9px', textTransform: 'lowercase', marginTop: '2px', color: 'var(--text-muted)' }}>
                        att | quiz
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {gradebook.rows.map((row) => (
                  <tr key={row.student_id}>
                    <td style={{ position: 'sticky', left: 0, background: 'var(--bg-secondary)', zIndex: 10, color: 'var(--text-primary)', fontWeight: '600' }}>
                      {row.student_name}
                    </td>
                    <td>{row.reg_number}</td>
                    
                    {row.lectures.map((lec) => {
                      const isOverriding = activeOverrideCell?.studentId === row.student_id && activeOverrideCell?.quizId === lec.quiz_id;
                      
                      return (
                        <td key={lec.lecture_id} style={{ textAlign: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                            
                            {/* Attendance toggler */}
                            <button
                              type="button"
                              onClick={() => handleToggleAttendance(row.student_id, lec.lecture_id, lec.is_present)}
                              style={{ 
                                background: 'transparent', 
                                border: 'none', 
                                padding: '2px', 
                                cursor: 'pointer',
                                display: 'flex', 
                                alignItems: 'center' 
                              }}
                            >
                              {lec.is_present ? (
                                <span className="badge badge-success" style={{ fontSize: '9px', padding: '2px 6px' }}>Present</span>
                              ) : (
                                <span className="badge badge-danger" style={{ fontSize: '9px', padding: '2px 6px' }}>Absent</span>
                              )}
                            </button>

                            <span style={{ color: 'var(--border)' }}>|</span>

                            {/* Quiz score override */}
                            {lec.quiz_id ? (
                              isOverriding ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <input 
                                    type="text" 
                                    className="form-control"
                                    style={{ width: '40px', padding: '2px 4px', fontSize: '11px', textAlign: 'center', height: '24px' }}
                                    value={overrideScoreVal}
                                    placeholder={lec.quiz_score !== null ? lec.quiz_score.toString() : '0'}
                                    onChange={(e) => setOverrideScoreVal(e.target.value)}
                                  />
                                  <button 
                                    type="button"
                                    onClick={() => handleSaveGradeOverride(row.student_id, lec.quiz_id)}
                                    style={{ border: 'none', background: 'transparent', color: 'var(--success)', cursor: 'pointer', display: 'flex' }}
                                  >
                                    <Check size={14} />
                                  </button>
                                  <button 
                                    type="button"
                                    onClick={() => { setActiveOverrideCell(null); setOverrideScoreVal(''); }}
                                    style={{ border: 'none', background: 'transparent', color: 'var(--danger)', cursor: 'pointer', display: 'flex' }}
                                  >
                                    <X size={14} />
                                  </button>
                                </div>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setActiveOverrideCell({ studentId: row.student_id, quizId: lec.quiz_id });
                                    setOverrideScoreVal(lec.quiz_score !== null ? lec.quiz_score.toString() : '0');
                                  }}
                                  style={{ 
                                    background: 'transparent', 
                                    border: 'none', 
                                    color: lec.quiz_score !== null ? 'var(--text-primary)' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    fontSize: '13px',
                                    fontWeight: lec.quiz_score !== null ? 'bold' : 'normal'
                                  }}
                                  title="Click to override score"
                                >
                                  {lec.quiz_score !== null ? `${lec.quiz_score}/${lec.quiz_total}` : 'N/A'}
                                </button>
                              )
                            ) : (
                              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>-</span>
                            )}

                          </div>
                        </td>
                      );
                    })}

                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
