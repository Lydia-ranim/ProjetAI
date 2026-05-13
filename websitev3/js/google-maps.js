/* LYHLYH Google Maps loader. Rendering only; routing stays in FastAPI. */

let googleMapsConfig = null;
let googleMapsReadyPromise = null;
let googleMapsAuthFailed = false;

window.gm_authFailure = function () {
  googleMapsAuthFailed = true;
  console.error(
    'LYHLYH: Google Maps authentication failed. Check API key restrictions, billing, and enabled APIs.'
  );
  const msg =
    'Google Maps authentication failed. Enable Maps JavaScript API, Places API, billing, and allow this localhost URL in Google Cloud.';
  if (typeof notif === 'function') notif('Google Maps', msg, 'error');
};

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      existing.addEventListener('load', resolve, { once: true });
      existing.addEventListener('error', reject, { once: true });
      return;
    }
    const s = document.createElement('script');
    s.src = src;
    s.async = true;
    s.defer = true;
    s.onload = resolve;
    s.onerror = reject;
    document.head.appendChild(s);
  });
}

async function initGoogleMapsPlatform() {
  if (googleMapsReadyPromise) return googleMapsReadyPromise;
  googleMapsReadyPromise = (async () => {
    googleMapsConfig = await fetchMapConfig();
    if (!googleMapsConfig || !googleMapsConfig.enabled || !googleMapsConfig.apiKey) {
      console.warn('LYHLYH: Google Maps key missing. Map rendering disabled.');
      return null;
    }

    const params = new URLSearchParams({
      key: googleMapsConfig.apiKey,
      libraries: (googleMapsConfig.libraries || ['places', 'geometry', 'marker']).join(','),
      language: googleMapsConfig.language || 'fr',
      region: googleMapsConfig.region || 'DZ',
      v: 'weekly',
    });
    await loadScript(`https://maps.googleapis.com/maps/api/js?${params.toString()}`);
    if (googleMapsAuthFailed || !window.google || !google.maps) {
      throw new Error('Google Maps failed to authenticate or initialize');
    }

    try {
      await loadScript('https://unpkg.com/@googlemaps/markerclusterer/dist/index.min.js');
    } catch (err) {
      console.warn('LYHLYH: marker clusterer unavailable', err);
    }
    return google.maps;
  })();
  return googleMapsReadyPromise;
}

function googleMapsBoundsLiteral() {
  return googleMapsConfig?.bounds || { south: 36.48, west: 2.75, north: 36.98, east: 3.55 };
}

function googleMapsCenterLiteral() {
  return googleMapsConfig?.center || { lat: 36.737, lng: 3.086 };
}
