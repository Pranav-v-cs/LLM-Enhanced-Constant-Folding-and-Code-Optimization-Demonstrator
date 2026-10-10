# NeuroFold: LLM-Enhanced Code Optimizer

**NeuroFold** is an AI-assisted compiler optimization project that pairs a traditional C-based compiler with a Large Language Model (LLM) to enhance constant folding and overall code optimization. It identifies constant expressions, performs compile-time simplifications, and uses a local LLM served by **Ollama** to verify semantic correctness and suggest further safe optimizations.

## Features

- **Automated Code Optimization**: Paste your C code into the web interface and receive an optimized version in seconds.
- **Constant Folding**: The C-based optimizer identifies and evaluates constant expressions at compile time.
- **LLM-Powered Analysis**: The optimized code is reviewed by a local model served through Ollama (`qwen2.5-coder:14b` by default), which verifies semantic correctness, flags potential issues, and recommends further optimizations (e.g., aggressive constant folding, dead code elimination, strength reduction).
- **Interactive UI**: A React + Tailwind CSS interface for entering code and viewing results.
- **Detailed Feedback**: The UI shows the optimized code, the LLM's suggestions, an optimization status summary, and highlights any issues found.
- **Downloadable Results**: Before/after code and the full LLM review can be saved as text files.

## How It Works

The project is split into a frontend, a Flask backend, and a C-based compiler/optimizer:

1. **Code Submission**: The user enters C code in the React frontend and clicks **Optimize**.
2. **Backend Processing**: The code is POSTed to the Flask API, which writes it to `backend/compiler/source.c`.
3. **Compilation**: The C compiler performs lexing, parsing, and semantic analysis to build an AST and generate three-address code (TAC), saved to `IR.txt`.
4. **Optimization**: The C optimizer reads `IR.txt`, performs constant folding, and writes the optimized TAC to `Output.txt`.
5. **LLM Review**: The optimized TAC is sent to a local LLM via Ollama, which reviews semantic correctness, identifies issues, and suggests further optimizations.
6. **Results Display**: The backend returns the optimized code, LLM suggestions, and status to the frontend for display.

## Tech Stack

- **Frontend**: React 19, Vite 7, Tailwind CSS 4, daisyUI 5, recharts, lucide-react
- **Backend**: Flask, Flask-Cors, gunicorn, python-dotenv, ollama
- **Compiler / Optimizer**: C (GCC)
- **LLM**: Local model via [Ollama](https://ollama.com) (`qwen2.5-coder:14b` by default)

## Project Structure

```
.
├── backend/
│   ├── app.py              # Flask API entry point
│   ├── requirements.txt
│   ├── build.sh            # Compiles the C programs for Linux
│   ├── Procfile            # gunicorn start command (deployment)
│   ├── gunicorn_config.py  # gunicorn timeout/worker settings
│   ├── llm/
│   │   └── LLM.py          # Runs compiler/optimizer + Ollama review pipeline
│   └── compiler/
│       ├── compiler.c      # Lexer, parser, semantic analysis, IR (TAC) generation
│       ├── optimizer.c     # Constant-folding optimizer over IR
│       └── build.sh        # Builds the `compiler` and `optimizer` executables
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx         # Main UI + API call logic
        └── components/     # NavBar, CodeInput, OutputPanel, TACCostComparison, ...
```

Runtime artifacts (`compiler`, `optimizer`, `source.c`, `IR.txt`, `Output.txt`, `LLM_Report.txt`, `LLM_Review.json`) are generated under `backend/compiler` and `backend/llm` and are git-ignored.

## Prerequisites

- Node.js and npm
- Python 3 and pip
- A C compiler (GCC)
- [Ollama](https://ollama.com) installed and running locally

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Pranav-v-cs/LLM-Enhanced-Constant-Folding-and-Code-Optimization-Demonstrator.git
   cd LLM-Enhanced-Constant-Folding-and-Code-Optimization
   ```

2. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   ```

3. **Install backend dependencies**:
   ```bash
   cd ../backend
   pip install -r requirements.txt
   ```

4. **Build the C compiler and optimizer**:
   ```bash
   cd backend
   ./build.sh
   # or manually:
   # cd compiler && gcc -o compiler compiler.c -lm && gcc -o optimizer optimizer.c -lm
   ```

5. **Install Ollama and pull the model**:
   - Install Ollama from [ollama.com](https://ollama.com) and make sure the server is running (`ollama serve`).
   - Pull the default model:
     ```bash
     ollama pull qwen2.5-coder:14b
     ```

6. **(Optional) Configure the LLM**:
   - Create a `.env` file in the `backend` directory if you want to override the defaults:
     ```
     OLLAMA_MODEL=qwen2.5-coder:14b
     OLLAMA_HOST=http://localhost:11434
     ```
   The `.env` file is git-ignored.

## Running Locally

1. **Start the backend server**:
   ```bash
   cd backend
   python app.py
   ```
   The API listens on `http://0.0.0.0:10000` with the endpoint `POST /run-llm`.

2. **Start the frontend development server**:
   ```bash
   cd frontend
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

3. **Point the frontend at the local backend**:
   By default the frontend targets a deployed Render backend (`https://neurofold-j01j.onrender.com/run-llm`). For local development, comment that line out and enable the localhost fetch in `frontend/src/App.jsx`:
   ```js
   const res = await fetch("http://127.0.0.1:5010/run-llm", {
   ```
   (bump the port to `10000` to match `app.py`).

## API Reference

### `POST /run-llm`

Accepts C source code and returns the optimized code plus the LLM review.

**Request** (JSON):
```json
{
  "code": "int main() { int x = 2 + 3; return 0; }"
}
```

**Response** (JSON):
```json
{
  "status": "Optimization Correct",
  "summary": "✅ Optimization Correct",
  "suggestions": ["Constant-fold `2 + 3` into `5`."],
  "optimized_code": "t1 = 5",
  "unoptimized_code": "t1 = 2 + 3",
  "full_text": "..."
}
```

The frontend maps these fields to the output panel:
- `optimized_code` → optimized TAC display
- `unoptimized_code` → original TAC display
- `suggestions` → optimization log
- `status` / `summary` → status badge
- `full_text` → raw LLM review

## Configuration

| Variable | Description |
| --- | --- |
| `OLLAMA_MODEL` | Local model name (default `qwen2.5-coder:14b`), read in `backend/llm/LLM.py` |
| `OLLAMA_HOST` | Ollama server URL (default `http://localhost:11434`) |

The Ollama call uses 3 retries with exponential backoff. Because local inference is slower, gunicorn is configured with a 600s timeout and 2 sync workers in `gunicorn_config.py`.

## Deployment

The backend is ready for Render:

- `Procfile` starts the app: `gunicorn --config gunicorn_config.py app:app`
- `build.sh` compiles the C programs for Linux before the server starts.

Since the LLM runs locally via Ollama, the backend must be able to reach an Ollama server (e.g., run both on the same host, or point `OLLAMA_HOST` at a reachable instance).

## Troubleshooting

- **`Compiler executable not found` / `Optimizer executable not found`**: Run `./build.sh` inside `backend` so the `compiler` and `optimizer` binaries exist in `backend/compiler`.
- **`No source code provided`**: The request body must contain a non-empty `code` field.
- **`Could not reach Ollama`**: The Ollama server isn't running or `OLLAMA_HOST` is wrong. Start it with `ollama serve` and confirm `http://localhost:11434` responds.
- **`Model 'qwen2.5-coder:14b' not found`**: Pull the model with `ollama pull qwen2.5-coder:14b` (or set `OLLAMA_MODEL` to a model you have).
- **Frontend shows `Error contacting backend`**: The backend URL in `frontend/src/App.jsx` is unreachable — switch it to the local endpoint for local runs.
- **CORS issues**: Flask-Cors is enabled; ensure the frontend origin is allowed by the backend config if you customize it.

## Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request for new optimizations, additional language support, or UI improvements.
