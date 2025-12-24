import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { ColumnSelector } from './components/ColumnSelector';
import { StatsOverview } from './components/StatsOverview';
import { TranslationTable } from './components/TranslationTable';
import { api, ColumnPreview } from './api';
import { DashboardData } from './types';
import { AlertCircle, Loader } from 'lucide-react';
import './App.css';

function App() {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [columnPreview, setColumnPreview] = useState<ColumnPreview | null>(null);
    const [useManualSelection, setUseManualSelection] = useState(false);
    const selectedMode = 'all';

    console.log('App rendering');
    console.log('api object:', api);

    useEffect(() => {
        console.log('useEffect running');
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            setError(null);
            setSuccessMessage(null);
            const result = await api.fetchData();
            setData(result);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || '載入資料時發生錯誤');
        } finally {
            setLoading(false);
        }
    };



    const handleFileUpload = async (file: File) => {
        try {
            console.log('[Upload] 開始上傳檔案:', file.name, 'Size:', file.size, 'bytes');
            setUploading(true);
            setError(null);
            setSuccessMessage(null);

            // Always show column selector for user to choose
            console.log('[Upload] 正在載入欄位預覽...');
            const preview = await api.uploadFilePreview(file);
            console.log('[Upload] 欄位預覽載入成功:', {
                columns: preview.columns.length,
                rowCount: preview.row_count
            });

            setColumnPreview(preview);
            setUseManualSelection(true);
            setUploading(false);
        } catch (err: any) {
            console.error('[Upload] 上傳失敗:', err);
            console.error('[Upload] 錯誤詳情:', {
                message: err.message,
                response: err.response?.data,
                status: err.response?.status
            });
            setError(err.response?.data?.detail || err.message || '上傳檔案時發生錯誤');
            setUploading(false);
        }
    };

    const handleColumnConfigConfirm = async (config: any) => {
        try {
            console.log('[ColumnConfig] 處理使用者設定:', config);
            setUploading(true);
            setError(null);
            setColumnPreview(null);
            setUseManualSelection(false);

            const result = await api.processUploadedFile(config);
            console.log('[ColumnConfig] 處理成功:', {
                dataCount: result.data?.length,
                models: result.models,
                metrics: result.available_metrics,
            });

            setData(null);
            await new Promise(resolve => setTimeout(resolve, 100));
            setData(result);
            setSuccessMessage(`資料載入成功！已載入 ${result.data.length} 筆資料，${result.models.length} 個模型。`);
            setTimeout(() => setSuccessMessage(null), 5000);
        } catch (err: any) {
            console.error('[ColumnConfig] 處理失敗:', err);
            setError(err.response?.data?.detail || err.message || '處理資料時發生錯誤');
        } finally {
            setUploading(false);
        }
    };

    const handleColumnConfigCancel = () => {
        setColumnPreview(null);
        setUseManualSelection(false);
    };



    if (loading) {
        return (
            <div className="app">
                <Header onFileUpload={handleFileUpload} isUploading={uploading} />
                <main className="main-content">
                    <div className="container">
                        <div className="loading-state">
                            <Loader size={48} className="loading-spinner" />
                            <h2>載入中...</h2>
                            <p>正在讀取翻譯品質資料</p>
                        </div>
                    </div>
                </main>
            </div>
        );
    }

    if (error) {
        console.log('[Render] 顯示錯誤狀態:', error);
        return (
            <div className="app">
                <Header onFileUpload={handleFileUpload} isUploading={uploading} />
                <main className="main-content">
                    <div className="container">
                        <div className="error-state card">
                            <AlertCircle size={48} className="error-icon" />
                            <h2>發生錯誤</h2>
                            <p>{error}</p>
                            <button className="btn btn-primary" onClick={loadData}>
                                重試
                            </button>
                        </div>
                    </div>
                </main>
            </div>
        );
    }

    if (!data || data.data.length === 0) {
        console.log('[Render] 顯示空資料狀態, data:', data);
        return (
            <div className="app">
                <Header onFileUpload={handleFileUpload} isUploading={uploading} />
                <main className="main-content">
                    <div className="container">
                        <div className="empty-state card">
                            <AlertCircle size={48} className="empty-icon" />
                            <h2>沒有資料</h2>
                            <p>請上傳 Excel 檔案以開始分析翻譯品質</p>
                        </div>
                    </div>
                </main>
            </div>
        );
    }

    console.log('[Render] 顯示主要內容, data:', {
        dataCount: data.data.length,
        models: data.models,
        metrics: data.available_metrics,
        hasMetricTypes: !!data.metric_types
    });

    return (
        <div className="app">
            <Header onFileUpload={handleFileUpload} isUploading={uploading} />

            <main className="main-content">
                <div className="container">
                    {/* Success Message */}
                    {successMessage && (
                        <div className="alert alert-success animate-fade-in">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M10 0C4.48 0 0 4.48 0 10C0 15.52 4.48 20 10 20C15.52 20 20 15.52 20 10C20 4.48 15.52 0 10 0ZM8 15L3 10L4.41 8.59L8 12.17L15.59 4.58L17 6L8 15Z" fill="currentColor" />
                            </svg>
                            <span>{successMessage}</span>
                            <button onClick={() => setSuccessMessage(null)} className="alert-close">×</button>
                        </div>
                    )}

                    {/* Error Message */}
                    {error && (
                        <div className="alert alert-error animate-fade-in">
                            <AlertCircle size={20} />
                            <span>{error}</span>
                            <button onClick={() => setError(null)} className="alert-close">×</button>
                        </div>
                    )}

                    {/* Upload Loading State */}
                    {uploading && (
                        <div className="alert alert-info animate-fade-in">
                            <Loader size={20} className="loading-spinner" />
                            <span>正在上傳並分析檔案...</span>
                        </div>
                    )}

                    {/* Mode Selector and Dashboard - only show if new properties exist */}
                    {data.available_metrics && data.metric_types ? (
                        <>
                            <div className="dashboard-grid">
                                <section className="dashboard-section">
                                    <StatsOverview
                                        stats={data.stats}
                                        models={data.models}
                                        availableMetrics={data.available_metrics}
                                        metricTypes={data.metric_types}
                                        selectedMode={selectedMode}
                                    />
                                </section>

                                <section className="dashboard-section">
                                    <TranslationTable
                                        data={data.data}
                                        models={data.models}
                                        availableMetrics={data.available_metrics}
                                        metricTypes={data.metric_types}
                                        selectedMode={selectedMode}
                                    />
                                </section>
                            </div>
                        </>
                    ) : (
                        <div className="alert alert-info">
                            <span>正在載入新功能...</span>
                        </div>
                    )}
                </div>
            </main>

            <footer className="footer">
                <div className="container">
                    <p className="footer-text">
                        Translation Quality Dashboard © 2025 |
                        使用 <span className="gradient-text">FastAPI</span> + <span className="gradient-text">React</span> 建立
                    </p>
                </div>
            </footer>

            {/* Column Selector Modal */}
            {useManualSelection && columnPreview && (
                <ColumnSelector
                    preview={columnPreview}
                    onConfirm={handleColumnConfigConfirm}
                    onCancel={handleColumnConfigCancel}
                />
            )}
        </div>
    );
}

export default App;
