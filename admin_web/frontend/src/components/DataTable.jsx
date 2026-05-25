import { useState, useMemo } from 'react';
import { Search, ChevronDown, ChevronUp } from 'lucide-react';

export default function DataTable({
  headers,
  data = [],
  searchKeys = [], // e.g. ['name', 'code', 'full_name']
  searchPlaceholder = 'Search...',
  actions,
  renderRow,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortConfig, setSortConfig] = useState(null);

  // Sorting handler
  const handleSort = (key) => {
    let direction = 'ascending';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
  };

  // Filter and sort data
  const processedData = useMemo(() => {
    let result = [...data];

    // Filter
    if (searchQuery && searchKeys.length > 0) {
      result = result.filter((item) =>
        searchKeys.some((key) => {
          const val = item[key];
          return val ? String(val).toLowerCase().includes(searchQuery.toLowerCase()) : false;
        })
      );
    }

    // Sort
    if (sortConfig !== null) {
      result.sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];

        if (aVal === undefined || aVal === null) return 1;
        if (bVal === undefined || bVal === null) return -1;

        if (aVal < bVal) {
          return sortConfig.direction === 'ascending' ? -1 : 1;
        }
        if (aVal > bVal) {
          return sortConfig.direction === 'ascending' ? 1 : -1;
        }
        return 0;
      });
    }

    return result;
  }, [data, searchQuery, searchKeys, sortConfig]);

  return (
    <div className="card">
      <div className="card-header">
        {searchKeys.length > 0 ? (
          <div className="search-box">
            <Search size={16} />
            <input
              type="text"
              className="form-control"
              placeholder={searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        ) : (
          <div />
        )}
        {actions && <div className="toolbar-actions">{actions}</div>}
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                {headers.map((h) => (
                  <th
                    key={h.key}
                    onClick={() => h.sortable !== false && handleSort(h.key)}
                    style={{ cursor: h.sortable !== false ? 'pointer' : 'default', userSelect: 'none' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {h.label}
                      {h.sortable !== false && sortConfig?.key === h.key && (
                        sortConfig.direction === 'ascending' ? <ChevronUp size={12} /> : <ChevronDown size={12} />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {processedData.length > 0 ? (
                processedData.map((item, idx) => (
                  <tr key={item.id || idx}>
                    {renderRow ? renderRow(item) : headers.map((h) => <td key={h.key}>{item[h.key]}</td>)}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={headers.length} className="empty-state">
                    <div className="empty-state-icon">🔍</div>
                    <h3>No items found</h3>
                    <p>Try adjusting your search query or add a new record.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
