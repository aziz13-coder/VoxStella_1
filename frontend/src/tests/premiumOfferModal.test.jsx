import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import PremiumOfferModal from '../features/astroclock/PremiumOfferModal.jsx';

describe('PremiumOfferModal', () => {
  let originalElectronAPI;

  beforeEach(() => {
    originalElectronAPI = window.electronAPI;
    window.electronAPI = {
      openPayPalCheckout: vi.fn().mockResolvedValue({ ok: true }),
      activatePayPalSubscription: vi.fn(),
    };
  });

  afterEach(() => {
    window.electronAPI = originalElectronAPI;
  });

  it('opens discounted PayPal checkout in the system browser without loading remote renderer scripts', async () => {
    render(
      <PremiumOfferModal
        open
        featureName="Astrocartography"
        onClose={() => {}}
      />
    );

    expect(document.querySelector('script[src^="https://www.paypal.com/"]')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /Continue securely with PayPal/i }));

    await waitFor(() => {
      expect(window.electronAPI.openPayPalCheckout).toHaveBeenCalledWith();
      expect(screen.getByRole('status')).toHaveTextContent('Secure checkout opened in your browser');
    });
  });

  it('does not render the free-mode fallback action in the desktop offer', () => {
    render(
      <PremiumOfferModal
        open
        featureName="Astro Clock"
        onClose={() => {}}
      />
    );

    expect(screen.queryByRole('button', { name: /Keep using free mode/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/Keep using free mode/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Unlock the full suite/i)).toBeInTheDocument();
    expect(screen.getByText(/Save nearly 30%/i)).toBeInTheDocument();
    expect(screen.queryByText(/Save \$10 monthly/i)).not.toBeInTheDocument();
  });

  it('verifies the pasted subscription ID and activates the local license', async () => {
    const onActivated = vi.fn();
    window.electronAPI.activatePayPalSubscription.mockResolvedValue({
      ok: true,
      status: { active: true, plan: 'premium-desktop-monthly' },
    });

    render(
      <PremiumOfferModal
        open
        featureName="Transits"
        onClose={() => {}}
        onActivated={onActivated}
      />
    );

    fireEvent.change(screen.getByLabelText(/PayPal subscription ID/i), {
      target: { value: ' I-SUBSCRIPTION-123 ' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Verify subscription and unlock/i }));

    await waitFor(() => {
      expect(window.electronAPI.activatePayPalSubscription).toHaveBeenCalledWith({
        subscriptionId: 'I-SUBSCRIPTION-123',
      });
      expect(onActivated).toHaveBeenCalledWith({ active: true, plan: 'premium-desktop-monthly' });
      expect(screen.getByRole('status')).toHaveTextContent('Premium access is active on this device.');
    });
  });

  it('keeps protected features locked while PayPal verification is pending', async () => {
    window.electronAPI.activatePayPalSubscription.mockResolvedValue({
      ok: true,
      provisional: true,
      status: {
        active: false,
        plan: 'premium-desktop-monthly',
        provisional: true,
        pendingPayPalVerification: true,
      },
    });

    render(
      <PremiumOfferModal
        open
        featureName="Forensic"
        onClose={() => {}}
        onActivated={() => {}}
      />
    );

    fireEvent.change(screen.getByLabelText(/PayPal subscription ID/i), {
      target: { value: 'I-PENDING-123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Verify subscription and unlock/i }));

    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent('PayPal activation is pending');
      expect(screen.getByRole('status')).toHaveTextContent('Protected features remain locked');
    });
  });

  it('reports an external-browser handoff failure without navigating the renderer', async () => {
    window.electronAPI.openPayPalCheckout.mockResolvedValue({
      ok: false,
      error: 'checkout_url_unavailable',
    });

    render(
      <PremiumOfferModal
        open
        featureName="Election"
        onClose={() => {}}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Continue securely with PayPal/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('checkout_url_unavailable');
    });
    expect(window.location.href).toBe('http://localhost:3000/');
  });
});
