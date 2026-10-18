const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const profileKey = 'tripwise-profile-v1';
let profile = localStorage.getItem(profileKey);
if (!profile) { profile = crypto.randomUUID().replaceAll('-', ''); localStorage.setItem(profileKey, profile); }
let destinations = [], cities = [], selectedCity = null, itinerary = [], currentQuery = '', toastTimer;
const grid = $('#destination-grid'), statusLine = $('#status-line');
const selectedCategory = () => $('#interest-nav .interest-chip.active')?.dataset.category || 'all';
const headers = () => ({ 'X-TripWise-User': profile });
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const placeLine = place => [place.region, place.country].filter(Boolean).join(', ') || 'Somewhere on Earth';
const palette = place => `palette-${(String(place.id).split('').reduce((sum, ch) => sum + ch.charCodeAt(0), 0) % 6) + 1}`;
const formatPopulation = value => value ? `${new Intl.NumberFormat('en', { notation:'compact', maximumFractionDigits:1 }).format(value)} people` : 'A place to discover';
const artHtml = (place, extra = '') => place.image ? `<div class="card-art has-photo ${palette(place)}"><img src="${esc(place.image)}" alt="${esc(place.name)}" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentElement.classList.remove('has-photo');this.remove()">${extra}</div>` : `<div class="card-art ${palette(place)}"><span class="card-art-mark">✳</span>${extra}</div>`;
const travelMeta = place => place.distanceKm != null ? `${place.distanceKm} km from ${place.nearCity || 'city centre'}` : formatPopulation(place.population);

function showToast(message) {
  const el = $('#toast'); el.textContent = message; el.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 2500);
}
async function api(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { ...headers(), ...(options.headers || {}) } });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
  return data;
}
async function publicJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Public search returned HTTP ${response.status}.`);
  return response.json();
}
async function browserCitySearch(query) {
  const url = 'https://geocoding-api.open-meteo.com/v1/search?' + new URLSearchParams({name:query, count:'10', language:'en', format:'json'});
  const data = await publicJson(url);
  return {results:(data.results || []).map(row => ({
    id:String(row.id || `${row.latitude},${row.longitude}`), name:row.name || '', country:row.country || '',
    countryCode:row.country_code || '', region:row.admin1 || '', latitude:row.latitude, longitude:row.longitude,
    population:Number(row.population || 0), featureCode:row.feature_code || '',
    kind:Number(row.population || 0) >= 500000 ? 'Major city' : 'Town', timezone:row.timezone || ''
  })), source:'Open-Meteo'};
}
const wikiKinds = [
  ['Museum','Culture',['museum','gallery']], ['Temple','Spiritual',['temple','church','cathedral','mosque','basilica','shrine','gurdwara','synagogue']],
  ['Beach','Nature',['beach']], ['Park','Nature',['park','garden','zoo','lake','waterfall','sanctuary','reserve']],
  ['Monument','History',['fort','castle','palace','monument','memorial','tomb','ruins','heritage','historic','lighthouse','tower']],
  ['Attraction','Sights',['tourist','attraction','landmark','market','bridge','square','stadium','aquarium','theme']]
];
function distanceKm(lat1, lon1, lat2, lon2) {
  const rad = n => n * Math.PI / 180, dlat = rad(lat2-lat1), dlon = rad(lon2-lon1);
  const a = Math.sin(dlat/2)**2 + Math.cos(rad(lat1))*Math.cos(rad(lat2))*Math.sin(dlon/2)**2;
  return Math.round(6371 * 2 * Math.asin(Math.sqrt(a)) * 10) / 10;
}
async function browserWikipediaPlaces(city, radius) {
  const params = new URLSearchParams({origin:'*', action:'query', format:'json', generator:'geosearch',
    ggscoord:`${city.latitude}|${city.longitude}`, ggsradius:String(Math.min(Number(radius), 10000)),
    ggslimit:'100', prop:'coordinates|description', colimit:'100'});
  const data = await publicJson(`https://en.wikipedia.org/w/api.php?${params}`);
  const pages = Object.values(data.query?.pages || {}), places = [];
  for (const page of pages) {
    const point = page.coordinates?.[0];
    if (!point) continue;
    const description = page.description || '', words = `${page.title} ${description}`.toLowerCase();
    const kind = wikiKinds.find(([, , terms]) => terms.some(term => words.includes(term))) || ['Notable place','Sights',[]];
    const distance = distanceKm(city.latitude, city.longitude, point.lat, point.lon);
    if (distance > Number(radius)/1000) continue;
    places.push({id:`wiki/${page.pageid}`, name:page.title, kind:kind[0], category:kind[1],
      latitude:point.lat, longitude:point.lon, region:city.region || '', country:city.country || '',
      description, website:'', wikipedia:`en:${page.title}`, osmUrl:`https://en.wikipedia.org/?curid=${page.pageid}`,
      dataSource:'wikipedia', distanceKm:distance, nearCity:city.name});
  }
  return {results:places, source:'Wikipedia nearby landmarks'};
}
function card(place, savedIds = new Set()) {
  const saved = savedIds.has(String(place.id));
  return `<article class="destination-card">${artHtml(place, `<span class="card-kind">${esc(place.category || place.kind)}</span>`)}<div class="card-body"><div class="card-title-row"><div class="card-title" title="${esc(place.name)}">${esc(place.name)}</div><button class="save-button ${saved?'saved':''}" data-save="${esc(place.id)}" aria-label="${saved?'Remove':'Add'} ${esc(place.name)} ${saved?'from':'to'} itinerary" title="${saved?'Saved to your trip':'Add to your trip'}">${saved?'✓':'+'}</button></div><div class="card-location">${esc(place.kind)}${place.region ? ` · ${esc(place.region)}` : ''}</div><div class="card-footer"><span class="population">${esc(travelMeta(place))}</span><button class="details-link" data-details="${esc(place.id)}">Explore place ↗</button></div></div></article>`;
}
function bindCards(root = document) {
  $$('[data-details]', root).forEach(btn => btn.addEventListener('click', () => openDetails(destinations.find(p => String(p.id) === btn.dataset.details) || itinerary.find(i => String(i.destination.id) === btn.dataset.details)?.destination)));
  $$('[data-save]', root).forEach(btn => btn.addEventListener('click', async () => {
    const item = destinations.find(p => String(p.id) === btn.dataset.save) || itinerary.find(i => String(i.destination.id) === btn.dataset.save)?.destination;
    if (item) await toggleSave(item);
  }));
}
function renderDestinations() {
  if (!destinations.length) {
    grid.innerHTML = selectedCity ? `<div class="empty-state"><div class="empty-symbol">✳</div><h3>No mapped places in this radius yet.</h3><p>Try widening the search to ${Number($('#radius-filter').value) < 30000 ? '15 or 30 km' : 'another city'} or choose a different city match.<br>Place coverage depends on what contributors have mapped.</p></div>` : `<div class="empty-state"><div class="empty-symbol">✳</div><h3>No places found this time.</h3><p>Try another spelling or search for a nearby city.<br>There are plenty more places out there.</p></div>`;
    return;
  }
  const saved = new Set(itinerary.map(i => String(i.destination.id)));
  grid.innerHTML = destinations.map(place => card(place, saved)).join(''); bindCards(grid);
}
async function search(query = $('#search-input').value.trim()) {
  if (query.length < 2) { showToast('Try at least two letters to get started.'); return; }
  currentQuery = query; $('#search-input').value = query;
  selectedCity = null;
  $('#results-title').textContent = `Finding places near ${query}…`;
  $('#quick-searches').hidden = true;
  $('#city-context').hidden = true;
  grid.innerHTML = Array.from({length:6}, () => '<div class="skeleton"></div>').join('');
  statusLine.textContent = 'Finding the city, then looking around…';
  try {
    let result;
    try {
      result = await api(`/api/destinations?${new URLSearchParams({q:query, count:'10'})}`);
    } catch (serverError) {
      statusLine.textContent = 'Trying direct city search…';
      try { result = await browserCitySearch(query); }
      catch { throw new Error('City search could not connect. Check your internet connection and try again.'); }
    }
    cities = result.results;
    cities.sort((a,b) => Number(b.name.toLowerCase() === query.toLowerCase()) - Number(a.name.toLowerCase() === query.toLowerCase()) || b.population - a.population);
    if (!cities.length) {
      destinations = []; $('#results-title').textContent = `No city found for “${query}”`;
      statusLine.textContent = ''; renderDestinations(); return;
    }
    selectedCity = cities[0];
    const citySelect = $('#city-select');
    citySelect.innerHTML = cities.map((city, i) => `<option value="${i}">${esc(city.name)}${city.region ? `, ${esc(city.region)}` : ''}${city.country ? ` · ${esc(city.country)}` : ''}</option>`).join('');
    citySelect.value = '0'; $('#city-context').hidden = false;
    await fetchNearbyPlaces();
  } catch (error) {
    destinations = []; grid.innerHTML = `<div class="empty-state"><div class="empty-symbol">↗</div><h3>We couldn’t reach the map.</h3><p>${esc(error.message)}<br>Check your connection and try again.</p><button class="details-link" id="retry-search">Try again →</button></div>`;
    statusLine.textContent = ''; $('#retry-search')?.addEventListener('click', () => search(currentQuery));
  }
}
async function fetchNearbyPlaces() {
  if (!selectedCity) return;
  const radius = $('#radius-filter').value;
  $('#results-title').textContent = `Places near ${selectedCity.name}`;
  const subtitle = selectedCity.region ? `${selectedCity.region}, ${selectedCity.country}` : selectedCity.country;
  statusLine.textContent = `Searching for places within ${Number(radius)/1000} km of ${subtitle || selectedCity.name}…`;
  grid.innerHTML = Array.from({length:6}, () => '<div class="skeleton"></div>').join('');
  const category = selectedCategory();
  const params = new URLSearchParams({latitude:selectedCity.latitude, longitude:selectedCity.longitude, radius, city:selectedCity.name, category, sort:$('#sort-filter').value});
  try {
    let result;
    try { result = await api(`/api/places?${params}`); }
    catch {
      statusLine.textContent = 'Trying a second nearby-place index…';
      result = await browserWikipediaPlaces(selectedCity, radius);
      if (category !== 'all') result.results = result.results.filter(place => place.category.toLowerCase() === category);
      if ($('#sort-filter').value === 'name') result.results.sort((a,b) => a.name.localeCompare(b.name));
      else result.results.sort((a,b) => a.distanceKm - b.distanceKm);
    }
    destinations = result.results;
    statusLine.textContent = `${destinations.length} places found within ${Number(radius)/1000} km${subtitle ? ` of ${subtitle}` : ''} · ${result.source || 'OpenStreetMap'}`;
    renderDestinations();
  } catch (error) {
    destinations = []; grid.innerHTML = `<div class="empty-state"><div class="empty-symbol">↗</div><h3>Nearby places are taking a while.</h3><p>${esc(error.message)}<br>You can retry or choose a smaller search radius.</p><button class="details-link" id="retry-places">Try again →</button></div>`;
    statusLine.textContent = ''; $('#retry-places')?.addEventListener('click', fetchNearbyPlaces);
  }
}
async function loadItinerary() {
  try { itinerary = (await api('/api/trips')).items; updateCounts(); }
  catch (error) { showToast(error.message); }
}
function updateCounts() {
  $('#trip-count').textContent = itinerary.length; $('#mobile-count').textContent = itinerary.length;
  if (destinations.length) renderDestinations();
}
async function toggleSave(place) {
  const existing = itinerary.find(item => String(item.destination.id) === String(place.id));
  try {
    if (existing) {
      await api(`/api/trips/${encodeURIComponent(existing.id)}`, {method:'DELETE'});
      itinerary = itinerary.filter(item => item.id !== existing.id); showToast(`${place.name} removed from your trip`);
    } else {
      const result = await api('/api/trips', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({destination:place})});
      itinerary = [result.item, ...itinerary]; showToast(`${place.name} saved to your trip`);
    }
    updateCounts(); renderTrip();
    if ($('#detail-dialog').open) openDetails(place, true);
  } catch (error) { showToast(error.message); }
}
function renderTrip() {
  const root = $('#trip-grid');
  $('#trip-summary').innerHTML = `<b>${itinerary.length}</b> ${itinerary.length === 1 ? 'place' : 'places'} on your list <span style="float:right">${itinerary.length ? 'GOOD THINGS TAKE TIME ✦' : 'YOUR NEXT CHAPTER STARTS HERE'}</span>`;
  if (!itinerary.length) {
    root.innerHTML = `<div class="empty-state"><div class="empty-symbol">⌕</div><h3>Nothing on the itinerary. Yet.</h3><p>That’s the fun part. Wander around Explore and save somewhere that calls to you.</p><button class="details-link" id="empty-explore">Find your somewhere →</button></div>`;
    $('#empty-explore').addEventListener('click', () => setView('explore'));
    return;
  }
  root.innerHTML = itinerary.map(item => `<article class="trip-card">${artHtml(item.destination, `<span class="card-kind">${esc(item.destination.category || item.destination.kind)}</span>`)}<div class="card-body"><div class="card-title-row"><div class="card-title" title="${esc(item.name)}">${esc(item.name)}</div><button class="save-button saved" data-details="${esc(item.destination.id)}" aria-label="View ${esc(item.name)} details">↗</button></div><div class="card-location">${esc([item.destination.region,item.country].filter(Boolean).join(', ') || 'Somewhere on Earth')}</div><div class="card-footer"><span class="population">${esc(travelMeta(item.destination))}</span><button class="trip-remove" data-remove="${esc(item.id)}">Remove ×</button></div></div></article>`).join('');
  bindCards(root);
  $$('[data-remove]', root).forEach(btn => btn.addEventListener('click', async () => {
    try { await api(`/api/trips/${encodeURIComponent(btn.dataset.remove)}`, {method:'DELETE'}); itinerary = itinerary.filter(i => i.id !== btn.dataset.remove); updateCounts(); renderTrip(); showToast('Place removed from your trip'); }
    catch (error) { showToast(error.message); }
  }));
}
const weatherLabel = code => code === 0 ? ['Clear skies','☀'] : code <= 3 ? ['Partly cloudy','⛅'] : code <= 48 ? ['A little misty','🌫'] : code <= 67 ? ['Rain showers','🌧'] : code <= 77 ? ['Snowy','❄'] : code <= 82 ? ['Passing showers','🌦'] : code <= 86 ? ['Snow showers','🌨'] : ['Stormy','⛈'];
function temperature(value) { return Number.isFinite(value) ? `${Math.round(value)}°` : '—'; }
async function openDetails(place, refreshOnly = false) {
  if (!place) return;
  const dialog = $('#detail-dialog'), root = $('#detail-content');
  if (!refreshOnly) {
    const detailDescription = place.description || `${place.name} is mapped as a ${place.kind?.toLowerCase() || 'place'}${place.nearCity ? ` near ${place.nearCity}` : ''}. Save it to keep it on your list.`;
    const fromWikipedia = place.dataSource === 'wikipedia';
    const placeAttribution = fromWikipedia
      ? 'Place information by Wikipedia contributors (CC BY-SA).'
      : 'Place data © OpenStreetMap contributors (ODbL).';
    const placeLinkLabel = fromWikipedia ? 'Read the Wikipedia article ↗' : 'View place on OpenStreetMap ↗';
    root.innerHTML = `<div class="detail-art">${artHtml(place)}</div><div class="detail-content-body"><div class="eyebrow"><span class="eyebrow-line"></span> ${esc(place.category || place.kind)} · PLACE NOTES</div><h2>${esc(place.name)}</h2><div class="detail-place">${esc(placeLine(place))}</div><p class="detail-description">${esc(detailDescription)}</p><div class="detail-meta"><div class="meta-item"><span>Place type</span><b>${esc(place.kind || 'Destination')}</b></div><div class="meta-item"><span>From city centre</span><b>${place.distanceKm != null ? `${esc(place.distanceKm)} km` : esc(place.nearCity || place.country || 'Explore nearby')}</b></div></div><div class="weather-wrap" id="weather-wrap"><div class="status-line">Checking the skies…</div></div><button class="detail-add" id="detail-add">Add to My trip</button><p class="detail-source">Live forecast by Open-Meteo · ${placeAttribution}</p><p class="detail-source"><a href="${esc(place.osmUrl || `https://www.openstreetmap.org/?mlat=${place.latitude}&mlon=${place.longitude}`)}" target="_blank" rel="noreferrer">${placeLinkLabel}</a></p></div>`;
    if (!dialog.open) dialog.showModal();
  }
  const isSaved = itinerary.some(i => String(i.destination.id) === String(place.id));
  $('#detail-add').textContent = isSaved ? 'Saved to My trip ✓' : 'Add to My trip';
  $('#detail-add').onclick = () => toggleSave(place);
  try {
    const p = new URLSearchParams({name:place.name, latitude:place.latitude, longitude:place.longitude});
    let data;
    try { data = await api(`/api/destinations/${encodeURIComponent(place.id)}?${p}`); }
    catch {
      const weatherParams = new URLSearchParams({latitude:place.latitude, longitude:place.longitude,
        current:'temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m',
        daily:'weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_probability_max',
        timezone:'auto', forecast_days:'5'});
      data = {weather:await publicJson(`https://api.open-meteo.com/v1/forecast?${weatherParams}`)};
    }
    const weather = data.weather;
    const current = weather.current || {}, daily = weather.daily || {}, [label, emoji] = weatherLabel(current.weather_code ?? 3);
    const days = (daily.time || []).slice(0,5).map((date, i) => {
      const [dayLabel, icon] = weatherLabel(daily.weather_code[i] ?? 3);
      const day = new Date(`${date}T12:00:00`).toLocaleDateString('en', {weekday:'short'});
      return `<div class="forecast-day"><div>${day}</div><div class="forecast-icon" title="${dayLabel}">${icon}</div><div class="forecast-temp">${temperature(daily.temperature_2m_max[i])}</div></div>`;
    }).join('');
    $('#weather-wrap').innerHTML = `<div class="weather-head"><strong>Right now in ${esc(place.name)}</strong><span>${esc(weather.timezone || '')}</span></div><div class="weather-current"><span class="weather-emoji">${emoji}</span><span class="weather-temp">${temperature(current.temperature_2m)}</span><span class="weather-caption">${label}<br>Feels like ${temperature(current.apparent_temperature)} · Wind ${Math.round(current.wind_speed_10m || 0)} km/h</span></div><div class="forecast">${days}</div>`;
  } catch (error) {
    const weatherRoot = $('#weather-wrap'); if (weatherRoot) weatherRoot.innerHTML = `<div class="status-line">Weather is taking a breather. ${esc(error.message)}</div>`;
  }
}
function setView(name) {
  $$('.view').forEach(view => view.classList.toggle('active', view.id === `${name}-view`));
  $$('[data-view]').forEach(button => button.classList.toggle('active', button.dataset.view === name));
  if (name === 'trip') renderTrip();
  window.scrollTo({top:0, behavior:'smooth'});
}
$$('[data-view]').forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
$('#search-button').addEventListener('click', () => search());
$('#search-input').addEventListener('keydown', event => { if (event.key === 'Enter') search(); });
$('#interest-nav').addEventListener('click', event => {
  const button = event.target.closest('[data-category]');
  if (!button) return;
  $$('#interest-nav .interest-chip').forEach(chip => {
    const active = chip === button;
    chip.classList.toggle('active', active);
    chip.setAttribute('aria-pressed', String(active));
  });
  fetchNearbyPlaces();
});
$('#sort-filter').addEventListener('change', fetchNearbyPlaces);
$('#radius-filter').addEventListener('change', fetchNearbyPlaces);
$('#city-select').addEventListener('change', () => { selectedCity = cities[Number($('#city-select').value)] || cities[0]; fetchNearbyPlaces(); });
$$('[data-query]').forEach(button => button.addEventListener('click', () => search(button.dataset.query)));
$('#dialog-close').addEventListener('click', () => $('#detail-dialog').close());
$('#detail-dialog').addEventListener('click', event => { if (event.target === $('#detail-dialog')) $('#detail-dialog').close(); });
$('#today-label').textContent = new Intl.DateTimeFormat('en', {weekday:'short', month:'short', day:'numeric'}).format(new Date()).toUpperCase();

loadItinerary().then(() => search('Chennai'));
