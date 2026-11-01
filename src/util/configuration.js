// No secrets here: everything in this file ships to the browser.
// Tokens and passwords live on the Flask backend, which proxies these calls
// (see the "API proxy" section in postgress_connector.py).
//
// Leave VITE_API_BASE_URL unset when the frontend is served by Flask (same origin).
// In local dev, Vite forwards /api to Flask (see vite.config.js).
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';
const PROXY = `${API_BASE}/api/proxy`;

export const configuration = {
  api_base_url: API_BASE,

  // Our own proxy routes
  GSEARCH_BASEURL: `${PROXY}/gsearch`,
  ADGANGSADRESSER_URL: `${PROXY}/adgangsadresser`,

  // Properties the SAUL library expects; tokens stay empty and the proxy adds them
  API_STAC_BASEURL: `${PROXY}/stac`,
  API_STAC_TOKEN: '',
  API_DHM_BASEURL: `${PROXY}/dhm/koter`,
  API_DHM_WCS_BASEURL: `${PROXY}/dhm/wcs`,
  API_DHM_TOKENA: '',
  API_DHM_TOKENB: '',
};
