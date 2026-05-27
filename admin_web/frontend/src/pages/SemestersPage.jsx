import { useState, useEffect } from 'react';
import { semesterApi } from '../services/api';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { Plus, Edit2, Trash2, Calendar, AlertCircle, RefreshCw, ArrowRight, ArrowLeft, ShieldAlert, CheckCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function SemestersPage() {
  const [semesters, setSemesters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSemester, setEditingSemester] = useState(null);

  // Form states
  const [name, setName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [midStart, setMidStart] = useState('');
  const [midEnd, setMidEnd] = useState('');
  const [endDate, setEndDate] = useState('');
  const [finalStart, setFinalStart] = useState('');
  const [finalEnd, setFinalEnd] = useState('');
  const [isActive, setIsActive] = useState(true);

  // Rollover wizard states
  const [rolloverModalOpen, setRolloverModalOpen] = useState(false);
  const [rolloverSem, setRolloverSem] = useState(null);
  const [rolloverStep, setRolloverStep] = useState(1);
  const [confirmText, setConfirmText] = useState('');
  const [rollingOver, setRollingOver] = useState(false);
  const [rolloverResult, setRolloverResult] = useState(null);

  // Next semester configuration states (Wizard Step 3)
  const [nextName, setNextName] = useState('');
  const [nextStartDate, setNextStartDate] = useState('');
  const [nextMidStart, setNextMidStart] = useState('');
  const [nextMidEnd, setNextMidEnd] = useState('');
  const [nextEndDate, setNextEndDate] = useState('');
  const [nextFinalStart, setNextFinalStart] = useState('');
  const [nextFinalEnd, setNextFinalEnd] = useState('');
  const [creatingNext, setCreatingNext] = useState(false);
  const [nextSemResult, setNextSemResult] = useState(null);

  const openRolloverWizard = (sem) => {
    setRolloverSem(sem);
    setRolloverStep(1);
    setConfirmText('');
    setRolloverResult(null);
    setNextName('');
    setNextStartDate('');
    setNextMidStart('');
    setNextMidEnd('');
    setNextEndDate('');
    setNextFinalStart('');
    setNextFinalEnd('');
    setNextSemResult(null);
    setRolloverModalOpen(true);
  };

  const handleRolloverSubmit = async () => {
    if (confirmText !== 'ROLLOVER') {
      toast.error('Please type ROLLOVER to confirm.');
      return;
    }
    setRollingOver(true);
    try {
      const res = await semesterApi.rollover(rolloverSem.id);
      setRolloverResult(res.data);
      toast.success('Current semester archived successfully.');
      
      // Auto-suggest next semester name if format matches e.g. "Spring 2026"
      if (rolloverSem && rolloverSem.name) {
        const parts = rolloverSem.name.split(' ');
        if (parts.length === 2) {
          const semType = parts[0].toLowerCase();
          const year = parseInt(parts[1], 10);
          if (semType === 'fall') {
            setNextName(`Spring ${year + 1}`);
          } else if (semType === 'spring') {
            setNextName(`Fall ${year}`);
          } else if (semType === 'summer') {
            setNextName(`Fall ${year}`);
          }
        }
      }
      
      setRolloverStep(3);
      fetchSemesters();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Rollover execution failed.');
    } finally {
      setRollingOver(false);
    }
  };

  const handleCreateNextSemester = async (e) => {
    if (e) e.preventDefault();
    if (!nextName.trim()) {
      toast.error('Semester name is required.');
      return;
    }
    setCreatingNext(true);
    try {
      const payload = {
        name: nextName,
        start_date: nextStartDate || null,
        mid_start: nextMidStart || null,
        mid_end: nextMidEnd || null,
        end_date: nextEndDate || null,
        final_start: nextFinalStart || null,
        final_end: nextFinalEnd || null,
        is_active: true,
      };
      const res = await semesterApi.create(payload);
      setNextSemResult(res.data);
      toast.success(`New active semester "${res.data.name}" initialized!`);
      setRolloverStep(4);
      fetchSemesters();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to initialize next semester.');
    } finally {
      setCreatingNext(false);
    }
  };

  const fetchSemesters = async () => {
    setLoading(true);
    try {
      const res = await semesterApi.list();
      setSemesters(res.data);
    } catch (err) {
      setError('Failed to fetch semesters.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSemesters();
  }, []);

  const openCreateModal = () => {
    setEditingSemester(null);
    setName('');
    setStartDate('');
    setMidStart('');
    setMidEnd('');
    setEndDate('');
    setFinalStart('');
    setFinalEnd('');
    setIsActive(true);
    setModalOpen(true);
  };

  const openEditModal = (sem) => {
    setEditingSemester(sem);
    setName(sem.name);
    setStartDate(sem.start_date || '');
    setMidStart(sem.mid_start || '');
    setMidEnd(sem.mid_end || '');
    setEndDate(sem.end_date || '');
    setFinalStart(sem.final_start || '');
    setFinalEnd(sem.final_end || '');
    setIsActive(sem.is_active);
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name,
        start_date: startDate || null,
        mid_start: midStart || null,
        mid_end: midEnd || null,
        end_date: endDate || null,
        final_start: finalStart || null,
        final_end: finalEnd || null,
        is_active: isActive,
      };

      if (editingSemester) {
        await semesterApi.update(editingSemester.id, payload);
        toast.success('Semester updated successfully');
      } else {
        await semesterApi.create(payload);
        toast.success('Semester session created successfully');
      }
      setModalOpen(false);
      fetchSemesters();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this semester? This will unlink associated courses and sections!')) return;
    try {
      await semesterApi.delete(id);
      toast.success('Semester deleted');
      fetchSemesters();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete semester.');
    }
  };

  const headers = [
    { key: 'name', label: 'Semester Session' },
    { key: 'start_date', label: 'Start Date' },
    { key: 'mid_exams', label: 'Midterm Exams', sortable: false },
    { key: 'final_exams', label: 'Final Exams', sortable: false },
    { key: 'end_date', label: 'End Date' },
    { key: 'is_active', label: 'Active Session' },
    { key: 'actions', label: 'Actions', sortable: false },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Semester Sessions</h1>
          <p className="page-subtitle">Configure academic sessions, midterms schedule boundaries, and final exam terms.</p>
        </div>
        <button className="btn btn-primary" onClick={openCreateModal}>
          <Plus size={16} />
          <span>Add Semester</span>
        </button>
      </div>

      {error && (
        <div className="result-box error mb-4" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="loading" style={{ textAlign: 'center', padding: '24px' }}>Loading academic semesters...</div>
      ) : (
        <DataTable
          headers={headers}
          data={semesters}
          searchKeys={['name']}
          searchPlaceholder="Search semesters..."
          renderRow={(sem) => (
            <>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                  <Calendar size={16} className="text-accent" />
                  <span>{sem.name}</span>
                </div>
              </td>
              <td>{sem.start_date ? new Date(sem.start_date).toLocaleDateString() : <span className="text-muted">TBD</span>}</td>
              <td>
                {sem.mid_start && sem.mid_end ? (
                  <span className="badge badge-warning" style={{ fontSize: '11px' }}>
                    {new Date(sem.mid_start).toLocaleDateString()} - {new Date(sem.mid_end).toLocaleDateString()}
                  </span>
                ) : (
                  <span className="text-muted">-</span>
                )}
              </td>
              <td>
                {sem.final_start && sem.final_end ? (
                  <span className="badge badge-danger" style={{ fontSize: '11px' }}>
                    {new Date(sem.final_start).toLocaleDateString()} - {new Date(sem.final_end).toLocaleDateString()}
                  </span>
                ) : (
                  <span className="text-muted">-</span>
                )}
              </td>
              <td>{sem.end_date ? new Date(sem.end_date).toLocaleDateString() : <span className="text-muted">TBD</span>}</td>
              <td>
                <span className={`badge ${sem.is_active ? 'badge-success' : 'badge-danger'}`}>
                  {sem.is_active ? 'Active' : 'Archived'}
                </span>
              </td>
              <td>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button className="btn btn-secondary btn-sm btn-icon" onClick={() => openEditModal(sem)} title="Edit">
                    <Edit2 size={14} />
                  </button>
                  <button className="btn btn-danger btn-sm btn-icon" onClick={() => handleDelete(sem.id)} title="Delete">
                    <Trash2 size={14} />
                  </button>
                  {sem.is_active && (
                    <button
                      className="btn btn-warning btn-sm"
                      onClick={() => openRolloverWizard(sem)}
                      style={{ padding: '4px 8px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                      title="Run Rollover Wizard"
                    >
                      <RefreshCw size={11} />
                      <span>Rollover</span>
                    </button>
                  )}
                </div>
              </td>
            </>
          )}
        />
      )}

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingSemester ? 'Edit Semester Calendar' : 'Create Semester Session'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSubmit}>
              {editingSemester ? 'Save Changes' : 'Create Session'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label">Semester Name</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Spring 2026, Fall 2026"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Start Date</label>
              <input
                type="date"
                className="form-control"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">End Date</label>
              <input
                type="date"
                className="form-control"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>
          <fieldset style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <legend style={{ padding: '0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Midterm Exams Slot</legend>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Mids Start Date</label>
                <input
                  type="date"
                  className="form-control"
                  value={midStart}
                  onChange={(e) => setMidStart(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Mids End Date</label>
                <input
                  type="date"
                  className="form-control"
                  value={midEnd}
                  onChange={(e) => setMidEnd(e.target.value)}
                />
              </div>
            </div>
          </fieldset>
          <fieldset style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <legend style={{ padding: '0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Final Exams Slot</legend>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Finals Start Date</label>
                <input
                  type="date"
                  className="form-control"
                  value={finalStart}
                  onChange={(e) => setFinalStart(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Finals End Date</label>
                <input
                  type="date"
                  className="form-control"
                  value={finalEnd}
                  onChange={(e) => setFinalEnd(e.target.value)}
                />
              </div>
            </div>
          </fieldset>
          <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '10px', marginTop: '4px' }}>
            <input
              type="checkbox"
              id="isActive"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              style={{ width: '16px', height: '16px' }}
            />
            <label className="form-label" htmlFor="isActive" style={{ cursor: 'pointer' }}>Set as active session</label>
          </div>
        </form>
      </Modal>

      {/* SEMESTER ROLLOVER STEPPER WIZARD MODAL */}
      <Modal
        isOpen={rolloverModalOpen}
        onClose={() => !rollingOver && !creatingNext && setRolloverModalOpen(false)}
        title={`Semester Transition Wizard: ${rolloverSem?.name}`}
        footer={
          <div style={{ display: 'flex', width: '100%', justifyContent: 'space-between' }}>
            <div>
              {rolloverStep === 2 && (
                <button
                  className="btn btn-secondary"
                  disabled={rollingOver}
                  onClick={() => setRolloverStep(1)}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <ArrowLeft size={14} />
                  <span>Back</span>
                </button>
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              {rolloverStep !== 4 && (
                <button className="btn btn-secondary" disabled={rollingOver || creatingNext} onClick={() => setRolloverModalOpen(false)}>
                  Cancel
                </button>
              )}
              
              {rolloverStep === 1 && (
                <button
                  className="btn btn-primary"
                  onClick={() => setRolloverStep(2)}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <span>Next Step</span>
                  <ArrowRight size={14} />
                </button>
              )}

              {rolloverStep === 2 && (
                <button
                  className="btn btn-warning"
                  disabled={confirmText !== 'ROLLOVER' || rollingOver}
                  onClick={handleRolloverSubmit}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <RefreshCw size={14} className={rollingOver ? 'spin' : ''} />
                  <span>{rollingOver ? 'Executing...' : 'Execute Rollover'}</span>
                </button>
              )}

              {rolloverStep === 3 && (
                <button
                  className="btn btn-success"
                  disabled={creatingNext || !nextName}
                  onClick={handleCreateNextSemester}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <span>{creatingNext ? 'Initializing...' : 'Initialize & Activate'}</span>
                  <ArrowRight size={14} />
                </button>
              )}

              {rolloverStep === 4 && (
                <button className="btn btn-primary" onClick={() => setRolloverModalOpen(false)}>
                  Done
                </button>
              )}
            </div>
          </div>
        }
      >
        <div>
          {/* Step Indicators */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px', position: 'relative' }}>
            <div style={{
              position: 'absolute',
              top: '14px',
              left: '10%',
              right: '10%',
              height: '2px',
              background: 'var(--border)',
              zIndex: 0
            }} />
            <div style={{
              position: 'absolute',
              top: '14px',
              left: '10%',
              width: rolloverStep === 1 ? '0%' : rolloverStep === 2 ? '33.3%' : rolloverStep === 3 ? '66.6%' : '100%',
              height: '2px',
              background: 'var(--accent)',
              zIndex: 0,
              transition: 'width 0.3s ease'
            }} />
            
            <div style={{ zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
              <div style={{
                width: '30px',
                height: '30px',
                borderRadius: '50%',
                background: rolloverStep >= 1 ? 'var(--accent)' : 'var(--bg-secondary)',
                border: '2px solid var(--border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                color: '#fff',
                fontSize: '12px'
              }}>1</div>
              <span style={{ fontSize: '10px', marginTop: '4px', color: rolloverStep >= 1 ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Impact Summary</span>
            </div>

            <div style={{ zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
              <div style={{
                width: '30px',
                height: '30px',
                borderRadius: '50%',
                background: rolloverStep >= 2 ? 'var(--accent)' : 'var(--bg-secondary)',
                border: '2px solid var(--border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                color: '#fff',
                fontSize: '12px'
              }}>2</div>
              <span style={{ fontSize: '10px', marginTop: '4px', color: rolloverStep >= 2 ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Authorization</span>
            </div>

            <div style={{ zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
              <div style={{
                width: '30px',
                height: '30px',
                borderRadius: '50%',
                background: rolloverStep >= 3 ? 'var(--accent)' : 'var(--bg-secondary)',
                border: '2px solid var(--border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                color: '#fff',
                fontSize: '12px'
              }}>3</div>
              <span style={{ fontSize: '10px', marginTop: '4px', color: rolloverStep >= 3 ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Next Semester</span>
            </div>

            <div style={{ zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
              <div style={{
                width: '30px',
                height: '30px',
                borderRadius: '50%',
                background: rolloverStep >= 4 ? 'var(--success)' : 'var(--bg-secondary)',
                border: '2px solid var(--border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                color: '#fff',
                fontSize: '12px'
              }}>{rolloverStep === 4 ? <CheckCircle size={14} /> : '4'}</div>
              <span style={{ fontSize: '10px', marginTop: '4px', color: rolloverStep >= 4 ? 'var(--success)' : 'var(--text-secondary)' }}>Completion</span>
            </div>
          </div>

          {/* STEP 1: Impact summary */}
          {rolloverStep === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{
                background: 'rgba(239, 68, 68, 0.04)',
                border: '1px solid rgba(239, 68, 68, 0.2)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                display: 'flex',
                gap: '12px'
              }}>
                <ShieldAlert className="text-danger" size={24} style={{ flexShrink: 0 }} />
                <div>
                  <h4 style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '14px', marginBottom: '4px' }}>Irreversible Administrative Action</h4>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                    Executing a semester rollover marks the current calendar session as closed. This action cannot be undone. Please review the system impacts below.
                  </p>
                </div>
              </div>
              
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
                <h5 style={{ fontWeight: 600, marginBottom: '10px', fontSize: '13px' }}>System Changes Imposed:</h5>
                <ul style={{ fontSize: '13px', color: 'var(--text-secondary)', paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <li>Deactivates the current active semester calendar (marks <code>is_active = false</code>).</li>
                  <li>Archives all associated courses linked to this semester (marks <code>is_archived = true</code>), hiding them from active courses listings.</li>
                  <li>Deactivates student enrollments across all class sections belonging to this semester.</li>
                  <li>Audit trail logging: Saves a permanent record of who triggered the rollover and the statistics of modifications.</li>
                </ul>
              </div>
            </div>
          )}

          {/* STEP 2: Authorization */}
          {rolloverStep === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                To authorize this rollover transaction, please confirm that you have exported all academic backups and grades.
              </p>
              
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600, marginBottom: '6px' }}>
                  Type <span style={{ color: 'var(--warning)' }}>ROLLOVER</span> to confirm authorization:
                </label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Type ROLLOVER in all caps"
                  value={confirmText}
                  onChange={e => setConfirmText(e.target.value)}
                  style={{ textTransform: 'uppercase' }}
                  required
                />
              </div>
            </div>
          )}

          {/* STEP 3: Configure Next Semester */}
          {rolloverStep === 3 && (
            <form onSubmit={handleCreateNextSemester} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{
                background: 'rgba(99, 102, 241, 0.08)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
                borderRadius: 'var(--radius-md)',
                padding: '14px',
                fontSize: '13px',
                color: 'var(--text-secondary)'
              }}>
                <strong>Current active semester has been rolled over and archived.</strong> Now, initialize the next active semester calendar session to keep the platform active.
              </div>

              <div className="form-group">
                <label className="form-label">Semester Name *</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Fall 2026, Spring 2027"
                  required
                  value={nextName}
                  onChange={(e) => setNextName(e.target.value)}
                />
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">Start Date</label>
                  <input
                    type="date"
                    className="form-control"
                    value={nextStartDate}
                    onChange={(e) => setNextStartDate(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">End Date</label>
                  <input
                    type="date"
                    className="form-control"
                    value={nextEndDate}
                    onChange={(e) => setNextEndDate(e.target.value)}
                  />
                </div>
              </div>

              <fieldset style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <legend style={{ padding: '0 8px', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>Midterm Exams Slot</legend>
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label">Mids Start Date</label>
                    <input
                      type="date"
                      className="form-control"
                      value={nextMidStart}
                      onChange={(e) => setNextMidStart(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Mids End Date</label>
                    <input
                      type="date"
                      className="form-control"
                      value={nextMidEnd}
                      onChange={(e) => setNextMidEnd(e.target.value)}
                    />
                  </div>
                </div>
              </fieldset>

              <fieldset style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <legend style={{ padding: '0 8px', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>Final Exams Slot</legend>
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label">Finals Start Date</label>
                    <input
                      type="date"
                      className="form-control"
                      value={nextFinalStart}
                      onChange={(e) => setNextFinalStart(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Finals End Date</label>
                    <input
                      type="date"
                      className="form-control"
                      value={nextFinalEnd}
                      onChange={(e) => setNextFinalEnd(e.target.value)}
                    />
                  </div>
                </div>
              </fieldset>
            </form>
          )}

          {/* STEP 4: Success & Finish */}
          {rolloverStep === 4 && (
            <div style={{ textAlign: 'center', padding: '16px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                background: 'rgba(16, 185, 129, 0.1)',
                border: '2px solid var(--success)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--success)'
              }}>
                <CheckCircle size={32} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)' }}>Semester Transition Complete!</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '380px' }}>
                Semester transition has been executed successfully. The database has been updated.
              </p>

              <div style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                width: '100%',
                maxWidth: '400px',
                marginTop: '8px',
                textAlign: 'left',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>Archived Session ({rolloverSem?.name})</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Courses Archived:</span>
                  <span style={{ fontWeight: 600 }}>{rolloverResult?.courses_archived}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Enrollments Deactivated:</span>
                  <span style={{ fontWeight: 600 }}>{rolloverResult?.enrollments_deactivated}</span>
                </div>

                <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--accent-light)', borderBottom: '1px solid var(--border)', paddingBottom: '4px', marginTop: '12px' }}>Activated Session ({nextSemResult?.name})</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Status:</span>
                  <span style={{ fontWeight: 600, color: 'var(--success)' }}>Active Academic Session</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Start Date:</span>
                  <span style={{ fontWeight: 600 }}>{nextSemResult?.start_date ? new Date(nextSemResult.start_date).toLocaleDateString() : 'TBD'}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
