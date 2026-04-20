import React from 'react';

/**
 * Renders reasoning entries as simple rows.
 * @param {Object} bundle - The reasoning bundle.
 * @param {string} bundle.version - Version identifier.
 * @param {Array} bundle.entries - Array of reasoning entries {text, weight}.
 * @returns {JSX.Element[]} Array of JSX rows.
 */
// Function to highlight horary terms
const highlightHoraryTerms = (text) => {
  if (typeof text !== 'string') return text;
  
  const terms = {
    'occurrence': 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    'perfection': 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300', 
    'quality': 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
    'aspect type': 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
    'hard aspect': 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
  };
  
  let parts = [{ text, highlighted: false }];
  
  // Process each term
  Object.entries(terms).forEach(([term, className]) => {
    const newParts = [];
    parts.forEach(part => {
      if (!part.highlighted) {
        const regex = new RegExp(`\\b${term}\\b`, 'gi');
        const matches = [...part.text.matchAll(regex)];
        
        if (matches.length > 0) {
          let lastIndex = 0;
          matches.forEach(match => {
            if (match.index > lastIndex) {
              newParts.push({ 
                text: part.text.slice(lastIndex, match.index), 
                highlighted: false 
              });
            }
            newParts.push({ 
              text: match[0], 
              highlighted: true, 
              className 
            });
            lastIndex = match.index + match[0].length;
          });
          if (lastIndex < part.text.length) {
            newParts.push({ 
              text: part.text.slice(lastIndex), 
              highlighted: false 
            });
          }
        } else {
          newParts.push(part);
        }
      } else {
        newParts.push(part);
      }
    });
    parts = newParts;
  });
  
  return (
    <span>
      {parts.map((part, index) => 
        part.highlighted ? (
          <span key={index} className={`px-1 rounded ${part.className}`}>
            {part.text}
          </span>
        ) : part.text
      )}
    </span>
  );
};

export function renderReasoning({ version, entries }) {
  if (!entries || !Array.isArray(entries)) return [];

  return entries.map((entry, idx) => (
    <div key={idx} className="flex items-center space-x-2 py-1">
      <span className="text-sm flex-1">{highlightHoraryTerms(entry.text)}</span>
      <span
        className={`text-xs font-semibold ${
          entry.weight > 0
            ? 'text-emerald-600'
            : entry.weight < 0
            ? 'text-red-600'
            : 'text-amber-600'
        }`}
      >
        {entry.weight > 0 ? '+' : ''}{entry.weight}
      </span>
    </div>
  ));
}

export default renderReasoning;
