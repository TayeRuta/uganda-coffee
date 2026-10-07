/**************************************************************************
 * Uganda coffee zones: monthly temperature and rainfall, January 1990 to
 * the latest available month.
 *
 * Paste into the Earth Engine Code Editor (code.earthengine.google.com) and
 * press Run. Check the printed zone list and areas, then start the export
 * from the Tasks tab. It is light: a few minutes to half an hour.
 *
 * Zones (district groups, filtered by elevation so each zone covers the land
 * where that coffee type actually grows):
 *   Arabica, Mt Elgon   Elgon districts, land at 1,300 m or higher
 *   Arabica, Rwenzori   Rwenzori districts, land at 1,300 m or higher
 *   Robusta, Greater Masaka / Central / South-west / Busoga
 *                       those districts, land below 1,500 m
 *
 * Output: uganda_coffee_zones_climate.csv, one row per zone and month:
 *   zone, type, date, year, month, tmean_c, tmax_c, tmin_c, rain_chirps_mm, area_km2
 *   tmean/tmax/tmin  ERA5-Land monthly mean of 2 m air temperature and of the
 *                    daily maximum and minimum (deg C, about 11 km resolution)
 *   rain_chirps_mm   CHIRPS monthly rainfall total (mm, about 5.5 km)
 *
 * Feeds notebooks/02 in the uganda-coffee project.
 **************************************************************************/

// ---------------------------------------------------------------- settings
var START = '1990-01-01';
// ERA5-Land monthly data appear about 2–3 months after the month ends
var END = ee.Date(Date.now()).advance(-3, 'month');

var ZONES = [
  {zone: 'Arabica, Mt Elgon', type: 'arabica', minElev: 1300, maxElev: 9000,
   districts: ['Mbale', 'Bududa', 'Manafwa', 'Namisindwa', 'Sironko', 'Bulambuli', 'Kapchorwa', 'Kween', 'Bukwo']},
  {zone: 'Arabica, Rwenzori', type: 'arabica', minElev: 1300, maxElev: 9000,
   districts: ['Kasese', 'Bundibugyo', 'Ntoroko', 'Kabarole', 'Bunyangabu']},
  {zone: 'Robusta, Greater Masaka', type: 'robusta', minElev: 0, maxElev: 1500,
   districts: ['Masaka', 'Lwengo', 'Bukomansimbi', 'Kalungu', 'Rakai', 'Kyotera', 'Lyantonde', 'Sembabule']},
  {zone: 'Robusta, Central', type: 'robusta', minElev: 0, maxElev: 1500,
   districts: ['Mpigi', 'Butambala', 'Gomba', 'Mubende', 'Mityana', 'Luwero', 'Nakaseke', 'Mukono', 'Kayunga', 'Wakiso', 'Kiboga', 'Kyankwanzi']},
  {zone: 'Robusta, South-west', type: 'robusta', minElev: 0, maxElev: 1500,
   districts: ['Bushenyi', 'Sheema', 'Buhweju', 'Rubirizi', 'Mitooma', 'Ibanda', 'Kiruhura', 'Ntungamo', 'Mbarara', 'Isingiro', 'Kamwenge']},
  {zone: 'Robusta, Busoga', type: 'robusta', minElev: 0, maxElev: 1500,
   districts: ['Iganga', 'Jinja', 'Kamuli', 'Mayuge', 'Luuka', 'Bugiri', 'Namutumba', 'Buyende', 'Kaliro']}
];

// ---------------------------------------------------------------- zones
var districts = ee.FeatureCollection('FAO/GAUL/2015/level1').filter(ee.Filter.eq('ADM0_NAME', 'Uganda'));
var elev = ee.Image('USGS/SRTMGL1_003');
var water = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence').unmask(0).gte(50);

// Each zone: the matched districts, as one feature. GAUL 2015 predates some newer
// districts (e.g. Namisindwa, Kyotera); their land is still covered by the parent district.
var zoneFeatures = ee.FeatureCollection(ZONES.map(function (z) {
  var matched = districts.filter(ee.Filter.inList('ADM1_NAME', z.districts));
  return ee.Feature(matched.geometry().dissolve(1000), {
    zone: z.zone, type: z.type, minElev: z.minElev, maxElev: z.maxElev,
    matched: matched.aggregate_array('ADM1_NAME')
  });
}));
print('Districts matched in each zone (some new districts sit inside their parent):',
      zoneFeatures.aggregate_array('zone'), zoneFeatures.aggregate_array('matched'));

// Elevation and open-water mask per zone, as a weight image (1 = counted, masked = not)
function zoneMask(f) {
  f = ee.Feature(f);
  return elev.gte(ee.Number(f.get('minElev'))).and(elev.lt(ee.Number(f.get('maxElev')))).and(water.not());
}

var areas = ee.FeatureCollection(zoneFeatures.map(function (f) {
  var a = ee.Image.pixelArea().divide(1e6).updateMask(zoneMask(f)).reduceRegion({
    reducer: ee.Reducer.sum(), geometry: f.geometry(), scale: 500, maxPixels: 1e10, tileScale: 4
  }).get('area');
  return f.set('area_km2', a);
}));
print('Zone area after the elevation filter (km²):', areas.aggregate_array('zone'), areas.aggregate_array('area_km2'));

// ---------------------------------------------------------------- climate
var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/MONTHLY_AGGR')
  .select(['temperature_2m', 'temperature_2m_max', 'temperature_2m_min']);
var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').select('precipitation');

var start = ee.Date(START);
var nMonths = END.difference(start, 'month').floor();
var months = ee.List.sequence(0, nMonths.subtract(1));

function monthRows(i) {
  var m0 = start.advance(ee.Number(i), 'month');
  var m1 = m0.advance(1, 'month');
  var t = ee.Image(era5.filterDate(m0, m1).first()).subtract(273.15)
    .rename(['tmean_c', 'tmax_c', 'tmin_c']);
  var r = chirps.filterDate(m0, m1).sum().rename('rain_chirps_mm');
  var img = t.addBands(r);
  return areas.map(function (f) {
    var v = img.updateMask(zoneMask(f)).reduceRegion({
      reducer: ee.Reducer.mean(), geometry: f.geometry(), scale: 5566, maxPixels: 1e10, tileScale: 4
    });
    return ee.Feature(null, {
      zone: f.get('zone'), type: f.get('type'), area_km2: f.get('area_km2'),
      date: m0.format('YYYY-MM'), year: m0.get('year'), month: m0.get('month'),
      tmean_c: v.get('tmean_c'), tmax_c: v.get('tmax_c'), tmin_c: v.get('tmin_c'),
      rain_chirps_mm: v.get('rain_chirps_mm')
    });
  });
}

var table = ee.FeatureCollection(months.map(monthRows)).flatten();

// ---------------------------------------------------------------- checks
print('Months to export (expect about 430):', nMonths);
print('Preview, one recent month:', ee.FeatureCollection(monthRows(nMonths.subtract(13))));
Map.centerObject(districts, 7);
Map.addLayer(areas.style({color: '1a1a1a', fillColor: '00000000', width: 1}), {}, 'Coffee zones (districts)');
Map.addLayer(zoneMask(areas.first()).selfMask().clip(areas.first().geometry()), {palette: ['c4572e']}, 'Elgon arabica land (≥1,300 m)');

// ---------------------------------------------------------------- export
Export.table.toDrive({
  collection: table,
  description: 'uganda_coffee_zones_climate',
  fileNamePrefix: 'uganda_coffee_zones_climate',
  fileFormat: 'CSV',
  selectors: ['zone', 'type', 'date', 'year', 'month', 'tmean_c', 'tmax_c', 'tmin_c', 'rain_chirps_mm', 'area_km2']
});
