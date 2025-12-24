import React, { useState } from 'react';
import { ColumnPreview } from '../api';
import { X, Plus, Trash2, CheckCircle } from 'lucide-react';
import './ColumnSelector.css';

interface ModelConfig {
    id: string;
    name: string;
    text_column: string;
    metric_columns: Record<string, string>;
}

interface ColumnSelectorProps {
    preview: ColumnPreview;
    onConfirm: (config: any) => void;
    onCancel: () => void;
}

const COMMON_METRICS = [
    'BLEU',
    'BLEURT',
    'COMET',
    'COMET-KIWI',
    'TransQuest',
    'chrF',
    'TER',
    'METEOR',
    'BERTScore'
];

export const ColumnSelector: React.FC<ColumnSelectorProps> = ({ preview, onConfirm, onCancel }) => {
    const [sourceColumn, setSourceColumn] = useState<string>('');
    const [referenceColumn, setReferenceColumn] = useState<string>('');
    const [models, setModels] = useState<ModelConfig[]>([]);
    const [nextId, setNextId] = useState(1);

    // Auto-detect columns on mount
    React.useEffect(() => {
        autoDetectColumns();
    }, [preview]);

    const autoDetectColumns = () => {
        const cols = preview.columns;

        // Try to find source column (en, english, source, etc.)
        const sourceCol = cols.find(c =>
            c.toLowerCase() === 'en' ||
            c.toLowerCase() === 'english' ||
            c.toLowerCase().includes('source')
        );
        if (sourceCol) setSourceColumn(sourceCol);

        // Try to find reference column
        const refCol = cols.find(c =>
            c.toLowerCase().includes('reference') ||
            c.toLowerCase() === 'zh_reference'
        );
        if (refCol) setReferenceColumn(refCol);

        // Try to auto-detect models
        const detectedModels: ModelConfig[] = [];
        const textColumns = cols.filter(c => {
            const lower = c.toLowerCase();
            // Look for columns that might be translations
            return (lower.startsWith('zh(') || lower.includes('translation')) &&
                !lower.includes('bleu') &&
                !lower.includes('comet') &&
                !lower.includes('bleurt') &&
                !lower.includes('transquest') &&
                !lower.includes('bert');
        });

        textColumns.forEach((textCol, idx) => {
            const modelName = textCol.replace(/^zh\(/, '').replace(/\)$/, '').replace('translation_', '');
            const metricCols: Record<string, string> = {};

            // Try to find metric columns for this model
            COMMON_METRICS.forEach(metric => {
                const metricCol = cols.find(c => {
                    const lower = c.toLowerCase();
                    return lower.includes(textCol.toLowerCase()) &&
                        lower.includes(metric.toLowerCase());
                });
                if (metricCol) {
                    metricCols[metric] = metricCol;
                }
            });

            detectedModels.push({
                id: `model-${idx}`,
                name: modelName || `Model ${idx + 1}`,
                text_column: textCol,
                metric_columns: metricCols
            });
        });

        if (detectedModels.length > 0) {
            setModels(detectedModels);
            setNextId(detectedModels.length);
        }
    };

    const addModel = () => {
        setModels([...models, {
            id: `model-${nextId}`,
            name: `Model ${nextId}`,
            text_column: '',
            metric_columns: {}
        }]);
        setNextId(nextId + 1);
    };

    const removeModel = (id: string) => {
        setModels(models.filter(m => m.id !== id));
    };

    const updateModel = (id: string, field: keyof ModelConfig, value: any) => {
        setModels(models.map(m => m.id === id ? { ...m, [field]: value } : m));
    };

    const addMetricToModel = (modelId: string, metricName: string) => {
        setModels(models.map(m => {
            if (m.id === modelId) {
                return {
                    ...m,
                    metric_columns: { ...m.metric_columns, [metricName]: '' }
                };
            }
            return m;
        }));
    };

    const removeMetricFromModel = (modelId: string, metricName: string) => {
        setModels(models.map(m => {
            if (m.id === modelId) {
                const newMetrics = { ...m.metric_columns };
                delete newMetrics[metricName];
                return { ...m, metric_columns: newMetrics };
            }
            return m;
        }));
    };

    const updateMetricColumn = (modelId: string, metricName: string, columnName: string) => {
        setModels(models.map(m => {
            if (m.id === modelId) {
                return {
                    ...m,
                    metric_columns: { ...m.metric_columns, [metricName]: columnName }
                };
            }
            return m;
        }));
    };

    const handleConfirm = () => {
        const config = {
            temp_path: preview.temp_path,
            source_column: sourceColumn || undefined,
            reference_column: referenceColumn || undefined,
            model_columns: models.map(m => ({
                name: m.name,
                text_column: m.text_column,
                metric_columns: m.metric_columns
            }))
        };
        onConfirm(config);
    };

    const isValid = () => {
        // At least one model with a text column
        return models.length > 0 && models.every(m => m.name && m.text_column);
    };

    return (
        <div className="column-selector-overlay">
            <div className="column-selector-modal">
                <div className="modal-header">
                    <h2>設定欄位對應</h2>
                    <button className="close-btn" onClick={onCancel}>
                        <X size={24} />
                    </button>
                </div>

                <div className="modal-body">
                    <div className="file-info">
                        <p><strong>檔案名稱：</strong>{preview.filename}</p>
                        <p><strong>資料筆數：</strong>{preview.row_count} 筆</p>
                    </div>

                    {/* Basic Columns */}
                    <div className="config-section">
                        <h3>基本欄位</h3>

                        <div className="form-group">
                            <label>來源文本欄位（英文）</label>
                            <select
                                value={sourceColumn}
                                onChange={(e) => setSourceColumn(e.target.value)}
                                className="form-select"
                            >
                                <option value="">-- 選擇欄位 --</option>
                                {preview.columns.map(col => (
                                    <option key={col} value={col}>{col}</option>
                                ))}
                            </select>
                            {sourceColumn && preview.sample_data[sourceColumn] && (
                                <div className="sample-preview">
                                    <small>範例：{preview.sample_data[sourceColumn][0]}</small>
                                </div>
                            )}
                        </div>

                        <div className="form-group">
                            <label>參考翻譯欄位（選填）</label>
                            <select
                                value={referenceColumn}
                                onChange={(e) => setReferenceColumn(e.target.value)}
                                className="form-select"
                            >
                                <option value="">-- 無參考翻譯 --</option>
                                {preview.columns.map(col => (
                                    <option key={col} value={col}>{col}</option>
                                ))}
                            </select>
                            {referenceColumn && preview.sample_data[referenceColumn] && (
                                <div className="sample-preview">
                                    <small>範例：{preview.sample_data[referenceColumn][0]}</small>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Models */}
                    <div className="config-section">
                        <div className="section-header">
                            <h3>翻譯模型</h3>
                            <button className="btn btn-secondary btn-sm" onClick={addModel}>
                                <Plus size={16} /> 新增模型
                            </button>
                        </div>

                        {models.length === 0 && (
                            <div className="empty-state-small">
                                <p>尚未設定任何模型，請點擊「新增模型」開始</p>
                            </div>
                        )}

                        {models.map((model, idx) => (
                            <div key={model.id} className="model-config-card">
                                <div className="model-header">
                                    <h4>模型 {idx + 1}</h4>
                                    <button
                                        className="btn-icon-danger"
                                        onClick={() => removeModel(model.id)}
                                        title="刪除模型"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>

                                <div className="form-group">
                                    <label>模型名稱</label>
                                    <input
                                        type="text"
                                        value={model.name}
                                        onChange={(e) => updateModel(model.id, 'name', e.target.value)}
                                        className="form-input"
                                        placeholder="例如：GPT-4, Claude, etc."
                                    />
                                </div>

                                <div className="form-group">
                                    <label>翻譯文本欄位 *</label>
                                    <select
                                        value={model.text_column}
                                        onChange={(e) => updateModel(model.id, 'text_column', e.target.value)}
                                        className="form-select"
                                    >
                                        <option value="">-- 選擇欄位 --</option>
                                        {preview.columns.map(col => (
                                            <option key={col} value={col}>{col}</option>
                                        ))}
                                    </select>
                                    {model.text_column && preview.sample_data[model.text_column] && (
                                        <div className="sample-preview">
                                            <small>範例：{preview.sample_data[model.text_column][0]}</small>
                                        </div>
                                    )}
                                </div>

                                <div className="metrics-section">
                                    <div className="metrics-header">
                                        <label>評分指標</label>
                                        <select
                                            onChange={(e) => {
                                                if (e.target.value) {
                                                    addMetricToModel(model.id, e.target.value);
                                                    e.target.value = '';
                                                }
                                            }}
                                            className="form-select-sm"
                                        >
                                            <option value="">+ 新增指標</option>
                                            {COMMON_METRICS.filter(m => !model.metric_columns[m]).map(metric => (
                                                <option key={metric} value={metric}>{metric}</option>
                                            ))}
                                        </select>
                                    </div>

                                    {Object.keys(model.metric_columns).length === 0 && (
                                        <p className="hint-text">此模型尚未設定評分指標</p>
                                    )}

                                    {Object.entries(model.metric_columns).map(([metricName, columnName]) => (
                                        <div key={metricName} className="metric-row">
                                            <span className="metric-name">{metricName}</span>
                                            <select
                                                value={columnName}
                                                onChange={(e) => updateMetricColumn(model.id, metricName, e.target.value)}
                                                className="form-select-sm flex-1"
                                            >
                                                <option value="">-- 選擇欄位 --</option>
                                                {preview.columns.map(col => (
                                                    <option key={col} value={col}>{col}</option>
                                                ))}
                                            </select>
                                            <button
                                                className="btn-icon-danger-sm"
                                                onClick={() => removeMetricFromModel(model.id, metricName)}
                                                title="移除指標"
                                            >
                                                <X size={14} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="modal-footer">
                    <button className="btn btn-secondary" onClick={onCancel}>
                        取消
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={handleConfirm}
                        disabled={!isValid()}
                    >
                        <CheckCircle size={18} />
                        確認並載入資料
                    </button>
                </div>
            </div>
        </div>
    );
};
