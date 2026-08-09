import { useState, useRef, useCallback } from 'react';
import { X } from 'lucide-react';

export default function Modal({ isOpen, onClose, title, children, footer }) {
  const [shaking, setShaking] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const toastTimerRef = useRef(null);

  const handleOverlayClick = useCallback((e) => {
    // Only trigger if the overlay itself was clicked (not the modal content)
    if (e.target !== e.currentTarget) return;

    // Trigger shake animation
    setShaking(true);
    setTimeout(() => setShaking(false), 500);

    // Show toast warning
    setShowToast(true);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setShowToast(false), 2500);
  }, []);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className={`modal${shaking ? ' modal-shake' : ''}`} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{title}</h2>
          <button className="modal-close" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        <div className="modal-body">
          {children}
        </div>
        {footer && (
          <div className="modal-footer">
            {footer}
          </div>
        )}
      </div>

      {/* Dismiss Warning Toast */}
      {showToast && (
        <div className="modal-dismiss-toast">
          <span className="modal-dismiss-toast-icon">⚠️</span>
          <span>Please close this dialog first using the <strong>✕</strong> button</span>
        </div>
      )}
    </div>
  );
}
