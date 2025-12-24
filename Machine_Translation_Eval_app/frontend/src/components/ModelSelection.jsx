import React, { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

const ModelSelection = ({ selectedModels, onModelChange, availableModels }) => {
    const [selectedCategory, setSelectedCategory] = useState(null);

    const categories = [
        { id: 'Quality Estimation', name: 'Quality Estimation', description: 'Reference-free evaluation' },
        { id: 'Reference-based', name: 'Reference-based', description: 'Requires reference translation' }
    ];

    // Group available models by category
    const modelsByCategory = {
        'Quality Estimation': [],
        'Reference-based': []
    };

    Object.entries(availableModels).forEach(([id, model]) => {
        if (modelsByCategory[model.category]) {
            modelsByCategory[model.category].push({
                id: id, // Ensure ID is passed explicitly
                name: model.model_name.split('/').pop(), // Simple name extraction
                description: model.type === 'comet' ? 'Comet model' : 'TransQuest model', // Basic description
                ...model
            });
        }
    });

    const toggleModel = (id) => {
        if (selectedModels.includes(id)) {
            onModelChange(selectedModels.filter(m => m !== id));
        } else {
            onModelChange([...selectedModels, id]);
        }
    };

    const [hfToken, setHfToken] = useState("");
    const [verificationStatus, setVerificationStatus] = useState(null); // 'success', 'error', 'loading'
    const [verificationMessage, setVerificationMessage] = useState("");

    const verifyToken = async () => {
        if (!hfToken) {
            setVerificationStatus('error');
            setVerificationMessage('Please enter a token');
            return;
        }
        setVerificationStatus('loading');
        setVerificationMessage('Verifying...');
        try {
            await axios.post(`${API_URL}/verify_token`, { token: hfToken });
            setVerificationStatus('success');
            setVerificationMessage('Token verified successfully!');
        } catch (error) {
            setVerificationStatus('error');
            setVerificationMessage(error.response?.data?.detail || 'Verification failed');
        }
    };

    return (
        <div className="w-full max-w-xl mx-auto mb-8">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Select Evaluation Models</h3>

            {/* Hugging Face Token Section */}
            <div className="mb-8 p-4 bg-white border border-gray-200 rounded-xl shadow-sm">
                <h4 className="text-md font-medium text-gray-700 mb-2">Hugging Face Token (Optional)</h4>
                <p className="text-sm text-gray-500 mb-3">
                    Required for gated models like CometKiwi.
                </p>
                <div className="flex gap-2">
                    <input
                        type="password"
                        value={hfToken}
                        onChange={(e) => setHfToken(e.target.value)}
                        placeholder="Enter Hugging Face Token"
                        className="flex-1 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                    <button
                        onClick={verifyToken}
                        disabled={verificationStatus === 'loading'}
                        className={`px-4 py-2 rounded-lg font-medium text-white transition-colors
                            ${verificationStatus === 'loading'
                                ? 'bg-gray-400 cursor-not-allowed'
                                : 'bg-gray-800 hover:bg-gray-900'}
                        `}
                    >
                        {verificationStatus === 'loading' ? 'Verifying...' : 'Verify'}
                    </button>
                </div>
                {verificationMessage && (
                    <p className={`text-sm mt-2 ${verificationStatus === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                        {verificationMessage}
                    </p>
                )}
            </div>

            {/* Category Selection */}
            <div className="flex space-x-4 mb-6">
                {categories.map((cat) => (
                    <button
                        key={cat.id}
                        onClick={() => setSelectedCategory(cat.id)}
                        className={`flex-1 p-4 rounded-xl border-2 transition-all duration-200 text-left
                            ${selectedCategory === cat.id
                                ? 'border-blue-500 bg-blue-50 shadow-md'
                                : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'}
                        `}
                    >
                        <p className="font-medium text-gray-900">{cat.name}</p>
                        <p className="text-sm text-gray-500 mt-1">{cat.description}</p>
                    </button>
                ))}
            </div>

            {/* Model Selection */}
            {selectedCategory && (
                <div className="space-y-3">
                    <h4 className="text-md font-medium text-gray-700 mb-2">
                        Available Models for {categories.find(c => c.id === selectedCategory).name}
                    </h4>
                    <div className="grid grid-cols-1 gap-3">
                        {modelsByCategory[selectedCategory].map((model) => (
                            <div
                                key={model.id}
                                onClick={() => toggleModel(model.id)}
                                className={`cursor-pointer p-4 rounded-xl border transition-all duration-200
                                    ${selectedModels.includes(model.id)
                                        ? 'border-blue-500 ring-2 ring-blue-500 bg-blue-100 shadow-md'
                                        : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm'}
                                `}
                            >
                                <div className="flex items-start justify-between">
                                    <div>
                                        <p className="font-medium text-gray-900">{model.name}</p>
                                        <p className="text-sm text-gray-500 mt-1">{model.description}</p>
                                    </div>
                                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center
                                        ${selectedModels.includes(model.id) ? 'border-blue-500 bg-blue-500' : 'border-gray-300'}
                                    `}>
                                        {selectedModels.includes(model.id) && (
                                            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                                            </svg>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                        {modelsByCategory[selectedCategory].length === 0 && (
                            <p className="text-gray-500 italic">No models available in this category.</p>
                        )}
                    </div>
                </div>
            )}

            {/* Summary of selected models */}
            {selectedModels.length > 0 && (
                <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-sm font-medium text-gray-700 mb-2">Selected Models:</p>
                    <div className="flex flex-wrap gap-2">
                        {selectedModels.map(id => {
                            const model = availableModels[id];
                            return (
                                <span key={id} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                    {model ? model.model_name.split('/').pop() : id}
                                </span>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

export default ModelSelection;
