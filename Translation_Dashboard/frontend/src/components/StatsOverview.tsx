import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { TrendingUp, BookOpen, Bot, Trophy } from 'lucide-react';
import { ModelStats } from '../types';
import './StatsOverview.css';

interface StatsOverviewProps {
    stats: { [modelName: string]: ModelStats };
    models: string[];
    availableMetrics: string[];
    metricTypes: { [key: string]: 'reference' | 'qe' };
    selectedMode: 'all' | 'reference' | 'qe';
}

export const StatsOverview: React.FC<StatsOverviewProps> = ({
    stats,
    models,
    availableMetrics,
    metricTypes,
    selectedMode
}) => {
    // Filter metrics based on selected mode
    const displayMetrics = selectedMode === 'all'
        ? availableMetrics
        : availableMetrics.filter(m => metricTypes[m] === selectedMode);

    // Helpers
    const isLowerBetter = (metric: string) => {
        const m = metric.toLowerCase();
        return m.includes('ter') || m.includes('mer');
    };

    const getMetricDescription = (metric: string) => {
        if (isLowerBetter(metric)) return "↓ Lower Score is Better";
        return "↑ Higher Score is Better";
    };

    // Calculate ranking to find winner
    const getSortedData = (metric: string) => {
        const data = models.map(model => ({
            name: model,
            value: stats[model]?.[metric] || 0
        }));

        // Sort for ranking logic (not for display, display follows model order)
        const sorted = [...data].sort((a, b) => {
            if (isLowerBetter(metric)) {
                return a.value - b.value;
            }
            return b.value - a.value;
        });

        const winnerName = sorted[0]?.name;

        return { chartData: data, winnerName };
    };

    return (
        <div className="stats-overview">
            <div className="stats-header">
                <div className="stats-title-group">
                    <TrendingUp size={24} className="stats-icon" />
                    <h2 className="stats-title">Performance by Metric</h2>
                </div>
                <p className="stats-subtitle">
                    Individual breakdown of each evaluation metric
                </p>
            </div>

            <div className="winners-grid">
                {displayMetrics.map(metric => {
                    const { chartData, winnerName } = getSortedData(metric);
                    const isRef = metricTypes[metric] === 'reference';

                    if (chartData.every(d => d.value === 0)) return null;

                    return (
                        <div key={metric} className="metric-card animate-scale-in">
                            <div className="metric-card-header">
                                <div className="metric-info">
                                    <span className="metric-name">{metric}</span>
                                    <span className="metric-description">
                                        {getMetricDescription(metric)}
                                    </span>
                                </div>
                                <div className="metric-icon">
                                    {isRef ? <BookOpen size={16} /> : <Bot size={16} />}
                                </div>
                            </div>

                            <div className="winner-banner">
                                <Trophy size={14} fill="#FFD700" color="#B8860B" />
                                <span>Winner: <strong>{winnerName}</strong></span>
                            </div>

                            <div className="mini-chart-container" style={{ width: '100%', height: 200, marginTop: '1rem' }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                                        <XAxis
                                            dataKey="name"
                                            tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }}
                                            interval={0}
                                        />
                                        <YAxis
                                            tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }}
                                            domain={['auto', 'auto']}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                backgroundColor: 'var(--color-bg-tertiary)',
                                                border: '1px solid var(--color-border)',
                                                fontSize: '12px'
                                            }}
                                            formatter={(val: number) => val.toFixed(4)}
                                        />
                                        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                                            {chartData.map((entry, index) => (
                                                <Cell
                                                    key={`cell-${index}`}
                                                    fill={entry.name === winnerName ? '#FFD700' : 'var(--color-primary)'}
                                                    opacity={entry.name === winnerName ? 1 : 0.6}
                                                />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
