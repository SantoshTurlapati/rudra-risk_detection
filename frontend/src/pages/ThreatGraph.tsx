import React, { useEffect, useState } from 'react';
import {
  Share2, ZoomIn, ZoomOut, RotateCcw, Filter,
  Info, ShieldAlert, Globe, User, Smartphone, Phone, Flag
} from 'lucide-react';
import { api } from '../services/api';
import { ThreatGraphNode, ThreatGraphLink } from '../types';

export const ThreatGraph: React.FC = () => {
  const [nodes, setNodes] = useState<ThreatGraphNode[]>([]);
  const [links, setLinks] = useState<ThreatGraphLink[]>([]);
  const [selectedNode, setSelectedNode] = useState<ThreatGraphNode | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [zoom, setZoom] = useState<number>(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchGraph = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await api.getThreatGraph();
        setNodes(data.nodes);
        setLinks(data.links);
        setSelectedNode(data.nodes[0] || null);
      } catch (err) {
        console.error("Failed to load threat graph", err);
        setError('The evidence graph could not be loaded. Please retry.');
      } finally {
        setLoading(false);
      }
    };
    fetchGraph();
  }, []);

  const getNodePos = (index: number, total: number) => {
    if (total <= 1) return { x: 300, y: 220 };
    const angle = index * ((2 * Math.PI) / total) - Math.PI / 2;
    const radius = 170;
    return {
      x: 300 + radius * Math.cos(angle),
      y: 220 + radius * Math.sin(angle)
    };
  };

  const nodeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'brand': return '#087CF0';
      case 'domain': return '#EF4444';
      case 'social profile': return '#F59E0B';
      case 'campaign': return '#8B5CF6';
      case 'app': return '#EC4899';
      case 'mobile app': return '#EC4899';
      case 'contact': return '#12B981';
      case 'message': return '#12B981';
      case 'url': return '#EF4444';
      case 'website': return '#EF4444';
      case 'investigation': return '#657792';
      default: return '#657792';
    }
  };

  const filteredNodes = nodes.filter(n => (
    filterType === 'all'
    || (filterType === 'app' && ['app', 'mobile app'].includes(n.type.toLowerCase()))
    || n.type.toLowerCase() === filterType.toLowerCase()
  ));
  const visibleNodeIds = new Set(filteredNodes.map(node => node.id));

  useEffect(() => {
    if (!filteredNodes.some(node => node.id === selectedNode?.id)) {
      setSelectedNode(filteredNodes[0] || null);
    }
  }, [filterType, nodes]);

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#102447] flex items-center gap-2">
            <Share2 className="w-5 h-5 text-[#087CF0]" />
            Interactive Threat &amp; Evidence Graph
          </h1>
          <p className="text-xs text-[#657792] mt-0.5">
            Saved investigations, recorded evidence relationships, and possible exact matches; not independent attribution
          </p>
        </div>

        {/* Filter controls */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-[#657792]">Filter:</span>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="text-xs font-semibold px-3 py-1.5 bg-white border border-[#DCE7F5] rounded-xl text-[#102447] focus:outline-none"
          >
            <option value="all">All Entity Types</option>
            <option value="brand">Brands</option>
            <option value="domain">Domains</option>
            <option value="url">URLs</option>
            <option value="website">Websites</option>
            <option value="social profile">Social Profiles</option>
            <option value="message">Messages</option>
            <option value="campaign">Campaigns</option>
            <option value="app">Mobile Apps</option>
            <option value="investigation">Investigations</option>
          </select>
        </div>
      </div>

      {error && (
        <div role="alert" className="flex flex-col items-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-xl bg-red-600 px-4 py-2 font-semibold text-white hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      )}

      {loading && (
        <div role="status" className="rounded-2xl border border-[#DCE7F5] bg-white p-8 text-center text-sm font-medium text-[#657792]">
          Loading recorded evidence graph...
        </div>
      )}

      {!loading && !error && nodes.length === 0 && (
        <div className="rounded-2xl border border-dashed border-[#DCE7F5] bg-white p-10 text-center">
          <p className="text-sm font-semibold text-[#102447]">No graph evidence is recorded yet.</p>
          <p className="mt-1 text-xs text-[#657792]">Saved investigations and explicitly recorded relationships will appear here.</p>
        </div>
      )}

      {!loading && !error && nodes.length > 0 && (
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* SVG Graph Viewport */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-[#DCE7F5] shadow-card p-4 relative overflow-hidden h-[540px]">

          {/* Zoom Controls */}
          <div className="absolute top-4 right-4 z-20 flex items-center gap-1.5 bg-white/90 backdrop-blur-sm border border-[#DCE7F5] p-1 rounded-xl shadow-sm">
            <button
              onClick={() => setZoom(prev => Math.min(prev + 0.15, 1.8))}
              className="p-1.5 text-[#657792] hover:text-[#087CF0]"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom(prev => Math.max(prev - 0.15, 0.6))}
              className="p-1.5 text-[#657792] hover:text-[#087CF0]"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom(1)}
              className="p-1.5 text-[#657792] hover:text-[#087CF0]"
              title="Reset Zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 z-20 flex flex-wrap gap-2 text-[10px] font-semibold bg-white/90 backdrop-blur-sm border border-[#DCE7F5] px-3 py-2 rounded-xl shadow-sm">
            <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#087CF0]" /> Brand</div>
            <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#EF4444]" /> Domain</div>
            <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" /> Social Profile</div>
            <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#EF4444]" /> URL / Website</div>
            <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#8B5CF6]" /> Campaign</div>
            <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#EC4899]" /> App</div>
            <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#12B981]" /> Contact</div>
            <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#12B981]" /> Message</div>
            <div className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#657792]" /> Image / Other</div>
          </div>

          {/* SVG Canvas */}
          <svg
            className="w-full h-full select-none cursor-move transition-transform duration-150"
            viewBox="0 0 600 440"
            style={{ transform: `scale(${zoom})`, transformOrigin: 'center center' }}
          >
            {/* Edges */}
            {links.filter(link => visibleNodeIds.has(link.source) && visibleNodeIds.has(link.target)).map((link) => {
              const srcIdx = nodes.findIndex(n => n.id === link.source);
              const tgtIdx = nodes.findIndex(n => n.id === link.target);
              if (srcIdx < 0 || tgtIdx < 0) return null;
              const p1 = getNodePos(srcIdx, nodes.length);
              const p2 = getNodePos(tgtIdx, nodes.length);

              const midX = (p1.x + p2.x) / 2;
              const midY = (p1.y + p2.y) / 2;

              return (
                <g key={link.id}>
                  <line
                    x1={p1.x} y1={p1.y}
                    x2={p2.x} y2={p2.y}
                    stroke={link.relationship_status === 'possible' ? '#F59E0B' : '#087CF0'}
                    strokeWidth="2"
                    strokeDasharray={link.relationship_status === 'possible' ? '5 4' : undefined}
                  />
                  {/* Relationship Label */}
                  <rect
                    x={midX - 35} y={midY - 8}
                    width="70" height="16"
                    rx="4" fill="#FFFFFF"
                    stroke="#DCE7F5"
                  />
                  <text
                    x={midX} y={midY + 3}
                    fontSize="8"
                    fill="#657792"
                    fontWeight="700"
                    textAnchor="middle"
                  >
                    {link.relationship_type.replace(/_/g, ' ')}
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {filteredNodes.map((node) => {
              const originalIdx = nodes.findIndex(n => n.id === node.id);
              const pos = getNodePos(originalIdx, nodes.length);
              const isSelected = selectedNode?.id === node.id;
              const color = nodeColor(node.type);

              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onClick={() => setSelectedNode(node)}
                  className="cursor-pointer transition-transform hover:scale-110"
                >
                  {/* Outer selection ring */}
                  {isSelected && (
                    <circle r="30" fill="none" stroke="#087CF0" strokeWidth="2.5" strokeDasharray="3 3" className="animate-spin" />
                  )}
                  {/* Node Circle */}
                  <circle
                    r="22"
                    fill={color}
                    stroke="#FFFFFF"
                    strokeWidth="3"
                    className="drop-shadow-md"
                  />
                  {/* Inner Initial */}
                  <text
                    x="0" y="4"
                    fontSize="11"
                    fontWeight="800"
                    fill="#FFFFFF"
                    textAnchor="middle"
                  >
                    {node.name[0]?.toUpperCase() || '?'}
                  </text>
                  {/* Label under node */}
                  <text
                    x="0" y="34"
                    fontSize="10"
                    fontWeight="600"
                    fill="#102447"
                    textAnchor="middle"
                    className="bg-white px-1"
                  >
                    {node.name.length > 15 ? node.name.slice(0, 13) + '..' : node.name}
                  </text>
                </g>
              );
            })}
              {filteredNodes.length === 0 && (
                <text x="300" y="220" textAnchor="middle" fontSize="12" fill="#657792">
                  No nodes match this filter.
                </text>
              )}
          </svg>

        </div>

        {/* Right Entity Inspector Drawer */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-[#DCE7F5] shadow-card p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#DCE7F5]">
            <h3 className="text-sm font-bold text-[#102447] flex items-center gap-2">
              <Info className="w-4 h-4 text-[#087CF0]" />
              Entity Inspector
            </h3>
            {selectedNode && (
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${
                selectedNode.risk_score == null ? 'bg-gray-100 text-gray-700' :
                selectedNode.risk_score >= 70 ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
              }`}>
                Score: {selectedNode.risk_score == null ? 'Not assessed' : `${selectedNode.risk_score}/100`}
              </span>
            )}
          </div>

          {selectedNode ? (
            <div className="space-y-4 text-xs">
              {selectedNode.details?.case_number && (
                <div>
                  <p className="text-[10px] font-bold text-[#657792] uppercase">Investigation</p>
                  <p className="font-mono font-bold text-[#087CF0] mt-0.5">{selectedNode.details.case_number}</p>
                  <p className="mt-0.5 text-[#657792]">
                    {selectedNode.details.status || 'Status unavailable'} · {selectedNode.details.severity || 'Severity unavailable'}
                  </p>
                </div>
              )}
              <div>
                <p className="text-[10px] font-bold text-[#657792] uppercase">Entity Name</p>
                <p className="text-sm font-bold text-[#102447] mt-0.5">{selectedNode.name}</p>
              </div>

              <div>
                <p className="text-[10px] font-bold text-[#657792] uppercase">Classification Type</p>
                <p className="font-semibold text-[#087CF0] mt-0.5">{selectedNode.type}</p>
              </div>

              <div>
                <p className="text-[10px] font-bold text-[#657792] uppercase">Indicator Reference</p>
                <p className="font-mono bg-[#F8FAFC] p-2 rounded-lg border border-[#E2E8F0] text-[#102447] mt-0.5 break-all">
                  {selectedNode.indicator || 'N/A'}
                </p>
              </div>

              {/* Connected Relationships list */}
              <div>
                <p className="text-[10px] font-bold text-[#657792] uppercase mb-1.5">Recorded Relationships and Possible Matches</p>
                <div className="space-y-1.5">
                  {links
                    .filter(l => l.source === selectedNode.id || l.target === selectedNode.id)
                    .map((edge) => {
                      const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                      const otherNode = nodes.find(n => n.id === otherId);
                      return (
                        <div key={edge.id} className="p-2 bg-[#F1F7FF] rounded-lg border border-[#D0E4FA] flex items-center justify-between text-[11px]">
                          <div className="min-w-0">
                            <p className="truncate font-semibold text-[#102447]">{otherNode?.name || 'Entity'}</p>
                            <p className="font-mono text-[#087CF0]">{edge.relationship_type.replace(/_/g, ' ')}</p>
                            {edge.details?.basis && (
                              <p className="mt-0.5 text-[10px] font-normal text-[#657792]">{edge.details.basis}</p>
                            )}
                          </div>
                          <span className={`ml-2 shrink-0 rounded-full px-2 py-0.5 text-[9px] font-bold ${
                            edge.relationship_status === 'possible'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}>
                            {edge.relationship_status === 'possible' ? 'Possible' : 'Recorded'}
                          </span>
                        </div>
                      );
                    })}
                </div>
              </div>

              {selectedNode.details?.evidence?.length ? (
                <div>
                  <p className="text-[10px] font-bold text-[#657792] uppercase mb-1.5">Saved Evidence</p>
                  <ul className="list-disc space-y-1 pl-4 text-[#334155]">
                    {selectedNode.details.evidence.map((item, index) => <li key={index}>{item}</li>)}
                  </ul>
                </div>
              ) : null}

            </div>
          ) : (
            <p className="text-xs text-[#657792]">Click on any node in the graph to inspect evidence and stored edges.</p>
          )}

        </div>
      </div>
      )}

    </div>
  );
};
