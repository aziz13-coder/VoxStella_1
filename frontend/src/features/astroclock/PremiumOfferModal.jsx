import React, { useState } from 'react';
import { X } from 'lucide-react';

const monoStyle = { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace' };
export const PREMIUM_OFFER_PAYPAL_PRODUCT_DESCRIPTION = 'Vox Stella Premium Desktop Monthly - discounted in-app monthly subscription for full access to Astro Clock premium workflows, Synastry, Transits, Astrocartography, Trait Profile, Election, Forensic, Certification, saved analysis tools, AI-ready prompts, exports, and professional chart workspaces.';

function PayPalSubscriptionCheckout({ onActivated }) {
  const [status, setStatus] = useState('idle');
  const [subscriptionId, setSubscriptionId] = useState('');
  const [activationError, setActivationError] = useState('');

  const openCheckout = async () => {
    setActivationError('');
    const openPayPalCheckout = window.electronAPI?.openPayPalCheckout;
    if (typeof openPayPalCheckout !== 'function') {
      setStatus('checkout_error');
      setActivationError('Secure browser checkout is available in the desktop app.');
      return;
    }
    setStatus('opening');
    try {
      const result = await openPayPalCheckout();
      if (result?.ok === false) {
        setActivationError(result.error || 'The secure checkout page could not be opened.');
        setStatus('checkout_error');
        return;
      }
      setStatus('checkout_opened');
    } catch (error) {
      setActivationError(error?.message || 'The secure checkout page could not be opened.');
      setStatus('checkout_error');
    }
  };

  const activateSubscription = async () => {
    const approvedSubscriptionId = subscriptionId.trim();
    setActivationError('');
    if (!approvedSubscriptionId) {
      setActivationError('Enter the PayPal subscription ID shown after checkout.');
      setStatus('activation_error');
      return;
    }

    const activatePayPalSubscription = window.electronAPI?.activatePayPalSubscription;
    if (typeof activatePayPalSubscription !== 'function') {
      setActivationError('License activation is available in the desktop app.');
      setStatus('activation_error');
      return;
    }

    setStatus('activating');
    try {
      const result = await activatePayPalSubscription({ subscriptionId: approvedSubscriptionId });
      if (result?.ok) {
        const pending = result?.provisional || result?.status?.pendingPayPalVerification;
        setStatus(pending ? 'temporary_activated' : 'activated');
        onActivated?.(result.status || { active: true });
      } else {
        setActivationError(result?.error || 'License activation failed.');
        setStatus('activation_error');
      }
    } catch (error) {
      setActivationError(error?.message || 'License activation failed.');
      setStatus('activation_error');
    }
  };

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={openCheckout}
        disabled={status === 'opening'}
        className="w-full rounded-[6px] bg-[#ffc439] px-4 py-3 text-sm font-bold text-slate-950 shadow-sm transition hover:bg-[#f4b72f] disabled:cursor-wait disabled:opacity-70"
      >
        {status === 'opening' ? 'Opening secure checkout...' : 'Continue securely with PayPal'}
      </button>
      <p className="text-xs leading-5 text-slate-500">
        Checkout opens in your normal browser, isolated from the app. Return here with the subscription ID PayPal displays after approval.
      </p>
      <label className="block text-xs font-semibold text-zinc-700" htmlFor="premium-paypal-subscription-id">
        PayPal subscription ID
      </label>
      <input
        id="premium-paypal-subscription-id"
        value={subscriptionId}
        onChange={(event) => setSubscriptionId(event.target.value)}
        placeholder="I-..."
        autoComplete="off"
        spellCheck="false"
        className="w-full rounded-[6px] border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
      />
      <button
        type="button"
        onClick={activateSubscription}
        disabled={status === 'activating'}
        className="w-full rounded-[6px] border border-zinc-300 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-900 shadow-sm transition hover:border-zinc-500 disabled:cursor-wait disabled:opacity-70"
      >
        {status === 'activating' ? 'Verifying subscription...' : 'Verify subscription and unlock'}
      </button>
      {status === 'checkout_opened' ? (
        <p role="status" className="rounded-[6px] border border-blue-200 bg-blue-50 px-3 py-2 text-xs leading-5 text-blue-800">
          Secure checkout opened in your browser. Complete it there, then paste the PayPal subscription ID above.
        </p>
      ) : null}
      {status === 'checkout_error' ? (
        <p role="alert" className="rounded-[6px] border border-rose-200 bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-700">
          {activationError || 'PayPal checkout could not be opened. Check your connection and try again.'}
        </p>
      ) : null}
      {status === 'activating' ? (
        <p role="status" className="rounded-[6px] border border-blue-200 bg-blue-50 px-3 py-2 text-xs leading-5 text-blue-800">
          Verifying subscription {subscriptionId.trim()} and activating premium access on this device...
        </p>
      ) : null}
      {status === 'activated' ? (
        <p role="status" className="rounded-[6px] border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs leading-5 text-emerald-800">
          Premium access is active on this device. You can close this window and continue in Vox Stella.
        </p>
      ) : null}
      {status === 'temporary_activated' ? (
        <p role="status" className="rounded-[6px] border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
          PayPal activation is pending. Protected features remain locked until the license server confirms the subscription. Open Settings and press Finish PayPal activation when reachable.
        </p>
      ) : null}
      {status === 'activation_error' ? (
        <p role="alert" className="rounded-[6px] border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
          {activationError || 'Vox Stella could not verify this subscription. Check the ID or contact support.'}
        </p>
      ) : null}
    </div>
  );
}

export default function PremiumOfferModal({
  open,
  featureName = 'Premium workflow',
  onClose,
  onActivated,
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[95] flex items-stretch justify-center bg-slate-950/48 p-3 backdrop-blur-sm sm:items-center sm:p-5">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Vox Stella desktop offer"
        data-testid="premium-offer-modal"
        className="relative flex max-h-[calc(100dvh-1.5rem)] w-full max-w-[900px] flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white text-zinc-950 shadow-[0_30px_80px_rgba(20,20,18,0.18),0_4px_16px_rgba(20,20,18,0.06)] sm:max-h-[calc(100dvh-2.5rem)]"
      >
        <div className="flex items-start justify-between gap-4 border-b border-zinc-200 px-5 py-5 sm:px-7">
          <div className="min-w-0">
            <div className="text-[0.68rem] font-extrabold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
              Desktop offer
            </div>
            <h2 className="mt-3 max-w-2xl text-[1.75rem] font-semibold leading-tight tracking-normal text-zinc-950 sm:text-[2.1rem]">
              Unlock the full suite
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-600">
              This desktop-only monthly offer unlocks premium workflows inside the app, including Astro Clock, saved analysis, AI-ready exports, and professional chart workspace tools.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close offer"
            title="Close offer"
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-zinc-200 bg-white text-zinc-600 shadow-sm transition hover:border-zinc-400 hover:text-zinc-950"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-7 sm:py-6">
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-0">
            <div className="min-w-0">
              <div className="flex flex-wrap items-end gap-x-3 gap-y-1 font-extrabold text-zinc-950">
                <span className="text-[2.75rem] leading-none">$25</span>
                <span className="pb-1 text-[0.95rem] font-semibold text-zinc-500">/ month</span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-zinc-600">
                <span className="rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 font-semibold text-zinc-700">
                  Standard monthly plan: $35
                </span>
                <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 font-semibold text-amber-800">
                  Save nearly 30%
                </span>
              </div>

              <ul className="mt-5 grid gap-3 text-sm leading-6 text-zinc-900 sm:grid-cols-2">
                {[
                  'Synastry, Transits, Astrocartography, Trait Profile',
                  'Election, Forensic, Certification, and specialty models',
                  'Full Astro Clock premium feature rail',
                  'AI-ready prompts, exports, and saved workflow tools',
                ].map((item) => (
                  <li key={item} className="relative pl-6">
                    <span className="absolute left-0 top-2 h-2.5 w-2.5 rounded-full bg-amber-400" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex flex-col justify-between gap-4 border-t border-zinc-200 pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
              <div>
                <div className="text-[0.7rem] font-extrabold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
                  Checkout
                </div>
                <p className="mt-2 text-sm leading-6 text-zinc-600">
                  Subscribe securely with PayPal. Vox Stella never collects or stores your card details.
                </p>
                <div className="mt-4 border-t border-zinc-200 pt-4">
                  <div className="text-[0.65rem] font-extrabold uppercase tracking-[0.16em] text-zinc-500" style={monoStyle}>
                    Product description
                  </div>
                  <p className="mt-2 text-xs leading-5 text-zinc-600">
                    {PREMIUM_OFFER_PAYPAL_PRODUCT_DESCRIPTION}
                  </p>
                </div>
              </div>
              <PayPalSubscriptionCheckout onActivated={onActivated} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
