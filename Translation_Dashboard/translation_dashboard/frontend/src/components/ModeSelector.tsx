import React from 'react';
import { BookOpen, Bot, Sparkles } from 'lucide-react';
import './ModeSelector.css';

interface ModeSelectorProps {
    currentMode: 'all' | 'reference' | 'qe';
    availableMetrics: string[];
    metricTypes: { [key: string]: 'reference' | 'qe' };
    hasReference: boolean;
    onModeChange: (mode: 'all' | 'reference' | 'qe') => void;
}

export const ModeSelector: React.FC<ModeSelectorProps> = ({
    currentMode,
    availableMetrics,
    metricTypes,
    hasReference,
    onModeChange,
}) => {
    const referenceMetrics = availableMetrics.filter(m => metricTypes[m] === 'reference');
    const qeMetrics = availableMetrics.filter(m => metricTypes[m] === 'qe');

    const hasReferenceMetrics = referenceMetrics.length > 0;
    const hasQEMetrics = qeMetrics.length > 0;

    return (
        <div className="mode-selector card-glass">
            <div className="mode-selector-header">
                <Sparkles size={20} className="mode-icon" />
                <h3 className="mode-title">評估模式</h3>
            </div>

            <div className="mode-tabs">
                <button
                    className={`mode-tab ${currentMode === 'all' ? 'active' : ''}`}
                    onClick={() => onModeChange('all')}
                >
                    <div className="mode-tab-content">
                        <Sparkles size={18} />
                        <span>全部指標</span>
                    </div>
                    <div className="mode-tab-metrics">
                        {availableMetrics.length} 個指標
                    </div>
                </button>

                {hasReferenceMetrics && (
                    <button
                        className={`mode-tab mode-tab-reference ${currentMode === 'reference' ? 'active' : ''}`}
                        onClick={() => onModeChange('reference')}
                        disabled={!hasReferenceMetrics}
                    >
                        <div className="mode-tab-content">
                            <BookOpen size={18} />
                            <span>有參考翻譯</span>
                        </div>
                        <div className="mode-tab-metrics">
                            {referenceMetrics.join(', ')}
                        </div>
                    </button>
                )}

                {hasQEMetrics && (
                    <button
                        className={`mode-tab mode-tab-qe ${currentMode === 'qe' ? 'active' : ''}`}
                        onClick={() => onModeChange('qe')}
                        disabled={!hasQEMetrics}
                    >
                        <div className="mode-tab-content">
                            <Bot size={18} />
                            <span>無參考翻譯 (QE)</span>
                        </div>
                        <div className="mode-tab-metrics">
                            {qeMetrics.join(', ')}
                        </div>
                    </button>
                )}
            </div>

            {hasReference && (
                <div className="mode-info">
                    <div className="info-badge">
                        <BookOpen size={14} />
                        <span>資料包含人工參考翻譯</span>
                    </div>
                </div>
            )}
        </div>
    );
};
