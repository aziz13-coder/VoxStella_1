/**
 * Tests for license verification UI wiring.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import LicenseActivationSection from '../components/LicenseActivationSection.jsx';

const makeElectronAPI = (overrides = {}) => ({
  getLicenseStatus: vi.fn().mockResolvedValue({ active: false, plan: 'dev' }),
  activateLicense: vi.fn().mockResolvedValue({ ok: true, status: { active: true, plan: 'dev' } }),
  deactivateLicense: vi.fn().mockResolvedValue({ ok: true }),
  getLicenseToken: vi.fn().mockResolvedValue('dev-token'),
  verifyLicense: vi.fn().mockResolvedValue({ ok: true, result: { status: 'ok' } }),
  activatePayPalPurchase: vi.fn().mockResolvedValue({ ok: true, status: { active: true, plan: 'premium-desktop-lifetime' } }),
  openExternal: vi.fn(),
  ...overrides,
});

const renderSection = (props = {}) => {
  render(
    <LicenseActivationSection
      darkMode={false}
      electronAPI={window.electronAPI}
      onInvalidateToken={vi.fn()}
      {...props}
    />
  );
};

describe('License Verification Settings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      writable: true,
      value: makeElectronAPI(),
    });
    Object.defineProperty(window, 'IS_PACKAGED', {
      configurable: true,
      writable: true,
      value: undefined,
    });
  });

  it('keeps PayPal verification primary while inactive and hides online recheck', async () => {
    renderSection();

    await screen.findByRole('heading', { name: /License and Activation/i });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Verify and unlock/i })).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: 'Verify Now' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^License Key$/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Use a license key instead/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Purchase License/i })).toBeInTheDocument();
  });

  it('renders Verify Now button for an active license', async () => {
    const mockAPI = makeElectronAPI({
      getLicenseStatus: vi.fn().mockResolvedValue({ active: true, plan: 'premium-desktop-monthly' }),
    });
    window.electronAPI = mockAPI;

    renderSection({ electronAPI: mockAPI });
    expect(await screen.findByRole('button', { name: 'Verify Now' })).toBeInTheDocument();
  });

  it('invokes electronAPI.verifyLicense when Verify Now is clicked for an active license', async () => {
    const mockAPI = makeElectronAPI({
      getLicenseStatus: vi.fn().mockResolvedValue({ active: true, plan: 'premium-desktop-monthly' }),
    });
    window.electronAPI = mockAPI;

    renderSection({ electronAPI: mockAPI });
    const button = await screen.findByRole('button', { name: 'Verify Now' });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockAPI.verifyLicense).toHaveBeenCalled();
      expect(screen.getByText(/License verification succeeded/i)).toBeInTheDocument();
    });
  });

  it('shows error message if verification fails', async () => {
    const mockAPI = makeElectronAPI({
      getLicenseStatus: vi.fn().mockResolvedValue({ active: true, plan: 'premium-desktop-monthly' }),
      verifyLicense: vi.fn().mockResolvedValue({ ok: false, error: 'server-down' }),
    });
    window.electronAPI = mockAPI;

    renderSection({ electronAPI: mockAPI });
    const button = await screen.findByRole('button', { name: 'Verify Now' });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/server-down|verification failed/i)).toBeInTheDocument();
    });
  });

  it('keeps manual license key activation behind a secondary action', async () => {
    const mockAPI = makeElectronAPI();
    window.electronAPI = mockAPI;

    renderSection({ electronAPI: mockAPI });

    await screen.findByRole('heading', { name: /License and Activation/i });
    expect(screen.queryByLabelText(/^License Key$/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Use a license key instead/i }));
    fireEvent.change(screen.getByLabelText(/^License Key$/i), { target: { value: 'OLD-KEY-123' } });
    fireEvent.click(screen.getByRole('button', { name: /Activate license key/i }));

    await waitFor(() => {
      expect(mockAPI.activateLicense).toHaveBeenCalledWith({
        key: 'OLD-KEY-123',
        email: '',
      });
      expect(screen.getByText(/^Activated$/i)).toBeInTheDocument();
    });
  });

  it('does not reload license status when only the parent callback identity changes', async () => {
    const mockAPI = makeElectronAPI({
      getLicenseStatus: vi.fn().mockResolvedValue({ active: false, plan: 'standard' }),
    });
    const firstCallback = vi.fn();
    const secondCallback = vi.fn();

    const { rerender } = render(
      <LicenseActivationSection
        darkMode={false}
        electronAPI={mockAPI}
        onInvalidateToken={vi.fn()}
        onLicenseChanged={firstCallback}
      />
    );

    await waitFor(() => {
      expect(mockAPI.getLicenseStatus).toHaveBeenCalledTimes(1);
    });

    rerender(
      <LicenseActivationSection
        darkMode={false}
        electronAPI={mockAPI}
        onInvalidateToken={vi.fn()}
        onLicenseChanged={secondCallback}
      />
    );

    await new Promise((resolve) => {
      setTimeout(resolve, 25);
    });

    expect(mockAPI.getLicenseStatus).toHaveBeenCalledTimes(1);
  });

  it('activates an existing PayPal purchase id from settings', async () => {
    const mockAPI = makeElectronAPI({
      activatePayPalPurchase: vi.fn().mockResolvedValue({
        ok: true,
        status: { active: true, plan: 'premium-desktop-lifetime' },
      }),
    });
    window.electronAPI = mockAPI;

    renderSection({ electronAPI: mockAPI });

    const paypalInput = await screen.findByPlaceholderText(/I-.*transaction ID/i);
    fireEvent.change(paypalInput, { target: { value: 'CAPTURE-250' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify and unlock/i }));

    await waitFor(() => {
      expect(mockAPI.activatePayPalPurchase).toHaveBeenCalledWith({
        paypalId: 'CAPTURE-250',
        email: '',
      });
      expect(screen.getByText(/Purchase verified/i)).toBeInTheDocument();
    });
  });

  it('does not treat PayPal verification as active without an active license status', async () => {
    const mockAPI = makeElectronAPI({
      activatePayPalPurchase: vi.fn().mockResolvedValue({ ok: true }),
    });
    const onLicenseChanged = vi.fn();
    window.electronAPI = mockAPI;

    renderSection({ electronAPI: mockAPI, onLicenseChanged });

    const paypalInput = await screen.findByPlaceholderText(/I-.*transaction ID/i);
    fireEvent.change(paypalInput, { target: { value: 'CAPTURE-250' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify and unlock/i }));

    await waitFor(() => {
      expect(onLicenseChanged).not.toHaveBeenCalledWith(expect.objectContaining({ active: true }));
      expect(screen.getByText(/Verification did not return an active license/i)).toBeInTheDocument();
    });
  });

  it('renders pending PayPal verification as locked even if a legacy status says active', async () => {
    const mockAPI = makeElectronAPI({
      getLicenseStatus: vi.fn().mockResolvedValue({
        active: true,
        plan: 'premium-desktop-monthly',
        pendingPayPalVerification: true,
        pendingExpiresAt: 1_800_086_400,
      }),
    });
    window.electronAPI = mockAPI;

    renderSection({ electronAPI: mockAPI });

    expect(await screen.findByText(/PayPal verification pending/i)).toBeInTheDocument();
    expect(screen.getByText(/protected features stay locked/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Clear pending activation/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Finish PayPal activation/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Verify Now' })).not.toBeInTheDocument();
  });

  it('shows dev bypass messaging instead of verification controls in non-packaged runtime', async () => {
    window.IS_PACKAGED = false;
    window.electronAPI = makeElectronAPI({
      getLicenseStatus: vi.fn().mockResolvedValue({ active: false, plan: 'standard' }),
    });

    renderSection({ devLicenseRuntime: true });

    await screen.findByRole('heading', { name: /License and Activation/i });
    expect(screen.getByText(/Source-run development bypass is active/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Verify Now' })).not.toBeInTheDocument();
  });
});
