import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import McpIntegrationSection from '../components/McpIntegrationSection.jsx';


afterEach(() => {
  vi.restoreAllMocks();
});


function readySetup() {
  return {
    supported: true,
    ready: true,
    state: 'ready',
    detail: 'Licensed MCP is ready for local clients.',
    launcherPath: 'C:\\Program Files\\Vox Stella\\VoxStella-MCP.cmd',
    launcherExists: true,
    tools: [
      'get_astrological_capabilities',
      'calculate_astrological_chart',
      'get_current_astrological_positions',
      'calculate_planetary_hours',
    ],
    scope: { excluded: ['transit relationship and window scans'] },
  };
}


describe('McpIntegrationSection', () => {
  it('shows installed readiness, tools, launcher, and the privacy boundary', async () => {
    const electronAPI = {
      getMcpSetup: vi.fn().mockResolvedValue(readySetup()),
      copyMcpConfig: vi.fn(),
      openMcpLauncherFolder: vi.fn(),
    };
    render(<McpIntegrationSection darkMode={false} electronAPI={electronAPI} />);

    expect(await screen.findByText('Ready')).toBeInTheDocument();
    expect(screen.getByText('Chart calculation')).toBeInTheDocument();
    expect(screen.getByText(/VoxStella-MCP\.cmd/)).toBeInTheDocument();
    expect(screen.getByText(/does not expose saved charts/i)).toBeInTheDocument();
  });

  it('copies tested direct configurations and opens the launcher folder', async () => {
    const electronAPI = {
      getMcpSetup: vi.fn().mockResolvedValue(readySetup()),
      copyMcpConfig: vi.fn().mockResolvedValue({ ok: true }),
      openMcpLauncherFolder: vi.fn().mockResolvedValue({ ok: true }),
    };
    render(<McpIntegrationSection darkMode={false} electronAPI={electronAPI} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Copy JSON config' }));
    await waitFor(() => expect(electronAPI.copyMcpConfig).toHaveBeenCalledWith('json'));
    expect(await screen.findByText('JSON configuration copied.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Show launcher' }));
    await waitFor(() => expect(electronAPI.openMcpLauncherFolder).toHaveBeenCalledTimes(1));
  });

  it('explains that setup requires an installed build outside Electron', async () => {
    render(<McpIntegrationSection darkMode={false} electronAPI={undefined} />);

    expect(await screen.findByText('Setup required')).toBeInTheDocument();
    expect(screen.getByText(/installed Windows application/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Copy JSON config' })).toBeDisabled();
  });
});
