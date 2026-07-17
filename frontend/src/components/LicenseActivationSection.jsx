import React, { useEffect, useId, useRef, useState } from 'react';
import { Shield } from 'lucide-react';

const devRuntimeFallback = () => (
  typeof window !== 'undefined' && window.IS_PACKAGED === false
);

export default function LicenseActivationSection({
  darkMode,
  devLicenseRuntime,
  electronAPI,
  onInvalidateToken,
  onLicenseChanged,
}) {
  const api = electronAPI ?? (typeof window !== 'undefined' ? window.electronAPI : undefined);
  const invalidateToken = typeof onInvalidateToken === 'function' ? onInvalidateToken : () => {};
  const onLicenseChangedRef = useRef(onLicenseChanged);
  const isDevRuntime = typeof devLicenseRuntime === 'boolean'
    ? devLicenseRuntime
    : devRuntimeFallback();
  const cardBg = darkMode
    ? 'bg-gray-800/60 backdrop-blur-xl border-gray-700'
    : 'bg-white/60 backdrop-blur-xl border-white/80';
  const inputClass = `w-full px-3 py-2 rounded border ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'}`;
  const mutedText = darkMode ? 'text-gray-400' : 'text-gray-500';
  const divider = darkMode ? 'border-gray-700' : 'border-gray-200';
  const reactId = useId();
  const licenseKeyInputId = `${reactId}-license-key`;
  const licenseEmailInputId = `${reactId}-license-email`;
  const paypalPurchaseInputId = `${reactId}-paypal-purchase-id`;
  const licenseKeyPanelId = `${reactId}-license-key-panel`;

  const [license, setLicense] = useState(() =>
    isDevRuntime ? { active: true, plan: 'dev' } : { active: false }
  );
  const [licenseKey, setLicenseKey] = useState('');
  const [licenseEmail, setLicenseEmail] = useState('');
  const [paypalPurchaseId, setPayPalPurchaseId] = useState('');
  const [showLicenseKeyActivation, setShowLicenseKeyActivation] = useState(false);
  const [licMsg, setLicMsg] = useState('');
  const [verifyMeta, setVerifyMeta] = useState(null);
  const [verifyLoading, setVerifyLoading] = useState(false);

  useEffect(() => {
    onLicenseChangedRef.current = onLicenseChanged;
  }, [onLicenseChanged]);

  useEffect(() => {
    let cancelled = false;

    const loadLicenseStatus = async () => {
      try {
        if (isDevRuntime) {
          const status = { active: true, plan: 'dev' };
          if (!cancelled) {
            setLicense(status);
            onLicenseChangedRef.current && onLicenseChangedRef.current(status);
          }
          return;
        }

        const status = await api?.getLicenseStatus?.();
        if (!cancelled && status) {
          setLicense(status);
          onLicenseChangedRef.current && onLicenseChangedRef.current(status);
        }
      } catch (_) {}
    };

    loadLicenseStatus();
    return () => {
      cancelled = true;
    };
  }, [api, isDevRuntime]);

  const handleActivate = async () => {
    setLicMsg('Activating...');
    try {
      const response = await api?.activateLicense?.({
        key: licenseKey.trim(),
        email: licenseEmail.trim(),
      });

      if (response?.ok) {
        if (response?.status?.active !== true) {
          setLicMsg('Verification did not return an active license');
          return;
        }
        invalidateToken();
        setLicense(response.status);
        onLicenseChangedRef.current && onLicenseChangedRef.current(response.status);
        setLicMsg('Activated');
        return;
      }

      setLicMsg(response?.error || 'Activation failed');
    } catch (error) {
      setLicMsg(String(error));
    }
  };

  const handleActivatePayPalPurchase = async () => {
    const paypalId = paypalPurchaseId.trim();
    if (!paypalId) {
      setLicMsg('Enter your PayPal subscription or transaction ID');
      return;
    }
    if (typeof api?.activatePayPalPurchase !== 'function') {
      setLicMsg('PayPal verification is unavailable in this build');
      return;
    }

    setLicMsg('Activating PayPal purchase...');
    try {
      const response = await api.activatePayPalPurchase({
        paypalId,
        email: licenseEmail.trim(),
      });

      if (response?.ok) {
        if (response?.status?.active !== true) {
          setLicMsg('Verification did not return an active license');
          return;
        }
        invalidateToken();
        setLicense(response.status);
        onLicenseChangedRef.current && onLicenseChangedRef.current(response.status);
        setLicMsg('Purchase verified');
        return;
      }

      setLicMsg(response?.error || 'Verification failed');
    } catch (error) {
      setLicMsg(String(error));
    }
  };

  const handleDeactivate = async () => {
    try {
      await api?.deactivateLicense?.();
    } catch (_) {}

    const status = await api?.getLicenseStatus?.();
    setLicense(status || { active: false });
    if (status) {
      onLicenseChangedRef.current && onLicenseChangedRef.current(status);
    }
    setLicMsg('Deactivated');
    invalidateToken();
  };

  const handleVerifyNow = async () => {
    setVerifyLoading(true);
    setLicMsg('Verifying online...');
    try {
      const result = await api?.verifyLicense?.();
      if (result?.ok) {
        const meta = {
          at: new Date().toISOString(),
          response: result.result || {},
          success: true,
        };
        setVerifyMeta(meta);
        setLicMsg('License verification succeeded');
        const status = await api?.getLicenseStatus?.();
        if (status) {
          setLicense(status);
          onLicenseChangedRef.current && onLicenseChangedRef.current(status);
        }
      } else {
        setVerifyMeta({
          at: new Date().toISOString(),
          success: false,
          error: result?.error || 'Verification failed',
          response: result?.result || null,
        });
        setLicMsg(result?.error || 'Verification failed');
        invalidateToken();
        const status = await api?.getLicenseStatus?.();
        setLicense(status || { active: false });
        if (status) {
          onLicenseChangedRef.current && onLicenseChangedRef.current(status);
        }
      }
    } catch (error) {
      setVerifyMeta({
        at: new Date().toISOString(),
        success: false,
        error: error.message,
      });
      setLicMsg(`Verification error: ${error.message}`);
    } finally {
      setVerifyLoading(false);
    }
  };

  return (
    <div className={`${cardBg} border rounded-2xl p-6`}>
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        License and Activation
        <Shield className="w-4 h-4 ml-2 text-indigo-500" />
      </h3>
      {isDevRuntime ? (
        <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
          <div className="flex justify-between">
            <span>Status</span>
            <span className="text-emerald-500">Development Active</span>
          </div>
          <div className="flex justify-between">
            <span>Plan</span>
            <span>dev</span>
          </div>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs leading-relaxed text-emerald-900 dark:border-emerald-800/40 dark:bg-emerald-900/20 dark:text-emerald-100">
            Source-run development bypass is active. License activation and online verification are disabled here,
            but packaged builds still require the normal secure license flow.
          </div>
        </div>
      ) : license.pendingPayPalVerification ? (
        <div className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
          <div className="flex justify-between">
            <span>Status</span>
            <span className="text-amber-500">PayPal verification pending</span>
          </div>
          <div className="flex justify-between"><span>Plan</span><span>{license.plan || 'pending'}</span></div>
          {license.pendingExpiresAt && (
            <div className="flex justify-between"><span>Pending until</span><span>{new Date((license.pendingExpiresAt || 0) * 1000).toLocaleDateString()}</span></div>
          )}
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-900 dark:border-amber-800/40 dark:bg-amber-900/20 dark:text-amber-100">
            PayPal activation is saved on this device, but protected features stay locked until the license server confirms the subscription.
          </div>
          <div className="pt-3 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={handleDeactivate} className="px-3 py-1.5 text-sm rounded bg-red-600 text-white hover:bg-red-700">Clear pending activation</button>
              <button
                onClick={handleVerifyNow}
                disabled={verifyLoading}
                className="px-3 py-1.5 text-sm rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-gray-400"
              >
                {verifyLoading ? 'Verifying...' : 'Finish PayPal activation'}
              </button>
            </div>
            {licMsg && <div className="text-xs text-gray-500">{licMsg}</div>}
            {verifyMeta && (
              <div className="text-xs text-gray-500">
                Last verified: {new Date(verifyMeta.at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      ) : license.active ? (
        <div className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
          <div className="flex justify-between">
            <span>Status</span>
            <span className="text-emerald-500">Active</span>
          </div>
          <div className="flex justify-between"><span>Plan</span><span>{license.plan || 'standard'}</span></div>
          {license.exp && (
            <div className="flex justify-between"><span>Expires</span><span>{new Date((license.exp || 0) * 1000).toLocaleDateString()}</span></div>
          )}
          {license.deviceId && (
            <div className="flex justify-between"><span>Device</span><span className="truncate max-w-xs">{license.deviceId}</span></div>
          )}
          <div className="pt-3 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={handleDeactivate} className="px-3 py-1.5 text-sm rounded bg-red-600 text-white hover:bg-red-700">Deactivate this device</button>
              <button
                onClick={handleVerifyNow}
                disabled={verifyLoading}
                className="px-3 py-1.5 text-sm rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-gray-400"
              >
                {verifyLoading ? 'Verifying...' : 'Verify Now'}
              </button>
            </div>
            {licMsg && <div className="text-xs text-gray-500">{licMsg}</div>}
            {verifyMeta && (
              <div className="text-xs text-gray-500">
                Last verified: {new Date(verifyMeta.at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-4 text-sm">
          <div className="space-y-3">
            <div>
              <label htmlFor={paypalPurchaseInputId} className="block mb-1">PayPal subscription or transaction ID</label>
              <input
                id={paypalPurchaseInputId}
                value={paypalPurchaseId}
                onChange={(event) => setPayPalPurchaseId(event.target.value)}
                className={inputClass}
                placeholder="I-... subscription or transaction ID"
              />
            </div>
            <div>
              <label htmlFor={licenseEmailInputId} className="block mb-1">Email (optional)</label>
              <input
                id={licenseEmailInputId}
                value={licenseEmail}
                onChange={(event) => setLicenseEmail(event.target.value)}
                className={inputClass}
                placeholder="name@example.com"
              />
            </div>
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <button onClick={handleActivatePayPalPurchase} className="px-4 py-2 text-sm font-medium rounded bg-amber-500 text-gray-950 hover:bg-amber-400">Verify and unlock</button>
              <button onClick={() => api?.openExternal?.('https://voxstella.app/product')} className={`text-sm font-medium underline-offset-4 hover:underline ${mutedText}`}>Purchase License</button>
            </div>
          </div>

          <div className={`border-t ${divider} pt-3 space-y-3`}>
            <button
              type="button"
              aria-expanded={showLicenseKeyActivation}
              aria-controls={licenseKeyPanelId}
              onClick={() => setShowLicenseKeyActivation((value) => !value)}
              className="text-sm font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-300 dark:hover:text-indigo-200"
            >
              {showLicenseKeyActivation ? 'Hide license key' : 'Use a license key instead'}
            </button>
            {showLicenseKeyActivation && (
              <div id={licenseKeyPanelId} className="space-y-3">
                <div>
                  <label htmlFor={licenseKeyInputId} className="block mb-1">License Key</label>
                  <input
                    id={licenseKeyInputId}
                    value={licenseKey}
                    onChange={(event) => setLicenseKey(event.target.value)}
                    className={inputClass}
                    placeholder="XXXX-XXXX-XXXX-XXXX"
                  />
                </div>
                <button onClick={handleActivate} className="px-3 py-1.5 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700">Activate license key</button>
              </div>
            )}
          </div>

          {licMsg && <div className="text-xs text-gray-500">{licMsg}</div>}
          {verifyMeta && (
            <div className="text-xs text-gray-500">
              Last verified: {new Date(verifyMeta.at).toLocaleString()}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
