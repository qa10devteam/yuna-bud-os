'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  CloudRain,
  Sun,
  Wind,
  Snowflake,
  AlertTriangle,
  Cloud,
  CloudSnow,
  CloudLightning,
  Droplets,
  Thermometer,
  MapPin,
} from 'lucide-react';
import { PageShell } from '@/components/PageShell';

// ── Polish cities ─────────────────────────────────────────────────────────────
const PL_CITIES = [
  'Warszawa', 'Kraków', 'Łódź', 'Wrocław', 'Poznań', 'Gdańsk', 'Szczecin',
  'Bydgoszcz', 'Lublin', 'Katowice', 'Białystok', 'Gdynia', 'Częstochowa',
  'Radom', 'Sosnowiec', 'Toruń', 'Kielce', 'Rzeszów', 'Gliwice', 'Zabrze',
  'Olsztyn', 'Bielsko-Biała', 'Bytom', 'Zielona Góra', 'Rybnik', 'Ruda Śląska',
  'Opole', 'Tychy', 'Gorzów Wielkopolski', 'Płock', 'Dąbrowa Górnicza',
  'Elbląg', 'Wałbrzych', 'Włocławek', 'Tarnów', 'Chorzów', 'Koszalin',
  'Kalisz', 'Legnica', 'Grudziądz',
];

// ── Polish day names ──────────────────────────────────────────────────────────
const PL_DAYS = ['Nd', 'Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob'];
const PL_DAYS_FULL = ['Niedziela', 'Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota'];

// ── Weather helpers ───────────────────────────────────────────────────────────
function WeatherIcon({ code, className = 'w-6 h-6' }: { code?: number | null; className?: string }) {
  const c = code ?? 0;
  if (c === 0) return <Sun className={`${className} text-yellow-400`} />;
  if (c <= 3) return <Cloud className={`${className} text-earth-400`} />;
  if (c <= 49) return <Droplets className={`${className} text-accent-info`} />;
  if (c <= 59) return <CloudRain className={`${className} text-accent-info`} />;
  if (c <= 69) return <CloudSnow className={`${className} text-sky-300`} />;
  if (c <= 79) return <Snowflake className={`${className} text-sky-200`} />;
  if (c <= 84) return <CloudRain className={`${className} text-blue-500`} />;
  if (c <= 94) return <CloudSnow className={`${className} text-sky-300`} />;
  return <CloudLightning className={`${className} text-yellow-400`} />;
}

function weatherLabel(code?: number | null): string {
  const c = code ?? 0;
  if (c === 0) return 'Słonecznie';
  if (c <= 3) return 'Pochmurno';
  if (c <= 49) return 'Mgła';
  if (c <= 59) return 'Mżawka';
  if (c <= 69) return 'Deszcz';
  if (c <= 79) return 'Śnieg';
  if (c <= 84) return 'Przelotne opady';
  if (c <= 94) return 'Śnieg/krupy';
  return 'Burza';
}

// ── Risk ──────────────────────────────────────────────────────────────────────
type RiskLevel = 'wysoki' | 'średni' | 'niski';

function calcRisk(precipitation: number, windspeed: number, tempMin: number): RiskLevel {
  if (precipitation > 15 || windspeed > 60 || tempMin < -5) return 'wysoki';
  if (precipitation > 5 || windspeed > 35 || tempMin < 0) return 'średni';
  return 'niski';
}

function apiRiskToLevel(apiRisk?: string | null): RiskLevel | null {
  if (!apiRisk) return null;
  const r = apiRisk.toLowerCase();
  if (r === 'wysoki' || r === 'stop') return 'wysoki';
  if (r === 'średni' || r === 'caution') return 'średni';
  if (r === 'niski' || r === 'ok') return 'niski';
  return null;
}

const riskConfig: Record<RiskLevel, { cls: string; dot: string; label: string; icon: string }> = {
  wysoki: { cls: 'bg-accent-danger/15 text-accent-danger border border-accent-danger/30',   dot: 'bg-accent-danger',   label: 'Stop roboty', icon: '⛔' },
  średni: { cls: 'bg-accent-warning/15 text-accent-warning border border-accent-warning/30', dot: 'bg-accent-warning', label: 'Ostrożnie',    icon: '⚠️' },
  niski:  { cls: 'bg-accent-primary/15 text-accent-primary border border-accent-primary/30', dot: 'bg-accent-primary', label: 'OK',           icon: '✓' },
};

// ── Types ──────────────────────────────────────────────────────────────────────
interface DayForecast {
  date: string;
  temp_min: number;
  temp_max: number;
  precipitation_mm: number;
  wind_max_kmh: number;
  weather_code?: number | null;
  construction_risk?: string | null;
  snowfall_cm?: number | null;
  wind_gusts_kmh?: number | null;
  precip_probability_pct?: number | null;
  risk_reasons?: string[];
}

interface WeatherResponse {
  city?: string | null;
  forecast: DayForecast[];
  lat?: number;
  lon?: number;
  timezone?: string;
  source?: string;
  forecast_days?: number;
  summary?: unknown;
}

// ── Skeleton cards ────────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="card p-4 rounded-token-lg animate-pulse-soft">
      <div className="h-3 bg-earth-800 rounded w-10 mb-3" />
      <div className="w-10 h-10 bg-earth-800 rounded-token mb-3 mx-auto" />
      <div className="h-4 bg-earth-800 rounded w-16 mb-1.5 mx-auto" />
      <div className="h-3 bg-earth-800 rounded w-12 mx-auto" />
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function PogodaPage() {
  const [city, setCity] = useState('Warszawa');
  const [inputValue, setInputValue] = useState('Warszawa');
  const [showDropdown, setShowDropdown] = useState(false);
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDay, setSelectedDay] = useState<DayForecast | null>(null);

  const filteredCities = PL_CITIES.filter((c) =>
    c.toLowerCase().includes(inputValue.toLowerCase())
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSelectedDay(null);

    fetch(`/api/v1/market/weather/city/${encodeURIComponent(city)}?days=14`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: WeatherResponse) => {
        if (!cancelled) {
          setWeather(data);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
          setWeather(generateMock(city));
        }
      });

    return () => { cancelled = true; };
  }, [city]);

  function selectCity(name: string) {
    setCity(name);
    setInputValue(name);
    setShowDropdown(false);
  }

  const forecast = weather?.forecast ?? [];
  const firstRow = forecast.slice(0, 7);
  const secondRow = forecast.slice(7, 14);

  function getDayLabel(dateStr: string, short = false) {
    const d = new Date(dateStr);
    const dayIdx = d.getDay();
    const dayName = short ? PL_DAYS[dayIdx] : PL_DAYS_FULL[dayIdx];
    const dd = d.toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit' });
    return { dayName, dd };
  }

  function DayCard({ day, size = 'normal' }: { day: DayForecast; size?: 'normal' | 'small' }) {
    const risk: RiskLevel =
      apiRiskToLevel(day.construction_risk) ??
      calcRisk(day.precipitation_mm ?? 0, day.wind_max_kmh ?? 0, day.temp_min ?? 0);
    const rc = riskConfig[risk];
    const { dayName, dd } = getDayLabel(day.date, true);
    const isSelected = selectedDay?.date === day.date;
    const isSmall = size === 'small';

    return (
      <motion.div
        whileHover={{ y: -2 }}
        onClick={() => setSelectedDay(isSelected ? null : day)}
        className={`card rounded-token-lg cursor-pointer transition-all duration-200 ${
          isSmall ? 'p-3' : 'p-4'
        } ${isSelected ? 'ring-2 ring-accent-primary/60' : 'card-hover'}`}
      >
        <div className="text-center">
          <p className="text-xs font-semibold text-earth-400 uppercase">{dayName}</p>
          <p className="text-xs text-earth-600 mb-2">{dd}</p>

          <WeatherIcon
            code={day.weather_code}
            className={isSmall ? 'w-7 h-7 mx-auto mb-2' : 'w-10 h-10 mx-auto mb-2'}
          />

          {!isSmall && (
            <p className="text-earth-500 text-xs mb-2">{weatherLabel(day.weather_code)}</p>
          )}

          <div className="flex items-center justify-center gap-1 mb-2">
            <span className="text-blue-400 font-mono text-xs">{(day.temp_min ?? 0).toFixed(0)}°</span>
            <span className="text-earth-700 text-xs">/</span>
            <span className="text-orange-400 font-mono text-xs font-semibold">{(day.temp_max ?? 0).toFixed(0)}°</span>
          </div>

          <div className="flex items-center justify-center gap-2 text-xs text-earth-600 mb-2">
            <span><CloudRain className="w-3 h-3 inline mr-0.5" />{(day.precipitation_mm ?? 0).toFixed(0)}mm</span>
            <span><Wind className="w-3 h-3 inline mr-0.5" />{(day.wind_max_kmh ?? 0).toFixed(0)}</span>
          </div>

          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-xs font-medium ${rc.cls}`}>
            <span>{rc.icon}</span>
            {isSmall ? risk.slice(0, 3) : rc.label}
          </span>
        </div>
      </motion.div>
    );
  }

  return (
    <PageShell
      title="Pogoda Budowlana"
      subtitle="Warunki meteorologiczne dla placów budowy"
      actions={
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-token bg-earth-800/60 border border-earth-700/40">
          <MapPin className="w-3.5 h-3.5 text-accent-primary" />
          <span className="text-sm text-earth-300 font-medium">{city}</span>
        </div>
      }
    >
      <div className="space-y-6 max-w-6xl">
        {/* City search */}
        <div className="relative max-w-sm">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => { setInputValue(e.target.value); setShowDropdown(true); }}
            onFocus={() => setShowDropdown(true)}
            onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
            placeholder="Wyszukaj miasto..."
            className="input-base w-full"
          />
          <AnimatePresence>
            {showDropdown && filteredCities.length > 0 ? (
              <motion.div
                key="city-dropdown"
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="absolute top-full mt-1 left-0 right-0 bg-earth-900 border border-earth-700 rounded-token-lg shadow-token-lg z-50 max-h-60 overflow-y-auto"
              >
                {filteredCities.map((c) => (
                  <button
                    key={c}
                    onMouseDown={() => selectCity(c)}
                    className={`w-full text-left px-4 py-2 text-sm transition-colors hover:bg-earth-800 ${
                      c === city ? 'text-accent-primary bg-earth-800/50' : 'text-earth-300'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>

        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-2 px-4 py-2.5 bg-accent-warning/10 border border-accent-warning/30 rounded-token-lg text-accent-warning text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Dane demonstracyjne (API niedostępne): {error}</span>
          </div>
        )}

        {/* First 7 days */}
        <div>
          <h3 className="section-label mb-3">Najbliższe 7 dni</h3>
          <div className="grid grid-cols-7 gap-2">
            {loading
              ? Array.from({ length: 7 }).map((_, i) => <SkeletonCard key={i} />)
              : firstRow.length > 0
                ? firstRow.map(day => <DayCard key={day.date} day={day} size="normal" />)
                : (
                  <div className="col-span-7 flex flex-col items-center justify-center py-10 text-center">
                    <CloudRain className="w-10 h-10 text-earth-600 mb-3" />
                    <p className="text-earth-400 text-sm font-medium">Brak danych pogodowych</p>
                    <p className="text-earth-600 text-xs mt-1">Wybierz miasto powyżej</p>
                  </div>
                )
            }
          </div>
        </div>

        {/* Next 7 days */}
        {(secondRow.length > 0 || loading) && (
          <div>
            <h3 className="section-label mb-3">Kolejne 7 dni</h3>
            <div className="grid grid-cols-7 gap-2">
              {loading
                ? Array.from({ length: 7 }).map((_, i) => <SkeletonCard key={i} />)
                : secondRow.map(day => <DayCard key={day.date} day={day} size="small" />)
              }
            </div>
          </div>
        )}

        {/* Selected day detail */}
        <AnimatePresence>
          {selectedDay ? (
            <motion.div
              key="day-detail"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="card rounded-token-xl p-5 shadow-token-md"
            >
              {(() => {
                const risk: RiskLevel =
                  apiRiskToLevel(selectedDay.construction_risk) ??
                  calcRisk(selectedDay.precipitation_mm ?? 0, selectedDay.wind_max_kmh ?? 0, selectedDay.temp_min ?? 0);
                const rc = riskConfig[risk];
                const { dayName, dd } = getDayLabel(selectedDay.date, false);
                return (
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <WeatherIcon code={selectedDay.weather_code} className="w-10 h-10" />
                        <div>
                          <h4 className="text-earth-100 font-semibold">{dayName}, {dd}</h4>
                          <p className="text-earth-500 text-sm">{weatherLabel(selectedDay.weather_code)}</p>
                        </div>
                      </div>
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold ${rc.cls}`}>
                        {rc.icon} {risk.charAt(0).toUpperCase() + risk.slice(1)} ryzyko budowy
                      </span>
                    </div>
                    <div className="grid grid-cols-4 gap-3">
                      <div className="bg-earth-800/40 rounded-token-lg p-3 text-center">
                        <Thermometer className="w-4 h-4 text-blue-400 mx-auto mb-1" />
                        <p className="text-blue-400 font-mono text-lg">{(selectedDay.temp_min ?? 0).toFixed(1)}°C</p>
                        <p className="text-earth-600 text-xs">Min</p>
                      </div>
                      <div className="bg-earth-800/40 rounded-token-lg p-3 text-center">
                        <Thermometer className="w-4 h-4 text-orange-400 mx-auto mb-1" />
                        <p className="text-orange-400 font-mono text-lg">{(selectedDay.temp_max ?? 0).toFixed(1)}°C</p>
                        <p className="text-earth-600 text-xs">Max</p>
                      </div>
                      <div className="bg-earth-800/40 rounded-token-lg p-3 text-center">
                        <CloudRain className="w-4 h-4 text-accent-info mx-auto mb-1" />
                        <p className="text-accent-info font-mono text-lg">{(selectedDay.precipitation_mm ?? 0).toFixed(1)}</p>
                        <p className="text-earth-600 text-xs">Opady mm</p>
                      </div>
                      <div className="bg-earth-800/40 rounded-token-lg p-3 text-center">
                        <Wind className="w-4 h-4 text-earth-400 mx-auto mb-1" />
                        <p className="text-earth-200 font-mono text-lg">{(selectedDay.wind_max_kmh ?? 0).toFixed(0)}</p>
                        <p className="text-earth-600 text-xs">Wiatr km/h</p>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </motion.div>
          ) : null}
        </AnimatePresence>

        {/* Risk legend */}
        <div className="flex items-center gap-4 px-4 py-3 bg-earth-900/40 rounded-token-lg border border-earth-800/40">
          <span className="section-label">Ryzyko budowy:</span>
          {(Object.entries(riskConfig) as [RiskLevel, typeof riskConfig[RiskLevel]][]).map(([level, cfg]) => (
            <span key={level} className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.cls}`}>
              {cfg.icon} {level.charAt(0).toUpperCase() + level.slice(1)}
            </span>
          ))}
        </div>
      </div>
    </PageShell>
  );
}

// ── Mock data fallback ────────────────────────────────────────────────────────
function generateMock(city: string): WeatherResponse {
  const forecast: DayForecast[] = [];
  const today = new Date();
  for (let i = 0; i < 14; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    const precip = Math.round(Math.random() * 20 * 10) / 10;
    const wind = Math.round(Math.random() * 80);
    const tempMin = Math.round((Math.random() * 20 - 5) * 10) / 10;
    forecast.push({
      date: d.toISOString().split('T')[0],
      weather_code: [0, 1, 2, 3, 51, 61, 71, 80, 95][Math.floor(Math.random() * 9)],
      temp_min: tempMin,
      temp_max: Math.round((tempMin + Math.random() * 15 + 5) * 10) / 10,
      precipitation_mm: precip,
      wind_max_kmh: wind,
      construction_risk: calcRisk(precip, wind, tempMin),
    });
  }
  return { city, forecast };
}
