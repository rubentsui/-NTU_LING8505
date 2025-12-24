import React from 'react';

const ColumnSelection = ({
    columns,
    selectedSource,
    selectedTargets,
    selectedReference,
    onSourceChange,
    onTargetsChange,
    onReferenceChange,
    isReferenceRequired
}) => {
    const handleTargetChange = (col) => {
        if (selectedTargets.includes(col)) {
            onTargetsChange(selectedTargets.filter(c => c !== col));
        } else {
            onTargetsChange([...selectedTargets, col]);
        }
    };

    return (
        <div className="w-full max-w-xl mx-auto mb-8">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Select Columns</h3>

                {/* Source Column */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Source Column (Original Text)</label>
                    <select
                        value={selectedSource || ''}
                        onChange={(e) => onSourceChange(e.target.value)}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    >
                        <option value="" disabled>Select a column...</option>
                        {columns.map(col => (
                            <option key={col} value={col}>{col}</option>
                        ))}
                    </select>
                </div>

                {/* Reference Column */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Reference Column
                        {isReferenceRequired ? <span className="text-red-500 ml-1">*</span> : <span className="text-gray-400 ml-1">(Optional)</span>}
                    </label>
                    <select
                        value={selectedReference || ''}
                        onChange={(e) => onReferenceChange(e.target.value)}
                        className={`w-full p-2 border rounded-md focus:ring-blue-500 focus:border-blue-500
                            ${isReferenceRequired && !selectedReference ? 'border-red-300' : 'border-gray-300'}
                        `}
                    >
                        <option value="">{isReferenceRequired ? "Select a column..." : "None"}</option>
                        {columns.map(col => (
                            <option key={col} value={col} disabled={col === selectedSource}>{col}</option>
                        ))}
                    </select>
                    {isReferenceRequired && !selectedReference && (
                        <p className="text-xs text-red-500 mt-1">Required for selected reference-based metrics.</p>
                    )}
                </div>

                {/* Target Columns */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Target Columns (Translations)</label>
                    <div className="space-y-2 max-h-48 overflow-y-auto border border-gray-200 rounded-md p-2">
                        {columns.map(col => (
                            <div key={col} className="flex items-center">
                                <input
                                    type="checkbox"
                                    id={`target-${col}`}
                                    checked={selectedTargets.includes(col)}
                                    onChange={() => handleTargetChange(col)}
                                    disabled={col === selectedSource || col === selectedReference}
                                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                />
                                <label htmlFor={`target-${col}`} className={`ml-2 block text-sm ${col === selectedSource || col === selectedReference ? 'text-gray-400' : 'text-gray-900'}`}>
                                    {col}
                                </label>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ColumnSelection;
