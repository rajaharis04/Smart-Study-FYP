import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { academicSectionApi, deptApi, studentApi } from '../services/api';
import Modal from '../components/Modal';
import CSVUploader from '../components/CSVUploader';
import {
  Plus, Trash2, Users, ArrowLeft, ChevronDown, ChevronUp,
  UserPlus, UserMinus, Upload, Key, Edit2,
  ToggleLeft, ToggleRight, Eye, EyeOff, AlertCircle, School, X
} from 'lucide-react';
import { toast } from 'react-hot-toast';

// ═══════════════════════════════════════════════════════
//  MAIN PAGE — Students & Sections
// ═══════════════════════════════════════════════════════
export default function AcademicSectionsPage() {
  const [grouped, setGrouped]       = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading]       = useState(true);

  // Full-screen section detail view
  const [openSection, setOpenSection] = useState(null);  // section object

  // Create section modal
  const [createOpen, setCreateOpen] = useState(false);
  const [batch, setBatch]           = useState('');
  const [deptId, setDeptId]         = useState('');
  const [secName, setSecName]       = useState('');
  const [saving, setSaving]         = useState(false);

  // Collapse state per batch
  const [collapsedBatches, setCollapsedBatches] = useState({});

  const fetchData = async () => {
    setLoading(true);
    try {
      const [gRes, dRes] = await Promise.all([
        academicSectionApi.listGrouped(),
        deptApi.list(),
      ]);
      setGrouped(gRes.data);
      setDepartments(dRes.data);
    } catch {
      toast.error('Data load karne mein masla hua.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // ── Create Section ──────────────────────────────────
  const handleCreate = async (e) => {
    e.preventDefault();
    if (!batch.trim() || !deptId || !secName.trim()) {
      toast.error('Sab fields fill karo.');
      return;
    }
    setSaving(true);
    try {
      await academicSectionApi.create({
        batch: batch.trim().toUpperCase(),
        department_id: parseInt(deptId),
        section_name: secName.trim().toUpperCase(),
      });
      toast.success('Section ban gaya!');
      setCreateOpen(false);
      setBatch(''); setDeptId(''); setSecName('');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Section nahi bana.');
    } finally {
      setSaving(false);
    }
  };

  // ── Delete Section ──────────────────────────────────
  const handleDelete = async (sec, e) => {
    e.stopPropagation();
    if (!window.confirm(`"${sec.full_label}" delete karna chahte ho? Sab students unassign ho jayenge.`)) return;
    try {
      await academicSectionApi.delete(sec.id);
      toast.success(`"${sec.full_label}" delete ho gaya.`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Delete nahi hua.');
    }
  };

  const toggleBatch = (b) =>
    setCollapsedBatches(prev => ({ ...prev, [b]: !prev[b] }));

  // Stats
  const totalSections = grouped.reduce(
    (s, b) => s + b.departments.reduce((ds, d) => ds + d.sections.length, 0), 0
  );
  const totalStudents = grouped.reduce(
    (s, b) => s + b.departments.reduce(
      (ds, d) => ds + d.sections.reduce((ss, sec) => ss + sec.student_count, 0), 0
    ), 0
  );

  // ── If a section is open, show full-screen detail ──
  if (openSection) {
    return (
      <SectionDetailPage
        section={openSection}
        departments={departments}
        onBack={() => { setOpenSection(null); fetchData(); }}
      />
    );
  }

  return (
    <div>
      {/* ── Page Header ── */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Students &amp; Sections</h1>
          <p className="page-subtitle">
            Academic hierarchy manage karo — Batch → Department → Section → Students
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreateOpen(true)}>
          <Plus size={16} />
          <span>New Section</span>
        </button>
      </div>

      {/* ── Stats ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '16px', maxWidth: 560, marginBottom: '28px' }}>
        {[
          { icon: '🎓', val: grouped.length, label: 'Total Batches', color: 'var(--accent)' },
          { icon: '🏫', val: totalSections,  label: 'Total Sections', color: 'var(--success)' },
          { icon: '👥', val: totalStudents,  label: 'Assigned Students', color: 'var(--info)' },
        ].map(s => (
          <div key={s.label} className="stat-card" style={{ '--card-color': s.color }}>
            <div className="stat-card-icon">{s.icon}</div>
            <div className="stat-card-value">{s.val}</div>
            <div className="stat-card-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Hierarchy ── */}
      {loading ? (
        <div className="loading" style={{ textAlign: 'center', padding: '48px' }}>Loading...</div>
      ) : grouped.length === 0 ? (
        <EmptyState onCreate={() => setCreateOpen(true)} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {grouped.map((batchGroup, bi) => (
            <div key={batchGroup.batch}>
              {bi > 0 && (
                <div style={{
                  height: '2px',
                  background: 'linear-gradient(90deg, var(--accent) 0%, transparent 60%)',
                  marginBottom: '28px', borderRadius: '99px', opacity: 0.4,
                }} />
              )}

              {/* Batch Heading */}
              <div
                onClick={() => toggleBatch(batchGroup.batch)}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  cursor: 'pointer', marginBottom: '20px', padding: '14px 20px',
                  background: 'linear-gradient(135deg,rgba(99,102,241,0.15),rgba(99,102,241,0.04))',
                  border: '1px solid rgba(99,102,241,0.25)', borderRadius: '14px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div style={{
                    width: '46px', height: '46px',
                    background: 'linear-gradient(135deg,var(--accent),var(--accent-dark))',
                    borderRadius: '12px', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', fontSize: '22px',
                    boxShadow: '0 0 16px rgba(99,102,241,0.4)',
                  }}>🎓</div>
                  <div>
                    <div style={{ fontSize: '22px', fontWeight: '800', color: 'var(--accent-light)', letterSpacing: '-0.5px' }}>
                      Batch {batchGroup.batch}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {batchGroup.departments.length} dept(s) &bull;{' '}
                      {batchGroup.departments.reduce((s, d) => s + d.sections.length, 0)} section(s) &bull;{' '}
                      {batchGroup.departments.reduce(
                        (s, d) => s + d.sections.reduce((ss, sec) => ss + sec.student_count, 0), 0
                      )} students
                    </div>
                  </div>
                </div>
                {collapsedBatches[batchGroup.batch]
                  ? <ChevronDown size={20} color="var(--text-muted)" />
                  : <ChevronUp size={20} color="var(--text-muted)" />}
              </div>

              {!collapsedBatches[batchGroup.batch] && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  {batchGroup.departments.map(dept => (
                    <div key={dept.department_id} style={{ paddingLeft: '8px' }}>
                      {/* Department Heading */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
                        <div style={{
                          width: '8px', height: '8px', background: 'var(--success)',
                          borderRadius: '50%', boxShadow: '0 0 10px var(--success)',
                        }} />
                        <span style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
                          {dept.department_name}
                        </span>
                        <span style={{
                          fontSize: '11px', color: 'var(--text-muted)',
                          background: 'rgba(255,255,255,0.05)',
                          border: '1px solid var(--border)', borderRadius: '6px', padding: '2px 8px',
                        }}>
                          {dept.department_code}
                        </span>
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          — {dept.sections.length} section(s)
                        </span>
                      </div>

                      {/* Section Boxes Grid */}
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                        gap: '14px', paddingLeft: '12px',
                      }}>
                        {dept.sections.map(sec => (
                          <SectionBox
                            key={sec.id}
                            sec={sec}
                            onClick={() => setOpenSection(sec)}
                            onDelete={(e) => handleDelete(sec, e)}
                          />
                        ))}
                        {/* Quick-add shortcut */}
                        <QuickAddBox
                          batch={batchGroup.batch}
                          deptId={dept.department_id}
                          deptCode={dept.department_code}
                          onCreated={fetchData}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Create Section Modal ── */}
      <Modal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        title="New Academic Section"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setCreateOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleCreate} disabled={saving}>
              {saving ? 'Ban raha hai...' : 'Create Section'}
            </button>
          </>
        }
      >
        <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Batch Number</label>
              <input className="form-control" placeholder="e.g. SP23, FA24"
                value={batch} onChange={e => setBatch(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">Section Name</label>
              <input className="form-control" placeholder="e.g. A, B, C" maxLength={5}
                value={secName} onChange={e => setSecName(e.target.value)} required />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Department</label>
            <select className="form-control" value={deptId}
              onChange={e => setDeptId(e.target.value)} required>
              <option value="">-- Department Select Karo --</option>
              {departments.map(d => (
                <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
              ))}
            </select>
          </div>
          {batch && deptId && secName && (
            <div style={{
              background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)',
              borderRadius: '8px', padding: '12px 16px', fontSize: '13px', color: 'var(--accent-light)',
            }}>
              Preview: <strong>
                {batch.toUpperCase()}-{departments.find(d => String(d.id) === String(deptId))?.code || '?'}-{secName.toUpperCase()}
              </strong>
            </div>
          )}
        </form>
      </Modal>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
//  FULL-SCREEN SECTION DETAIL PAGE
// ═══════════════════════════════════════════════════════
function SectionDetailPage({ section, departments, onBack }) {
  const [students, setStudents]         = useState([]);
  const [loading, setLoading]           = useState(true);
  const [allStudents, setAllStudents]   = useState([]);

  // Tabs: 'list' | 'add' | 'bulk'
  const [activeTab, setActiveTab] = useState('list');

  // Add Student Form
  const [fullName, setFullName]   = useState('');
  const [email, setEmail]         = useState('');
  const [regNumber, setRegNumber] = useState('');
  const [formSaving, setFormSaving] = useState(false);

  // Password modal
  const [pwModal, setPwModal]     = useState(false);
  const [pwTitle, setPwTitle]     = useState('');
  const [pw, setPw]               = useState('');
  const [showPw, setShowPw]       = useState(false);

  // Edit student modal
  const [editOpen, setEditOpen]   = useState(false);
  const [editStudent, setEditStudent] = useState(null);
  const [editName, setEditName]   = useState('');
  const [editEmail, setEditEmail] = useState('');

  const navigate = useNavigate();
  const handleOpenDetails = (student) => {
    navigate(`/students/${student.id}`);
  };

  const fetchStudents = async () => {
    setLoading(true);
    try {
      const res = await academicSectionApi.getSectionStudents(section.id);
      setStudents(res.data.students);
    } catch {
      toast.error('Students load nahi huye.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStudents(); }, [section.id]);

  // ── Create Student directly in this section ──────────
  const handleAddStudent = async (e) => {
    e.preventDefault();
    if (!fullName || !email || !regNumber) {
      toast.error('Sab fields fill karo.');
      return;
    }
    setFormSaving(true);
    try {
      // Create student with section's batch and department
      const res = await studentApi.create({
        full_name: fullName,
        email,
        reg_number: regNumber,
        batch: section.batch,
        department_id: section.department_id,
      });
      const newId = res.data.id;
      // Assign to this section
      await academicSectionApi.assignStudent(section.id, newId);
      toast.success(`${fullName} add ho gaya!`);
      setFullName(''); setEmail(''); setRegNumber('');
      setActiveTab('list');
      fetchStudents();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Student nahi bana.');
    } finally {
      setFormSaving(false);
    }
  };

  // ── Bulk CSV Upload — directly into this section ─────
  const handleCSV = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await academicSectionApi.bulkUploadToSection(section.id, formData);
    const { created, skipped, errors: errs } = res.data;

    if (created > 0) {
      toast.success(`✅ ${created} students create aur section mein assign ho gaye!`);
    }
    if (skipped > 0) {
      toast(`⚠️ ${skipped} records skip ho gaye (already exist)`, { icon: '⚠️' });
    }
    if (errs?.length > 0) {
      toast.error(`${errs.length} errors — console dekho`, { duration: 4000 });
      console.warn('Bulk upload errors:', errs);
    }

    fetchStudents();
    return res.data;
  };

  // ── Reset Password ────────────────────────────────────
  const handleResetPw = async (s) => {
    if (!window.confirm(`${s.full_name} ka password reset karna chahte ho?`)) return;
    try {
      const res = await studentApi.resetPassword(s.id);
      setPw(res.data.new_password);
      setPwTitle(`Password Reset — ${s.full_name}`);
      setShowPw(false);
      setPwModal(true);
    } catch { toast.error('Password reset nahi hua.'); }
  };

  // ── Toggle Active ─────────────────────────────────────
  const handleToggle = async (s) => {
    try {
      await studentApi.update(s.id, { is_active: !s.is_active });
      toast.success(`Account ${s.is_active ? 'deactivate' : 'activate'} ho gaya.`);
      fetchStudents();
    } catch { toast.error('Status nahi badla.'); }
  };

  // ── Remove from section ───────────────────────────────
  const handleRemove = async (s) => {
    if (!window.confirm(`"${s.full_name}" ko is section se remove karna chahte ho?`)) return;
    try {
      await academicSectionApi.removeStudent(section.id, s.id);
      toast.success(`${s.full_name} remove ho gaya.`);
      fetchStudents();
    } catch { toast.error('Remove nahi hua.'); }
  };

  // ── Delete Student Permanently ────────────────────────
  const handleDelete = async (s) => {
    if (!window.confirm(`"${s.full_name}" ko permanently delete karna chahte ho? Yeh action undo nahi hoga!`)) return;
    try {
      await studentApi.delete(s.id);
      toast.success(`${s.full_name} delete ho gaya.`);
      fetchStudents();
    } catch { toast.error('Delete nahi hua.'); }
  };

  // ── Edit Student ──────────────────────────────────────
  const openEdit = (s) => {
    setEditStudent(s);
    setEditName(s.full_name);
    setEditEmail(s.email);
    setEditOpen(true);
  };

  const handleEditSave = async () => {
    try {
      await studentApi.update(editStudent.id, { full_name: editName, email: editEmail });
      toast.success('Student update ho gaya.');
      setEditOpen(false);
      fetchStudents();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update nahi hua.');
    }
  };

  return (
    <div style={{ animation: 'fadeIn 0.2s ease' }}>
      {/* ── Top Bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '28px',
        padding: '16px 20px',
        background: 'linear-gradient(135deg,rgba(99,102,241,0.15),rgba(99,102,241,0.04))',
        border: '1px solid rgba(99,102,241,0.25)', borderRadius: '16px',
      }}>
        <button className="btn btn-secondary btn-sm btn-icon" onClick={onBack} title="Back">
          <ArrowLeft size={18} />
        </button>
        <div style={{
          width: '52px', height: '52px',
          background: 'linear-gradient(135deg,var(--accent),var(--accent-dark))',
          borderRadius: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '24px', boxShadow: '0 0 20px rgba(99,102,241,0.4)', flexShrink: 0,
        }}>🏫</div>
        <div>
          <div style={{ fontSize: '26px', fontWeight: '800', color: 'var(--accent-light)', letterSpacing: '-0.5px' }}>
            {section.full_label}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
            {section.department_name} &bull; Batch {section.batch} &bull; {students.length} students
          </div>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '24px',
        background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)',
        borderRadius: '12px', padding: '4px', width: 'fit-content' }}>
        {[
          { id: 'list', label: 'Students List', icon: Users },
          { id: 'add',  label: 'Add Student',   icon: UserPlus },
          { id: 'bulk', label: 'Bulk Upload CSV', icon: Upload },
        ].map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: '7px',
                padding: '9px 18px', borderRadius: '9px', border: 'none', cursor: 'pointer',
                fontSize: '13px', fontWeight: '600', transition: 'all 0.2s ease',
                background: activeTab === tab.id
                  ? 'linear-gradient(135deg,var(--accent),var(--accent-dark))'
                  : 'transparent',
                color: activeTab === tab.id ? '#fff' : 'var(--text-secondary)',
                boxShadow: activeTab === tab.id ? '0 2px 8px rgba(99,102,241,0.4)' : 'none',
              }}
            >
              <Icon size={15} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ════════ TAB: Students List ════════ */}
      {activeTab === 'list' && (
        <div>
          {loading ? (
            <div className="loading" style={{ textAlign: 'center', padding: '40px' }}>
              Students load ho rahe hain...
            </div>
          ) : students.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">👤</div>
              <h3>Koi Student Nahi</h3>
              <p>
                <button className="btn btn-primary btn-sm" style={{ marginTop: '12px' }}
                  onClick={() => setActiveTab('add')}>
                  <UserPlus size={14} /> Student Add Karo
                </button>
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1px',
              background: 'var(--border)', borderRadius: '14px', overflow: 'hidden',
              border: '1px solid var(--border)' }}>
              {/* Table Header */}
              <div style={{
                display: 'grid', gridTemplateColumns: '2fr 2fr 1.5fr 1fr 1fr 1fr auto',
                padding: '12px 20px', background: 'var(--bg-secondary)',
                fontSize: '11px', fontWeight: '600', textTransform: 'uppercase',
                letterSpacing: '0.06em', color: 'var(--text-muted)', gap: '12px',
              }}>
                <span>Student</span>
                <span>Email</span>
                <span>Reg No</span>
                <span>Batch</span>
                <span>Status</span>
                <span>Actions</span>
              </div>
              {students.map((s, i) => (
                <StudentTableRow
                  key={s.id}
                  student={s}
                  even={i % 2 === 0}
                  onEdit={() => openEdit(s)}
                  onResetPw={() => handleResetPw(s)}
                  onToggle={() => handleToggle(s)}
                  onRemove={() => handleRemove(s)}
                  onDelete={() => handleDelete(s)}
                  onRowClick={handleOpenDetails}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ════════ TAB: Add Student ════════ */}
      {activeTab === 'add' && (
        <div style={{ maxWidth: 580 }}>
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Student Account Banao</div>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Yeh student automatically <strong style={{ color: 'var(--accent-light)' }}>{section.full_label}</strong> section mein assign ho jayega
                </div>
              </div>
            </div>
            <div className="card-body">
              <form onSubmit={handleAddStudent} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                {/* Auto-filled read-only info */}
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label">Batch (Auto)</label>
                    <input className="form-control" value={section.batch} disabled
                      style={{ opacity: 0.6, cursor: 'not-allowed' }} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Department (Auto)</label>
                    <input className="form-control" value={section.department_name} disabled
                      style={{ opacity: 0.6, cursor: 'not-allowed' }} />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Registration Number *</label>
                  <input className="form-control" placeholder="e.g. SP23-BCS-011"
                    value={regNumber} onChange={e => setRegNumber(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Full Name *</label>
                  <input className="form-control" placeholder="e.g. Ali Hassan"
                    value={fullName} onChange={e => setFullName(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Email Address *</label>
                  <input type="email" className="form-control"
                    placeholder="e.g. ali@std.edu.pk"
                    value={email} onChange={e => setEmail(e.target.value)} required />
                </div>

                <div style={{ display: 'flex', gap: '12px' }}>
                  <button type="submit" className="btn btn-primary" disabled={formSaving}>
                    <UserPlus size={15} />
                    {formSaving ? 'Add ho raha hai...' : 'Student Add Karo'}
                  </button>
                  <button type="button" className="btn btn-secondary"
                    onClick={() => { setFullName(''); setEmail(''); setRegNumber(''); }}>
                    Clear
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* ════════ TAB: Bulk Upload ════════ */}
      {activeTab === 'bulk' && (
        <div style={{ maxWidth: 600 }}>
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Bulk CSV Upload</div>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  CSV se multiple students ek sath upload karo — sab <strong style={{ color: 'var(--success)' }}>automatically {section.full_label} mein assign</strong> ho jayenge
                </div>
              </div>
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

              {/* ── Auto-assign notice ── */}
              <div style={{
                background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)',
                borderRadius: '10px', padding: '12px 16px', fontSize: '13px',
                display: 'flex', gap: '10px', alignItems: 'flex-start',
              }}>
                <span style={{ fontSize: '18px' }}>✅</span>
                <div>
                  <div style={{ fontWeight: '600', color: 'var(--success)', marginBottom: '4px' }}>
                    Auto-Assignment Active
                  </div>
                  <div style={{ color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                    Upload hone ke baad sab students <strong>{section.full_label}</strong> section mein automatically assign ho jayenge.
                    Batch (<strong>{section.batch}</strong>) aur Department (<strong>{section.department_name}</strong>) bhi auto-set ho gi.
                  </div>
                </div>
              </div>

              {/* ── CSV Format + Download Template ── */}
              <div style={{
                background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
                borderRadius: '10px', padding: '14px 16px', fontSize: '13px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ fontWeight: '600', color: 'var(--accent-light)' }}>
                    📋 CSV Format (Required Columns)
                  </div>
                  {/* ── Download Template Button ── */}
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      const csvContent = [
                        'Name,Email,RegNumber',
                        `Ahmad Ali,ahmad.ali@std.edu.pk,${section.batch}-${section.department_code || 'DEPT'}-001`,
                        `Sara Khan,sara.khan@std.edu.pk,${section.batch}-${section.department_code || 'DEPT'}-002`,
                      ].join('\n');

                      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                      const url  = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href     = url;
                      link.download = `students_template_${section.full_label}.csv`;
                      link.click();
                      URL.revokeObjectURL(url);
                    }}
                    style={{ display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Download Template
                  </button>
                </div>

                {/* Columns preview */}
                <div style={{
                  fontFamily: 'monospace', fontSize: '12px', color: 'var(--text-secondary)',
                  background: 'rgba(0,0,0,0.2)', borderRadius: '6px', padding: '8px 12px',
                  marginBottom: '8px', letterSpacing: '0.02em',
                }}>
                  Name, Email, RegNumber
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '12px', lineHeight: '1.6' }}>
                  <strong>Optional:</strong> Batch (agar missing ho to "{section.batch}" use hoga) &bull; Department (section se auto-set hogi)
                </div>
              </div>

              <CSVUploader
                title="Drag &amp; Drop Student CSV"
                subtitle={`Columns: Name, Email, RegNumber — Section: ${section.full_label}`}
                onUpload={handleCSV}
              />

            </div>
          </div>
        </div>
      )}

      {/* ── Edit Modal ── */}
      <Modal
        isOpen={editOpen}
        onClose={() => setEditOpen(false)}
        title={`Edit — ${editStudent?.full_name}`}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setEditOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleEditSave}>Save Changes</button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input className="form-control" value={editName} onChange={e => setEditName(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input type="email" className="form-control" value={editEmail} onChange={e => setEditEmail(e.target.value)} />
          </div>
        </div>
      </Modal>

      {/* ── Password Modal ── */}
      <Modal
        isOpen={pwModal}
        onClose={() => setPwModal(false)}
        title={pwTitle}
        footer={
          <button className="btn btn-primary w-full" onClick={() => setPwModal(false)}>Done</button>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            Naya temporary password — student ko share karo:
          </p>
          <div style={{ position: 'relative' }}>
            <div className="password-box">{showPw ? pw : '••••••••••••'}</div>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowPw(!showPw)}
              style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', padding: '4px 8px' }}>
              {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          <button className="btn btn-secondary btn-sm w-full"
            onClick={() => { navigator.clipboard.writeText(pw); toast.success('Copied!'); }}>
            Copy Password
          </button>
        </div>
      </Modal>


    </div>
  );
}

// ═══════════════════════════════════════════════════════
//  Student Table Row
// ═══════════════════════════════════════════════════════
function StudentTableRow({ student: s, even, onEdit, onResetPw, onToggle, onRemove, onDelete, onRowClick }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '2fr 2fr 1.5fr 1fr 1fr auto',
      padding: '14px 20px', gap: '12px', alignItems: 'center',
      background: even ? 'rgba(255,255,255,0.015)' : 'var(--bg-secondary)',
      transition: 'background 0.15s',
      cursor: 'pointer',
    }}
      onClick={() => onRowClick && onRowClick(s)}
      onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.06)'}
      onMouseLeave={e => e.currentTarget.style.background = even ? 'rgba(255,255,255,0.015)' : 'var(--bg-secondary)'}
    >
      {/* Name + avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {s.profile_picture ? (
          <img src={`http://localhost:8001${s.profile_picture}`} alt=""
            style={{ width: '34px', height: '34px', borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }} />
        ) : (
          <div style={{
            width: '34px', height: '34px', borderRadius: '50%', flexShrink: 0,
            background: 'linear-gradient(135deg,var(--accent),var(--accent-dark))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '13px', fontWeight: '700',
          }}>
            {s.full_name?.[0] || '?'}
          </div>
        )}
        <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>
          {s.full_name}
        </span>
      </div>

      {/* Email */}
      <span style={{ fontSize: '13px', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {s.email}
      </span>

      {/* Reg No */}
      <span style={{ fontSize: '12px', fontFamily: 'monospace', color: 'var(--accent-light)',
        background: 'var(--accent-glow)', padding: '2px 8px', borderRadius: '6px', width: 'fit-content' }}>
        {s.reg_number}
      </span>

      {/* Batch */}
      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{s.batch}</span>

      {/* Status */}
      <span className={`badge ${s.is_active ? 'badge-success' : 'badge-danger'}`}>
        {s.is_active ? 'Active' : 'Inactive'}
      </span>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
        <button className="btn btn-secondary btn-sm btn-icon" onClick={onEdit} title="Edit" style={{ width: '30px', height: '30px' }}>
          <Edit2 size={12} />
        </button>
        <button className="btn btn-secondary btn-sm btn-icon" onClick={onResetPw} title="Reset Password" style={{ width: '30px', height: '30px' }}>
          <Key size={12} />
        </button>
        <button className={`btn btn-sm btn-icon ${s.is_active ? 'btn-danger' : 'btn-success'}`}
          onClick={onToggle} title={s.is_active ? 'Deactivate' : 'Activate'} style={{ width: '30px', height: '30px' }}>
          {s.is_active ? <ToggleLeft size={13} /> : <ToggleRight size={13} />}
        </button>
        <button className="btn btn-danger btn-sm btn-icon" onClick={onRemove} title="Remove from Section" style={{ width: '30px', height: '30px' }}>
          <UserMinus size={12} />
        </button>
        <button className="btn btn-danger btn-sm btn-icon" onClick={onDelete} title="Delete Permanently" style={{ width: '30px', height: '30px' }}>
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
//  Section Box Card
// ═══════════════════════════════════════════════════════
function SectionBox({ sec, onClick, onDelete }) {
  const [hov, setHov] = useState(false);
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: hov ? 'rgba(99,102,241,0.13)' : 'rgba(255,255,255,0.04)',
        border: `1px solid ${hov ? 'rgba(99,102,241,0.45)' : 'rgba(255,255,255,0.08)'}`,
        borderRadius: '16px', padding: '22px 16px', cursor: 'pointer',
        transition: 'all 0.2s ease',
        transform: hov ? 'translateY(-4px)' : 'none',
        boxShadow: hov ? '0 10px 28px rgba(99,102,241,0.22)' : 'none',
        position: 'relative', userSelect: 'none',
      }}
      onClick={onClick}
    >
      {/* Delete btn */}
      <button
        className="btn btn-danger btn-sm btn-icon"
        style={{
          position: 'absolute', top: '8px', right: '8px',
          width: '26px', height: '26px',
          opacity: hov ? 1 : 0, transition: 'opacity 0.2s',
        }}
        onClick={onDelete}
        title="Delete Section"
      >
        <Trash2 size={11} />
      </button>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
        <div style={{
          width: '58px', height: '58px',
          background: 'linear-gradient(135deg,var(--accent),var(--accent-dark))',
          borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '26px', boxShadow: '0 4px 14px rgba(99,102,241,0.35)',
        }}>🏫</div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '17px', fontWeight: '800', color: 'var(--text-primary)', letterSpacing: '-0.3px' }}>
            {sec.full_label}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', marginTop: '6px' }}>
            <Users size={12} color="var(--text-muted)" />
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{sec.student_count} students</span>
          </div>
          {hov && (
            <div style={{
              marginTop: '8px', fontSize: '11px', color: 'var(--accent-light)',
              fontWeight: '600', letterSpacing: '0.04em',
            }}>
              Click to Open →
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
//  Quick Add Box (same dept/batch)
// ═══════════════════════════════════════════════════════
function QuickAddBox({ batch, deptId, deptCode, onCreated }) {
  const [open, setOpen]     = useState(false);
  const [secName, setSecName] = useState('');
  const [saving, setSaving] = useState(false);

  const handle = async (e) => {
    e.preventDefault();
    if (!secName.trim()) return;
    setSaving(true);
    try {
      await academicSectionApi.create({
        batch, department_id: deptId,
        section_name: secName.trim().toUpperCase(),
      });
      toast.success(`${batch}-${deptCode}-${secName.toUpperCase()} ban gaya!`);
      setSecName(''); setOpen(false);
      onCreated();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Nahi bana.');
    } finally { setSaving(false); }
  };

  if (!open) return (
    <div onClick={() => setOpen(true)} style={{
      border: '2px dashed rgba(99,102,241,0.25)', borderRadius: '16px',
      padding: '22px 16px', cursor: 'pointer', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: '8px',
      color: 'var(--text-muted)', transition: 'all 0.2s ease', minHeight: '120px',
    }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(99,102,241,0.5)'; e.currentTarget.style.color = 'var(--accent-light)'; e.currentTarget.style.background = 'rgba(99,102,241,0.06)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(99,102,241,0.25)'; e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; }}
    >
      <Plus size={24} />
      <span style={{ fontSize: '12px', fontWeight: '600' }}>{batch}-{deptCode}-?</span>
      <span style={{ fontSize: '11px' }}>Section add karo</span>
    </div>
  );

  return (
    <div style={{
      border: '1px solid rgba(99,102,241,0.4)', borderRadius: '16px',
      padding: '16px', background: 'rgba(99,102,241,0.08)',
    }}>
      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
        {batch}-{deptCode}-
      </div>
      <form onSubmit={handle} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <input className="form-control" style={{ fontSize: '14px', padding: '8px 12px' }}
          placeholder="Section name (e.g. D)" maxLength={5}
          value={secName} onChange={e => setSecName(e.target.value)} autoFocus />
        <div style={{ display: 'flex', gap: '8px' }}>
          <button type="submit" className="btn btn-primary btn-sm" disabled={saving} style={{ flex: 1 }}>
            {saving ? '...' : 'Banao'}
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setOpen(false)}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
//  Empty State
// ═══════════════════════════════════════════════════════
function EmptyState({ onCreate }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">🏫</div>
      <h3>Koi Section Nahi</h3>
      <p style={{ marginBottom: '16px' }}>Abhi koi academic section nahi hai.</p>
      <button className="btn btn-primary" onClick={onCreate}>
        <Plus size={15} /> Pehla Section Banao
      </button>
    </div>
  );
}
