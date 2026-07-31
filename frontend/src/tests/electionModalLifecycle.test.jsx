import React from 'react';
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const apiMocks = vi.hoisted(() => ({
  electionStream: vi.fn(),
  listSnaps: vi.fn().mockResolvedValue({ items: [] }),
  validateElection: vi.fn().mockResolvedValue({ ok: true }),
}));

vi.mock('../features/astroclock/api.mjs', () => ({
  AstroClockAPI: apiMocks,
}));

import ElectionModal from '../features/astroclock/ElectionModal.jsx';


describe('ElectionModal lifecycle', () => {
  it('keeps a stable hook order while opening and closing', async () => {
    const props = {
      onClose: vi.fn(),
      onJumpToTime: vi.fn(),
    };
    const { rerender } = render(<ElectionModal {...props} open={false} />);

    expect(screen.queryByRole('heading', { name: 'Election' })).not.toBeInTheDocument();

    rerender(<ElectionModal {...props} open />);
    expect(await screen.findByRole('heading', { name: 'Election' })).toBeInTheDocument();

    rerender(<ElectionModal {...props} open={false} />);
    expect(screen.queryByRole('heading', { name: 'Election' })).not.toBeInTheDocument();
  });

  it('cancels an active scan and ignores its late result after changing models', async () => {
    const stream = {
      close: vi.fn(),
      readyState: 1,
      onerror: null,
      onmessage: null,
    };
    apiMocks.electionStream.mockResolvedValueOnce(stream);
    const { container } = render(
      <ElectionModal open onClose={vi.fn()} onJumpToTime={vi.fn()} />,
    );

    const dateInputs = container.querySelectorAll('input[type="date"]');
    const timeInputs = container.querySelectorAll('input[type="time"]');
    fireEvent.change(dateInputs[0], { target: { value: '2026-08-01' } });
    fireEvent.change(timeInputs[0], { target: { value: '09:00' } });
    fireEvent.change(dateInputs[1], { target: { value: '2026-08-01' } });
    fireEvent.change(timeInputs[1], { target: { value: '12:00' } });
    fireEvent.change(screen.getByPlaceholderText('e.g., London, UK'), {
      target: { value: 'London, UK' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Scan' }));

    await waitFor(() => expect(apiMocks.electionStream).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/Scanning/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Surgery' }));
    await waitFor(() => expect(stream.close).toHaveBeenCalledTimes(1));
    expect(screen.queryByText(/Scanning/)).not.toBeInTheDocument();

    stream.onmessage({
      data: JSON.stringify({
        type: 'done',
        data: {
          matter: 'marriage',
          model_metadata: {
            id: 'marriage:alpha',
            version: 'test',
            source_profile: 'test',
          },
        },
      }),
    });

    expect(screen.queryByText(/Model marriage:alpha/)).not.toBeInTheDocument();
  });
});
