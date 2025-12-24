import React from 'react';
import { Upload, BarChart3 } from 'lucide-react';
import './Header.css';

interface HeaderProps {
    onFileUpload: (file: File) => void;
    isUploading: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onFileUpload, isUploading }) => {
    const fileInputRef = React.useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            onFileUpload(file);
            // Reset input
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    return (
        <header className="header">
            <div className="container">
                <div className="header-content">
                    <div className="header-brand">
                        <div className="brand-icon">
                            <BarChart3 size={32} />
                        </div>
                        <div className="brand-text">
                            <h1 className="brand-title">Translation Quality Dashboard</h1>
                            <p className="brand-subtitle">多維度翻譯品質評估系統</p>
                        </div>
                    </div>

                    <div className="header-actions">
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".xlsx,.xls"
                            onChange={handleFileChange}
                            style={{ display: 'none' }}
                            id="file-upload"
                        />
                        <button
                            className="btn btn-primary"
                            onClick={() => fileInputRef.current?.click()}
                            disabled={isUploading}
                        >
                            <Upload size={18} />
                            {isUploading ? '上傳中...' : '上傳檔案'}
                        </button>
                    </div>
                </div>
            </div>
        </header>
    );
};
