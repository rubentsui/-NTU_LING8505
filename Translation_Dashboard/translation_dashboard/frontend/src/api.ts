import axios from 'axios';
import { DashboardData } from './types';

const API_BASE_URL = '/api';

export interface ColumnPreview {
    filename: string;
    temp_path: string;
    columns: string[];
    sample_data: Record<string, any[]>;
    row_count: number;
}

export interface ColumnConfig {
    temp_path: string;
    source_column?: string;
    reference_column?: string;
    model_columns: Array<{
        name: string;
        text_column: string;
        metric_columns: Record<string, string>;
    }>;
}

export const api = {
    async fetchData(): Promise<DashboardData> {
        const response = await axios.get(`${API_BASE_URL}/data`);
        return response.data;
    },

    async uploadFile(file: File): Promise<DashboardData> {
        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });

        return response.data;
    },

    async uploadFilePreview(file: File): Promise<ColumnPreview> {
        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(`${API_BASE_URL}/upload/preview`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });

        return response.data;
    },

    async processUploadedFile(config: ColumnConfig): Promise<DashboardData> {
        const response = await axios.post(`${API_BASE_URL}/upload/process`, config);
        return response.data;
    },
};
