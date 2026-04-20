import React, { useEffect, useState } from 'react';

// Lightweight modal to collect a name and report it back to parent
// Props:
// - open: boolean
// - type: 'natal' | 'case' | 'asset'
// - onCancel: () => void
// - onSubmit: (name: string) => void
export default function NamePromptModal({ open, type, onCancel, onSubmit }) {
  const [value, setValue] = useState('');

  useEffect(() => {
    if (open) setValue('');
  }, [open]);

  if (!open) return null;

  const submit = () => {
    const name = (value || '').trim();
    if (!name) return;
    onSubmit?.(name);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative z-10 w-full max-w-sm">
        <div className="rounded-2xl border shadow-xl p-5 
            bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl 
            border-gray-200/80 dark:border-gray-700">
          <h3 className="font-semibold text-sm mb-3">
            {type === 'natal' ? 'Enter Person Name' : (type === 'asset' ? 'Enter Asset/Instrument Name' : 'Enter Case Name')}
          </h3>
          <input
            autoFocus
            type="text"
            value={value}
            onChange={e=> setValue(e.target.value)}
            onKeyDown={e=> { if (e.key === 'Enter') { e.preventDefault(); submit(); } if (e.key === 'Escape') { e.preventDefault(); onCancel?.(); } }}
            placeholder={
              type === 'natal' ? 'e.g., Jane Doe'
              : type === 'asset' ? 'e.g., Apple Inc. (AAPL)'
              : 'e.g., Springfield burglary'
            }
            className="w-full px-3 py-2 rounded-lg border 
                       bg-white/80 dark:bg-gray-900/60 
                       border-gray-300 dark:border-gray-700 
                       focus:outline-none focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-500 mb-4"
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="px-1.5 py-0.5 rounded-lg border text-[11px]
                         bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300
                         dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700"
              onClick={onCancel}
            >Cancel</button>
            <button
              type="button"
              className="px-1.5 py-0.5 rounded-lg border text-[11px]
                         bg-white/70 hover:bg-white/90 text-gray-800 border-gray-300
                         dark:bg-gray-700/60 dark:hover:bg-gray-700/80 dark:text-gray-100 dark:border-gray-700
                         disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={!value.trim()}
              onClick={submit}
            >Copy</button>
          </div>
        </div>
      </div>
    </div>
  );
}
