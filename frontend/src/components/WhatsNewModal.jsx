import React from 'react';

const serifStyle = { fontFamily: 'Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif' };
const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };

function formatPublishedDate(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  try {
    return new Intl.DateTimeFormat('en-GB', {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
    }).format(new Date(raw));
  } catch (_) {
    return raw;
  }
}

function normalizeReleaseItems(items = []) {
  return (Array.isArray(items) ? items : [])
    .map((item, index) => {
      if (typeof item === 'string') {
        return {
          id: `release-item-${index}`,
          title: `Update ${String(index + 1).padStart(2, '0')}`,
          body: item,
          tag: '',
        };
      }
      const title = String(item?.title || '').trim();
      const body = String(item?.body || '').trim();
      if (!title && !body) return null;
      return {
        id: String(item?.id || title || `release-item-${index}`),
        title: title || `Update ${String(index + 1).padStart(2, '0')}`,
        body,
        tag: String(item?.tag || '').trim(),
      };
    })
    .filter(Boolean);
}

export default function WhatsNewModal({ darkMode, release, onClose }) {
  if (!release) return null;

  const requestedVersion = String(release.requestedVersion || release.version || '').trim();
  const sourceVersion = String(release.sourceVersion || release.version || '').trim();
  const versionLabel =
    release.isFallback && requestedVersion && requestedVersion !== sourceVersion
      ? `Version ${requestedVersion} - notes from ${sourceVersion}`
      : `Version ${sourceVersion}`;
  const publishedLabel = formatPublishedDate(release.publishedAt);
  const summary = String(release.summary || '').trim();
  const note = String(release.note || '').trim();
  const items = normalizeReleaseItems(release.items);

  const shellClass = darkMode
    ? 'border-zinc-800 bg-zinc-950 text-zinc-100 shadow-[0_32px_96px_rgba(0,0,0,0.56)]'
    : 'border-zinc-200 bg-[#fffdfa] text-zinc-900 shadow-[0_32px_96px_rgba(20,14,33,0.18)]';
  const dividerClass = darkMode ? 'border-zinc-800' : 'border-zinc-200';
  const topBarClass = darkMode ? 'border-zinc-800 bg-zinc-950' : 'border-zinc-200 bg-[#fffdfa]';
  const eyebrowClass = darkMode ? 'text-teal-200/85' : 'text-teal-700';
  const subtleClass = darkMode ? 'text-zinc-400' : 'text-zinc-500';
  const bodyClass = darkMode ? 'text-zinc-300' : 'text-zinc-600';
  const titleClass = darkMode ? 'text-zinc-50' : 'text-zinc-900';
  const quietButtonClass = darkMode
    ? 'border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-zinc-100'
    : 'border-zinc-300 text-zinc-600 hover:border-zinc-500 hover:text-zinc-900';
  const pillClass = darkMode
    ? 'border-zinc-700 bg-zinc-900 text-zinc-300'
    : 'border-zinc-200 bg-zinc-100 text-zinc-700';
  const tagClass = darkMode
    ? 'border-teal-500/30 bg-teal-950 text-teal-100'
    : 'border-teal-200 bg-teal-100 text-teal-800';
  const noteClass = darkMode
    ? 'border-amber-500/25 bg-[#241a0e] text-amber-100'
    : 'border-amber-200 bg-[#fff7e8] text-amber-900';
  const railClass = darkMode ? 'border-zinc-800' : 'border-zinc-200';
  const sectionTintClass = darkMode ? 'bg-zinc-950' : 'bg-[#fffdfa]';
  const indexBadgeClass = darkMode
    ? 'border-zinc-700 bg-zinc-900 text-teal-100'
    : 'border-zinc-200 bg-white text-teal-700';
  const itemTitleClass = darkMode ? 'text-zinc-100' : 'text-zinc-900';

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/35 p-4 backdrop-blur-[2px]">
      <div className={`w-full max-w-[980px] overflow-hidden rounded-[28px] border ${shellClass}`}>
        <div className={`flex items-center gap-4 border-b px-6 py-4 ${topBarClass}`}>
          <div className="flex items-center gap-3">
            <div className={`flex h-8 w-8 items-center justify-center rounded-full border ${darkMode ? 'border-teal-500/30 bg-teal-500/10 text-teal-100' : 'border-teal-200 bg-teal-50 text-teal-700'}`}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M8 2.2L9.3 5.3L12.4 6.6L9.3 7.9L8 11L6.7 7.9L3.6 6.6L6.7 5.3L8 2.2Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <div className={`text-[10px] font-semibold uppercase tracking-[0.24em] ${eyebrowClass}`} style={monoStyle}>
                New in this build
              </div>
              <div className={`mt-1 text-sm ${subtleClass}`}>Version notes for the current desktop release</div>
            </div>
          </div>
          <div className="flex-1" />
          <button
            type="button"
            onClick={onClose}
            className={`border-b pb-1 text-[13px] transition ${quietButtonClass}`}
            aria-label="Close What's New"
          >
            Close
          </button>
        </div>

        <div className={`grid gap-8 px-6 py-6 sm:px-8 sm:py-7 xl:grid-cols-[272px_minmax(0,1fr)] ${sectionTintClass}`}>
          <aside className={`space-y-5 xl:border-r xl:pr-8 ${railClass}`}>
            <div>
              <div className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${subtleClass}`} style={monoStyle}>
                Build overview
              </div>
              <h2 className={`mt-3 text-[2rem] font-medium leading-[1.05] tracking-[-0.05em] ${titleClass}`} style={serifStyle}>
                {release.headline}
              </h2>
              {summary ? <p className={`mt-4 text-sm leading-relaxed ${bodyClass}`}>{summary}</p> : null}
            </div>

            <div className="flex flex-wrap gap-2">
              <span className={`inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-medium ${pillClass}`}>
                {versionLabel}
              </span>
              {publishedLabel ? (
                <span className={`inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-medium ${pillClass}`}>
                  {publishedLabel}
                </span>
              ) : null}
            </div>

            {note ? (
              <div className={`rounded-[20px] border px-4 py-4 ${noteClass}`}>
                <div className="text-[10px] font-semibold uppercase tracking-[0.18em]" style={monoStyle}>
                  Note
                </div>
                <p className="mt-2 text-sm leading-relaxed">{note}</p>
              </div>
            ) : null}
          </aside>

          <section>
            <div className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${subtleClass}`} style={monoStyle}>
              Highlights
            </div>
            <div className={`mt-4 divide-y ${dividerClass}`}>
              {items.map((item, index) => (
                <div key={item.id} className="grid gap-4 py-4 md:grid-cols-[84px_minmax(0,1fr)]">
                  <div className="flex flex-col gap-2 md:pt-0.5">
                    <span className={`inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${indexBadgeClass}`} style={monoStyle}>
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    {item.tag ? (
                      <span className={`inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${tagClass}`} style={monoStyle}>
                        {item.tag}
                      </span>
                    ) : null}
                  </div>
                  <div>
                    <h3 className={`text-[1.05rem] font-semibold tracking-[-0.02em] ${itemTitleClass}`}>{item.title}</h3>
                    {item.body ? <p className={`mt-2 text-sm leading-relaxed ${bodyClass}`}>{item.body}</p> : null}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
