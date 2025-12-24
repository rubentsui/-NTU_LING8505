import React, { useState, useEffect } from 'react';
import axios from 'axios';
import FileUpload from './components/FileUpload';
import ModelSelection from './components/ModelSelection';
import ColumnSelection from './components/ColumnSelection';
import ResultsVisualization from './components/ResultsVisualization';

const API_URL = 'http://localhost:8000';

function App() {
  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [columns, setColumns] = useState([]);
  const [selectedSource, setSelectedSource] = useState(null);
  const [selectedReference, setSelectedReference] = useState(null);
  const [selectedTargets, setSelectedTargets] = useState([]);
  const [selectedModels, setSelectedModels] = useState([]);

  const [isEvaluating, setIsEvaluating] = useState(false);
  const [results, setResults] = useState(null);
  const [estimatedTime, setEstimatedTime] = useState(null);
  const [progress, setProgress] = useState("");
  const [clientId] = useState(() => Math.random().toString(36).substring(7));

  const [availableModels, setAvailableModels] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await axios.get(`${API_URL}/models`);
        setAvailableModels(response.data);
        setError(null);
      } catch (error) {
        console.error("Failed to fetch models", error);
        setError("Failed to connect to backend. Is it running on http://localhost:8000?");
      }
    };
    fetchModels();
  }, []);

  // Models that require a reference column
  // Check if any selected model is in the 'Reference-based' category
  const isReferenceRequired = selectedModels.some(modelId => {
    const model = availableModels[modelId];
    return model && model.category === 'Reference-based';
  });

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`);
    ws.onmessage = (event) => {
      setProgress(event.data);
    };
    return () => ws.close();
  }, [clientId]);

  const [totalRows, setTotalRows] = useState(0);

  const handleUpload = async (uploadedFile) => {
    const formData = new FormData();
    formData.append('file', uploadedFile);

    try {
      const response = await axios.post(`${API_URL}/upload`, formData);
      setFile(uploadedFile);
      setColumns(response.data.columns);
      setTotalRows(response.data.total_rows);
      setStep(2);
    } catch (error) {
      console.error("Upload failed", error);
      alert("Upload failed: " + error.message);
    }
  };

  useEffect(() => {
    const fetchEstimate = async () => {
      if (totalRows > 0 && selectedModels.length > 0) {
        try {
          const response = await axios.post(`${API_URL}/estimate_time`, {
            rows: totalRows,
            models: selectedModels
          });
          setEstimatedTime(response.data.estimated_seconds);
        } catch (error) {
          console.error("Failed to get estimate", error);
        }
      } else {
        setEstimatedTime(null);
      }
    };
    fetchEstimate();
  }, [totalRows, selectedModels]);

  const formatTime = (seconds) => {
    if (seconds < 60) return `${Math.round(seconds)} seconds`;
    const minutes = Math.round(seconds / 60);
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
  };

  const handleEvaluate = async () => {
    setIsEvaluating(true);
    setProgress("Initializing evaluation...");
    try {
      const response = await axios.post(`${API_URL}/evaluate`, {
        filename: file.name,
        src_col: selectedSource,
        tgt_cols: selectedTargets,
        models: selectedModels,
        ref_col: selectedReference,
        client_id: clientId
      });
      setResults(response.data);
      setStep(3);
    } catch (error) {
      console.error("Evaluation failed", error);
      alert("Evaluation failed: " + error.message);
    } finally {
      setIsEvaluating(false);
      setProgress("");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-extrabold text-gray-900 sm:text-5xl sm:tracking-tight lg:text-6xl">
            MT Evaluation
          </h1>
          <p className="mt-5 max-w-xl mx-auto text-xl text-gray-500">
            Evaluate Machine Translation quality with state-of-the-art models.
          </p>

        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-6" role="alert">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        {/* Progress Steps */}
        <div className="mb-8 flex justify-center">
          <div className="flex items-center space-x-4">
            {[1, 2, 3].map(s => (
              <div key={s} className={`flex items-center ${s < 3 ? 'after:content-[""] after:h-1 after:w-12 after:bg-gray-200 after:mx-2' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${step >= s ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
                  {s}
                </div>
              </div>
            ))}
          </div>
        </div>

        {step === 1 && (
          <FileUpload onUpload={handleUpload} />
        )}

        {step === 2 && (
          <>
            <ModelSelection
              selectedModels={selectedModels}
              onModelChange={setSelectedModels}
              availableModels={availableModels}
            />
            <ColumnSelection
              columns={columns}
              selectedSource={selectedSource}
              selectedTargets={selectedTargets}
              selectedReference={selectedReference}
              onSourceChange={setSelectedSource}
              onTargetsChange={setSelectedTargets}
              onReferenceChange={setSelectedReference}
              isReferenceRequired={isReferenceRequired}
            />

            {estimatedTime !== null && (
              <div className="text-center mb-4 p-4 bg-blue-50 rounded-lg border border-blue-100 max-w-md mx-auto">
                <p className="text-blue-800 font-medium">
                  Estimated time: <span className="font-bold">{formatTime(estimatedTime)}</span>
                </p>
                <p className="text-xs text-blue-600 mt-1">
                  (Based on {totalRows} rows and your hardware)
                </p>
              </div>
            )}

            <div className="flex flex-col items-center mt-8">
              <button
                disabled={!selectedSource || selectedTargets.length === 0 || selectedModels.length === 0 || isEvaluating || (isReferenceRequired && !selectedReference)}
                onClick={handleEvaluate}
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-8 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isEvaluating ? 'Evaluating...' : 'Start Evaluation'}
              </button>

              {isEvaluating && (
                <div className="w-full max-w-md mt-6">
                  <div className="relative pt-1">
                    <div className="flex mb-2 items-center justify-between">
                      <div>
                        <span className="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-blue-600 bg-blue-200">
                          Processing
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-xs font-semibold inline-block text-blue-600">
                          {progress || "Please wait..."}
                        </span>
                      </div>
                    </div>
                    <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-blue-200">
                      <div className="animate-progress-indeterminate shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500"></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {step === 3 && (
          <ResultsVisualization results={results} filename={file ? file.name : ""} />
        )}
      </div>
    </div>
  );
}

export default App;
