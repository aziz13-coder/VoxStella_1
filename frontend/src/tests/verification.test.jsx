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

  it('renders Verify Now button in packaged settings mode', async () => {
    renderSection();

    await screen.findByRole('heading', { name: /License and Activation/i });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Verify Now' })).toBeInTheDocument();
    });
  });

  it('invokes electronAPI.verifyLicense when Verify Now is clicked', async () => {
    const mockAPI = makeElectronAPI();
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
