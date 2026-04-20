import React from 'react';

const NOTE_LINK_CLASS =
  'underline decoration-indigo-400 underline-offset-2 break-all text-indigo-700 hover:text-indigo-900 dark:text-indigo-300 dark:hover:text-indigo-200';
const NOTE_INLINE_CODE_CLASS =
  'rounded bg-gray-200 px-1 py-0.5 font-mono text-[0.92em] text-gray-900 dark:bg-gray-700 dark:text-gray-100';

const ATTACHMENT_TEMPLATES = {
  voice: '- Voice note: [Add recording title](https://example.com/voice-note)',
  video: '- Video link: [Add video title](https://example.com/video)',
  link: '- External reference: [Add link title](https://example.com/reference)',
};

function isSafeExternalUrl(url) {
  const normalized = String(url || '').trim();
  return /^(https?:\/\/|mailto:)/i.test(normalized);
}

function openExternalUrl(url, openExternal) {
  const normalized = String(url || '').trim();
  if (!isSafeExternalUrl(normalized)) return;
  try {
    if (typeof openExternal === 'function') {
      openExternal(normalized);
      return;
    }
  } catch (_) {}
  try {
    if (typeof window !== 'undefined' && typeof window.open === 'function') {
      window.open(normalized, '_blank', 'noopener,noreferrer');
    }
  } catch (_) {}
}

function renderInlineMarkdown(text, { openExternal, keyPrefix }) {
  const source = String(text || '');
  if (!source) return null;

  const pattern = /(\[([^\]]+)\]\(([^)\s]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*)/g;
  const nodes = [];
  let lastIndex = 0;
  let match;
  let partIndex = 0;

  while ((match = pattern.exec(source)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(source.slice(lastIndex, match.index));
    }

    const [token, , linkLabel, linkUrl, inlineCode, boldText, italicText] = match;
    const key = `${keyPrefix}-${partIndex++}`;

    if (linkLabel && linkUrl) {
      if (isSafeExternalUrl(linkUrl)) {
        nodes.push(
          <a
            key={key}
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={NOTE_LINK_CLASS}
            onClick={(event) => {
              event.preventDefault();
              openExternalUrl(linkUrl, openExternal);
            }}
          >
            {linkLabel}
          </a>,
        );
      } else {
        nodes.push(token);
      }
    } else if (inlineCode) {
      nodes.push(
        <code key={key} className={NOTE_INLINE_CODE_CLASS}>
          {inlineCode}
        </code>,
      );
    } else if (boldText) {
      nodes.push(<strong key={key}>{boldText}</strong>);
    } else if (italicText) {
      nodes.push(<em key={key}>{italicText}</em>);
    } else {
      nodes.push(token);
    }

    lastIndex = match.index + token.length;
  }

  if (lastIndex < source.length) {
    nodes.push(source.slice(lastIndex));
  }

  return nodes;
}

export function appendNoteAttachment(noteText, kind) {
  const template = ATTACHMENT_TEMPLATES[kind];
  if (!template) return String(noteText || '');
  const existing = String(noteText || '').trimEnd();
  return existing ? `${existing}\n\n${template}` : template;
}

export function renderNoteMarkdown(noteText, { openExternal } = {}) {
  const normalized = String(noteText || '').replace(/\r\n?/g, '\n').trim();
  if (!normalized) return null;

  const blocks = [];
  const paragraphLines = [];
  let listState = null;

  const flushParagraph = () => {
    if (!paragraphLines.length) return;
    blocks.push({ type: 'paragraph', lines: [...paragraphLines] });
    paragraphLines.length = 0;
  };

  const flushList = () => {
    if (!listState) return;
    blocks.push({ ...listState });
    listState = null;
  };

  for (const rawLine of normalized.split('\n')) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2],
      });
      continue;
    }

    const quoteMatch = line.match(/^>\s?(.+)$/);
    if (quoteMatch) {
      flushParagraph();
      flushList();
      blocks.push({ type: 'blockquote', text: quoteMatch[1] });
      continue;
    }

    const unorderedMatch = line.match(/^[-*]\s+(.+)$/);
    if (unorderedMatch) {
      flushParagraph();
      if (!listState || listState.ordered) {
        flushList();
        listState = { type: 'list', ordered: false, items: [] };
      }
      listState.items.push(unorderedMatch[1]);
      continue;
    }

    const orderedMatch = line.match(/^\d+\.\s+(.+)$/);
    if (orderedMatch) {
      flushParagraph();
      if (!listState || !listState.ordered) {
        flushList();
        listState = { type: 'list', ordered: true, items: [] };
      }
      listState.items.push(orderedMatch[1]);
      continue;
    }

    flushList();
    paragraphLines.push(line);
  }

  flushParagraph();
  flushList();

  return blocks.map((block, index) => {
    const keyPrefix = `note-${index}`;

    if (block.type === 'heading') {
      const Tag = `h${block.level}`;
      const sizeClass =
        block.level === 1
          ? 'text-lg font-semibold'
          : block.level === 2
            ? 'text-base font-semibold'
            : 'text-sm font-semibold';
      return (
        <Tag key={keyPrefix} className={`${sizeClass} leading-6`}>
          {renderInlineMarkdown(block.text, { openExternal, keyPrefix })}
        </Tag>
      );
    }

    if (block.type === 'blockquote') {
      return (
        <blockquote
          key={keyPrefix}
          className="border-l-2 border-indigo-300 pl-3 italic text-gray-600 dark:border-indigo-500 dark:text-gray-300"
        >
          {renderInlineMarkdown(block.text, { openExternal, keyPrefix })}
        </blockquote>
      );
    }

    if (block.type === 'list') {
      const ListTag = block.ordered ? 'ol' : 'ul';
      return (
        <ListTag
          key={keyPrefix}
          className={`space-y-1 pl-5 ${block.ordered ? 'list-decimal' : 'list-disc'}`}
        >
          {block.items.map((item, itemIndex) => (
            <li key={`${keyPrefix}-item-${itemIndex}`}>
              {renderInlineMarkdown(item, {
                openExternal,
                keyPrefix: `${keyPrefix}-item-${itemIndex}`,
              })}
            </li>
          ))}
        </ListTag>
      );
    }

    return (
      <p key={keyPrefix} className="leading-6">
        {block.lines.map((line, lineIndex) => (
          <React.Fragment key={`${keyPrefix}-line-${lineIndex}`}>
            {lineIndex > 0 ? <br /> : null}
            {renderInlineMarkdown(line, {
              openExternal,
              keyPrefix: `${keyPrefix}-line-${lineIndex}`,
            })}
          </React.Fragment>
        ))}
      </p>
    );
  });
}
