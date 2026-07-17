import React, { useState } from 'react';

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

function ExistingPlanActivationPanel({ darkMode, electronAPI, onLicenseChanged }) {
  const api = electronAPI ?? (typeof window !== 'undefined' ? window.electronAPI : undefined);
  const [paypalId, setPayPalId] = useState('');
  const [email, setEmail] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [statusTone, setStatusTone] = useState('muted');
  const [isVerifying, setIsVerifying] = useState(false);

  const panelClass = darkMode
    ? 'border-teal-500/25 bg-teal-950/30 text-teal-50'
    : 'border-teal-200 bg-teal-50 text-teal-950';
  const helperClass = darkMode ? 'text-teal-100/80' : 'text-teal-900/75';
  const inputClass = darkMode
    ? 'border-teal-500/25 bg-zinc-950/80 text-zinc-50 placeholder:text-zinc-500 focus:border-teal-300'
    : 'border-teal-200 bg-white text-zinc-900 placeholder:text-zinc-400 focus:border-teal-600';
  const buttonClass = darkMode
    ? 'bg-teal-200 text-zinc-950 hover:bg-teal-100 disabled:bg-zinc-700 disabled:text-zinc-400'
    : 'bg-teal-700 text-white hover:bg-teal-800 disabled:bg-zinc-300 disabled:text-zinc-500';
  const messageClass =
    statusTone === 'success'
      ? darkMode ? 'text-emerald-200' : 'text-emerald-700'
      : statusTone === 'error'
        ? darkMode ? 'text-rose-200' : 'text-rose-700'
        : helperClass;

  const handleSubmit = async (event) => {
    event.preventDefault();
    const cleanPayPalId = paypalId.trim();
    const cleanEmail = email.trim();

    if (!cleanPayPalId) {
      setStatusTone('error');
      setStatusMessage('Enter your PayPal subscription or transaction ID');
      return;
    }
    if (typeof api?.activatePayPalPurchase !== 'function') {
      setStatusTone('error');
      setStatusMessage('PayPal verification is unavailable in this build');
      return;
    }

    setIsVerifying(true);
    setStatusTone('muted');
    setStatusMessage('Verifying...');
    try {
      const response = await api.activatePayPalPurchase({
        paypalId: cleanPayPalId,
        email: cleanEmail,
      });

      if (response?.ok) {
        if (response?.status?.active !== true) {
          setStatusTone('error');
          setStatusMessage('Verification did not return an active license');
          return;
        }
        setStatusTone('success');
        setStatusMessage('Purchase verified');
        onLicenseChanged && onLicenseChanged(response.status);
        return;
      }

      setStatusTone('error');
      setStatusMessage(response?.error || 'Verification failed');
    } catch (error) {
      setStatusTone('error');
      setStatusMessage(error?.message || 'Verification failed');
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <form className={`rounded-[20px] border px-4 py-4 ${panelClass}`} onSubmit={handleSubmit}>
      <div className="text-[10px] font-semibold uppercase" style={monoStyle}>
        Account access
      </div>
      <h3 className="mt-2 text-[1rem] font-semibold">Activate your plan</h3>
      <p className={`mt-2 text-xs leading-relaxed ${helperClass}`}>
        Have an active PayPal subscription or purchase receipt? Verify it here to unlock premium features on this device.
      </p>
      <div className="mt-3 space-y-2">
        <input
          value={paypalId}
          onChange={(event) => setPayPalId(event.target.value)}
          className={`w-full rounded-lg border px-3 py-2 text-xs outline-none transition ${inputClass}`}
          placeholder="I-... subscription or transaction ID"
          aria-label="PayPal subscription or transaction ID"
        />
        <input
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className={`w-full rounded-lg border px-3 py-2 text-xs outline-none transition ${inputClass}`}
          placeholder="PayPal email"
          aria-label="PayPal email"
        />
        <button
          type="submit"
          disabled={isVerifying}
          className={`w-full rounded-lg px-3 py-2 text-xs font-semibold transition ${buttonClass}`}
        >
          {isVerifying ? 'Verifying...' : 'Verify and unlock'}
        </button>
      </div>
      {statusMessage ? <div className={`mt-2 text-xs ${messageClass}`}>{statusMessage}</div> : null}
    </form>
  );
}

export default function WhatsNewModal({
  darkMode,
  release,
  onClose,
  license,
  electronAPI,
  onLicenseChanged,
}) {
  const [existingPlanVerified, setExistingPlanVerified] = useState(false);

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
  const handleExistingPlanChanged = (status) => {
    setExistingPlanVerified(true);
    onLicenseChanged && onLicenseChanged(status);
  };
  const showExistingPlanActivation =
    Boolean(license) && !license?.checking && (!license?.active || existingPlanVerified);

  return (
    <div className="fixed inset-0 z-[90] flex items-stretch justify-center bg-black/35 p-3 backdrop-blur-[2px] sm:items-center sm:p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="What's New"
        className={`flex max-h-[calc(100dvh-1.5rem)] w-full max-w-[980px] flex-col overflow-hidden rounded-2xl border sm:max-h-[calc(100dvh-2rem)] sm:rounded-[28px] ${shellClass}`}
      >
        <div className={`flex shrink-0 flex-wrap items-center gap-3 border-b px-4 py-3 sm:gap-4 sm:px-6 sm:py-4 ${topBarClass}`}>
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${darkMode ? 'border-teal-500/30 bg-teal-500/10 text-teal-100' : 'border-teal-200 bg-teal-50 text-teal-700'}`}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M8 2.2L9.3 5.3L12.4 6.6L9.3 7.9L8 11L6.7 7.9L3.6 6.6L6.7 5.3L8 2.2Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="min-w-0">
              <div className={`text-[10px] font-semibold uppercase ${eyebrowClass}`} style={monoStyle}>
                New in this build
              </div>
              <div className={`mt-1 text-sm ${subtleClass}`}>Version notes for the current desktop release</div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className={`shrink-0 border-b pb-1 text-[13px] transition ${quietButtonClass}`}
            aria-label="Close What's New"
          >
            Close
          </button>
        </div>

        <div
          data-testid="whats-new-scroll-body"
          className={`grid min-h-0 flex-1 gap-6 overflow-y-auto px-4 py-5 sm:gap-8 sm:px-8 sm:py-7 lg:grid-cols-[272px_minmax(0,1fr)] ${sectionTintClass}`}
        >
          <aside className={`min-w-0 space-y-5 lg:border-r lg:pr-8 ${railClass}`}>
            <div>
              <div className={`text-[10px] font-semibold uppercase ${subtleClass}`} style={monoStyle}>
                Build overview
              </div>
              <h2 className={`mt-3 break-words text-[1.65rem] font-medium leading-[1.08] sm:text-[2rem] ${titleClass}`} style={serifStyle}>
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

            {showExistingPlanActivation ? (
              <ExistingPlanActivationPanel
                darkMode={darkMode}
                electronAPI={electronAPI}
                onLicenseChanged={handleExistingPlanChanged}
              />
            ) : null}

            {note ? (
              <div className={`rounded-[20px] border px-4 py-4 ${noteClass}`}>
                <div className="text-[10px] font-semibold uppercase" style={monoStyle}>
                  Note
                </div>
                <p className="mt-2 text-sm leading-relaxed">{note}</p>
              </div>
            ) : null}
          </aside>

          <section className="min-w-0">
            <div className={`text-[10px] font-semibold uppercase ${subtleClass}`} style={monoStyle}>
              Highlights
            </div>
            <div className={`mt-4 divide-y ${dividerClass}`}>
              {items.map((item, index) => (
                <div key={item.id} className="grid gap-4 py-4 md:grid-cols-[84px_minmax(0,1fr)]">
                  <div className="flex flex-col gap-2 md:pt-0.5">
                    <span className={`inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase ${indexBadgeClass}`} style={monoStyle}>
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    {item.tag ? (
                      <span className={`inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase ${tagClass}`} style={monoStyle}>
                        {item.tag}
                      </span>
                    ) : null}
                  </div>
                  <div className="min-w-0">
                    <h3 className={`break-words text-[1.05rem] font-semibold ${itemTitleClass}`}>{item.title}</h3>
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
