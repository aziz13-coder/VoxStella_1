import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';


describe('AstroClock source boundaries', () => {
  it('keeps AstroClock routed through the feature module instead of a stale inline App component', () => {
    const appSource = readFileSync(resolve(process.cwd(), 'src/App.jsx'), 'utf8');

    expect(appSource).toContain("import AstroClockPage from './features/astroclock/AstroClock.jsx';");
    expect(appSource).not.toMatch(/\bconst\s+AstroClock\s*=\s*\(/);
  });

  it('keeps the unfinished Research workspace behind the dev-only frontend gate', () => {
    const appSource = readFileSync(resolve(process.cwd(), 'src/App.jsx'), 'utf8');

    expect(appSource).toContain('export const SHOW_RESEARCH_WORKSPACE = import.meta.env.DEV;');
    expect(appSource).not.toContain("import ResearchWorkspace from './features/research/ResearchWorkspace.jsx';");
    expect(appSource).not.toContain('DEV_RESEARCH_WORKSPACE_MODULE');
    expect(appSource).toContain("import('./features/research/ResearchWorkspace.jsx')");
    expect(appSource).toContain("...(SHOW_RESEARCH_WORKSPACE ? [{ id: 'research', label: 'Research' }] : []),");
    expect(appSource).toContain('{SHOW_RESEARCH_WORKSPACE ? (');
  });
});
