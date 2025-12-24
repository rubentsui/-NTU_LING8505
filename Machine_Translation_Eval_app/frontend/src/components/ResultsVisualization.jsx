import React, { useMemo } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';
import { Scatter } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend
);

const ResultsVisualization = ({ results, filename }) => {
    if (!results || results.length === 0) return null;

    // Helper to identify and prepare chart data for each metric column
    const chartsData = useMemo(() => {
        if (results.length === 0) return [];
        const firstRow = results[0];
        const allKeys = Object.keys(firstRow);

        // Identify metric columns
        const metricColumns = allKeys.filter(key =>
            key.startsWith('ter_') ||
            key.startsWith('bertscore_') ||
            key.startsWith('sacrebleu_') ||
            key.startsWith('chrf_') ||
            key.includes('wmt22-cometkiwi-da') ||
            key.includes('wmt22-comet-da') ||
            key.includes('monotransquest')
        );

        const preparedData = metricColumns.map(col => {
            // Calculate Average
            const values = results.map(row => parseFloat(row[col]) || 0);
            const sum = values.reduce((acc, val) => acc + val, 0);
            const average = sum / values.length;

            // Scatter Data (Points)
            const scatterData = values.map((val, i) => ({ x: i + 1, y: val }));

            // Average Line Data (Line)
            // We create a line from x=0 to x=totalRows+1 to span the whole chart
            const averageLineData = [
                { x: 0, y: average },
                { x: values.length + 1, y: average }
            ];

            return {
                title: col,
                average: average,
                chartData: {
                    datasets: [
                        {
                            type: 'scatter',
                            label: 'Score',
                            data: scatterData,
                            backgroundColor: 'rgba(53, 162, 235, 0.6)',
                            borderColor: 'rgba(53, 162, 235, 1)',
                            pointRadius: 4,
                            pointHoverRadius: 6,
                        },
                        {
                            type: 'line',
                            label: `Average: ${average.toFixed(4)}`,
                            data: averageLineData,
                            borderColor: 'rgba(255, 99, 132, 0.8)',
                            borderWidth: 2,
                            borderDash: [6, 6],
                            pointRadius: 0, // No points on the average line
                            fill: false,
                        }
                    ]
                }
            };
        });

        return preparedData;
    }, [results]);

    const downloadExcel = () => {
        if (!filename) {
            alert("Filename not found.");
            return;
        }
        const resultFilename = `results_${filename}`;
        const downloadUrl = `http://localhost:8000/download/${resultFilename}`;

        // Trigger download
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.setAttribute('download', resultFilename);
        document.body.appendChild(link);
        link.click();
        link.remove();
    };

    return (
        <div className="w-full max-w-6xl mx-auto mt-8 space-y-12">
            <h3 className="text-3xl font-bold text-gray-800 mb-8 text-center">Evaluation Results</h3>

            <div className="grid grid-cols-1 gap-12">
                {chartsData.map((data, index) => (
                    <div key={index} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                        <h4 className="text-xl font-semibold text-gray-700 mb-4 text-center">{data.title}</h4>
                        <div className="h-96 w-full"> {/* Fixed height for uniformity */}
                            <Scatter
                                data={data.chartData}
                                options={{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    scales: {
                                        x: {
                                            type: 'linear',
                                            position: 'bottom',
                                            title: {
                                                display: true,
                                                text: 'Sentence Index'
                                            },
                                            min: 0,
                                            suggestedMax: results.length + 1
                                        },
                                        y: {
                                            title: {
                                                display: true,
                                                text: 'Score'
                                            },
                                            beginAtZero: true // Optional: depends if metrics can be negative, but usually 0-1 or 0-100
                                        }
                                    },
                                    plugins: {
                                        tooltip: {
                                            callbacks: {
                                                label: (context) => {
                                                    if (context.dataset.type === 'line') {
                                                        return `Average: ${context.parsed.y.toFixed(4)}`;
                                                    }
                                                    return `Sentence ${context.parsed.x}: ${context.parsed.y.toFixed(4)}`;
                                                }
                                            }
                                        }
                                    }
                                }}
                            />
                        </div>
                    </div>
                ))}
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <h4 className="text-2xl font-semibold text-gray-700 border-b pb-2 mb-4">Data Preview</h4>
                <div className="overflow-x-auto">
                    <div className="max-h-96 overflow-y-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50 sticky top-0">
                                <tr>
                                    {results.length > 0 && Object.keys(results[0]).map((header) => (
                                        <th key={header} scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">
                                            {header}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {results.slice(0, 100).map((row, rowIndex) => (
                                    <tr key={rowIndex}>
                                        {Object.values(row).map((cell, cellIndex) => (
                                            <td key={cellIndex} className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {typeof cell === 'number' ? cell.toFixed(4) : String(cell).substring(0, 50) + (String(cell).length > 50 ? '...' : '')}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {results.length > 100 && (
                        <div className="text-center py-2 text-sm text-gray-500 bg-gray-50">
                            Showing first 100 rows of {results.length}
                        </div>
                    )}
                </div>
            </div>

            <div className="flex justify-center pt-8">
                <button
                    className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-8 rounded-lg transition-colors shadow-lg flex items-center"
                    onClick={downloadExcel}
                >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download Results (.xlsx)
                </button>
            </div>
        </div>
    );
};

export default ResultsVisualization;
