import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';


describe('desktop window responsive contracts', () => {
  it('keeps desktop navigation available in compact desktop windows', () => {
    const appSource = readFileSync(resolve(process.cwd(), 'src/App.jsx'), 'utf8');

    expect(appSource).toContain('className="hidden min-[900px]:block"');
    expect(appSource).toContain('border-t min-[900px]:hidden');
    expect(appSource).toContain('min-[1100px]:px-4 min-[1100px]:py-2');
    expect(appSource).toContain('min-[1100px]:px-4 min-[1100px]:text-sm');
  });

  it('keeps the five-card dashboard rhythm at desktop window widths', () => {
    const appSource = readFileSync(resolve(process.cwd(), 'src/App.jsx'), 'utf8');

    expect(appSource).toContain('sm:grid-cols-3');
    expect(appSource).toContain('min-[900px]:grid-cols-5');
    expect(appSource).toContain('p-4 min-[1100px]:p-6');
    expect(appSource).toContain('min-[1100px]:h-12 min-[1100px]:w-12');
    expect(appSource).toContain('min-[1100px]:text-lg');
  });

  it('prevents the Electron window from shrinking below the supported layout', () => {
    const mainSource = readFileSync(resolve(process.cwd(), 'main.js'), 'utf8');

    expect(mainSource).toMatch(/minWidth:\s*720/);
    expect(mainSource).toMatch(/minHeight:\s*600/);
  });
});
