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

const isBrowserDevelopmentRuntime = () => {
  if (typeof window === 'undefined') return false;
  if (window.IS_PACKAGED === false) return true;
  return Boolean(import.meta.env.DEV && !window.electronAPI);
};

const getBrowserDevelopmentLicenseToken = () => {
  if (!isBrowserDevelopmentRuntime()) return null;
  const configuredToken = import.meta.env.VITE_DEV_LICENSE_TOKEN;
  if (typeof configuredToken !== 'string') return null;
  return configuredToken.trim() || null;
};

export const AstroClockLicenseTokenProvider = (() => {
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
      if (isBrowserDevelopmentRuntime()) {
        // Browser dev should rely on the source backend's explicit dev-bypass mode,
        // or use the configured strict-license token when one is supplied.
        return storeToken(getBrowserDevelopmentLicenseToken());
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
  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, effectiveTimeoutMs);
  const relayAbort = () => controller.abort();
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener('abort', relayAbort, { once: true });
    }
  }

  const createAbortError = () => {
    const error = new Error('Request aborted');
    error.name = 'AbortError';
    return error;
  };
  const withCancellation = (promise) => {
    if (controller.signal.aborted) return Promise.reject(createAbortError());
    return new Promise((resolve, reject) => {
      const handleAbort = () => reject(createAbortError());
      controller.signal.addEventListener('abort', handleAbort, { once: true });
      Promise.resolve(promise).then(resolve, reject).finally(() => {
        controller.signal.removeEventListener('abort', handleAbort);
      });
    });
  };

  const send = async (token, allowRetry) => {
    const baseHeaders = { ...(rawOptions.headers || {}) };
    if (!skipLicense && token) {
      baseHeaders.Authorization = `Bearer ${token}`;
    }
    if (!(method === 'GET' || method === 'HEAD')) {
      if (!('Content-Type' in baseHeaders)) baseHeaders['Content-Type'] = 'application/json';
    }

    try {
      const res = await withCancellation(
        fetch(url, { ...rawOptions, headers: baseHeaders, signal: controller.signal })
      );
      if ((res.status === 402 || res.status === 403) && !skipLicense) {
        AstroClockLicenseTokenProvider.invalidate();
      }
      if (expectedType === 'blob') {
        if (!res.ok) {
          const errText = await withCancellation(res.text().catch(() => ''));
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
          blob: await withCancellation(res.blob()),
          contentType: res.headers.get('Content-Type') || res.headers.get('content-type') || '',
          filename: parseFilenameFromDisposition(
            res.headers.get('Content-Disposition') || res.headers.get('content-disposition') || ''
          ),
        };
      }

      const data = await withCancellation(res.json().catch(() => ({})));
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
      if (error?.authFailure) {
        const retryToken = await withCancellation(
          AstroClockLicenseTokenProvider.getToken().catch(() => null)
        );
        if (retryToken && retryToken !== token) {
          return send(retryToken, false);
        }
      }
      throw error;
    }
  };

  try {
    const initialToken = skipLicense
      ? null
      : await withCancellation(AstroClockLicenseTokenProvider.getToken().catch(() => null));
    return await send(initialToken, true);
  } catch (error) {
    if (timedOut && (controller.signal.aborted || error?.name === 'AbortError')) {
      throw new Error(`Request timed out after ${Math.round(effectiveTimeoutMs / 1000)}s`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
    if (externalSignal) {
      externalSignal.removeEventListener('abort', relayAbort);
    }
  }
}

const ASTRO_CLOCK_CORE_TIMEOUT_MS = 90000;

function appendClockContext(params, opts = {}) {
  if (!(params instanceof URLSearchParams)) return;
  if (opts.mode) params.set('mode', String(opts.mode));
  if (opts.datetime) params.set('datetime', String(opts.datetime));
  if (opts.location) params.set('location', String(opts.location));
  if (opts.timezone) params.set('timezone', String(opts.timezone));
  if (opts.houseSystem) params.set('house_system_code', String(opts.houseSystem));
  appendCoordinates(params, opts);
}

function appendCoordinates(params, opts = {}) {
  if (!(params instanceof URLSearchParams)) return;
  if (opts.latitude != null) params.set('latitude', String(opts.latitude));
  if (opts.longitude != null) params.set('longitude', String(opts.longitude));
}

function isFiniteCoordinate(value) {
  if (value == null || String(value).trim() === '') return false;
  return Number.isFinite(Number(value));
}

function normalizeAstrocartographyTarget(target, fallbackLocation = '') {
  const source = target && typeof target === 'object' ? target : {};
  const location = String(
    source.query
    || source.label
    || source.name
    || (typeof target === 'string' ? target : fallbackLocation)
    || ''
  ).trim();
  const explicitTargetId = String(
    source.candidate_id
    || source.target_id
    || source.catalog_id
    || ''
  ).trim();
  const rawGeonameId = String(source.geonameid || '').trim();
  const targetId = explicitTargetId || (
    rawGeonameId
      ? (rawGeonameId.startsWith('geonames:') ? rawGeonameId : `geonames:${rawGeonameId}`)
      : String(source.id || '').trim()
  );
  const latitude = source.latitude ?? source.lat;
  const longitude = source.longitude ?? source.lon ?? source.lng;
  const coordinateLabel = isFiniteCoordinate(latitude) && isFiniteCoordinate(longitude)
    ? `Coordinates ${Number(latitude).toFixed(6)}, ${Number(longitude).toFixed(6)}`
    : '';
  return {
    location: location || coordinateLabel,
    targetId,
    latitude,
    longitude,
  };
}

function appendAstrocartographyTarget(params, opts = {}) {
  if (!(params instanceof URLSearchParams)) return;
  const normalized = normalizeAstrocartographyTarget(
    opts.target,
    opts.targetLocation || opts.targetLabel || ''
  );
  const targetLatitude = opts.targetLatitude ?? normalized.latitude;
  const targetLongitude = opts.targetLongitude ?? normalized.longitude;
  const coordinateLabel = isFiniteCoordinate(targetLatitude) && isFiniteCoordinate(targetLongitude)
    ? `Coordinates ${Number(targetLatitude).toFixed(6)}, ${Number(targetLongitude).toFixed(6)}`
    : '';
  const targetLocation = normalized.location || String(opts.targetLocation || '').trim() || coordinateLabel;
  const targetId = normalized.targetId || String(opts.targetId || '').trim();
  if (targetLocation) params.set('target_location', targetLocation);
  if (targetId) params.set('target_id', targetId);
  if (isFiniteCoordinate(targetLatitude) && isFiniteCoordinate(targetLongitude)) {
    params.set('target_latitude', String(Number(targetLatitude)));
    params.set('target_longitude', String(Number(targetLongitude)));
  }
}

function appendAstrocartographyCompareTargets(params, opts = {}) {
  if (!(params instanceof URLSearchParams)) return;
  const rawTargets = Array.isArray(opts.targets) && opts.targets.length
    ? opts.targets
    : (Array.isArray(opts.targetLocations) ? opts.targetLocations : []);
  const targets = rawTargets.map((target) => normalizeAstrocartographyTarget(target));
  if (targets.some((target) => !target.location)) {
    throw new Error('Every astrocartography compare target must include a label/query or a complete coordinate pair.');
  }
  targets.forEach((target) => params.append('target_location', target.location));

  const anyHaveCoordinates = targets.some((target) => (
    target.latitude != null || target.longitude != null
  ));
  const allHaveCoordinates = targets.length > 0 && targets.every((target) => (
    isFiniteCoordinate(target.latitude) && isFiniteCoordinate(target.longitude)
  ));
  if (anyHaveCoordinates && !allHaveCoordinates) {
    throw new Error('Every astrocartography compare target must include both latitude and longitude when exact coordinates are used.');
  }
  if (allHaveCoordinates) {
    targets.forEach((target) => {
      params.append('target_latitude', String(Number(target.latitude)));
      params.append('target_longitude', String(Number(target.longitude)));
    });
  }

  const hasAnyTargetIds = targets.some((target) => Boolean(target.targetId));
  if (hasAnyTargetIds) {
    targets.forEach((target) => params.append('target_id', target.targetId || ''));
  }
}

function appendElectionParams(params, opts = {}) {
  if (!(params instanceof URLSearchParams)) return;
  if (opts.matter) params.set('matter', String(opts.matter));
  if (opts.start) params.set('start', String(opts.start));
  if (opts.end) params.set('end', String(opts.end));
  if (opts.location) params.set('location', String(opts.location));
  if (opts.timezone) params.set('timezone', String(opts.timezone));
  if (opts.houseSystem) params.set('house_system_code', String(opts.houseSystem));
  appendCoordinates(params, opts);
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
  if (opts.estateDirection) params.set('estate_direction', String(opts.estateDirection));
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
  if (opts.estateDisplayMode) params.set('estate_display_mode', String(opts.estateDisplayMode));
  if (opts.estateScope) params.set('estate_scope', String(opts.estateScope));
  if (opts.estateCurrentLineId) params.set('estate_current_line_id', String(opts.estateCurrentLineId));
  if (opts.estateLevelPercent != null) {
    params.set('estate_level_percent', String(opts.estateLevelPercent));
  }
  if (Array.isArray(opts.estateSelectedLineIds)) {
    opts.estateSelectedLineIds.forEach((lineId) => {
      if (lineId != null && String(lineId).trim() !== '') {
        params.append('estate_selected_line_id', String(lineId).trim());
      }
    });
  }
  if (opts.participantASnapId) params.set('participant_a_snap_id', String(opts.participantASnapId));
  if (opts.participantBSnapId) params.set('participant_b_snap_id', String(opts.participantBSnapId));
  if (opts.estateParticipantSnapId) params.set('estate_participant_snap_id', String(opts.estateParticipantSnapId));
  if (Array.isArray(opts.participantSnapIds)) {
    opts.participantSnapIds.forEach((snapId) => {
      if (snapId != null && String(snapId).trim() !== '') params.append('participant_snap_id', String(snapId).trim());
    });
  }
  if (opts.natalSnapId) params.set('natal_snap_id', String(opts.natalSnapId));
  if (opts.natalDatetime) params.set('natal_datetime', String(opts.natalDatetime));
  if (opts.natalLocation) params.set('natal_location', String(opts.natalLocation));
  if (opts.natalTimezone) params.set('natal_timezone', String(opts.natalTimezone));
  if (opts.considerMode) params.set('consider_mode', String(opts.considerMode));
  if (opts.levelPercent != null) params.set('level_percent', String(opts.levelPercent));
  if (opts.gender && String(opts.matter || '') === 'conception') params.set('gender', String(opts.gender));
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
  appendCoordinates(p, opts);
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
  appendCoordinates(p, opts);
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
    const token = await AstroClockLicenseTokenProvider.getToken({ forceRefresh: true }).catch(() => null);
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
  getCurrent: (opts = {}) => {
    const signal = opts?.signal;
    const params = new URLSearchParams();
    appendClockContext(params, opts);
    const q = params.toString();
    return request(`/api/astro-clock/current${q ? `?${q}` : ''}`, {
      signal,
      timeoutMs: ASTRO_CLOCK_CORE_TIMEOUT_MS,
    });
  },
  getTransits: (opts={}) => {
    const params = new URLSearchParams();
    if (opts.natalSnapId) params.set('natal_snap_id', opts.natalSnapId);
    if (opts.natalDatetime) params.set('natal_datetime', opts.natalDatetime);
    if (opts.natalLocation) params.set('natal_location', opts.natalLocation);
    if (opts.natalTimezone) params.set('natal_timezone', opts.natalTimezone);
    if (opts.houseSystem) params.set('house_system_code', opts.houseSystem);
    appendCoordinates(params, opts);
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
    appendCoordinates(p, opts);
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
      appendCoordinates(p, opts);
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
    appendCoordinates(p, opts);
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
  getDegreeHitPoints: (opts={}) => {
    const signal = opts?.signal;
    const params = new URLSearchParams();
    appendClockContext(params, opts);
    if (opts.sexCode != null && String(opts.sexCode).trim() !== '') {
      params.set('sex_code', String(opts.sexCode));
    }
    const q = params.toString();
    return request(`/api/astro-clock/points/degree-hits${q ? `?${q}` : ''}`, {
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
  createSnap: ({
    label,
    includeModern,
    specialDegrees,
    mode,
    datetime,
    location,
    timezone,
    latitude,
    longitude,
    houseSystem,
    certification,
    dashboard,
  } = {}) => request('/api/astro-clock/snap', {
    method: 'POST',
    timeoutMs: ASTRO_CLOCK_CORE_TIMEOUT_MS,
    body: JSON.stringify({
      label,
      include_modern: !!includeModern,
      special_degrees: Array.isArray(specialDegrees) ? specialDegrees : undefined,
      mode,
      datetime,
      location,
      timezone,
      latitude,
      longitude,
      house_system: houseSystem,
      house_system_code: houseSystem,
      certification,
      dashboard,
    })
  }),
  listSnaps: () => request('/api/astro-clock/snaps'),
  getSnap: (id, opts = {}) => request(`/api/astro-clock/snaps/${encodeURIComponent(id)}`, { signal: opts?.signal }),
  deleteSnap: (id) => request(`/api/astro-clock/snaps/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  getChineseAstrologyBazi: (opts = {}) => request('/api/astro-clock/chinese-astrology/bazi', {
    method: 'POST',
    timeoutMs: ASTRO_CLOCK_CORE_TIMEOUT_MS,
    body: JSON.stringify({
      snap_id: opts.snapId || opts.natalSnapId || '',
      birth: opts.birth || undefined,
      date: opts.date || undefined,
      time: opts.time || undefined,
      location: opts.location || undefined,
      timezone: opts.timezone || undefined,
      latitude: opts.latitude,
      longitude: opts.longitude,
      calculation_sex: opts.calculationSex || undefined,
      include_luck_pillars: !!opts.includeLuckPillars,
      use_true_solar_time: !!opts.useTrueSolarTime,
      day_boundary_rule: opts.dayBoundaryRule || undefined,
      hour_pillar_variant: opts.hourPillarVariant || undefined,
      luck_direction_rule: opts.luckDirectionRule || undefined,
    }),
  }),
  getChineseAstrologyCompatibility: (opts = {}) => request('/api/astro-clock/chinese-astrology/compatibility', {
    method: 'POST',
    timeoutMs: ASTRO_CLOCK_CORE_TIMEOUT_MS,
    body: JSON.stringify({
      primary_snap_id: opts.primarySnapId || opts.snapAId || opts.snapId || '',
      relationship_snap_id: opts.relationshipSnapId || opts.comparisonSnapId || opts.snapBId || '',
      relationship_context: opts.relationshipContext || opts.pairContext || opts.relationshipType || undefined,
      primary_calculation_sex: opts.primaryCalculationSex || undefined,
      relationship_calculation_sex: opts.relationshipCalculationSex || undefined,
      calculation_sex: opts.calculationSex || undefined,
      include_luck_pillars: opts.includeLuckPillars !== false,
      use_true_solar_time: !!opts.useTrueSolarTime,
      day_boundary_rule: opts.dayBoundaryRule || undefined,
      hour_pillar_variant: opts.hourPillarVariant || undefined,
      luck_direction_rule: opts.luckDirectionRule || undefined,
    }),
  }),
  getChineseAstrologyIChingOracle: (opts = {}) => request('/api/astro-clock/chinese-astrology/iching-oracle', {
    method: 'POST',
    timeoutMs: ASTRO_CLOCK_CORE_TIMEOUT_MS,
    body: JSON.stringify({
      question: opts.question || '',
      method: opts.method || opts.castingMethod || 'coins',
      lines: Array.isArray(opts.lines) ? opts.lines : undefined,
      coins: Array.isArray(opts.coins) ? opts.coins : undefined,
      seed: opts.seed,
      coin_value_scheme: opts.coinValueScheme || opts.coin_value_scheme || undefined,
    }),
  }),
  getAstrocartographyMap: (opts = {}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', String(opts.natalSnapId));
    if (opts.natalDatetime) p.set('natal_datetime', String(opts.natalDatetime));
    if (opts.natalLocation) p.set('natal_location', String(opts.natalLocation));
    if (opts.natalTimezone) p.set('natal_timezone', String(opts.natalTimezone));
    if (opts.houseSystem) p.set('house_system_code', String(opts.houseSystem));
    appendCoordinates(p, opts);
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
    return request(`/api/astro-clock/astrocartography/map${q ? `?${q}` : ''}`, {
      signal: opts.signal,
    });
  },
  getAstrocartographyLocation: (opts = {}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', String(opts.natalSnapId));
    if (opts.natalDatetime) p.set('natal_datetime', String(opts.natalDatetime));
    if (opts.natalLocation) p.set('natal_location', String(opts.natalLocation));
    if (opts.natalTimezone) p.set('natal_timezone', String(opts.natalTimezone));
    if (opts.houseSystem) p.set('house_system_code', String(opts.houseSystem));
    appendCoordinates(p, opts);
    if (opts.goalId) p.set('goal_id', String(opts.goalId));
    if (opts.transitDatetime) p.set('transit_datetime', String(opts.transitDatetime));
    if (opts.transitLocation) p.set('transit_location', String(opts.transitLocation));
    if (opts.transitTimezone) p.set('transit_timezone', String(opts.transitTimezone));
    appendAstrocartographyTarget(p, opts);
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
    return request(`/api/astro-clock/astrocartography/location${q ? `?${q}` : ''}`, {
      signal: opts.signal,
    });
  },
  listAstrocartographyGoals: (opts = {}) => request('/api/astro-clock/astrocartography/goals', {
    signal: opts.signal,
  }),
  searchAstrocartographyAtlas: (opts = {}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', String(opts.natalSnapId));
    if (opts.natalDatetime) p.set('natal_datetime', String(opts.natalDatetime));
    if (opts.natalLocation) p.set('natal_location', String(opts.natalLocation));
    if (opts.natalTimezone) p.set('natal_timezone', String(opts.natalTimezone));
    if (opts.houseSystem) p.set('house_system_code', String(opts.houseSystem));
    appendCoordinates(p, opts);
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
      signal: opts.signal,
    });
  },
  startAstrocartographyAtlasSearch: (opts = {}) => request('/api/astro-clock/astrocartography/atlas-search/start', {
    method: 'POST',
    body: JSON.stringify({
      natal_snap_id: opts.natalSnapId || '',
      natal_datetime: opts.natalDatetime || '',
      natal_location: opts.natalLocation || '',
      natal_timezone: opts.natalTimezone || '',
      latitude: opts.latitude,
      longitude: opts.longitude,
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
    signal: opts.signal,
  }),
  getAstrocartographyAtlasSearchProgress: (sessionId, opts = {}) => {
    const q = new URLSearchParams({ session_id: String(sessionId || '') }).toString();
    return request(`/api/astro-clock/astrocartography/atlas-search/progress?${q}`, {
      signal: opts.signal,
    });
  },
  getAstrocartographyAtlasSearchResult: (sessionId, opts = {}) => {
    const q = new URLSearchParams({ session_id: String(sessionId || '') }).toString();
    return request(`/api/astro-clock/astrocartography/atlas-search/result?${q}`, {
      signal: opts.signal,
    });
  },
  cancelAstrocartographyAtlasSearch: (sessionId, opts = {}) => request('/api/astro-clock/astrocartography/atlas-search/cancel', {
    method: 'POST',
    body: JSON.stringify({
      session_id: String(sessionId || ''),
    }),
    timeoutMs: 15000,
    signal: opts.signal,
  }),
  compareAstrocartographyTargets: (opts = {}) => {
    const p = new URLSearchParams();
    if (opts.natalSnapId) p.set('natal_snap_id', String(opts.natalSnapId));
    if (opts.natalDatetime) p.set('natal_datetime', String(opts.natalDatetime));
    if (opts.natalLocation) p.set('natal_location', String(opts.natalLocation));
    if (opts.natalTimezone) p.set('natal_timezone', String(opts.natalTimezone));
    if (opts.houseSystem) p.set('house_system_code', String(opts.houseSystem));
    appendCoordinates(p, opts);
    if (opts.goalId) p.set('goal_id', String(opts.goalId));
    if (opts.transitDatetime) p.set('transit_datetime', String(opts.transitDatetime));
    if (opts.transitLocation) p.set('transit_location', String(opts.transitLocation));
    if (opts.transitTimezone) p.set('transit_timezone', String(opts.transitTimezone));
    appendAstrocartographyCompareTargets(p, opts);
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
    return request(`/api/astro-clock/astrocartography/compare${q ? `?${q}` : ''}`, {
      signal: opts.signal,
    });
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
  setMode: ({ mode, datetime, location, timezone, latitude, longitude, houseSystem, signal }) => request('/api/astro-clock/mode', {
    method: 'POST',
    signal,
    timeoutMs: ASTRO_CLOCK_CORE_TIMEOUT_MS,
    body: JSON.stringify({
      mode,
      datetime,
      location,
      timezone,
      latitude,
      longitude,
      house_system: houseSystem,
      house_system_code: houseSystem,
    })
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
      appendClockContext(params, opts);
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
  getReceptions: (opts = {}) => {
    const params = new URLSearchParams();
    appendClockContext(params, opts);
    const qs = params.toString();
    return request(`/api/astro-clock/receptions${qs ? `?${qs}` : ''}`);
  },
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
    const params = new URLSearchParams();
    if (opts.includeModern) params.set('include_modern', '1');
    appendClockContext(params, opts);
    const q = params.toString();
    return request(`/api/astro-clock/compass${q ? `?${q}` : ''}`);
  }
  ,
  getDirectional3d: (opts={}) => {
    const params = new URLSearchParams();
    if (opts.includeModern) params.set('include_modern', '1');
    appendClockContext(params, opts);
    const q = params.toString();
    return request(`/api/astro-clock/directional-3d${q ? `?${q}` : ''}`);
  }
  ,
  rectifyBirthTime: (body={}) => request('/api/astro-clock/certification/rectify', {
    method: 'POST',
    body: JSON.stringify(body),
    timeoutMs: 300000,
  })
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
    appendCoordinates(p, opts);
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
  ,
  listResearchEvaluators: () => request('/api/astro-clock/research/evaluators')
  ,
  runResearchAnalysis: (body={}) => request('/api/astro-clock/research/analyze', {
    method: 'POST',
    timeoutMs: 300000,
    body: JSON.stringify(body)
  })
};
