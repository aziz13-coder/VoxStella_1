import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import WhatsNewModal from '../components/WhatsNewModal.jsx';

describe('WhatsNewModal', () => {
  const release = {
    version: '2.2.6',
    requestedVersion: '2.2.6',
    sourceVersion: '2.2.6',
    isFallback: false,
    publishedAt: '2026-04-19',
    headline: 'Synastry workspaces and new comparison views',
    summary: 'This build expands Astro Clock synastry with new ways to compare saved charts and a cleaner reading workspace.',
    note: 'Synastry is now broader and easier to navigate, and the comparison workspace will continue to be refined in upcoming builds.',
    items: [
      {
        title: 'Synastry',
        body: 'Saved-snap comparison now includes multiple views, so you can move between the memo, broad life themes, union-focused reading, and work-focused reading in one place.',
      },
      {
        title: 'Structured views',
        body: 'The new comparison views open into clearer worksheets with area summaries, grouped themes, and contact grids that are easier to scan.',
      },
    ],
  };

  it('renders the workspace-style release layout and closes from the header control', () => {
    const onClose = vi.fn();

    render(
      <WhatsNewModal
        darkMode={false}
        onClose={onClose}
        release={release}
      />
    );

    expect(screen.getByText('New in this build')).toBeInTheDocument();
    expect(screen.getByText('Build overview')).toBeInTheDocument();
    expect(screen.getByText('Highlights')).toBeInTheDocument();
    expect(screen.getByText('Synastry')).toBeInTheDocument();
    expect(screen.getByText('Structured views')).toBeInTheDocument();
    expect(screen.getByText('Note')).toBeInTheDocument();
    expect(screen.queryByText('Included in this build')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Continue' })).not.toBeInTheDocument();
    expect(screen.getByRole('dialog', { name: "What's New" })).toHaveClass(
      'max-h-[calc(100dvh-1.5rem)]',
      'flex-col',
      'overflow-hidden',
    );
    expect(screen.getByTestId('whats-new-scroll-body')).toHaveClass(
      'flex-1',
      'overflow-y-auto',
    );

    fireEvent.click(screen.getByRole('button', { name: "Close What's New" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('lets free PayPal buyers activate an existing plan before seeing gated offers', async () => {
    const onLicenseChanged = vi.fn();
    const electronAPI = {
      activatePayPalPurchase: vi.fn().mockResolvedValue({
        ok: true,
        status: { active: true, plan: 'premium-desktop-monthly' },
      }),
    };

    render(
      <WhatsNewModal
        darkMode={false}
        onClose={() => {}}
        release={release}
        license={{ active: false, checking: false }}
        electronAPI={electronAPI}
        onLicenseChanged={onLicenseChanged}
      />
    );

    expect(screen.getByText(/Activate your plan/i)).toBeInTheDocument();
    expect(screen.queryByText(/website/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/I-.*transaction ID/i), {
      target: { value: 'I-WEBSITE-123' },
    });
    fireEvent.change(screen.getByPlaceholderText(/PayPal email/i), {
      target: { value: 'buyer@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Verify and unlock/i }));

    await waitFor(() => {
      expect(electronAPI.activatePayPalPurchase).toHaveBeenCalledWith({
        paypalId: 'I-WEBSITE-123',
        email: 'buyer@example.com',
      });
      expect(onLicenseChanged).toHaveBeenCalledWith({ active: true, plan: 'premium-desktop-monthly' });
      expect(screen.getByText(/Purchase verified/i)).toBeInTheDocument();
    });
  });

  it('does not unlock when PayPal verification lacks an active license status', async () => {
    const onLicenseChanged = vi.fn();
    const electronAPI = {
      activatePayPalPurchase: vi.fn().mockResolvedValue({ ok: true }),
    };

    render(
      <WhatsNewModal
        darkMode={false}
        onClose={() => {}}
        release={release}
        license={{ active: false, checking: false }}
        electronAPI={electronAPI}
        onLicenseChanged={onLicenseChanged}
      />
    );

    fireEvent.change(screen.getByPlaceholderText(/I-.*transaction ID/i), {
      target: { value: 'I-WEBSITE-123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Verify and unlock/i }));

    await waitFor(() => {
      expect(onLicenseChanged).not.toHaveBeenCalled();
      expect(screen.getByText(/Verification did not return an active license/i)).toBeInTheDocument();
    });
  });

  it('does not show the website purchase verifier for licensed users', () => {
    render(
      <WhatsNewModal
        darkMode={false}
        onClose={() => {}}
        release={release}
        license={{ active: true, checking: false }}
      />
    );

    expect(screen.queryByText(/Activate your plan/i)).not.toBeInTheDocument();
  });

  it('shows fallback version context when the app is newer than the release registry', () => {
    render(
      <WhatsNewModal
        darkMode
        onClose={() => {}}
        release={{
          version: '2.2.6',
          requestedVersion: '2.2.7',
          sourceVersion: '2.2.6',
          isFallback: true,
          publishedAt: '2026-04-19',
          headline: 'Synastry workspaces and new comparison views',
          summary: 'Fallback copy for a newer build.',
          items: [{ title: 'Synastry', body: 'Fallback release note.' }],
        }}
      />
    );

    expect(screen.getByText('Version 2.2.7 - notes from 2.2.6')).toBeInTheDocument();
  });
});
