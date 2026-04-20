import React, { useEffect, useMemo, useState } from 'react';
import { BookOpen, Compass, Info, MapPin, Search } from 'lucide-react';

import { formatHouseLabel, isMissingPetLocationChart } from './lostObjectLocation.mjs';

const SectionCard = ({ title, icon: Icon, darkMode, children }) => (
  <div
    className={`p-4 rounded-xl border ${
      darkMode ? 'bg-gray-800/30 border-gray-600' : 'bg-gray-50/60 border-gray-200'
    }`}
  >
    <div className="flex items-center gap-2 mb-3">
      <Icon className="w-4 h-4 text-indigo-500" />
      <h4 className="font-semibold text-indigo-700 dark:text-indigo-300">{title}</h4>
    </div>
    {children}
  </div>
);

const HintList = ({ items, accentClass }) => (
  <div className="space-y-3">
    {items.map((item) => (
      <div key={`${item.label}-${item.reason}`} className={`rounded-xl border p-3 ${accentClass}`}>
        <div className="font-medium">{item.label}</div>
        {item.reason && (
          <div className="text-xs text-gray-600 dark:text-gray-400 mt-1 leading-relaxed">
            {item.reason}
          </div>
        )}
      </div>
    ))}
  </div>
);

const SectionTabs = ({ activeId, onChange, darkMode, sections }) => (
  <div
    data-testid="lost-object-location-section-tabs"
    className={`inline-flex flex-wrap gap-2 rounded-xl border p-2 ${
      darkMode ? 'bg-gray-900/20 border-gray-700' : 'bg-white/70 border-gray-200'
    }`}
  >
    {sections.map((section) => {
      const Icon = section.icon;
      const active = section.id === activeId;
      return (
        <button
          key={section.id}
          type="button"
          onClick={() => onChange(section.id)}
          className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
            active
              ? 'bg-indigo-600 text-white shadow-sm'
              : darkMode
                ? 'text-gray-300 hover:text-white hover:bg-gray-700'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
        >
          <Icon className="w-4 h-4" />
          {section.title}
        </button>
      );
    })}
  </div>
);

function buildEvidenceContent(evidence) {
  return (
    <div className="space-y-3">
      {evidence.map((entry) => (
        <div
          key={`${entry.factor}-${entry.rule}-${entry.clue}`}
          className="rounded-xl border p-3 bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-700"
        >
          <div className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {String(entry.factor || 'rule').replace(/_/g, ' ')}
          </div>
          <div className="font-medium mt-1">{entry.clue}</div>
          <div className="text-xs text-gray-600 dark:text-gray-400 mt-1 leading-relaxed">
            {entry.rule}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function LostObjectLocationPanel({ chart, darkMode }) {
  const projection = chart?.lost_object_location;
  const isLegacyLocationalChart = Boolean(
    chart?.question_analysis?.significators?.lost_object_family ||
      chart?.question_analysis?.significators?.passport_family === 'passport_lost_document' ||
      isMissingPetLocationChart(chart) ||
      String(chart?.question_analysis?.question_type || '').toUpperCase().includes('LOST_OBJECT')
  );
  const chartWorkflowLabel = isMissingPetLocationChart(chart) ? 'missing-pet' : 'lost-object';

  if (!projection?.applies) {
    return (
      <div className="space-y-4">
        <div
          className={`p-5 rounded-2xl border ${
            darkMode ? 'bg-gray-800/30 border-gray-600' : 'bg-gray-50/60 border-gray-200'
          }`}
        >
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-200">
              Location Clues
            </span>
            {isLegacyLocationalChart && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200">
                Saved chart
              </span>
            )}
          </div>

          <div className="text-sm text-gray-700 dark:text-gray-200 leading-relaxed">
            {isLegacyLocationalChart
              ? `This chart is a ${chartWorkflowLabel} case, but it does not yet include the newer structured location projection.`
              : 'No structured location clues were returned for this chart.'}
          </div>

          {isLegacyLocationalChart && (
            <div className="mt-3 text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
              Re-run the chart with the current engine build to populate ranked search places, direction clues,
              and supporting evidence in this tab.
            </div>
          )}
        </div>

        <div className="rounded-xl border p-4 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800/40">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 mt-0.5 text-amber-600 dark:text-amber-300" />
            <div className="text-xs text-amber-900 dark:text-amber-100 leading-relaxed">
              The location tab follows the same horary workflow as the other panels: house placement gives the main
              place, then sign, modality, direction, and dispositor refine the search.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const primaryPlaces = Array.isArray(projection.primary_places) ? projection.primary_places : [];
  const secondaryPlaces = Array.isArray(projection.secondary_places) ? projection.secondary_places : [];
  const environmentTraits = Array.isArray(projection.environment_traits)
    ? projection.environment_traits
    : [];
  const directionalCues = Array.isArray(projection.directional_cues) ? projection.directional_cues : [];
  const evidence = Array.isArray(projection.evidence) ? projection.evidence : [];

  const sections = useMemo(
    () =>
      [
        {
          id: 'primary',
          title: 'Primary Places',
          icon: MapPin,
          content: (
            <HintList
              items={primaryPlaces}
              accentClass="bg-indigo-50 dark:bg-indigo-900/20 border-indigo-100 dark:border-indigo-800/40"
            />
          ),
        },
        {
          id: 'clues',
          title: 'Further Clues',
          icon: Search,
          content: (
            <HintList
              items={[...secondaryPlaces, ...environmentTraits]}
              accentClass="bg-emerald-50 dark:bg-emerald-900/20 border-emerald-100 dark:border-emerald-800/40"
            />
          ),
        },
        directionalCues.length > 0
          ? {
              id: 'direction',
              title: 'Direction',
              icon: Compass,
              content: (
                <HintList
                  items={directionalCues}
                  accentClass="bg-sky-50 dark:bg-sky-900/20 border-sky-100 dark:border-sky-800/40"
                />
              ),
            }
          : null,
        evidence.length > 0
          ? {
              id: 'evidence',
              title: 'Evidence',
              icon: BookOpen,
              content: buildEvidenceContent(evidence),
            }
          : null,
      ].filter(Boolean),
    [directionalCues, environmentTraits, evidence, primaryPlaces, secondaryPlaces]
  );

  const [activeSectionId, setActiveSectionId] = useState(() => sections[0]?.id || 'primary');

  useEffect(() => {
    if (!sections.some((section) => section.id === activeSectionId)) {
      setActiveSectionId(sections[0]?.id || 'primary');
    }
  }, [activeSectionId, sections]);

  const activeSection = sections.find((section) => section.id === activeSectionId) || sections[0];

  return (
    <div className="space-y-4 text-sm">
      <div
        data-testid="lost-object-location-summary-card"
        className={`p-4 rounded-xl border ${
          darkMode ? 'bg-gray-800/30 border-gray-600' : 'bg-gray-50/60 border-gray-200'
        }`}
      >
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-200">
            {projection.object_significator || 'Object'} in {formatHouseLabel(projection.effective_house)}
          </span>
          {projection.object_sign && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-200">
              {projection.object_sign}
            </span>
          )}
          {projection.sign_element && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-200">
              {projection.sign_element}
            </span>
          )}
          {projection.sign_modality && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-200">
              {projection.sign_modality}
            </span>
          )}
        </div>

        <div className="text-gray-700 dark:text-gray-200 leading-relaxed">
          {projection.summary || 'Traditional location clues were derived from the object significator.'}
        </div>

        <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
          Confidence: {projection.confidence_label || 'moderate'} ({projection.confidence ?? 0}%) | Lost-object clues
          are ranked search hints, not an exact address.
        </div>
      </div>

      <div className="px-1">
        <SectionTabs
          activeId={activeSection?.id}
          onChange={setActiveSectionId}
          darkMode={darkMode}
          sections={sections}
        />
      </div>

      {activeSection && (
        <SectionCard title={activeSection.title} icon={activeSection.icon} darkMode={darkMode}>
          {activeSection.content}
        </SectionCard>
      )}

      <div className="rounded-xl border p-4 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800/40">
        <div className="flex items-start gap-2">
          <Info className="w-4 h-4 mt-0.5 text-amber-600 dark:text-amber-300" />
          <div className="text-xs text-amber-900 dark:text-amber-100 leading-relaxed">
            Search the strongest house clue first, then refine with sign, container, floor or height, and dispositor
            evidence if the first pass misses.
          </div>
        </div>
      </div>
    </div>
  );
}
