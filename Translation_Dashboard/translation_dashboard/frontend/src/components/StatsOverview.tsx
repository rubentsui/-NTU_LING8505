import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, Award, BookOpen, Bot, AlertCircle } from 'lucide-react';
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

    // Prepare chart data
    const chartData = models.map(model => {
        const data: any = { name: model };
        displayMetrics.forEach(metric => {
            const value = stats[model]?.[metric];
            data[metric] = value ? Number(value.toFixed(4)) : 0;
        });
        return data;
    });



    // Color palette for different metrics
    const metricColors: { [key: string]: string } = {
        // Reference-based metrics (Blues/Cyans/Greens)
        'BLEU': 'hsl(210, 84%, 54%)',       // Blue
        'ChrF': 'hsl(190, 84%, 45%)',       // Cyan
        'TER': 'hsl(0, 84%, 60%)',          // Red (often lower is better, distinguishing it)
        'METEOR': 'hsl(170, 70%, 45%)',     // Teal
        'ROUGE': 'hsl(330, 70%, 60%)',      // Pink
        'BERTScore': 'hsl(25, 85%, 55%)',   // Orange

        // Quality Estimation / Reference-free metrics (Purples/Violets/Indigos)
        'COMET': 'hsl(250, 84%, 54%)',      // Blue-Violet
        'TransQuest': 'hsl(280, 70%, 60%)', // Purple
        'BLEURT': 'hsl(240, 70%, 60%)',     // Indigo
        'COMET-KIWI': 'hsl(142, 76%, 46%)', // Green (distinct for QE)
        'COMETKIWI': 'hsl(142, 76%, 46%)',  // Green
        'MAHALANOBIS': 'hsl(30, 90%, 50%)', // Amber
    };

    const getMetricIcon = (metric: string) => {
        return metricTypes[metric] === 'reference' ? <BookOpen size={14} /> : <Bot size={14} />;
    };

    return (
        <div className="stats-overview">
            <div className="stats-header">
                <div className="stats-title-group">
                    <TrendingUp size={24} className="stats-icon" />
                    <h2 className="stats-title">模型效能總覽</h2>
                </div>
                <p className="stats-subtitle">
                    各翻譯模型的平均品質分數比較
                    {selectedMode !== 'all' && (
                        <span className="mode-badge">
                            {selectedMode === 'reference' ? (
                                <><BookOpen size={14} /> 有參考翻譯</>
                            ) : (
                                <><Bot size={14} /> 無參考翻譯 (QE)</>
                            )}
                        </span>
                    )}
                </p>
            </div>

            {/* Model Cards */}
            <div className="model-cards">
                {models.map((model, index) => {
                    const hasAnyScores = displayMetrics.some(metric => stats[model]?.[metric] !== undefined);

                    return (
                        <div
                            key={model}
                            className="model-card card-glass animate-fade-in"
                            style={{ animationDelay: `${index * 50}ms` }}
                        >
                            <div className="model-card-header">
                                <Award size={20} className="model-icon" />
                                <h3 className="model-name">{model}</h3>
                            </div>
                            <div className="model-scores">
                                {!hasAnyScores ? (
                                    <div className="no-scores-message" style={{
                                        padding: '1rem',
                                        textAlign: 'center',
                                        color: 'var(--color-text-muted)',
                                        fontSize: '0.875rem',
                                        fontStyle: 'italic'
                                    }}>
                                        <AlertCircle size={16} style={{ marginBottom: '0.5rem' }} />
                                        <p>此模型沒有評估分數</p>
                                        <p style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                                            請確認 Excel 檔案中包含此模型的評估指標欄位
                                        </p>
                                    </div>
                                ) : (
                                    displayMetrics.map((metric, idx) => {
                                        const score = stats[model]?.[metric];
                                        // Use defined color or generate one based on index (consistent with chart)
                                        const metricColor = metricColors[metric] || `hsl(${idx * 60}, 70%, 55%)`;

                                        return (
                                            <div key={metric} className="score-item">
                                                <div className="score-label-group">
                                                    <span className="score-label">{metric}</span>
                                                    <span className={`metric-type-badge ${metricTypes[metric]}`}>
                                                        {getMetricIcon(metric)}
                                                    </span>
                                                </div>
                                                <div className="score-value-group">
                                                    <span
                                                        className="score-value"
                                                        style={{ color: metricColor }}
                                                    >
                                                        {score?.toFixed(4) || 'N/A'}
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Chart */}
            {displayMetrics.length > 0 && (
                <div className="chart-container card">
                    <h3 className="chart-title">分數比較圖表</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                            <XAxis
                                dataKey="name"
                                stroke="var(--color-text-secondary)"
                                tick={{ fill: 'var(--color-text-secondary)' }}
                            />
                            <YAxis
                                stroke="var(--color-text-secondary)"
                                tick={{ fill: 'var(--color-text-secondary)' }}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: 'var(--color-bg-tertiary)',
                                    border: '1px solid var(--color-border)',
                                    borderRadius: 'var(--radius-md)',
                                    color: 'var(--color-text-primary)'
                                }}
                            />
                            <Legend
                                wrapperStyle={{
                                    color: 'var(--color-text-primary)'
                                }}
                            />
                            {displayMetrics.map((metric, index) => (
                                <Bar
                                    key={metric}
                                    dataKey={metric}
                                    fill={metricColors[metric] || `hsl(${index * 60}, 70%, 55%)`}
                                    radius={[8, 8, 0, 0]}
                                />
                            ))}
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
};
