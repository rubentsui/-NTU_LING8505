import React, { useState } from 'react';
import { Search, Filter, ChevronDown, ChevronUp, AlertCircle, BookOpen, Bot } from 'lucide-react';
import { TranslationItem, FilterOptions } from '../types';
import './TranslationTable.css';

interface TranslationTableProps {
    data: TranslationItem[];
    models: string[];
    availableMetrics: string[];
    metricTypes: { [key: string]: 'reference' | 'qe' };
    selectedMode: 'all' | 'reference' | 'qe';
}

export const TranslationTable: React.FC<TranslationTableProps> = ({
    data,
    models,
    availableMetrics,
    metricTypes,
    selectedMode
}) => {
    // Filter metrics based on selected mode
    const displayMetrics = selectedMode === 'all'
        ? availableMetrics
        : availableMetrics.filter(m => metricTypes[m] === selectedMode);

    const [filters, setFilters] = useState<FilterOptions>({
        searchQuery: '',
        selectedModels: models,
        selectedMetrics: displayMetrics,
        evaluationMode: selectedMode,
        minCOMET: 0,
        maxCOMET: 1,
        minTQ: 0,
        maxTQ: 1,
    });

    const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
    const [showFilters, setShowFilters] = useState(false);

    // Update filters when mode changes
    React.useEffect(() => {
        setFilters(prev => ({
            ...prev,
            selectedMetrics: displayMetrics,
            evaluationMode: selectedMode
        }));
    }, [selectedMode, displayMetrics.join(',')]);

    const toggleRow = (id: number) => {
        const newExpanded = new Set(expandedRows);
        if (newExpanded.has(id)) {
            newExpanded.delete(id);
        } else {
            newExpanded.add(id);
        }
        setExpandedRows(newExpanded);
    };

    const filteredData = data.filter(item => {
        // Search filter
        if (filters.searchQuery && !item.source.toLowerCase().includes(filters.searchQuery.toLowerCase())) {
            return false;
        }
        return true;
    });

    // Color palette for different metrics (consistent with StatsOverview)
    const metricColors: { [key: string]: string } = {
        // Reference-based metrics
        'BLEU': 'hsl(210, 84%, 54%)',       // Blue
        'ChrF': 'hsl(190, 84%, 45%)',       // Cyan
        'TER': 'hsl(0, 84%, 60%)',          // Red
        'METEOR': 'hsl(170, 70%, 45%)',     // Teal
        'ROUGE': 'hsl(330, 70%, 60%)',      // Pink
        'BERTScore': 'hsl(25, 85%, 55%)',   // Orange

        // Reference-free metrics
        'COMET': 'hsl(250, 84%, 54%)',      // Blue-Violet
        'TransQuest': 'hsl(280, 70%, 60%)', // Purple
        'BLEURT': 'hsl(240, 70%, 60%)',     // Indigo
        'COMET-KIWI': 'hsl(142, 76%, 46%)', // Green
        'COMETKIWI': 'hsl(142, 76%, 46%)',  // Green
        'MAHALANOBIS': 'hsl(30, 90%, 50%)', // Amber
    };

    const toggleModelFilter = (model: string) => {
        setFilters(prev => ({
            ...prev,
            selectedModels: prev.selectedModels.includes(model)
                ? prev.selectedModels.filter(m => m !== model)
                : [...prev.selectedModels, model]
        }));
    };

    const getMetricIcon = (metric: string) => {
        return metricTypes[metric] === 'reference' ? <BookOpen size={12} /> : <Bot size={12} />;
    };

    return (
        <div className="translation-table-container">
            <div className="table-header">
                <div className="table-title-group">
                    <h2 className="table-title">翻譯詳細資料</h2>
                    <span className="table-count">{filteredData.length} 筆資料</span>
                </div>

                <div className="table-controls">
                    <div className="search-box">
                        <Search size={18} className="search-icon" />
                        <input
                            type="text"
                            placeholder="搜尋原文..."
                            value={filters.searchQuery}
                            onChange={(e) => setFilters({ ...filters, searchQuery: e.target.value })}
                            className="search-input"
                        />
                    </div>

                    <button
                        className="btn btn-secondary"
                        onClick={() => setShowFilters(!showFilters)}
                    >
                        <Filter size={18} />
                        篩選
                    </button>
                </div>
            </div>

            {showFilters && (
                <div className="filters-panel card animate-fade-in">
                    <h3 className="filters-title">模型篩選</h3>
                    <div className="model-filters">
                        {models.map(model => (
                            <label key={model} className="checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={filters.selectedModels.includes(model)}
                                    onChange={() => toggleModelFilter(model)}
                                />
                                <span>{model}</span>
                            </label>
                        ))}
                    </div>
                </div>
            )}

            <div className="table-wrapper">
                {filteredData.length === 0 ? (
                    <div className="empty-state card">
                        <AlertCircle size={48} className="empty-icon" />
                        <h3>沒有找到資料</h3>
                        <p>請調整搜尋條件或上傳新的檔案</p>
                    </div>
                ) : (
                    <div className="translation-items">
                        {filteredData.map((item, index) => (
                            <div
                                key={item.id}
                                className="translation-item card animate-fade-in"
                                style={{ animationDelay: `${index * 30}ms` }}
                            >
                                <div className="item-header" onClick={() => toggleRow(item.id)}>
                                    <div className="item-source">
                                        <span className="item-id">#{item.id}</span>
                                        <div className="source-content">
                                            <p className="source-text">{item.source}</p>
                                            {item.reference && (
                                                <div className="reference-text">
                                                    <BookOpen size={14} />
                                                    <span>參考翻譯: {item.reference}</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    <button className="expand-btn">
                                        {expandedRows.has(item.id) ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                    </button>
                                </div>

                                {expandedRows.has(item.id) && (
                                    <div className="item-details animate-slide-in">
                                        {filters.selectedModels.map(model => {
                                            const modelData = item.models[model];
                                            if (!modelData) return null;

                                            return (
                                                <div key={model} className="model-translation">
                                                    <div className="model-header">
                                                        <h4 className="model-name-small">{model}</h4>
                                                        <div className="model-scores-inline">
                                                            {displayMetrics.map((metric, idx) => {
                                                                const score = modelData.scores[metric];
                                                                if (score === undefined) return null;

                                                                // Use defined color or generate one
                                                                const metricColor = metricColors[metric] || `hsl(${idx * 60}, 70%, 55%)`;

                                                                return (
                                                                    <span
                                                                        key={metric}
                                                                        className="score-text-item"
                                                                        style={{
                                                                            color: metricColor,
                                                                            display: 'inline-flex',
                                                                            alignItems: 'center',
                                                                            gap: '4px',
                                                                            marginRight: '12px',
                                                                            fontSize: '0.85rem',
                                                                            fontWeight: 500
                                                                        }}
                                                                    >
                                                                        <span className="metric-icon" style={{ opacity: 0.7 }}>
                                                                            {getMetricIcon(metric)}
                                                                        </span>
                                                                        {metric}: {score?.toFixed(4) || 'N/A'}
                                                                    </span>
                                                                );
                                                            })}
                                                        </div>
                                                    </div>
                                                    <p className="translation-text">{modelData.translation || '無翻譯'}</p>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
