import React from 'react';

// A panel is a block of the deep background on the ink page. No border, no shadow.
export const Panel: React.FC<{ title: string; note?: React.ReactNode; children: React.ReactNode }> = ({ title, note, children }) => (
  <div className="bg-deep rounded-md flex flex-col h-full overflow-hidden">
    <div className="px-4 pt-4 pb-2 flex items-baseline justify-between gap-2">
      <h2 className="font-display text-lg text-fog">{title}</h2>
      {note && <span className="text-sm text-mist">{note}</span>}
    </div>
    {children}
  </div>
);

export const verdictColor: Record<string, string> = {
  exploited: 'text-attack',
  blocked_by_edge: 'text-hold',
  sanitized_by_v2: 'text-ok',
  benign: 'text-mist',
};
