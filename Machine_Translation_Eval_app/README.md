# MT Evaluation Engine

A powerful, local web application for evaluating Machine Translation (MT) outputs using state-of-the-art metrics. This tool provides a user-friendly interface to run advanced evaluation metrics like COMET and TransQuest without writing code.

![Tech Stack](https://img.shields.io/badge/Tech-FastAPI%20%7C%20React%20%7C%20Vite%20%7C%20PyTorch-blue)

## 🚀 Features

-   **Multi-Metric Evaluation**: Support for industry-standard metrics:
    -   **COMET**: Neural framework for MT evaluation (Reference-based and Reference-free/QE).
    -   **TransQuest**: Quality Estimation (QE) for sentence-level translation quality.
    -   **SacreBLEU**: Standard BLEU scores.
    -   **TER**: Translation Edit Rate.
    -   **chrF**: Character n-gram F-score.
    -   **BERTScore**: Contextual embedding-based similarity.
-   **Excel Integration**: Seamlessly upload `.xlsx` files and download results in the same format.
-   **Interactive UI**:
    -   Dynamic column selection for Source, Reference, and Translations.
    -   Model selection based on metric types.
-   **Real-time Progress**: WebSocket integration for live status updates during heavy model evaluations.
-   **Privacy Focused**: Runs entirely locally on your machine. Data never leaves your system.

## 🛠️ Prerequisites

-   **Python**: 3.8 or higher
-   **Node.js**: 16.x or higher
-   **GPU**: Recommended (CUDA-capable) for faster evaluation with COMET/TransQuest, but runs on CPU as well.

## 🔐 Authentication

To use models gated by Hugging Face (like `cometkiwi`), you need to provide your authentication token. You can do this in two ways:

### Option 1: Via the Application UI (Recommended)
You can directly input your Hugging Face token in the web interface during **Step 2 (Model Selection)**.
1.  Start the evaluation process.
2.  In Step 2, locate the "Hugging Face Token" input field.
3.  Paste your token and click "Verify".

### Option 2: Via Environment Variable
Set the `HF_TOKEN` environment variable before running the backend.
-   **Windows (PowerShell)**: `$env:HF_TOKEN="your_token_here"`
-   **Linux/Mac**: `export HF_TOKEN="your_token_here"`

**Note**: To get your token, go to [Hugging Face Settings](https://huggingface.co/settings/tokens) and create a User Access Token.

## 📦 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd mt_eval_app
```

### 2. Backend Setup
Set up the Python environment and install dependencies (including PyTorch, Transformers, etc.).

```bash
cd backend
# Optional: Create a virtual environment
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup
Install the React dependencies.

```bash
cd frontend
npm install
```

## 🏃‍♂️ Usage

You need to run both the backend and frontend servers.

### Start the Backend
From the `backend` directory:
```bash
python main.py
```
The server will start at `http://127.0.0.1:8000`.

### Start the Frontend
From the `frontend` directory:
```bash
npm run dev
```
The application will open at `http://localhost:5173` (or the port shown in your terminal).

## 📊 Supported Metrics

| Metric | Type | Best For |
| Source | --- | --- |
| **COMET** | Neural (Ref-based/QE) | High-correlation with human judgment. |
| **TransQuest** | Neural (QE) | Estimating quality without a reference translation. |
| **SacreBLEU** | n-gram (Ref-based) | Standard reporting metric in research. |
| **TER** | Edit Distance (Ref-based) | Measuring post-editing effort. |
| **BERTScore** | Embedding (Ref-based) | Semantic similarity. |

## 🔧 Configuration

-   **Models**: New models can be added in `backend/config.py`.
-   **File Storage**: Uploaded files and results are stored in `backend/uploads/` (temporary storage).

## 📝 License

[MIT](LICENSE)
