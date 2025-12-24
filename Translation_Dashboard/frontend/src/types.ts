export interface TranslationModel {
    translation: string | null;
    scores: {
        [metricName: string]: number | null | undefined;
    };
}

export interface TranslationItem {
    id: number;
    source: string;
    reference?: string | null;  // Human reference translation (if exists)
    models: {
        [modelName: string]: TranslationModel;
    };
}

export interface ModelStats {
    [metricName: string]: number | undefined;
}

export interface DashboardData {
    data: TranslationItem[];
    stats: {
        [modelName: string]: ModelStats;
    };
    models: string[];
    available_metrics: string[];  // List of metrics present in data
    metric_types: {  // Metric type mapping
        [metricName: string]: 'reference' | 'qe';
    };
    has_reference: boolean;  // Whether reference translations exist
    mode: 'reference' | 'qe';  // Evaluation mode
}

export interface FilterOptions {
    searchQuery: string;
    selectedModels: string[];
    selectedMetrics: string[];  // Filter by metrics
    evaluationMode: 'all' | 'reference' | 'qe';  // Filter by evaluation type
    minCOMET: number;
    maxCOMET: number;
    minTQ: number;
    maxTQ: number;
}
