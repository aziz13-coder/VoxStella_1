// Thin API client for Astro Clock

const getApiBaseUrl = () => {
  // Prefer Electron-provided base URL for offline-first packaged builds
  if (typeof window !== 'undefined' && window.API_BASE_URL) return window.API_BASE_URL;
  try {
    if (import.meta && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
      return import.meta.env.VITE_API_BASE_URL;
    }
  } catch (_) {}
  return 'http://127.0.0.1:52525';
};

const LicenseTokenProvider = (() => {
  let cachedToken = null;
  let cacheExpiresAtMs = 0;
  let inflight = null;

  const decodeTokenClaims = (token) => {
    try {
      const parts = String(token || '').split('.');
      if (parts.length !== 2 || !parts[1]) return null;
      const json = atob(parts[1]);
      const parsed = JSON.parse(json);
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch (_) {
      return null;
    }
  };

  const computeCacheExpiryMs = (token) => {
    const now = Date.now();
    if (!token) return 0;
    const claims = decodeTokenClaims(token);
    const candidates = [now + 60 * 1000];
    const nextVerifyAt = Number(claims?.next_verify_at);
    const exp = Number(claims?.exp);
    if (Number.isFinite(nextVerifyAt) && nextVerifyAt > 0) {
      candidates.push((nextVerifyAt * 1000) - 1000);
    }
    if (Number.isFinite(exp) && exp > 0) {
      candidates.push((exp * 1000) - 1000);
    }
    return Math.max(now, Math.min(...candidates));
  };

  const storeToken = (token) => {
    cachedToken = token || null;
    cacheExpiresAtMs = computeCacheExpiryMs(cachedToken);
    return cachedToken;
  };

  const fetchToken = async () => {
    try {
      if (typeof window !== 'undefined' && window.electronAPI?.getLicenseToken) {
        return storeToken(await window.electronAPI.getLicenseToken());
      }
      if (import.meta?.env?.VITE_DEV_LICENSE_TOKEN) {
        return storeToken(import.meta.env.VITE_DEV_LICENSE_TOKEN);
      }
      if (import.meta?.env?.DEV && !(typeof window !== 'undefined' && window.electronAPI)) {
        // Browser dev should rely on the source backend's explicit dev-bypass mode,
        // not emit a fake token that the backend will reject as malformed.
        return storeToken(null);
      }
    } catch (_) {}
    return storeToken(null);
  };

  return {
    async getToken(options = {}) {
      const forceRefresh = options?.forceRefresh === true;
      if (!forceRefresh && cachedToken && Date.now() < cacheExpiresAtMs) {
        return cachedToken;
      }
      if (!inflight || forceRefresh) {
        inflight = fetchToken().finally(() => {
          inflight = null;
        });
      }
      return inflight;
    },
    invalidate() {
      cachedToken = null;
      cacheExpiresAtMs = 0;
      inflight = null;
    },
  };
})();

function parseFilenameFromDisposition(disposition) {
  const raw = String(disposition || '');
  if (!raw) return null;
  const utfMatch = raw.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch && utfMatch[1]) {
    try {
      return decodeURIComponent(utfMatch[1].trim().replace(/^"|"$/g, ''));
    } catch (_) {}
  }
  const basicMatch = raw.match(/filename="?([^";]+)"?/i);
  if (basicMatch && basicMatch[1]) {
    return basicMatch[1].trim();
  }
  return null;
}

export async function request(path, options = {}) {
  const { timeoutMs, skipLicense, responseType, ...rawOptions } = options;
  const url = `${getApiBaseUrl()}${path}`;
  const method = String(rawOptions.method || 'GET').toUpperCase();
  const expectedType = responseType === 'blob' ? 'blob' : 'json';
  const timeoutValue = Number(timeoutMs);
  const effectiveTimeoutMs =
    Number.isFinite(timeoutValue) && timeoutValue > 0 ? timeoutValue : 30000;
  const externalSignal = rawOptions.signal;
  if (externalSignal) delete rawOptions.signal;

  const send = async (token, allowRetry) => {
    const baseHeaders = { ...(rawOptions.headers || {}) };
    if (!skipLicense && token) {
      baseHeaders.Authorization = `Bearer ${token}`;
    }
    if (!(method === 'GET' || method === 'HEAD')) {
      if (!('Content-Type' in baseHeaders)) baseHeaders['Content-Type'] = 'application/json';
    }

    const controller = new AbortController();
    let timedOut = false;
    const timeoutId = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, effectiveTimeoutMs);
    let removeAbortRelay = null;
    if (externalSignal) {
      const relayAbort = () => controller.abort();
      if (externalSignal.aborted) {
        controller.abort();
      } else {
        externalSignal.addEventListener('abort', relayAbort, { once: true });
        removeAbortRelay = () => externalSignal.removeEventListener('abort', relayAbort);
      }
    }

    try {
      const res = await fetch(url, { ...rawOptions, headers: baseHeaders, signal: controller.signal });
      if ((res.status === 402 || res.status === 403) && !skipLicense) {
        LicenseTokenProvider.invalidate();
      }
      if (expectedType === 'blob') {
        if (!res.ok) {
          const errText = await res.text().catch(() => '');
          let parsedError = null;
          try {
            parsedError = errText ? JSON.parse(errText) : null;
          } catch (_) {}
          const error = new Error(
            parsedError?.error || parsedError?.detail || errText || `HTTP ${res.status}`
          );
          error.status = res.status;
          error.detail = parsedError?.detail || null;
          error.incidentId = parsedError?.incident_id || null;
          error.payload = parsedError || null;
          error.authFailure = !skipLicense && allowRetry && (res.status === 402 || res.status === 403);
          throw error;
        }
        return {
          blob: await res.blob(),
          contentType: res.headers.get('Content-Type') || res.headers.get('content-type') || '',
          filename: parseFilenameFromDisposition(
            res.headers.get('Content-Disposition') || res.headers.get('content-disposition') || ''
          ),
        };
      }

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const error = new Error(data?.error || data?.detail || `HTTP ${res.status}`);
        error.status = res.status;
        error.detail = data?.detail || null;
        error.incidentId = data?.incident_id || null;
        error.payload = data || null;
        error.authFailure = !skipLicense && allowRetry && (res.status === 402 || res.status === 403);
        throw error;
      }
      return data;
    } catch (error) {
      if (error?.name === 'AbortError' && timedOut) {
        throw new Error(`Request timed out after ${Math.round(effectiveTimeoutMs / 1000)}s`);
      }
      if (error?.authFailure) {
        const retryToken = await LicenseTokenProvider.getToken().catch(() => null);
        if (retryToken && retryToken !== token) {
          return send(retryToken, false);
        }
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
      if (removeAbortRelay) {
        removeAbortRelay();
      }
    }
  };

  const initialToken = skipLicense ? null : await LicenseTokenProvider.getToken().catch(() => null);
  return send(initialToken, true);
}

const ASTRO_CLOCK_CORE_TIMEOUT_MS = 90000;

function appendClockContext(params, opts = {}) {
  if (!(params instanceof URLSearchParams)) return;
  if (opts.mode) params.set('mode', String(opts.mode));
  if (opts.datetime) params.set('datetime', String(opts.datetime));
  if (opts.location) params.set('location', String(opts.location));
  if (opts.timezone) params.set('timezone', String(opts.timezone));
  if (opts.houseSystem) params.set('house_system_code', String(opts.houseSystem));
}

function appendElectionParams(params, opts = {}) {
  if (!(params instanceof URLSearchParams)) return;
  if (opts.matter) params.set('matter', String(opts.matter));
  if (opts.start) params.set('start', String(opts.start));
  if (opts.end) params.set('end', String(opts.end));
  if (opts.location) params.set('location', String(opts.location));
  if (opts.timezone) params.set('timezone', String(opts.timezone));
  if (opts.houseSystem) params.set('house_system_code', String(opts.houseSystem));
  if (opts.stepMinutes != null) params.set('step_minutes', String(opts.stepMinutes));
  if (opts.limit != null) params.set('limit', String(opts.limit));
  if (opts.includeSrLr) params.set('include_sr_lr', '1');
  if (opts.weekdayMode) params.set('weekday_mode', String(opts.weekdayMode));
  if (Array.isArray(opts.weekdays) && opts.weekdayMode !== 'all') {
    opts.weekdays.forEach((w) => {
      if (typeof w === 'string' && w.trim()) params.append('weekday', w.trim().toLowerCase());
    });
  }
  if (opts.hourStart != null && String(opts.hourStart).trim() !== '') params.set('hour_start', String(opts.hourStart));
  if (opts.hourEnd != null && String(opts.hourEnd).trim() !== '') params.set('hour_end', String(opts.hourEnd));
  if (opts.marriageAlgorithm) params.set('marriage_algorithm', String(opts.marriageAlgorithm));
  if (opts.businessAlgorithm) params.set('business_algorithm', String(opts.businessAlgorithm));
  if (opts.businessBetaDisplayMode) params.set('business_beta_display_mode', String(opts.businessBetaDisplayMode));
  if (opts.businessBetaScope) params.set('business_beta_scope', String(opts.businessBetaScope));
  if (opts.businessBetaCurrentLineId) params.set('business_beta_current_line_id', String(opts.businessBetaCurrentLineId));
  if (opts.businessBetaLevelPercent != null) {
    params.set('business_beta_level_percent', String(opts.businessBetaLevelPercent));
  }
  if (Array.isArray(opts.businessBetaSelectedLineIds)) {
    opts.businessBetaSelectedLineIds.forEach((lineId) => {
      if (lineId != null && String(lineId).trim() !== '') {
        params.append('business_beta_selected_line_id', String(lineId).trim());
      }
    });
  }
  if (opts.participantASnapId) params.set('participant_a_snap_id', String(opts.participantASnapId));
  if (opts.participantBSnapId) params.set('participant_b_snap_id', String(opts.participantBSnapId));
  if (Array.isArray(opts.participantSnapIds)) {
    opts.participantSnapIds.forEach((snapId) => {
      if (snapId != null && String(snapId).trim() !== '') params.append('participant_snap_id', String(snapId).trim());
    });
  }
  if (opts.natalSnapId) params.set('natal_snap_id', String(opts.natalSnapId));
  if (opts.natalDatetime) params.set('natal_datetime', String(opts.natalDatetime));
  if (opts.natalLocation) params.set('natal_location', String(opts.natalLocation));
  if (opts.natalTimezone) params.set('natal_timezone', String(opts.natalTimezone));
  if (opts.gender) params.set('gender', String(opts.gender));
  if (opts.hairGoal) params.set('hair_goal', String(opts.hairGoal));
  if (opts.surgerySign) params.set('surgery_sign', String(opts.surgerySign));
  if (opts.procedure) params.set('procedure', String(opts.procedure));
  if (opts.includeLunationScreen) params.set('include_lunation_screen', '1');
  if (opts.includeFixedStars) params.set('include_fixed_stars', '1');
  if (opts.includeTraditionalTiming) params.set('include_traditional_timing', '1');
  if (opts.businessMode) params.set('business_mode', String(opts.businessMode));
  if (opts.emphasizeCommerce) params.set('emphasize_commerce', '1');
  if (opts.journeyType) params.set('journey_type', String(opts.journeyType));
  if (opts.legalAction) params.set('legal_action', String(opts.legalAction));
  if (opts.actionType) params.set('action_type', String(opts.actionType));
  if (opts.bodyParts) {
    params.set('body_parts', Array.isArray(opts.bodyParts) ? opts.bodyParts.join(',') : String(opts.bodyParts));
  }
  if (opts.bodySigns) {
    params.set('body_signs', Array.isArray(opts.bodySigns) ? opts.bodySigns.join(',') : String(opts.bodySigns));
  }
  if (opts.procedureType) params.set('procedure_type', String(opts.procedureType));
  if (opts.preferFixedAsc != null) params.set('prefer_fixed_asc', opts.preferFixedAsc ? '1' : '0');
  if (opts.saturnBindingOk === false) params.set('saturn_binding_ok', '0');
  if (opts.minMercuryDirectDays != null) {
    params.set('min_mercury_direct_days', String(opts.minMercuryDirectDays));
  }
  if (opts.contractMode) params.set('contract_mode', String(opts.contractMode));
}

function appendMundaneParams(params, opts = {}) {
  if (!(params instanceof URLSearchParams)) return;
  if (opts.chartType) params.set('chart_type', String(opts.chartType));
  if (opts.domain) params.set('domain', String(opts.domain));
  if (opts.polityId) params.set('polity_id', String(opts.polityId));
  if (opts.customPolityLabel) params.set('custom_polity_label', String(opts.customPolityLabel));
  if (opts.locationContextType) params.set('location_context_type', String(opts.locationContextType));
  if (opts.referenceLocation) params.set('reference_location', String(opts.referenceLocation));
  if (opts.referenceLatitude != null) params.set('reference_latitude', String(opts.referenceLatitude));
  if (opts.referenceLongitude != null) params.set('reference_longitude', String(opts.referenceLongitude));
  if (opts.eventDatetime) params.set('event_datetime', String(opts.eventDatetime));
  if (opts.eventLocation) params.set('event_location', String(opts.eventLocation));
  if (opts.eventTimezone) params.set('event_timezone', String(opts.eventTimezone));
  if (opts.nationalChartId) params.set('national_chart_id', String(opts.nationalChartId));
  if (opts.customChartLabel) params.set('custom_chart_label', String(opts.customChartLabel));
  if (opts.customChartDatetime) params.set('custom_chart_datetime', String(opts.customChartDatetime));
  if (opts.customChartLocation) params.set('custom_chart_location', String(opts.customChartLocation));
  if (opts.customChartTimezone) params.set('custom_chart_timezone', String(opts.customChartTimezone));
  if (opts.visibilityScope) params.set('visibility_scope', String(opts.visibilityScope));
  if (opts.sourcePreference) params.set('source_preference', String(opts.sourcePreference));
}

function appendWeatherParams(params, opts = {}) {
  if (!(params instanceof URLSearchParams)) return;
  if (opts.familyId) params.set('family_id', String(opts.familyId));
  if (opts.forecastDatetime) params.set('forecast_datetime', String(opts.forecastDatetime));
  if (opts.location) params.set('location', String(opts.location));
  if (opts.timezone) params.set('timezone', String(opts.timezone));
  if (opts.latitude != null) params.set('latitude', String(opts.latitude));
  if (opts.longitude != null) params.set('longitude', String(opts.longitude));
  if (opts.houseSystem) params.set('house_system_code', String(opts.houseSystem));
  if (opts.sourcePreference) params.set('source_preference', String(opts.sourcePreference));
}

function appendWeatherScanParams(params, opts = {}) {
  if (!(params instanceof URLSearchParams)) return;
  appendWeatherParams(params, opts);
  if (opts.scanScope) params.set('scan_scope', String(opts.scanScope));
  if (opts.regionId) params.set('region_id', String(opts.regionId));
  if (opts.resolution) params.set('resolution', String(opts.resolution));
  if (opts.candidateLimit != null) params.set('candidate_limit', String(opts.candidateLimit));
  if (opts.topK != null) params.set('top_k', String(opts.topK));
  if (opts.startDatetime) params.set('start_datetime', String(opts.startDatetime));
  if (opts.endDatetime) params.set('end_datetime', String(opts.endDatetime));
  if (opts.timeStepHours != null) params.set('time_step_hours', String(opts.timeStepHours));
}

function buildTransitsExportQuery(opts = {}) {
  const p = new URLSearchParams();
  if (opts.natalSnapId) p.set('natal_snap_id', opts.natalSnapId);
  if (opts.natalDatetime) p.set('natal_datetime', opts.natalDatetime);
  if (opts.natalLocation) p.set('natal_location', opts.natalLocation);
  if (opts.natalTimezone) p.set('natal_timezone', opts.natalTimezone);
  if (opts.houseSystem) p.set('house_system_code', opts.houseSystem);
  if (opts.transitDatetime) p.set('transit_datetime', opts.transitDatetime);
  if (opts.includeModern) p.set('include_modern', '1');
  if (opts.includeNatalModern) p.set('include_natal_modern', '1');
  if (opts.includeCusps) p.set('include_cusps', '1');
  if (opts.includeAntiscia) p.set('include_antiscia', '1');
  if (opts.includeLots) p.set('include_lots', '1');
  if (Array.isArray(opts.focusHouses)) opts.focusHouses.forEach((h) => { const v = Number(h); if (!Number.isNaN(v)) p.append('focus_house', String(v)); });
  if (Array.isArray(opts.focusPlanets)) opts.focusPlanets.forEach((pl) => { if (typeof pl === 'string' && pl.trim()) p.append('focus_planet', pl.trim()); });
  if (Array.isArray(opts.sensitiveHouses)) opts.sensitiveHouses.forEach((h) => { const v = Number(h); if (!Number.isNaN(v)) p.append('sensitive_house', String(v)); });
  if (Array.isArray(opts.sensitivePlanets)) opts.sensitivePlanets.forEach((pl) => { if (typeof pl === 'string' && pl.trim()) p.append('sensitive_planet', pl.trim()); });
  if (Array.isArray(opts.transiting)) opts.transiting.forEach((pl) => { if (typeof pl === 'string' && pl.trim()) p.append('transiting', pl.trim()); });
  if (Array.isArray(opts.natal)) opts.natal.forEach((pl) => { if (typeof pl === 'string' && pl.trim()) p.append('natal', pl.trim()); });
  if (Array.isArray(opts.aspects)) opts.aspects.forEach((a) => { if (typeof a === 'string' && a.trim()) p.append('aspect', a.trim()); });
  if (opts.sigBeta != null) p.set('sig_beta', opts.sigBeta ? '1' : '0');
  return p.toString();
}

function buildTransitsWindowExportQuery(opts = {}) {
  const p = new URLSearchParams();
  if (opts.natalSnapId) p.set('natal_snap_id', opts.natalSnapId);
  if (opts.natalDatetime) p.set('natal_datetime', opts.natalDatetime);
  if (opts.natalLocation) p.set('natal_location', opts.natalLocation);
  if (opts.natalTimezone) p.set('natal_timezone', opts.natalTimezone);
  if (opts.houseSystem) p.set('house_system_code', opts.houseSystem);
  if (opts.start) p.set('start', opts.start);
  if (opts.end) p.set('end', opts.end);
  if (opts.center) p.set('center', opts.center);
  if (opts.rangeHours != null) p.set('range_hours', String(opts.rangeHours));
  if (opts.stepMinutes != null) p.set('step_minutes', String(opts.stepMinutes));
  if (opts.includeModern) p.set('include_modern', '1');
  if (opts.includeNatalModern) p.set('include_natal_modern', '1');
  if (opts.includeCusps) p.set('include_cusps', '1');
  if (opts.includeAntiscia) p.set('include_antiscia', '1');
  if (opts.includeLots) p.set('include_lots', '1');
  if (Array.isArray(opts.focusHouses)) opts.focusHouses.forEach((h) => { const v = Number(h); if (!Number.isNaN(v)) p.append('focus_house', String(v)); });
  if (Array.isArray(opts.focusPlanets)) opts.focusPlanets.forEach((pl) => { if (typeof pl === 'string' && pl.trim()) p.append('focus_planet', pl.trim()); });
  if (Array.isArray(opts.sensitiveHouses)) opts.sensitiveHouses.forEach((h) => { const v = Number(h); if (!Number.isNaN(v)) p.append('sensitive_house', String(v)); });
  if (Array.isArray(opts.sensitivePlanets)) opts.sensitivePlanets.forEach((pl) => { if (typeof pl === 'string' && pl.trim()) p.append('sensitive_planet', pl.trim()); });
  if (Array.isArray(opts.transiting)) opts.transiting.forEach((pl) => { if (typeof pl === 'string' && pl.trim()) p.append('transiting', pl.trim()); });
  if (Array.isArray(opts.natal)) opts.natal.forEach((pl) => { if (typeof pl === 'string' && pl.trim()) p.append('natal', pl.trim()); });
  if (Array.isArray(opts.aspects)) opts.aspects.forEach((a) => { if (typeof a === 'string' && a.trim()) p.append('aspect', a.trim()); });
  if (opts.pdStart) p.set('pd_start', opts.pdStart);
  if (opts.pdEnd) p.set('pd_end', opts.pdEnd);
  if (opts.progStart) p.set('prog_start', opts.progStart);
  if (opts.progEnd) p.set('prog_end', opts.progEnd);
  if (opts.saStart) p.set('sa_start', opts.saStart);
  if (opts.saEnd) p.set('sa_end', opts.saEnd);
  if (opts.sigBeta != null) p.set('sig_beta', opts.sigBeta ? '1' : '0');
  return p.toString();
}

async function buildStreamUrlWithTicket(pathWithQuery, { suppressErrors = false } = {}) {
  const relativePath = String(pathWithQuery || '');
  if (!relativePath.startsWith('/')) {
    if (suppressErrors) return null;
    throw new Error('Invalid stream path');
  }
  if (suppressErrors) {
    const token = await LicenseTokenProvider.getToken({ forceRefresh: true }).catch(() => null);
    if (!token) {
      return null;
    }
  }
  try {
    const res = await request('/api/astro-clock/stream-ticket', {
      method: 'POST',
      body: JSON.stringify({ path: relativePath }),
    });
    const ticket = typeof res?.ticket === 'string' ? res.ticket : '';
    if (!ticket) {
      if (suppressErrors) return null;
      throw new Error('Stream ticket was not issued');
    }
    const joiner = relativePath.includes('?') ? '&' : '?';
    return `${getApiBaseUrl()}${relativePath}${joiner}stream_ticket=${encodeURIComponent(ticket)}`;
  } catch (error) {
    if (suppressErrors) return null;
    throw error;
  }
}

export const AstroClockAPI = {
  getCurrent: () => request('/api/astro-clock/current'),
  getTransits: (opts={}) => {
    const params = new URLSearchParams();
    if (opts.natalSnapId) params.set('natal_snap_id', opts.natalSnapId);
    if (opts.natalDatetime) params.set('natal_datetime', opts.natalDatetime);
    if (opts.natalLocation) params.set('natal_location', opts.natalLocation);
    if (opts.natalTimezone) params.set('natal_timezone', opts.natalTimezone);
    if (opts.houseSystem) params.set('house_system_code', opts.houseSystem);
    if (opts.transitDatetime) params.set('transit_datetime', opts.transitDatetime);
    if (opts.includeModern) params.set('include_modern', '1');
    if (opts.includeNatalModern) params.set('include_natal_modern', '1');
    if (opts.includeCusps) params.set('include_cusps', '1');
    if (opts.includeAntiscia) params.set('include_antiscia', '1');
    if (opts.includeLots) params.set('include_lots', '1');
    if (Array.isArray(opts.sensitiveHouses)) opts.sensitiveHouses.forEach(h => { const v = Number(h); if (!Number.isNaN(v)) params.append('sensitive_house', String(v)); });
    if (Array.isArray(opts.sensitivePlanets)) opts.sensitivePlanets.forEach(p => { if (typeof p === 'string' && p.trim()) params.append('sensitive_planet', p.trim()); });
    if (Array.isArray(opts.focusHouses)) opts.focusHouses.forEach(h => { const v = Number(h); if (!Number.isNaN(v)) params.append('focus_house', String(v)); });
    if (Array.isArray(opts.focusPlanets)) opts.focusPlanets.forEach(p => { if (typeof p === 'string' && p.trim()) params.append('focus_planet', p.trim()); });
    if (Array.isArray(opts.transiting)) opts.transiting.forEach(p => { if (typeof p === 'string' && p.trim()) params.append('transiting', p.trim()); });
    if (Array.isArray(opts.natal)) opts.natal.forEach(p => { if (typeof p === 'string' && p.trim()) params.append('natal', p.trim()); });
    if (Array.isArray(opts.aspects)) opts.aspects.forEach(a => { if (typeof a === 'string' && a.trim()) params.append('aspect', a.trim()); });
    // no natal significance toggle
    const q = params.toString();
    return request(`/api/astro-clock/transits${q ? `?${q}` : ''}`);
  },
  getTransitsWindow: (opts={}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', opts.natalSnapId);
    if (opts.natalDatetime) p.set('natal_datetime', opts.natalDatetime);
    if (opts.natalLocation) p.set('natal_location', opts.natalLocation);
    if (opts.natalTimezone) p.set('natal_timezone', opts.natalTimezone);
    if (opts.houseSystem) p.set('house_system_code', opts.houseSystem);
    if (opts.start) p.set('start', opts.start);
    if (opts.end) p.set('end', opts.end);
    if (opts.center) p.set('center', opts.center);
    if (opts.rangeHours != null) p.set('range_hours', String(opts.rangeHours));
    if (opts.stepMinutes != null) p.set('step_minutes', String(opts.stepMinutes));
    if (opts.includeModern) p.set('include_modern', '1');
    if (opts.includeNatalModern) p.set('include_natal_modern', '1');
    if (opts.includeCusps) p.set('include_cusps', '1');
    if (opts.includeAntiscia) p.set('include_antiscia', '1');
    if (opts.includeLots) p.set('include_lots', '1');
    if (Array.isArray(opts.sensitiveHouses)) opts.sensitiveHouses.forEach(h => { const v = Number(h); if (!Number.isNaN(v)) p.append('sensitive_house', String(v)); });
    if (Array.isArray(opts.sensitivePlanets)) opts.sensitivePlanets.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('sensitive_planet', pl.trim()); });
    if (Array.isArray(opts.focusHouses)) opts.focusHouses.forEach(h => { const v = Number(h); if (!Number.isNaN(v)) p.append('focus_house', String(v)); });
    if (Array.isArray(opts.focusPlanets)) opts.focusPlanets.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('focus_planet', pl.trim()); });
    // Context windows (optional)
    if (opts.pdStart) p.set('pd_start', opts.pdStart);
    if (opts.pdEnd) p.set('pd_end', opts.pdEnd);
    if (opts.progStart) p.set('prog_start', opts.progStart);
    if (opts.progEnd) p.set('prog_end', opts.progEnd);
    if (opts.saStart) p.set('sa_start', opts.saStart);
    if (opts.saEnd) p.set('sa_end', opts.saEnd);
    if (Array.isArray(opts.transiting)) opts.transiting.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('transiting', pl.trim()); });
    if (Array.isArray(opts.natal)) opts.natal.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('natal', pl.trim()); });
    if (Array.isArray(opts.aspects)) opts.aspects.forEach(a => { if (typeof a === 'string' && a.trim()) p.append('aspect', a.trim()); });
    const q = p.toString();
    return request(`/api/astro-clock/transits/window${q ? `?${q}` : ''}`);
  },
  createTransitsWindowStream: async (opts={}) => {
    try {
      const p = new URLSearchParams();
      if (opts.natalSnapId) p.set('natal_snap_id', opts.natalSnapId);
      if (opts.natalDatetime) p.set('natal_datetime', opts.natalDatetime);
      if (opts.natalLocation) p.set('natal_location', opts.natalLocation);
      if (opts.natalTimezone) p.set('natal_timezone', opts.natalTimezone);
      if (opts.houseSystem) p.set('house_system_code', opts.houseSystem);
      if (opts.start) p.set('start', opts.start);
      if (opts.end) p.set('end', opts.end);
      if (opts.center) p.set('center', opts.center);
      if (opts.rangeHours != null) p.set('range_hours', String(opts.rangeHours));
      if (opts.stepMinutes != null) p.set('step_minutes', String(opts.stepMinutes));
      if (opts.includeModern) p.set('include_modern', '1');
      if (opts.includeNatalModern) p.set('include_natal_modern', '1');
      if (opts.includeCusps) p.set('include_cusps', '1');
      if (opts.includeAntiscia) p.set('include_antiscia', '1');
      if (opts.includeLots) p.set('include_lots', '1');
      if (Array.isArray(opts.sensitiveHouses)) opts.sensitiveHouses.forEach(h => { const v = Number(h); if (!Number.isNaN(v)) p.append('sensitive_house', String(v)); });
      if (Array.isArray(opts.sensitivePlanets)) opts.sensitivePlanets.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('sensitive_planet', pl.trim()); });
      if (Array.isArray(opts.focusHouses)) opts.focusHouses.forEach(h => { const v = Number(h); if (!Number.isNaN(v)) p.append('focus_house', String(v)); });
      if (Array.isArray(opts.focusPlanets)) opts.focusPlanets.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('focus_planet', pl.trim()); });
      if (opts.pdStart) p.set('pd_start', opts.pdStart);
      if (opts.pdEnd) p.set('pd_end', opts.pdEnd);
      if (opts.progStart) p.set('prog_start', opts.progStart);
      if (opts.progEnd) p.set('prog_end', opts.progEnd);
      if (opts.saStart) p.set('sa_start', opts.saStart);
      if (opts.saEnd) p.set('sa_end', opts.saEnd);
      if (Array.isArray(opts.transiting)) opts.transiting.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('transiting', pl.trim()); });
      if (Array.isArray(opts.natal)) opts.natal.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('natal', pl.trim()); });
      if (Array.isArray(opts.aspects)) opts.aspects.forEach(a => { if (typeof a === 'string' && a.trim()) p.append('aspect', a.trim()); });
      const q = p.toString();
      const url = await buildStreamUrlWithTicket(`/api/astro-clock/transits/window/stream${q ? `?${q}` : ''}`, { suppressErrors: true });
      if (!url) return null;
      return new EventSource(url);
    } catch (_) { return null; }
  },
  getPredictions: (opts={}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', opts.natalSnapId);
    if (opts.natalDatetime) p.set('natal_datetime', opts.natalDatetime);
    if (opts.natalLocation) p.set('natal_location', opts.natalLocation);
    if (opts.natalTimezone) p.set('natal_timezone', opts.natalTimezone);
    if (opts.houseSystem) p.set('house_system_code', opts.houseSystem);
    if (opts.start) p.set('start', opts.start);
    if (opts.end) p.set('end', opts.end);
    if (opts.stepMinutes != null) p.set('step_minutes', String(opts.stepMinutes));
    if (opts.location) p.set('location', opts.location);
    if (opts.timezone) p.set('timezone', opts.timezone);
    if (opts.limit != null) p.set('limit', String(opts.limit));
    if (opts.includeSeries) p.set('include_series', '1');
    if (opts.includeModern) p.set('include_modern', '1');
    if (opts.includeNatalModern) p.set('include_natal_modern', '1');
    if (opts.includeCusps) p.set('include_cusps', '1');
    if (opts.includeAntiscia) p.set('include_antiscia', '1');
    if (opts.includeLots) p.set('include_lots', '1');
    if (Array.isArray(opts.focusHouses)) opts.focusHouses.forEach(h => { const v = Number(h); if (!Number.isNaN(v)) p.append('focus_house', String(v)); });
    if (Array.isArray(opts.focusPlanets)) opts.focusPlanets.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('focus_planet', pl.trim()); });
    if (Array.isArray(opts.sensitiveHouses)) opts.sensitiveHouses.forEach(h => { const v = Number(h); if (!Number.isNaN(v)) p.append('sensitive_house', String(v)); });
    if (Array.isArray(opts.sensitivePlanets)) opts.sensitivePlanets.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('sensitive_planet', pl.trim()); });
    if (Array.isArray(opts.transiting)) opts.transiting.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('transiting', pl.trim()); });
    if (Array.isArray(opts.natal)) opts.natal.forEach(pl => { if (typeof pl === 'string' && pl.trim()) p.append('natal', pl.trim()); });
    if (Array.isArray(opts.aspects)) opts.aspects.forEach(a => { if (typeof a === 'string' && a.trim()) p.append('aspect', a.trim()); });
    if (opts.pdStart) p.set('pd_start', opts.pdStart);
    if (opts.pdEnd) p.set('pd_end', opts.pdEnd);
    if (opts.progStart) p.set('prog_start', opts.progStart);
    if (opts.progEnd) p.set('prog_end', opts.progEnd);
    if (opts.saStart) p.set('sa_start', opts.saStart);
    if (opts.saEnd) p.set('sa_end', opts.saEnd);
    if (opts.sigBeta) p.set('sig_beta', opts.sigBeta ? '1' : '0');
    const q = p.toString();
    return request(`/api/astro-clock/predictor${q ? `?${q}` : ''}`, {
      timeoutMs: 90000,
    });
  },
  exportTransits: (opts={}) => {
    const q = buildTransitsExportQuery(opts);
    return request(`/api/astro-clock/transits/export${q ? `?${q}` : ''}`, {
      responseType: 'blob',
      timeoutMs: 90000,
    });
  },
  exportTransitsWindow: (opts={}) => {
    const q = buildTransitsWindowExportQuery(opts);
    return request(`/api/astro-clock/transits/window/export${q ? `?${q}` : ''}`, {
      responseType: 'blob',
      timeoutMs: 90000,
    });
  },
  getDashboard: (opts={}) => {
    const signal = opts?.signal;
    const params = new URLSearchParams();
    if (opts.includeModern) params.set('include_modern', '1');
    if (opts.morin) params.set('morin', '1');
    if (Array.isArray(opts.specialDegrees) && opts.specialDegrees.length) {
      // use repeated params to preserve spaces in tokens like '25 Leo'
      for (const tok of opts.specialDegrees) {
        if (typeof tok === 'string' && tok.trim()) {
          params.append('special_degree', tok);
        }
      }
    }
    appendClockContext(params, opts);
    const q = params.toString();
    return request(`/api/astro-clock/dashboard${q ? `?${q}` : ''}`, {
      signal,
      timeoutMs: ASTRO_CLOCK_CORE_TIMEOUT_MS,
    });
  },
  getPlanetaryHours: (opts) => {
    let query = '';
    let signal;
    if (typeof opts === 'string') {
      query = `?date=${encodeURIComponent(opts)}`;
    } else if (opts && typeof opts === 'object') {
      signal = opts.signal;
      const params = new URLSearchParams();
      if (opts.date) params.set('date', opts.date);
      if (opts.datetime) params.set('datetime', opts.datetime);
      appendClockContext(params, opts);
      const qs = params.toString();
      if (qs) query = `?${qs}`;
    }
    return request(`/api/astro-clock/planetary-hours${query}`, {
      signal,
      timeoutMs: ASTRO_CLOCK_CORE_TIMEOUT_MS,
    });
  },
  createSnap: ({ label, includeModern, specialDegrees } = {}) => request('/api/astro-clock/snap', {
    method: 'POST',
    body: JSON.stringify({ label, include_modern: !!includeModern, special_degrees: Array.isArray(specialDegrees) ? specialDegrees : undefined })
  }),
  listSnaps: () => request('/api/astro-clock/snaps'),
  getSnap: (id) => request(`/api/astro-clock/snaps/${encodeURIComponent(id)}`),
  deleteSnap: (id) => request(`/api/astro-clock/snaps/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  getAstrocartographyMap: (opts = {}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', String(opts.natalSnapId));
    if (opts.natalDatetime) p.set('natal_datetime', String(opts.natalDatetime));
    if (opts.natalLocation) p.set('natal_location', String(opts.natalLocation));
    if (opts.natalTimezone) p.set('natal_timezone', String(opts.natalTimezone));
    if (opts.houseSystem) p.set('house_system_code', String(opts.houseSystem));
    if (opts.transitDatetime) p.set('transit_datetime', String(opts.transitDatetime));
    if (opts.transitLocation) p.set('transit_location', String(opts.transitLocation));
    if (opts.transitTimezone) p.set('transit_timezone', String(opts.transitTimezone));
    if (Array.isArray(opts.bodies)) {
      opts.bodies.forEach((body) => {
        if (typeof body === 'string' && body.trim()) p.append('body', body.trim());
      });
    }
    if (Array.isArray(opts.angles)) {
      opts.angles.forEach((angle) => {
        if (typeof angle === 'string' && angle.trim()) p.append('angle', angle.trim().toUpperCase());
      });
    }
    const q = p.toString();
    return request(`/api/astro-clock/astrocartography/map${q ? `?${q}` : ''}`);
  },
  getAstrocartographyLocation: (opts = {}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', String(opts.natalSnapId));
    if (opts.natalDatetime) p.set('natal_datetime', String(opts.natalDatetime));
    if (opts.natalLocation) p.set('natal_location', String(opts.natalLocation));
    if (opts.natalTimezone) p.set('natal_timezone', String(opts.natalTimezone));
    if (opts.houseSystem) p.set('house_system_code', String(opts.houseSystem));
    if (opts.goalId) p.set('goal_id', String(opts.goalId));
    if (opts.transitDatetime) p.set('transit_datetime', String(opts.transitDatetime));
    if (opts.transitLocation) p.set('transit_location', String(opts.transitLocation));
    if (opts.transitTimezone) p.set('transit_timezone', String(opts.transitTimezone));
    if (opts.targetLocation) p.set('target_location', String(opts.targetLocation));
    if (Array.isArray(opts.bodies)) {
      opts.bodies.forEach((body) => {
        if (typeof body === 'string' && body.trim()) p.append('body', body.trim());
      });
    }
    if (Array.isArray(opts.angles)) {
      opts.angles.forEach((angle) => {
        if (typeof angle === 'string' && angle.trim()) p.append('angle', angle.trim().toUpperCase());
      });
    }
    const q = p.toString();
    return request(`/api/astro-clock/astrocartography/location${q ? `?${q}` : ''}`);
  },
  listAstrocartographyGoals: () => request('/api/astro-clock/astrocartography/goals'),
  searchAstrocartographyAtlas: (opts = {}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', String(opts.natalSnapId));
    if (opts.natalDatetime) p.set('natal_datetime', String(opts.natalDatetime));
    if (opts.natalLocation) p.set('natal_location', String(opts.natalLocation));
    if (opts.natalTimezone) p.set('natal_timezone', String(opts.natalTimezone));
    if (opts.houseSystem) p.set('house_system_code', String(opts.houseSystem));
    if (opts.goalId) p.set('goal_id', String(opts.goalId));
    if (opts.query) p.set('query', String(opts.query));
    if (opts.countryCode) p.set('country_code', String(opts.countryCode).toUpperCase());
    if (opts.continentCode) p.set('continent_code', String(opts.continentCode).toUpperCase());
    if (opts.resolution) p.set('resolution', String(opts.resolution));
    if (opts.limit != null) p.set('limit', String(opts.limit));
    if (opts.transitDatetime) p.set('transit_datetime', String(opts.transitDatetime));
    if (opts.transitLocation) p.set('transit_location', String(opts.transitLocation));
    if (opts.transitTimezone) p.set('transit_timezone', String(opts.transitTimezone));
    if (Array.isArray(opts.bodies)) {
      opts.bodies.forEach((body) => {
        if (typeof body === 'string' && body.trim()) p.append('body', body.trim());
      });
    }
    if (Array.isArray(opts.angles)) {
      opts.angles.forEach((angle) => {
        if (typeof angle === 'string' && angle.trim()) p.append('angle', angle.trim().toUpperCase());
      });
    }
    const q = p.toString();
    return request(`/api/astro-clock/astrocartography/atlas-search${q ? `?${q}` : ''}`, {
      timeoutMs: 300000,
    });
  },
  startAstrocartographyAtlasSearch: (opts = {}) => request('/api/astro-clock/astrocartography/atlas-search/start', {
    method: 'POST',
    body: JSON.stringify({
      natal_snap_id: opts.natalSnapId || '',
      natal_datetime: opts.natalDatetime || '',
      natal_location: opts.natalLocation || '',
      natal_timezone: opts.natalTimezone || '',
      house_system_code: opts.houseSystem || '',
      goal_id: opts.goalId || '',
      query: opts.query || '',
      country_code: opts.countryCode || '',
      continent_code: opts.continentCode || '',
      resolution: opts.resolution || '',
      limit: opts.limit,
      transit_datetime: opts.transitDatetime || '',
      transit_location: opts.transitLocation || '',
      transit_timezone: opts.transitTimezone || '',
      body: Array.isArray(opts.bodies) ? opts.bodies : [],
      angle: Array.isArray(opts.angles) ? opts.angles : [],
    }),
  }),
  getAstrocartographyAtlasSearchProgress: (sessionId) => {
    const q = new URLSearchParams({ session_id: String(sessionId || '') }).toString();
    return request(`/api/astro-clock/astrocartography/atlas-search/progress?${q}`);
  },
  getAstrocartographyAtlasSearchResult: (sessionId) => {
    const q = new URLSearchParams({ session_id: String(sessionId || '') }).toString();
    return request(`/api/astro-clock/astrocartography/atlas-search/result?${q}`);
  },
  cancelAstrocartographyAtlasSearch: (sessionId) => request('/api/astro-clock/astrocartography/atlas-search/cancel', {
    method: 'POST',
    body: JSON.stringify({
      session_id: String(sessionId || ''),
    }),
    timeoutMs: 15000,
  }),
  compareAstrocartographyTargets: (opts = {}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', String(opts.natalSnapId));
    if (opts.natalDatetime) p.set('natal_datetime', String(opts.natalDatetime));
    if (opts.natalLocation) p.set('natal_location', String(opts.natalLocation));
    if (opts.natalTimezone) p.set('natal_timezone', String(opts.natalTimezone));
    if (opts.houseSystem) p.set('house_system_code', String(opts.houseSystem));
    if (opts.goalId) p.set('goal_id', String(opts.goalId));
    if (opts.transitDatetime) p.set('transit_datetime', String(opts.transitDatetime));
    if (opts.transitLocation) p.set('transit_location', String(opts.transitLocation));
    if (opts.transitTimezone) p.set('transit_timezone', String(opts.transitTimezone));
    if (Array.isArray(opts.targetLocations)) {
      opts.targetLocations.forEach((target) => {
        if (typeof target === 'string' && target.trim()) p.append('target_location', target.trim());
      });
    }
    if (Array.isArray(opts.bodies)) {
      opts.bodies.forEach((body) => {
        if (typeof body === 'string' && body.trim()) p.append('body', body.trim());
      });
    }
    if (Array.isArray(opts.angles)) {
      opts.angles.forEach((angle) => {
        if (typeof angle === 'string' && angle.trim()) p.append('angle', angle.trim().toUpperCase());
      });
    }
    const q = p.toString();
    return request(`/api/astro-clock/astrocartography/compare${q ? `?${q}` : ''}`);
  },
  listMundaneChartTypes: () => request('/api/astro-clock/mundane/chart-types'),
  resolveMundaneContext: (opts = {}) => {
    const p = new URLSearchParams();
    appendMundaneParams(p, opts);
    const q = p.toString();
    return request(`/api/astro-clock/mundane/context/resolve${q ? `?${q}` : ''}`);
  },
  analyzeMundane: (opts = {}) => {
    const p = new URLSearchParams();
    appendMundaneParams(p, opts);
    const q = p.toString();
    return request(`/api/astro-clock/mundane/analyze${q ? `?${q}` : ''}`);
  },
  listWeatherCatalog: () => request('/api/astro-clock/weather/catalog'),
  resolveWeatherContext: (opts = {}) => {
    const p = new URLSearchParams();
    appendWeatherParams(p, opts);
    const q = p.toString();
    return request(`/api/astro-clock/weather/context/resolve${q ? `?${q}` : ''}`);
  },
  analyzeWeather: (opts = {}) => {
    const p = new URLSearchParams();
    appendWeatherParams(p, opts);
    const q = p.toString();
    return request(`/api/astro-clock/weather/analyze${q ? `?${q}` : ''}`);
  },
  listWeatherScanCatalog: () => request('/api/astro-clock/weather/scan/catalog'),
  runWeatherScan: (opts = {}) => {
    const p = new URLSearchParams();
    appendWeatherScanParams(p, opts);
    const q = p.toString();
    return request(`/api/astro-clock/weather/scan/run${q ? `?${q}` : ''}`, {
      timeoutMs: 300000,
    });
  },
  startWeatherScan: (opts = {}) =>
    request('/api/astro-clock/weather/scan/start', {
      method: 'POST',
      body: JSON.stringify({
        family_id: opts.familyId,
        forecast_datetime: opts.forecastDatetime,
        location: opts.location,
        timezone: opts.timezone,
        latitude: opts.latitude,
        longitude: opts.longitude,
        house_system_code: opts.houseSystem,
        source_preference: opts.sourcePreference,
        scan_scope: opts.scanScope,
        region_id: opts.regionId,
        resolution: opts.resolution,
        candidate_limit: opts.candidateLimit,
        top_k: opts.topK,
        start_datetime: opts.startDatetime,
        end_datetime: opts.endDatetime,
        time_step_hours: opts.timeStepHours,
      }),
      timeoutMs: 30000,
    }),
  getWeatherScanProgress: (sessionId) => {
    const p = new URLSearchParams();
    p.set('session_id', String(sessionId || ''));
    return request(`/api/astro-clock/weather/scan/progress?${p.toString()}`);
  },
  getWeatherScanResult: (sessionId) => {
    const p = new URLSearchParams();
    p.set('session_id', String(sessionId || ''));
    return request(`/api/astro-clock/weather/scan/result?${p.toString()}`);
  },
  listMundaneScanCatalog: () => request('/api/astro-clock/mundane/scan/regions'),
  runMundaneScan: (opts = {}) => {
    const p = new URLSearchParams();
    appendMundaneParams(p, opts);
    if (opts.scanMode) p.set('scan_mode', String(opts.scanMode));
    if (opts.regionId) p.set('region_id', String(opts.regionId));
    if (opts.resolution) p.set('resolution', String(opts.resolution));
    if (opts.topK != null) p.set('top_k', String(opts.topK));
    if (opts.minimumScore != null) p.set('minimum_score', String(opts.minimumScore));
    if (opts.candidateLimit != null) p.set('candidate_limit', String(opts.candidateLimit));
    if (opts.fixedDatetime) p.set('fixed_datetime', String(opts.fixedDatetime));
    if (opts.startDatetime) p.set('start_datetime', String(opts.startDatetime));
    if (opts.endDatetime) p.set('end_datetime', String(opts.endDatetime));
    if (opts.timeStepHours != null) p.set('time_step_hours', String(opts.timeStepHours));
    if (opts.includeSeries) p.set('include_series', '1');
    const q = p.toString();
    return request(`/api/astro-clock/mundane/scan/run${q ? `?${q}` : ''}`, {
      timeoutMs: 300000,
    });
  },
  startMundaneScan: (opts = {}) => request('/api/astro-clock/mundane/scan/start', {
    method: 'POST',
    timeoutMs: 30000,
    body: JSON.stringify({
      chart_type: opts.chartType || '',
      domain: opts.domain || '',
      polity_id: opts.polityId || '',
      custom_polity_label: opts.customPolityLabel || '',
      national_chart_id: opts.nationalChartId || '',
      custom_chart_label: opts.customChartLabel || '',
      custom_chart_datetime: opts.customChartDatetime || '',
      custom_chart_location: opts.customChartLocation || '',
      custom_chart_timezone: opts.customChartTimezone || '',
      location_context_type: opts.locationContextType || '',
      reference_location: opts.referenceLocation || '',
      reference_latitude: opts.referenceLatitude,
      reference_longitude: opts.referenceLongitude,
      event_datetime: opts.eventDatetime || '',
      event_location: opts.eventLocation || '',
      event_timezone: opts.eventTimezone || '',
      visibility_scope: opts.visibilityScope || '',
      source_preference: opts.sourcePreference || '',
      scan_mode: opts.scanMode || '',
      region_id: opts.regionId || '',
      resolution: opts.resolution || '',
      top_k: opts.topK,
      minimum_score: opts.minimumScore,
      candidate_limit: opts.candidateLimit,
      fixed_datetime: opts.fixedDatetime || '',
      start_datetime: opts.startDatetime || '',
      end_datetime: opts.endDatetime || '',
      time_step_hours: opts.timeStepHours,
      include_series: opts.includeSeries ? true : false,
    }),
  }),
  getMundaneScanProgress: (sessionId) => {
    const q = new URLSearchParams({ session_id: String(sessionId || '') }).toString();
    return request(`/api/astro-clock/mundane/scan/progress?${q}`);
  },
  getMundaneScanResult: (sessionId) => {
    const q = new URLSearchParams({ session_id: String(sessionId || '') }).toString();
    return request(`/api/astro-clock/mundane/scan/result?${q}`, {
      timeoutMs: 300000,
    });
  },
  setMode: ({ mode, datetime, location, timezone, houseSystem, signal }) => request('/api/astro-clock/mode', {
    method: 'POST',
    signal,
    timeoutMs: ASTRO_CLOCK_CORE_TIMEOUT_MS,
    body: JSON.stringify({ mode, datetime, location, timezone, house_system: houseSystem, house_system_code: houseSystem })
  }),
  setLocation: (location) => request('/api/astro-clock/location', { method: 'POST', body: JSON.stringify({ location }) }),
  createStream: async (opts={}) => {
    try {
      const params = [];
      if (opts.includeModern) params.push('include_modern=1');
      const q = params.length ? `?${params.join('&')}` : '';
      const url = await buildStreamUrlWithTicket(`/api/astro-clock/stream${q}`, { suppressErrors: true });
      if (!url) return null;
      return new EventSource(url);
    } catch (_) { return null; }
  },
    getForensic: (opts = {}) => {
      const params = new URLSearchParams();
      if (opts.mode) params.set('mode', opts.mode);
      if (opts.datetime) params.set('datetime', opts.datetime);
      if (opts.location) params.set('location', opts.location);
      if (opts.timezone) params.set('timezone', opts.timezone);
      if (opts.houseSystem) params.set('house_system_code', String(opts.houseSystem));
      if (opts.caseType) params.set('case_type', String(opts.caseType));
      if (opts.abduction) params.set('abduction', opts.abduction ? '1' : '0');
      if (opts.origin && typeof opts.origin === 'string') params.set('origin', opts.origin);
    if (opts.origin && typeof opts.origin === 'object') {
      const { lat, lon } = opts.origin || {};
      if (lat != null && lon != null) params.set('origin', `${lat},${lon}`);
    }
    if (opts.line_zones != null) params.set('line_zones', opts.line_zones ? '1' : '0');
    if (opts.corridor_deg != null) params.set('corridor_deg', String(opts.corridor_deg));
    const qs = params.toString();
    return request(`/api/astro-clock/forensic${qs ? `?${qs}` : ''}`);
  },
  getReceptions: () => request('/api/astro-clock/receptions')
  ,
  validateElection: (opts={}) => {
    const p = new URLSearchParams();
    appendElectionParams(p, opts);
    const q = p.toString();
    return request(`/api/astro-clock/election/validate${q ? `?${q}` : ''}`);
  },
  electionStream: async (opts={}) => {
    const p = new URLSearchParams();
    appendElectionParams(p, opts);
    const q = p.toString();
    const url = await buildStreamUrlWithTicket(`/api/astro-clock/election/suggest/stream${q ? `?${q}` : ''}`);
    return new EventSource(url);
  }
  ,
  getCompass: (opts={}) => {
    const params = [];
    if (opts.includeModern) params.push('include_modern=1');
    const q = params.length ? `?${params.join('&')}` : '';
    return request(`/api/astro-clock/compass${q}`);
  }
  ,
  resolveTimezone: (location) => request('/api/get-timezone', { method: 'POST', body: JSON.stringify({ location }) })
  ,
  getAutoContext: (opts={}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', opts.natalSnapId);
    if (opts.natalDatetime) p.set('natal_datetime', opts.natalDatetime);
    if (opts.natalLocation) p.set('natal_location', opts.natalLocation);
    if (opts.natalTimezone) p.set('natal_timezone', opts.natalTimezone);
    if (opts.houseSystem) p.set('house_system_code', opts.houseSystem);
    if (opts.year) p.set('year', String(opts.year));
    // Anchor period for PD/SR/Progressions derivation
    if (opts.anchorStart) p.set('anchor_start', opts.anchorStart);
    if (opts.anchorEnd) p.set('anchor_end', opts.anchorEnd);
    if (opts.anchorCenter) p.set('anchor_center', opts.anchorCenter);
    const q = p.toString();
    return request(`/api/astro-clock/context/auto${q ? `?${q}` : ''}`);
  }
  ,
  getTraitProfile: (opts={}) => {
    const params = new URLSearchParams();
    if (Array.isArray(opts.specialDegrees) && opts.specialDegrees.length) {
      for (const tok of opts.specialDegrees) {
        if (typeof tok === 'string' && tok.trim()) params.append('special_degree', tok);
      }
    }
    appendClockContext(params, opts);
    const q = params.toString();
    return request(`/api/astro-clock/traits/profile${q ? `?${q}` : ''}`);
  }
  ,
  getSynastry: (opts={}) => {
    const params = new URLSearchParams();
    if (opts.snapAId) params.set('snap_a_id', String(opts.snapAId));
    if (opts.snapBId) params.set('snap_b_id', String(opts.snapBId));
    if (opts.engineId) params.set('engine_id', String(opts.engineId));
    if (opts.profileA) params.set('profile_a', String(opts.profileA));
    if (opts.profileB) params.set('profile_b', String(opts.profileB));
    if (opts.houseSystem) params.set('house_system_code', String(opts.houseSystem));
    if (typeof opts.includeModern === 'boolean') params.set('include_modern', opts.includeModern ? '1' : '0');
    if (typeof opts.includeNodes === 'boolean') params.set('include_nodes', opts.includeNodes ? '1' : '0');
    if (typeof opts.includeChiron === 'boolean') params.set('include_chiron', opts.includeChiron ? '1' : '0');
    if (opts.orbProfile) params.set('orb_profile', String(opts.orbProfile));
    const q = params.toString();
    return request(`/api/astro-clock/synastry${q ? `?${q}` : ''}`, {
      timeoutMs: 300000,
      signal: opts.signal,
    });
  }
  ,
  researchAnalyze: (body={}) => request('/api/astro-clock/research/lotto/analyze', {
    method: 'POST',
    body: JSON.stringify(body)
  })
  ,
  researchCompileStart: (body={}) => request('/api/astro-clock/research/lotto/compile/start', {
    method: 'POST',
    body: JSON.stringify(body)
  })
  ,
  researchProgress: (sessionId) => {
    const q = new URLSearchParams({ session_id: String(sessionId||'') }).toString();
    return request(`/api/astro-clock/research/lotto/progress?${q}`);
  }
  ,
  researchStop: (sessionId) => request('/api/astro-clock/research/lotto/stop', {
    method: 'POST',
    body: JSON.stringify({ sessionId })
  })
  ,
  researchCompile: (body={}) => request('/api/astro-clock/research/lotto/compile', {
    method: 'POST',
    body: JSON.stringify(body)
  })
};
