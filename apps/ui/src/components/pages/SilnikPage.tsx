'use client';

import { useState } from 'react';
import { riskAnalysis } from '@/lib/mockData';
import {
  Brain,
  AlertTriangle,
  ShieldAlert,
  CheckCircle,
  XCircle,
  Target,
  TrendingUp,
  TrendingDown,
  Info,
  Layers,
  Cpu,
} from 'lucide-react';
import dynamic from 'next/dynamic';

function BarChart({ data, label }: { data: { name: string; value: number; color: string }[]; label: string }) {
  const maxValue = Math.max(...data.map(d => d.value));
  const [hovered, setHovered] = useState<number | null>(null);
  
  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-earth-100 mb-4">{label}</h3>
      <div className="space-y-4">
        {data.map((bar, i) => (
          <div key={i}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-earth-300">{bar.name}</span>
              <span className="text-earth-100 font-semibold">{bar.value.toFixed(1)}%</span>
            </div>
            <div className="h-4 bg-earth-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${(bar.value / maxValue) * 100}%`,
                  backgroundColor: bar.color,
                  opacity: hovered === i ? 1 : 0.8,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScenarioChart({ scenarios }: { scenarios: typeof riskAnalysis.l2RiskDistribution.scenarios }) {
  const [hovered, setHovered] = useState<number | null>(null);
  
  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-earth-100 mb-4">Rozkład scenariuszy</h3>
      <div className="flex items-end justify-between h-48 gap-2">
        {scenarios.map((scenario, i) => (
          <div
            key={i}
            className="flex-1 flex flex-col items-center gap-2 cursor-pointer"
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          >
            <div className="text-xs text-earth-300">{(scenario.probability * 100).toFixed(0)}%</div>
            <div
              className="w-full rounded-t-lg transition-all duration-300"
              style={{
                height: `${(scenario.margin + 0.2) * 200}px`,
                backgroundColor: scenario.margin > 0 ? '#22C55E' : '#EF4444',
                opacity: hovered === i ? 1 : 0.7,
              }}
            />
            <div className="text-xs text-earth-300 text-center">{scenario.name}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SilnikPage() {
  const [activeTab, setActiveTab] = useState<'l1' | 'l2' | 'l3'>('l1');
  const { l1Feasibility, l2RiskDistribution, l3Explanation } = riskAnalysis;
  
  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      low: 'text-accent-info',
      medium: 'text-accent-warning',
      high: 'text-accent-danger',
      critical: 'text-accent-danger',
    };
    return colors[severity] || 'text-earth-400';
  };
  
  const getSeverityBadge = (severity: string) => {
    const classes: Record<string, string> = {
      low: 'badge-info',
      medium: 'badge-warning',
      high: 'badge-danger',
      critical: 'badge-danger',
    };
    return <span className={classes[severity] || 'badge-info'}>{severity}</span>;
  };
  
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold text-earth-100">SILNIK</h1>
          <span className="badge-warning">Silnik decyzyjny</span>
        </div>
        <p className="text-earth-400">
          3-warstwowy silnik aksjomatyczno-stochastyczny — L1 reguły twarde, L2 analiza ryzyka, L3 wyjaśnienie AI
        </p>
      </div>
      
      {/* Verdict */}
      <div className={`p-6 mb-6 rounded-lg border-2 ${
        l1Feasibility.verdict === 'feasible' ? 'bg-accent-success/10 border-accent-success' :
        l1Feasibility.verdict === 'risky' ? 'bg-accent-warning/10 border-accent-warning' :
        'bg-accent-danger/10 border-accent-danger'
      }`}>
        <div className="flex items-center gap-3 mb-4">
          {l1Feasibility.verdict === 'feasible' ? (
            <CheckCircle className="w-8 h-8 text-accent-success" />
          ) : l1Feasibility.verdict === 'risky' ? (
            <AlertTriangle className="w-8 h-8 text-accent-warning" />
          ) : (
            <XCircle className="w-8 h-8 text-accent-danger" />
          )}
          <div>
            <h2 className="text-2xl font-bold text-earth-100">
              {l1Feasibility.verdict === 'feasible' ? 'Wykonalny' :
               l1Feasibility.verdict === 'risky' ? 'Ryzykowny' :
               'Niewykonalny'}
            </h2>
            <p className="text-earth-300">
              {l1Feasibility.violations.length} naruszeń wykryto • {l1Feasibility.derivedFacts.length} faktów wyprowadzonych
            </p>
          </div>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'l1' ? 'bg-earth-700 text-earth-100' : 'bg-earth-800 text-earth-400 hover:bg-earth-700'
          }`}
          onClick={() => setActiveTab('l1')}
        >
          <Layers className="w-4 h-4 inline mr-2" />
          L1 — Reguły twarde
        </button>
        <button
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'l2' ? 'bg-earth-700 text-earth-100' : 'bg-earth-800 text-earth-400 hover:bg-earth-700'
          }`}
          onClick={() => setActiveTab('l2')}
        >
          <Target className="w-4 h-4 inline mr-2" />
          L2 — Analiza ryzyka
        </button>
        <button
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'l3' ? 'bg-earth-700 text-earth-100' : 'bg-earth-800 text-earth-400 hover:bg-earth-700'
          }`}
          onClick={() => setActiveTab('l3')}
        >
          <Cpu className="w-4 h-4 inline mr-2" />
          L3 — Wyjaśnienie AI
        </button>
      </div>
      
      {/* L1 Tab */}
      {activeTab === 'l1' && (
        <div className="space-y-6">
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-earth-100 mb-4 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-accent-danger" />
              Naruszenia reguł (L1)
            </h3>
            <div className="space-y-4">
              {l1Feasibility.violations.map((violation) => (
                <div key={violation.id} className="p-4 bg-earth-800 rounded-lg border border-earth-700">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="badge-info">{violation.axiomClass}</span>
                      <span className={`text-xs font-semibold uppercase ${getSeverityColor(violation.severity)}`}>
                        {violation.severity}
                      </span>
                    </div>
                    <span className="text-xs text-earth-400 font-mono">
                      {violation.provenance.page ? `str. ${violation.provenance.page}` : violation.provenance.clause}
                    </span>
                  </div>
                  <p className="text-earth-200">{violation.description}</p>
                </div>
              ))}
            </div>
          </div>
          
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-earth-100 mb-4 flex items-center gap-2">
              <Info className="w-5 h-5 text-accent-info" />
              Fakty wyprowadzone
            </h3>
            <div className="space-y-2">
              {l1Feasibility.derivedFacts.map((fact, i) => (
                <div key={i} className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-accent-success mt-1 flex-shrink-0" />
                  <span className="text-earth-200 text-sm">{fact}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      
      {/* L2 Tab */}
      {activeTab === 'l2' && (
        <div className="space-y-6">
          <ScenarioChart scenarios={l2RiskDistribution.scenarios} />
          
          <BarChart
            data={l2RiskDistribution.scenarios.map(s => ({
              name: s.name,
              value: s.probability * 100,
              color: s.margin > 0 ? '#22C55E' : '#EF4444',
            }))}
            label="Prawdopodobieństwo scenariuszy"
          />
          
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-earth-100 mb-4">Dominujące czynniki ryzyka</h3>
            <div className="space-y-2">
              {l2RiskDistribution.dominantDrivers.map((driver, i) => (
                <div key={i} className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-accent-warning mt-1 flex-shrink-0" />
                  <span className="text-earth-200 text-sm">{driver}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      
      {/* L3 Tab */}
      {activeTab === 'l3' && (
        <div className="space-y-6">
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-earth-100 mb-4 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-accent-violet" />
              Wyjaśnienie AI (L3)
            </h3>
            <div className="text-earth-200 leading-relaxed whitespace-pre-wrap">
              {l3Explanation}
            </div>
          </div>
          
          <div className="grid grid-cols-3 gap-4">
            <div className="card p-4">
              <div className="text-sm text-earth-400 mb-1">Model lokalny</div>
              <div className="text-lg font-bold text-earth-100">Ollama</div>
              <div className="text-xs text-earth-400">Qwen3 14B + Gemma 4 12B</div>
            </div>
            <div className="card p-4">
              <div className="text-sm text-earth-400 mb-1">Model chmurowy</div>
              <div className="text-lg font-bold text-earth-100">Claude</div>
              <div className="text-xs text-earth-400">Bedrock eu-central-1</div>
            </div>
            <div className="card p-4">
              <div className="text-sm text-earth-400 mb-1">Prawd. marży ≥10%</div>
              <div className="text-lg font-bold text-accent-success">
                {(l2RiskDistribution.targetMarginProbability * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-earth-400">Przy obecnych założeniach</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
