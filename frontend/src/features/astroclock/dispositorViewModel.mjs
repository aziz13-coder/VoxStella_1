const FINAL_TERMINALS = new Set(['domicile', 'final_dispositor']);

export function normalizeDispositorState(info = {}, anchor = '') {
  const chain = Array.isArray(info?.chain) && info.chain.length
    ? info.chain.map((item) => String(item)).filter(Boolean)
    : (anchor ? [String(anchor)] : []);
  const rawFinal = info?.final_dispositor ? String(info.final_dispositor) : null;
  const rawType = info?.terminal_type ? String(info.terminal_type) : '';
  const inferredType = rawType
    || (info?.mutual_reception ? 'mutual_reception'
      : (Array.isArray(info?.cycle) && info.cycle.length > 1 ? 'cycle'
        : (rawFinal ? (chain.length === 1 && rawFinal === chain[0] ? 'domicile' : 'final_dispositor') : 'unknown')));
  const terminalType = inferredType;
  const hasFinalDispositor = info?.has_final_dispositor === true
    || (FINAL_TERMINALS.has(terminalType) && Boolean(rawFinal));
  return {
    anchor: anchor ? String(anchor) : (chain[0] || ''),
    chain,
    terminalType,
    finalDispositor: hasFinalDispositor ? rawFinal : null,
    hasFinalDispositor,
    mutualReception: terminalType === 'mutual_reception' || info?.mutual_reception === true,
    receptionPartner: info?.reception_partner ? String(info.reception_partner) : null,
    cycle: Array.isArray(info?.cycle) ? info.cycle.map((item) => String(item)).filter(Boolean) : [],
  };
}

export function formatDispositorSummary(state, {
  planetGlyph = (name) => name || '-',
  domAnchor = false,
  domFinal = false,
} = {}) {
  if (state?.mutualReception) {
    const pair = state.cycle?.length === 2 ? state.cycle : [];
    if (state.receptionPartner) {
      return `Mutual reception with ${planetGlyph(state.receptionPartner)}.`;
    }
    if (pair.length === 2) {
      return `Terminates in mutual reception: ${pair.map(planetGlyph).join(' <-> ')}.`;
    }
    return 'Terminates in mutual reception.';
  }
  if (state?.terminalType === 'cycle') {
    const cycle = state.cycle?.length ? state.cycle : state.chain;
    return `Rulership cycle: ${cycle.map(planetGlyph).join(' -> ')}.`;
  }
  if (state?.hasFinalDispositor && state.finalDispositor) {
    if (domAnchor) return `${planetGlyph(state.anchor)} already rules its own sign.`;
    return `Final dispositor: ${planetGlyph(state.finalDispositor)}${domFinal ? ' in domicile' : ''}.`;
  }
  return 'No single final dispositor.';
}

export function shouldRenderDispositorSummary(state) {
  return state?.terminalType !== 'cycle';
}

export function formatDispositorTooltip(state, planetSign = () => null) {
  const path = (state?.chain || []).map((name) => {
    const sign = planetSign(name);
    return `${name}${sign ? ` (${sign})` : ''}`;
  }).join(' -> ');
  if (state?.mutualReception) {
    const pair = state.cycle?.length === 2 ? state.cycle.join(' <-> ') : '';
    if (state.receptionPartner) {
      return `${path} - mutual reception with ${state.receptionPartner}`;
    }
    return `${path} - terminates in mutual reception${pair ? `: ${pair}` : ''}`;
  }
  if (state?.terminalType === 'cycle') {
    return `${path} - rulership cycle, no single final dispositor`;
  }
  if (state?.hasFinalDispositor && state.finalDispositor) {
    return `${path} - final dispositor ${state.finalDispositor}`;
  }
  return `${path || 'No chain'} - no single final dispositor`;
}
