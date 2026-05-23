import React from 'react';

export default function MetricCard({ title, value, type }) {
  const formatRupiah = (val) => {
    return 'Rp ' + val.toLocaleString('id-ID');
  };

  return (
    <div className={`metric-card ${type}`}>
      <p className="metric-title">{title}</p>
      <p className="metric-value">{formatRupiah(value)}</p>
    </div>
  );
}
