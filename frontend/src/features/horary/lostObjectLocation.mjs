export function isLostObjectQuestionType(questionType) {
  const raw =
    typeof questionType === 'string'
      ? questionType
      : questionType?.value || questionType?.name || '';
  const normalized = String(raw).trim().toUpperCase().replace(/^CATEGORY\./, '');
  return normalized === 'LOST_OBJECT';
}

export function hasLostObjectLocationProjection(chart) {
  return Boolean(chart?.lost_object_location?.applies);
}

export function isMissingPetLocationChart(chart) {
  const questionType = chart?.question_analysis?.question_type;
  const normalizedQuestionType =
    typeof questionType === 'string'
      ? questionType.trim().toUpperCase().replace(/^CATEGORY\./, '')
      : '';

  if (normalizedQuestionType !== 'PET') return false;

  const petFamily =
    chart?.question_analysis?.pet_analysis?.family ||
    chart?.question_analysis?.significators?.pet_family;

  return typeof petFamily === 'string' && petFamily.trim().toLowerCase() === 'missing';
}

export function shouldShowLostObjectLocationTab(chart) {
  if (hasLostObjectLocationProjection(chart)) return true;

  const questionType = chart?.question_analysis?.question_type;
  if (isLostObjectQuestionType(questionType)) return true;
  if (isMissingPetLocationChart(chart)) return true;

  const significators = chart?.question_analysis?.significators || {};
  if (typeof significators?.lost_object_family === 'string' && significators.lost_object_family.trim()) {
    return true;
  }

  if (significators?.passport_family === 'passport_lost_document') {
    return true;
  }

  return false;
}

export function formatHouseLabel(house) {
  const value = Number(house);
  if (!Number.isFinite(value) || value <= 0) return 'Unknown house';
  const mod100 = value % 100;
  const suffix =
    mod100 >= 11 && mod100 <= 13
      ? 'th'
      : ({ 1: 'st', 2: 'nd', 3: 'rd' }[value % 10] || 'th');
  return `${value}${suffix} house`;
}
