export default function StatCard({ title, value, icon: Icon, color = 'var(--accent)' }) {
  return (
    <div className="stat-card" style={{ '--card-color': color }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span className="stat-card-label">{title}</span>
        {Icon && (
          <div className="stat-card-icon" style={{ background: color, color: '#fff' }}>
            <Icon size={20} />
          </div>
        )}
      </div>
      <div className="stat-card-value">
        {value !== undefined && value !== null ? value : '-'}
      </div>
    </div>
  );
}
