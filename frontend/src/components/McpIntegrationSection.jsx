import React, { useEffect, useState } from 'react';
import { CheckCircle, Copy, FolderOpen, Terminal, XCircle } from 'lucide-react';


const TOOL_LABELS = {
  get_astrological_capabilities: 'Astrological capabilities',
  calculate_astrological_chart: 'Chart calculation',
  get_current_astrological_positions: 'Current positions',
  calculate_planetary_hours: 'Planetary hours',
  analyze_synastry: 'Synastry',
  calculate_trait_profile: 'Trait Profile',
  analyze_transits: 'Exact transits',
  scan_transit_window: 'Transit window',
  analyze_astrocartography_location: 'Astrocartography location',
  generate_astrocartography_map: 'Astrocartography map',
  compare_astrocartography_locations: 'Astrocartography comparison',
  search_astrocartography_atlas: 'Astrocartography atlas',
  find_election_times: 'Election',
  calculate_bazi: 'Chinese Astrology · BaZi',
  analyze_chinese_compatibility: 'Chinese compatibility',
  cast_iching_oracle: 'I Ching oracle',
  analyze_forensic_event: 'Forensic',
  run_birth_time_certification: 'Certification',
};


export default function McpIntegrationSection({ darkMode, electronAPI }) {
  const [setup, setSetup] = useState(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    let active = true;
    if (typeof electronAPI?.getMcpSetup !== 'function') {
      setSetup({
        supported: false,
        ready: false,
        state: 'installed_build_required',
        detail: 'MCP setup is available in the installed Windows application.',
        tools: Object.keys(TOOL_LABELS),
        scope: { excluded: ['Saved-data browsing, mutations, and license identity'] },
      });
      return () => { active = false; };
    }
    electronAPI.getMcpSetup()
      .then((result) => {
        if (active) setSetup(result);
      })
      .catch((error) => {
        if (active) {
          setSetup({
            supported: true,
            ready: false,
            state: 'setup_error',
            detail: `MCP setup could not be loaded: ${error?.message || error}`,
            tools: Object.keys(TOOL_LABELS),
            scope: { excluded: [] },
          });
        }
      });
    return () => { active = false; };
  }, [electronAPI]);

  const copyConfiguration = async (format) => {
    setMessage(`Copying ${format === 'codex' ? 'Codex' : 'JSON'} configuration...`);
    try {
      const result = await electronAPI?.copyMcpConfig?.(format);
      setMessage(result?.ok
        ? `${format === 'codex' ? 'Codex' : 'JSON'} configuration copied.`
        : `Configuration could not be copied${result?.error ? `: ${result.error}` : '.'}`);
    } catch (error) {
      setMessage(`Configuration could not be copied: ${error?.message || error}`);
    }
  };

  const openLauncherFolder = async () => {
    setMessage('Opening the MCP launcher folder...');
    try {
      const result = await electronAPI?.openMcpLauncherFolder?.();
      setMessage(result?.ok
        ? 'MCP launcher selected in File Explorer.'
        : `Launcher folder could not be opened${result?.error ? `: ${result.error}` : '.'}`);
    } catch (error) {
      setMessage(`Launcher folder could not be opened: ${error?.message || error}`);
    }
  };

  const cardBg = darkMode
    ? 'bg-gray-800/60 backdrop-blur-xl border-gray-700'
    : 'bg-white/60 backdrop-blur-xl border-white/80';
  const statusClass = setup?.ready
    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200'
    : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200';

  return (
    <section className={`${cardBg} border rounded-2xl p-6`} aria-labelledby="mcp-integration-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 id="mcp-integration-title" className="text-lg font-semibold flex items-center">
            <Terminal className="w-5 h-5 mr-2 text-indigo-500" />
            Model Context Protocol (MCP)
          </h3>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Connect local AI clients to the licensed, read-only Vox Stella calculation engine.
          </p>
        </div>
        {setup ? (
          <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${statusClass}`}>
            {setup.ready
              ? <CheckCircle className="mr-1.5 h-4 w-4" />
              : <XCircle className="mr-1.5 h-4 w-4" />}
            {setup.ready ? 'Ready' : 'Setup required'}
          </span>
        ) : (
          <span className="text-xs text-gray-500">Checking MCP setup...</span>
        )}
      </div>

      {setup ? (
        <div className="mt-5 space-y-5">
          <div className={`rounded-xl border p-4 text-sm ${statusClass}`}>
            <div className="font-semibold">{setup.detail}</div>
            {setup.launcherPath ? (
              <code className="mt-2 block break-all text-xs">{setup.launcherPath}</code>
            ) : null}
          </div>

          <div>
            <h4 className="text-sm font-semibold">Available read-only tools</h4>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {(setup.tools || []).map((tool) => (
                <div key={tool} className="rounded-lg bg-gray-50 px-3 py-2 text-xs dark:bg-gray-900/50">
                  <div className="font-medium">{TOOL_LABELS[tool] || tool}</div>
                  <code className="text-gray-500 dark:text-gray-400">{tool}</code>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 p-4 text-xs text-gray-600 dark:border-gray-700 dark:text-gray-300">
            <div className="font-semibold text-gray-800 dark:text-gray-100">Deliberate privacy boundary</div>
            <p className="mt-1">
              MCP exposes licensed, read-only calculations for Synastry, Trait Profile, Transits, Astrocartography,
              Election, Chinese Astrology, Forensic, and Certification. It does not list private saved charts or notes,
              mutate app data, expose license identity, or return durable credentials. Specialized tools use explicit
              chart inputs; optional saved-chart IDs are accepted only by workflows that require a user-selected chart.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!setup.supported || !setup.launcherExists}
              onClick={() => copyConfiguration('json')}
              className="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Copy className="mr-2 h-4 w-4" />
              Copy JSON config
            </button>
            <button
              type="button"
              disabled={!setup.supported || !setup.launcherExists}
              onClick={() => copyConfiguration('codex')}
              className="inline-flex items-center rounded-lg bg-gray-700 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-600 dark:hover:bg-gray-500"
            >
              <Copy className="mr-2 h-4 w-4" />
              Copy Codex config
            </button>
            <button
              type="button"
              disabled={!setup.supported || !setup.launcherExists}
              onClick={openLauncherFolder}
              className="inline-flex items-center rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:hover:bg-gray-700"
            >
              <FolderOpen className="mr-2 h-4 w-4" />
              Show launcher
            </button>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Keep Vox Stella activated on this device. MCP clients receive no license key or durable credential.
          </p>
          <div aria-live="polite" className="min-h-4 text-xs text-gray-600 dark:text-gray-300">{message}</div>
        </div>
      ) : null}
    </section>
  );
}
