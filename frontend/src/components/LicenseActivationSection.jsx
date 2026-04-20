import React, { useEffect, useState } from 'react';
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
  const isDevRuntime = typeof devLicenseRuntime === 'boolean'
    ? devLicenseRuntime
    : devRuntimeFallback();
  const cardBg = darkMode
    ? 'bg-gray-800/60 backdrop-blur-xl border-gray-700'
    : 'bg-white/60 backdrop-blur-xl border-white/80';

  const [license, setLicense] = useState(() =>
    isDevRuntime ? { active: true, plan: 'dev' } : { active: false }
  );
  const [licenseKey, setLicenseKey] = useState('');
  const [licenseEmail, setLicenseEmail] = useState('');
  const [licMsg, setLicMsg] = useState('');
  const [verifyMeta, setVerifyMeta] = useState(null);
  const [verifyLoading, setVerifyLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadLicenseStatus = async () => {
      try {
        if (isDevRuntime) {
          const status = { active: true, plan: 'dev' };
          if (!cancelled) {
            setLicense(status);
            onLicenseChanged && onLicenseChanged(status);
          }
          return;
        }

        const status = await api?.getLicenseStatus?.();
        if (!cancelled && status) {
          setLicense(status);
          onLicenseChanged && onLicenseChanged(status);
        }
      } catch (_) {}
    };

    loadLicenseStatus();
    return () => {
      cancelled = true;
    };
  }, [api, isDevRuntime, onLicenseChanged]);

  const handleActivate = async () => {
    setLicMsg('Activating...');
    try {
      const response = await api?.activateLicense?.({
        key: licenseKey.trim(),
        email: licenseEmail.trim(),
      });

      if (response?.ok) {
        invalidateToken();
        setLicense(response.status);
        onLicenseChanged && onLicenseChanged(response.status);
        setLicMsg('Activated');
        return;
      }

      setLicMsg(response?.error || 'Activation failed');
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
      onLicenseChanged && onLicenseChanged(status);
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
          onLicenseChanged && onLicenseChanged(status);
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
          onLicenseChanged && onLicenseChanged(status);
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
      ) : license.active ? (
        <div className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
          <div className="flex justify-between"><span>Status</span><span className="text-emerald-500">Active</span></div>
          <div className="flex justify-between"><span>Plan</span><span>{license.plan || 'standard'}</span></div>
          {license.exp && (
            <div className="flex justify-between"><span>Expires</span><span>{new Date((license.exp || 0) * 1000).toLocaleDateString()}</span></div>
          )}
          {license.deviceId && (
            <div className="flex justify-between"><span>Device</span><span className="truncate max-w-xs">{license.deviceId}</span></div>
          )}
          <div className="pt-3 space-y-2">
            <div className="flex items-center space-x-2">
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
        <div className="space-y-3 text-sm">
          <div>
            <label className="block mb-1">License Key</label>
            <input value={licenseKey} onChange={(event) => setLicenseKey(event.target.value)} className={`w-full px-3 py-2 rounded border ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'}`} placeholder="XXXX-XXXX-XXXX-XXXX" />
          </div>
          <div>
            <label className="block mb-1">Email (optional)</label>
            <input value={licenseEmail} onChange={(event) => setLicenseEmail(event.target.value)} className={`w-full px-3 py-2 rounded border ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'}`} placeholder="name@example.com" />
          </div>
          <div className="pt-2 space-y-2">
            <div className="flex items-center space-x-2">
              <button onClick={handleActivate} className="px-3 py-1.5 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700">Activate</button>
              <button
                onClick={handleVerifyNow}
                disabled={verifyLoading}
                className="px-3 py-1.5 text-sm rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-gray-400"
              >
                {verifyLoading ? 'Verifying...' : 'Verify Now'}
              </button>
              <button onClick={() => api?.openExternal?.('https://voxstella.app/product')} className="px-3 py-1.5 text-sm rounded bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600">Purchase License</button>
            </div>
            {licMsg && <div className="text-xs text-gray-500">{licMsg}</div>}
            {verifyMeta && (
              <div className="text-xs text-gray-500">
                Last verified: {new Date(verifyMeta.at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
