function normalizeId(value) {
  return String(value || '').trim().toLowerCase().replace(/\s+/g, '_');
}

function stableSortDomains(domains, priorityIndex) {
  return [...domains].sort((left, right) => {
    const leftId = normalizeId(left?.id);
    const rightId = normalizeId(right?.id);
    const leftRank = priorityIndex.get(leftId) ?? 999;
    const rightRank = priorityIndex.get(rightId) ?? 999;
    if (leftRank !== rightRank) return leftRank - rightRank;
    const leftLabel = String(left?.label || left?.id || '');
    const rightLabel = String(right?.label || right?.id || '');
    return leftLabel.localeCompare(rightLabel);
  });
}

export function buildChartTypeDomainOptions(chartType, domains = []) {
  const preferredIds = Array.isArray(chartType?.preferred_domain_ids)
    ? chartType.preferred_domain_ids.map(normalizeId).filter(Boolean)
    : [];
  const supportedIds = Array.isArray(chartType?.supported_domain_ids)
    ? chartType.supported_domain_ids.map(normalizeId).filter(Boolean)
    : [];
  const discouragedIds = new Set(
    Array.isArray(chartType?.discouraged_domain_ids)
      ? chartType.discouraged_domain_ids.map(normalizeId).filter(Boolean)
      : [],
  );

  if (!preferredIds.length && !supportedIds.length) {
    return {
      availableDomains: [...domains],
      preferredDomains: [...domains],
      supportedDomains: [],
      defaultDomainId: normalizeId(chartType?.default_domain_id) || normalizeId(domains[0]?.id) || '',
      hasExplicitProfile: false,
    };
  }

  const domainIndex = new Map(domains.map((item) => [normalizeId(item?.id), item]));
  const preferredDomains = preferredIds
    .map((domainId) => domainIndex.get(domainId))
    .filter(Boolean);
  const supportedDomains = supportedIds
    .map((domainId) => domainIndex.get(domainId))
    .filter(Boolean);

  const priorityIndex = new Map();
  preferredIds.forEach((domainId, index) => priorityIndex.set(domainId, index));
  supportedIds.forEach((domainId, index) => {
    if (!priorityIndex.has(domainId)) priorityIndex.set(domainId, preferredIds.length + index);
  });

  const availableIds = new Set([...preferredIds, ...supportedIds]);
  const availableDomains = stableSortDomains(
    domains.filter((item) => availableIds.has(normalizeId(item?.id))),
    priorityIndex,
  );

  const defaultDomainId = normalizeId(chartType?.default_domain_id);
  const fallbackDefault = normalizeId(preferredDomains[0]?.id) || normalizeId(availableDomains[0]?.id) || '';

  return {
    availableDomains,
    preferredDomains: stableSortDomains(preferredDomains, priorityIndex),
    supportedDomains: stableSortDomains(supportedDomains, priorityIndex),
    defaultDomainId: availableIds.has(defaultDomainId) ? defaultDomainId : fallbackDefault,
    discouragedDomainIds: discouragedIds,
    hasExplicitProfile: true,
  };
}

export function isChartTypeDomainAllowed(chartType, domainId, domains = []) {
  const normalizedDomainId = normalizeId(domainId);
  if (!normalizedDomainId) return false;
  const { availableDomains, hasExplicitProfile } = buildChartTypeDomainOptions(chartType, domains);
  if (!hasExplicitProfile) return true;
  return availableDomains.some((item) => normalizeId(item?.id) === normalizedDomainId);
}
