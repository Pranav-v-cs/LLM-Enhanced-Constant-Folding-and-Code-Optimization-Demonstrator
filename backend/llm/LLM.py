import os
import subprocess
import json
import time
import re
import ollama
from dotenv import load_dotenv

# ============================================================
# CONFIGURATION
# ============================================================
def LLM():
    load_dotenv()

    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_client = ollama.Client(host=OLLAMA_HOST)

    # Use project directory instead of /tmp
    # Get backend directory (parent of llm directory)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    COMPILER_DIR = os.path.join(BASE_DIR, "compiler")
    
    print(f"📂 Base directory: {BASE_DIR}")
    print(f"📂 Compiler directory: {COMPILER_DIR}")
    
    # Ensure compiler directory exists
    os.makedirs(COMPILER_DIR, exist_ok=True)

    COMPILER_EXECUTABLE_NAME = "compiler"
    OPTIMIZER_EXECUTABLE_NAME = "optimizer"

    COMPILER_EXECUTABLE = os.path.join(COMPILER_DIR, COMPILER_EXECUTABLE_NAME)
    OPTIMIZER_EXECUTABLE = os.path.join(COMPILER_DIR, OPTIMIZER_EXECUTABLE_NAME)

    IR_FILE = os.path.join(COMPILER_DIR, "IR.txt")
    OUTPUT_FILE = os.path.join(COMPILER_DIR, "Output.txt")
    SOURCE_FILE = os.path.join(COMPILER_DIR, "source.c")

    # Create llm directory for reports if it doesn't exist
    LLM_REPORTS_DIR = os.path.join(BASE_DIR, "llm")
    os.makedirs(LLM_REPORTS_DIR, exist_ok=True)
    
    REPORT_TEXT = os.path.join(LLM_REPORTS_DIR, "LLM_Report.txt")
    REPORT_JSON = os.path.join(LLM_REPORTS_DIR, "LLM_Review.json")

    # ============================================================
    # CHECK IF EXECUTABLES EXIST
    # ============================================================
    print(f"🔍 Checking for compiler at: {COMPILER_EXECUTABLE}")
    print(f"   Exists: {os.path.exists(COMPILER_EXECUTABLE)}")
    
    print(f"🔍 Checking for optimizer at: {OPTIMIZER_EXECUTABLE}")
    print(f"   Exists: {os.path.exists(OPTIMIZER_EXECUTABLE)}")
    
    # Make executables executable (in case permissions were lost)
    for exe_path in [COMPILER_EXECUTABLE, OPTIMIZER_EXECUTABLE]:
        if os.path.exists(exe_path):
            try:
                os.chmod(exe_path, 0o755)
                print(f"✅ Set executable permissions for {exe_path}")
            except Exception as e:
                print(f"⚠️ Could not set permissions for {exe_path}: {e}")

    # ============================================================
    # RUN COMPILER EXECUTABLE TO GENERATE OUTPUT FILE
    # ============================================================

    def run_c_compiler():
        print("⚙️ Running C compiler to generate IR.txt...\n")

        if not os.path.exists(COMPILER_EXECUTABLE):
            print(f"❌ Compiler executable not found: {COMPILER_EXECUTABLE}")
            return False

        if not os.path.exists(SOURCE_FILE):
            print(f"❌ Source file not found: {SOURCE_FILE}")
            return False

        try:
            # Run compiler
            compiled = subprocess.run(
                [COMPILER_EXECUTABLE],
                cwd=COMPILER_DIR,
                capture_output=True,
                text=True,
                timeout=45
            )

            print("🔧 Compiler stdout:\n", compiled.stdout)
            print("⚠️ Compiler stderr:\n", compiled.stderr)
            print(f"🔧 Compiler return code: {compiled.returncode}")

            # Wait for IR.txt to appear
            for i in range(10):
                if os.path.exists(IR_FILE):
                    print("✅ IR.txt found!")
                    return True
                print(f"⏳ Waiting for IR.txt... ({i+1}/10)")
                time.sleep(1)

            print("❌ IR.txt not found after running compiler.")
            return False

        except subprocess.TimeoutExpired:
            print("❌ Compiler process timed out.")
            return False
        except Exception as e:
            print(f"❌ Error running compiler: {e}")
            import traceback
            traceback.print_exc()
            return False

   
    def run_c_optimizer():
        """Run the optimizer and wait for Output.txt to appear."""
        print("⚙️ Running C optimizer to generate Output.txt...\n")

        if not os.path.exists(OPTIMIZER_EXECUTABLE):
            print(f"❌ Optimizer executable not found: {OPTIMIZER_EXECUTABLE}")
            return False

        if not os.path.exists(IR_FILE):
            print(f"❌ IR.txt not found: {IR_FILE}")
            return False

        try:
            result = subprocess.run(
                [OPTIMIZER_EXECUTABLE],
                cwd=COMPILER_DIR,
                capture_output=True,
                text=True,
                timeout=45
            )

            print("🔧 Optimizer stdout:\n", result.stdout)
            print("⚠️ Optimizer stderr:\n", result.stderr)
            print(f"🔧 Optimizer return code: {result.returncode}")

            # Wait for Output.txt to appear
            for i in range(10):
                if os.path.exists(OUTPUT_FILE):
                    print("✅ Output.txt found!")
                    return True
                print(f"⏳ Waiting for Output.txt... ({i+1}/10)")
                time.sleep(1)

            print("❌ Output.txt not found after running optimizer.")
            return False

        except subprocess.TimeoutExpired:
            print("❌ Optimizer process timed out.")
            return False
        except Exception as e:
            print(f"❌ Error running optimizer: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ============================================================
    # OLLAMA CALL (LOCAL LLM WITH TIMEOUT & ERROR HANDLING)
    # ============================================================

    def call_ollama(prompt, retries=3, initial_delay=2):
        delay = initial_delay

        for attempt in range(1, retries + 1):
            print(f"🌐 Calling Ollama ({OLLAMA_MODEL}) (attempt {attempt}/{retries})...")

            try:
                response = ollama_client.chat(
                    model=OLLAMA_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    options={
                        "temperature": 0.3,
                        "num_predict": 2048,
                    },
                )

                print("✅ Ollama responded successfully")
                content = response.get("message", {}).get("content", "")
                if not content:
                    return "⚠️ Ollama returned no readable text.", response
                return content, response

            except ollama.ResponseError as e:
                print(f"❌ Ollama response error: {e}")
                if e.status_code == 404:
                    return (
                        f"⚠️ Model '{OLLAMA_MODEL}' not found. "
                        f"Run: ollama pull {OLLAMA_MODEL}",
                        {},
                    )
                if attempt < retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                return f"⚠️ Ollama error: {e}", {}

            except Exception as e:
                # Connection errors (Ollama server not running) land here
                print(f"🔌 Ollama connection/runtime error (attempt {attempt}/{retries}): {e}")
                if attempt < retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                return (
                    f"⚠️ Could not reach Ollama at {OLLAMA_HOST}. "
                    f"Is it running? Start it with: ollama serve",
                    {},
                )

        return "⚠️ Ollama unavailable after multiple retries", {}
    # ============================================================
    # PARSING HELPERS
    # ============================================================

    def extract_summary(review_text):
        lines = review_text.strip().splitlines()
        summary_line = ""
        for line in reversed(lines):
            if "✅" in line or "⚠️" in line:
                summary_line = line.strip()
                break

        if "✅" in summary_line:
            status = "Optimization Correct"
        elif "⚠️" in summary_line:
            status = "Issues Found"
        else:
            status = "Unclear"

        return {"summary": summary_line, "status": status}

    def extract_suggestions(review_text):
        # Capture the block between $Suggestions:$ and $Optimization:$ (or EOF)
        match = re.search(
            r"\$Suggestions:\$(.*?)(?:\$Optimization:\$|\Z)",
            review_text,
            re.DOTALL | re.IGNORECASE,
        )
        if not match:
            return []

        block = match.group(1)

        # Prefer explicit $...$ delimiters, else fall back to bullet lines
        suggestions = re.findall(r"\$(.+?)\$", block, re.DOTALL)
        if not suggestions:
            suggestions = [
                line for line in block.splitlines() if line.strip()
            ]

        return [
            re.sub(r"^\s*[-*•]?\s*", "", s.strip())
            for s in suggestions if s.strip()
        ]

    def extract_tac_code(review_text):
        # Find the $Optimization:$ header and capture everything after it
        match = re.search(
            r"\$Optimization:\$\s*\n(.*)",
            review_text,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            tac_code = match.group(1).strip()
            # Remove any extra markdown or formatting artifacts
            tac_code = re.sub(r"```[a-zA-Z]*|```", "", tac_code).strip()
            return tac_code
        return None


    # ============================================================
    # LLM REVIEW FUNCTION (OLLAMA)
    # ============================================================

    def review_output_file():
        if not os.path.exists(OUTPUT_FILE):
            print("❌ Output.txt not found! Run your optimizer first.")
            return {"success": False, "message": "Output.txt not found"}

        with open(OUTPUT_FILE, "r") as f:
            optimized_code = f.read()

        prompt = f"""You are an expert compiler engineer reviewing optimized three-address code (TAC).

Analyze the TAC below and reply using EXACTLY the format shown. Do not use markdown code fences.

NOTES
- <0 to 3 short bullet points on semantics and any unsafe optimizations>

$Suggestions:$
$<suggestion 1>$
$<suggestion 2>$

SUMMARY
<one line: "✅ Optimization Correct" or "⚠️ Issues Found: <reason>">

$Optimization:$
<your optimized TAC, one instruction per line>

Rules:
- Keep NOTES to at most 3 one-line bullets.
- Each suggestion must be wrapped in $...$ on its own line under the "$Suggestions:$" heading.
- Put your optimized TAC after the "$Optimization:$" heading, one instruction per line.
- The "$Optimization:$" block must be the LAST thing in your reply.
- End your review with a single SUMMARY line using the ✅ or ⚠️ marker.

--- Optimized TAC ---
{optimized_code}
"""

        print("🤖 Sending optimized TAC to Ollama...\n")

        try:
            review_text, raw_json = call_ollama(prompt)

            print("\n=== Ollama Review ===\n")
            print(review_text)

            summary_info = extract_summary(review_text)
            suggestions = extract_suggestions(review_text)
            optimized_tac = extract_tac_code(review_text)
            
            # Save plain text
            with open(REPORT_TEXT, "w", encoding="utf-8") as f:
                f.write(review_text)

            # Save structured JSON
            structured_output = {
                "summary": summary_info["summary"],
                "status": summary_info["status"],
                "suggestions": suggestions,
                "full_text": review_text,
                "optimized_code": optimized_tac,
                "unoptimized_code": optimized_code
            }

            with open(REPORT_JSON, "w", encoding="utf-8") as f:
                json.dump(structured_output, f, indent=2)

            print(f"📦 JSON review saved to {REPORT_JSON}")
            return structured_output
            
        except Exception as e:
            print(f"❌ Error in review_output_file: {e}")
            
    # ============================================================
    # MAIN EXECUTION LOGIC
    # ============================================================
    print("========================================================")
    print("  Ollama Review Automation for C Optimizer Project      ")
    print("========================================================\n")

    if run_c_compiler() and run_c_optimizer():
        json_result = review_output_file()
        print("\n✅ Final structured JSON ready for frontend:\n")
        print(json.dumps(json_result, indent=2))
        return json_result
    else:
        return {"success": False, "message": "Compiler or optimizer failed to run."}
