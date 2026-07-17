import { describe, expect, it } from 'vitest';
import {
  formatDispositorSummary,
  formatDispositorTooltip,
  normalizeDispositorState,
  shouldRenderDispositorSummary,
} from '../features/astroclock/dispositorViewModel.mjs';

describe('dispositor view model', () => {
  it('renders mutual reception as reception, not a final dispositor', () => {
    const state = normalizeDispositorState({
      chain: ['Mars', 'Venus'],
      final_dispositor: null,
      mutual_reception: true,
      reception_partner: 'Venus',
      terminal_type: 'mutual_reception',
      has_final_dispositor: false,
      cycle: ['Mars', 'Venus'],
    }, 'Mars');

    expect(state.finalDispositor).toBeNull();
    expect(formatDispositorSummary(state)).toBe('Mutual reception with Venus.');
    expect(formatDispositorTooltip(state)).toContain('mutual reception with Venus');
  });

  it('renders long cycles as no single final dispositor', () => {
    const state = normalizeDispositorState({
      chain: ['Sun', 'Mars', 'Mercury'],
      final_dispositor: null,
      terminal_type: 'cycle',
      has_final_dispositor: false,
      cycle: ['Sun', 'Mars', 'Mercury'],
    }, 'Sun');

    expect(state.finalDispositor).toBeNull();
    expect(formatDispositorSummary(state)).toBe('Rulership cycle: Sun -> Mars -> Mercury.');
    expect(formatDispositorTooltip(state)).toContain('no single final dispositor');
    expect(shouldRenderDispositorSummary(state)).toBe(false);
  });

  it('renders a chain that terminates in a later mutual reception pair', () => {
    const state = normalizeDispositorState({
      chain: ['Moon', 'Venus', 'Mars'],
      final_dispositor: null,
      terminal_type: 'mutual_reception',
      mutual_reception: true,
      has_final_dispositor: false,
      cycle: ['Venus', 'Mars'],
    }, 'Moon');

    expect(state.receptionPartner).toBeNull();
    expect(formatDispositorSummary(state)).toBe('Terminates in mutual reception: Venus <-> Mars.');
    expect(formatDispositorTooltip(state)).toContain('Venus <-> Mars');
  });

  it('renders domicile-terminated chains as final dispositors', () => {
    const state = normalizeDispositorState({
      chain: ['Moon', 'Jupiter'],
      final_dispositor: 'Jupiter',
      terminal_type: 'domicile',
      has_final_dispositor: true,
    }, 'Moon');

    expect(state.finalDispositor).toBe('Jupiter');
    expect(formatDispositorSummary(state, { domFinal: true })).toBe('Final dispositor: Jupiter in domicile.');
    expect(shouldRenderDispositorSummary(state)).toBe(true);
  });
});
