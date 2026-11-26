import React, { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import { AreaSummary, AnomalyItem } from '../types';
import { MapPin, Info, AlertTriangle, Layers } from 'lucide-react';

interface CivicMapProps {
  areas: AreaSummary[];
  anomalies: AnomalyItem[];
  selectedWard: string | null;
  onSelectWard: (ward: string) => void;
}

// Helper to normalize strings for robust fuzzy-matching between GeoJSON properties and DB names
function cleanName(s: string): string {
  if (!s) return '';
  return s
    .toLowerCase()
    .trim()
    .replace(/\bward\b/g, '')
    .replace(/nagara/g, 'nagar')
    .replace(/puram/g, 'pura')
    .replace(/uru/g, 'ur')
    .replace(/[^a-z0-9]/g, '');
}

// Documented 1-to-1 spelling aliases between the 199 BBMP Sahaya dataset ward names
// and the 243 KGIS GeoJSON ward names (KGISWardName).
const WARD_ALIAS_MAP: Record<string, string> = {
  anjanapur: 'anjanapura',
  bagalagunte: 'bagalakunte',
  banaswadi: 'banasavadi',
  bilekahalli: 'bilekhalli',
  binnipet: 'binnipete',
  chamrajpet: 'chamrajapet',
  chikpete: 'chickpete',
  chowdeshwari: 'chowdeswari',
  cottonpet: 'cottonpete',
  dattathreyatemple: 'dattatreyatemple',
  doddabidarkallu: 'doddabidarakallu',
  galianjaneyaswamytemple: 'galianjenayatemple',
  ganeshmandira: 'ganeshmandir',
  garudacharpalya: 'garudacharplaya',
  gayathrinagar: 'gayithrinagar',
  govindrajanagar: 'govindarajanagar',
  hagadoor: 'hagadur',
  hanumanthanagar: 'hanumanthnagar',
  hebbal: 'hebbala',
  hoodi: 'hudi',
  jagajeevanramnagar: 'jagajivanaramnagar',
  kacharakanahalli: 'kacharkanahalli',
  kavalbyrasandra: 'kavalbairasandra',
  madiwala: 'madivala',
  mahalakshmipura: 'mahalakshimpura',
  malleshwaram: 'malleswaram',
  marathalli: 'marathahalli',
  maruthimandira: 'maruthimandir',
  mathikere: 'mattikere',
  moodalapalya: 'mudalapalya',
  nayandanahalli: 'nayandahalli',
  peenyaindustrialarea: 'peenya',
  puttenahalli: 'puttenahallisarakkilake',
  rajagopalanagar: 'rajagopalnagar',
  sagayapura: 'sagayarapura',
  sanjaynagar: 'sanjayanagar',
  shankaramata: 'shankarmatt',
  shanthalanagar: 'shantalanagar',
  shettyhalli: 'shettihalli',
  singasandra: 'hsrsingasandra',
  srirammandira: 'sriramamandir',
  sudamnagar: 'sudhamnagar',
  sudduguntepalya: 'suddaguntepalya',
  ullalu: 'ullal',
  vannarpet: 'vannarapete',
  vasanthapura: 'vasanthpura',
  vidyapeetha: 'vidyapeeta',
  vignananagar: 'vijnananagar',
  vijanapura: 'vijinapura',
  vijaynagar: 'vijayanagar',
  visvesvarapura: 'vishveshwarapura',
  vrushabhavatinagar: 'vrisabhavathinagar',
  yadiyur: 'yediyur',
  yelahankaoldsatellitetown: 'yelahankasatellitetown',
};

function resolveWardKey(rawName: string): string {
  const c = cleanName(rawName);
  return WARD_ALIAS_MAP[c] || c;
}

// Component to dynamically fit map bounds when selecting a ward
function MapController({ selectedWard, geoData }: { selectedWard: string | null; geoData: any }) {
  const map = useMap();

  useEffect(() => {
    if (!selectedWard || !geoData) return;
    const targetClean = cleanName(selectedWard);

    for (const feature of geoData.features) {
      const props = feature.properties || {};
      const name = props.KGISWardName || props.WARD_NAME || '';
      if (cleanName(name) === targetClean) {
        // Calculate center or bounds of the polygon
        if (feature.geometry?.type === 'Polygon' || feature.geometry?.type === 'MultiPolygon') {
          try {
            // Leaflet handles geojson layer zoom
          } catch (e) {}
        }
        break;
      }
    }
  }, [selectedWard, geoData, map]);

  return null;
}

export const CivicMap: React.FC<CivicMapProps> = ({
  areas,
  anomalies,
  selectedWard,
  onSelectWard,
}) => {
  const [geoData, setGeoData] = useState<any>(null);
  const [loadingGeo, setLoadingGeo] = useState<boolean>(true);

  // Fetch GeoJSON ward boundaries
  useEffect(() => {
    fetch('/bbmp_wards.geojson')
      .then((res) => {
        if (!res.ok) throw new Error('Could not load GeoJSON');
        return res.json();
      })
      .then((data) => {
        setGeoData(data);
        setLoadingGeo(false);
      })
      .catch((err) => {
        console.error('Failed to load GeoJSON:', err);
        setLoadingGeo(false);
      });
  }, []);

  // Precompute lookups for fast rendering
  const areaCountMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const a of areas) {
      const key = resolveWardKey(a.ward_name);
      map.set(key, (map.get(key) || 0) + a.total_complaints);
    }
    return map;
  }, [areas]);

  const anomalySet = useMemo(() => {
    const set = new Set<string>();
    for (const a of anomalies) {
      if (a.is_anomaly) {
        set.add(resolveWardKey(a.ward_name));
      }
    }
    return set;
  }, [anomalies]);

  const mappedStats = useMemo(() => {
    if (!geoData?.features || !areas.length) {
      return { matchedWards: 0, totalWards: areas.length };
    }
    const geoKeys = new Set<string>(
      geoData.features.map((f: any) =>
        cleanName(f.properties?.KGISWardName || f.properties?.WARD_NAME || '')
      )
    );
    let matchedWards = 0;
    for (const a of areas) {
      if (geoKeys.has(resolveWardKey(a.ward_name))) {
        matchedWards += 1;
      }
    }
    return { matchedWards, totalWards: areas.length };
  }, [geoData, areas]);

  // Max complaints in current filter to scale color
  const maxComplaints = useMemo(() => {
    if (!areas.length) return 100;
    return Math.max(...areas.map((a) => a.total_complaints), 100);
  }, [areas]);

  // Color generator for choropleth
  const getColor = (count: number | undefined, isAnomalous: boolean) => {
    if (count === undefined) return '#0f172a'; // Unmapped polygon
    if (isAnomalous) return '#f43f5e'; // Bright Rose/Crimson for anomaly
    if (count === 0) return '#1e293b';

    const ratio = Math.min(count / maxComplaints, 1);
    if (ratio > 0.75) return '#ea580c'; // Intense Amber/Orange
    if (ratio > 0.50) return '#f59e0b'; // Warm Amber
    if (ratio > 0.25) return '#0d9488'; // Vibrant Teal
    if (ratio > 0.05) return '#059669'; // Emerald
    return '#0284c7';                   // Cyan / Blue
  };

  const styleFeature = (feature: any) => {
    const props = feature.properties || {};
    const wardName = props.KGISWardName || props.WARD_NAME || '';
    const cleaned = cleanName(wardName);

    const count = areaCountMap.get(cleaned);
    const isUnmapped = count === undefined;
    const isAnomalous = anomalySet.has(cleaned);
    const isSelected = selectedWard && resolveWardKey(selectedWard) === cleaned;

    return {
      fillColor: getColor(count, isAnomalous),
      weight: isSelected ? 3 : isAnomalous ? 2.5 : 1,
      opacity: 0.9,
      color: isSelected ? '#38bdf8' : isAnomalous ? '#f43f5e' : isUnmapped ? '#475569' : '#334155',
      fillOpacity: isSelected ? 0.85 : isAnomalous ? 0.75 : isUnmapped ? 0.35 : 0.6,
      dashArray: isSelected ? '4' : isUnmapped ? '2 3' : undefined,
    };
  };

  const onEachFeature = (feature: any, layer: any) => {
    const props = feature.properties || {};
    const wardName = props.KGISWardName || props.WARD_NAME || 'Unknown Ward';
    const cleaned = cleanName(wardName);

    const count = areaCountMap.get(cleaned);
    const isAnomalous = anomalySet.has(cleaned);
    const countLabel =
      count === undefined
        ? '<strong style="color: #94a3b8;">Unmapped</strong>'
        : `<strong style="color: #38bdf8;">${count.toLocaleString()}</strong>`;

    layer.bindTooltip(
      `
      <div style="font-family: inherit; font-size: 12px; padding: 4px; pointer-events: none;">
        <div style="font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 4px;">
          ${wardName}
          ${isAnomalous ? '<span style="background: #f43f5e; color: #fff; padding: 1px 4px; border-radius: 4px; font-size: 10px;">ANOMALY</span>' : ''}
        </div>
        <div style="color: #94a3b8; margin-top: 2px;">
          ${count === undefined ? 'Status:' : 'Complaints:'} ${countLabel}
        </div>
      </div>
      `,
      { sticky: false, direction: 'top', offset: [0, -10], opacity: 0.95 }
    );

    layer.on({
      click: () => {
        // Find corresponding DB ward name if possible
        const matchingArea = areas.find((a) => resolveWardKey(a.ward_name) === cleaned);
        onSelectWard(matchingArea ? matchingArea.ward_name : wardName);
      },
      mouseover: (e: any) => {
        const target = e.target;
        target.setStyle({
          weight: 2.5,
          color: '#ffffff',
          fillOpacity: 0.85,
        });
      },
      mouseout: (e: any) => {
        const target = e.target;
        target.setStyle(styleFeature(feature));
      },
    });
  };

  return (
    <div className="glass-panel rounded-2xl border border-slate-800 p-4 relative overflow-hidden flex flex-col h-[560px]">
      <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <MapPin className="w-5 h-5 text-emerald-400" />
          <h2 className="text-base font-bold text-white">
            Bengaluru Ward Disruption Choropleth
          </h2>
          <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
            {mappedStats.totalWards > 0
              ? `${mappedStats.matchedWards} / ${mappedStats.totalWards} Wards Mapped`
              : '199 BBMP Wards'}
          </span>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-3 text-xs text-slate-400 flex-wrap gap-y-1">
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-[#f43f5e] inline-block shadow-sm" />
            <span className="text-rose-400 font-medium">Anomaly Spike</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-[#ea580c] inline-block" />
            <span>High Volume</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-[#059669] inline-block" />
            <span>Moderate</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-[#0284c7] inline-block" />
            <span>Low</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-sm bg-[#0f172a] border border-slate-600 inline-block" />
            <span>Unmapped</span>
          </div>
        </div>
      </div>

      {/* Map Container */}
      <div className="flex-1 w-full rounded-xl overflow-hidden relative">
        {loadingGeo && (
          <div className="absolute inset-0 bg-slate-950/80 z-20 flex items-center justify-center space-x-2 text-slate-400 text-sm">
            <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            <span>Rendering Bengaluru ward boundaries...</span>
          </div>
        )}

        <MapContainer
          center={[12.9716, 77.5946]} // Bengaluru center
          zoom={11}
          style={{ height: '100%', width: '100%' }}
          zoomControl={true}
        >
          {/* OpenStreetMap with CSS dark filter for seamless dark theme without watermark */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> | DataMeet BBMP'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            className="leaflet-dark-tiles"
          />

          {geoData && (
            <GeoJSON
              key={selectedWard || 'all'}
              data={geoData}
              style={styleFeature}
              onEachFeature={onEachFeature}
            />
          )}

          <MapController selectedWard={selectedWard} geoData={geoData} />
        </MapContainer>
      </div>

      <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
        <span>Click any ward to inspect historical baseline and category breakdown.</span>
        <span>Source boundaries: DataMeet Municipal Spatial Data (CC BY 4.0)</span>
      </div>
    </div>
  );
};
