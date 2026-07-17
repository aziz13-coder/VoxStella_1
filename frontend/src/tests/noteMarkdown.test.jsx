import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { appendNoteAttachment, renderNoteMarkdown } from '../utils/noteMarkdown.jsx';

describe('note markdown utilities', () => {
  it('renders headings, inline formatting, and lists', () => {
    render(
      <div>
        {renderNoteMarkdown(`# Working Notes

- **Key point**
- Follow-up with \`code\`

Paragraph with *emphasis*.`)}
      </div>,
    );

    expect(screen.getByRole('heading', { name: 'Working Notes' })).toBeInTheDocument();
    expect(screen.getByText('Key point').tagName).toBe('STRONG');
    expect(screen.getByText('code').tagName).toBe('CODE');
    expect(screen.getByText('emphasis').tagName).toBe('EM');
    expect(screen.getByRole('list')).toBeInTheDocument();
  });

  it('routes safe markdown links through the provided external opener', () => {
    const openExternal = vi.fn();

    render(
      <div>
        {renderNoteMarkdown('[Workspace docs](https://voxstella.app/docs/workspace/)', {
          openExternal,
        })}
      </div>,
    );

    fireEvent.click(screen.getByRole('link', { name: 'Workspace docs' }));
    expect(openExternal).toHaveBeenCalledWith('https://voxstella.app/docs/workspace/');
  });

  it('aligns note links with the Electron HTTPS/mailto external-navigation policy', () => {
    const openExternal = vi.fn();

    const { rerender } = render(
      <div>
        {renderNoteMarkdown('[Reference](https://example.com/research)', { openExternal })}
      </div>,
    );
    fireEvent.click(screen.getByRole('link', { name: 'Reference' }));
    expect(openExternal).toHaveBeenCalledWith('https://example.com/research');

    rerender(
      <div>
        {renderNoteMarkdown('[Unsafe](http://example.com)', { openExternal })}
      </div>,
    );
    expect(screen.queryByRole('link', { name: 'Unsafe' })).not.toBeInTheDocument();
    expect(screen.getByText('[Unsafe](http://example.com)')).toBeInTheDocument();
  });

  it('appends note attachment templates with stable spacing', () => {
    expect(appendNoteAttachment('', 'voice')).toContain('Voice note');
    expect(appendNoteAttachment('Existing note', 'link')).toBe(
      'Existing note\n\n- External reference: [Add link title](https://example.com/reference)',
    );
  });
});
