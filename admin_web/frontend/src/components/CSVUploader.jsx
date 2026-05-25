import { useState, useRef } from 'react';
import { UploadCloud, FileSpreadsheet, CheckCircle, AlertTriangle } from 'lucide-react';

export default function CSVUploader({
  title = 'Upload CSV File',
  subtitle = 'Drag and drop your file here, or click to browse',
  onUpload,
  accept = '.csv',
}) {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [successResult, setSuccessResult] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  };

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  };

  const processFile = (selectedFile) => {
    setError('');
    setSuccessResult(null);
    if (!selectedFile.name.endsWith('.csv')) {
      setError('Only CSV files are allowed.');
      setFile(null);
      return;
    }
    setFile(selectedFile);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const result = await onUpload(file);
      setSuccessResult(result);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to upload CSV.');
    } finally {
      setLoading(false);
    }
  };

  const handleAreaClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div
        className={`csv-drop-zone ${dragOver ? 'drag-over' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleAreaClick}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept={accept}
          style={{ display: 'none' }}
        />
        <UploadCloud size={40} style={{ color: 'var(--text-muted)', margin: '0 auto' }} />
        <h4>{title}</h4>
        <p>{subtitle}</p>
        {file && (
          <div
            style={{
              marginTop: '12px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: 'var(--bg-card-hover)',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <FileSpreadsheet size={16} style={{ color: 'var(--accent-light)' }} />
            <span style={{ fontSize: '13px', fontWeight: 500 }}>{file.name}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="result-box error" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {successResult && (
        <div className="result-box success" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
            <CheckCircle size={18} />
            <span>Upload Completed Successfully</span>
          </div>
          <ul style={{ paddingLeft: '20px', fontSize: '13px', marginTop: '4px' }}>
            <li>Created / Enrolled: <strong>{successResult.created ?? successResult.enrolled ?? 0}</strong></li>
            <li>Skipped: <strong>{successResult.skipped ?? 0}</strong></li>
            {successResult.errors && successResult.errors.length > 0 && (
              <li style={{ marginTop: '4px' }}>
                <span className="text-warning">Errors / Warnings ({successResult.errors.length}):</span>
                <div
                  style={{
                    maxHeight: '100px',
                    overflowY: 'auto',
                    background: 'rgba(0,0,0,0.2)',
                    padding: '8px',
                    borderRadius: '4px',
                    marginTop: '4px',
                    fontFamily: 'monospace',
                    fontSize: '11px',
                  }}
                >
                  {successResult.errors.map((err, i) => (
                    <div key={i}>{err}</div>
                  ))}
                </div>
              </li>
            )}
          </ul>
        </div>
      )}

      {file && (
        <button
          className="btn btn-primary w-full"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? 'Uploading...' : 'Process CSV File'}
        </button>
      )}
    </div>
  );
}
