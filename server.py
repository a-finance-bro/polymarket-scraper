from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import os
import glob
import json
from arbitrage import ArbitrageFinder

app = FastAPI()

# Mount static files for UI
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global state for progress tracking
class JobStatus:
    def __init__(self):
        self.is_running = False
        self.progress = 0
        self.current_step = "Idle"
        self.results_dir = None

job_status = JobStatus()

async def run_arbitrage_task(model_provider: str):
    global job_status
    job_status.is_running = True
    job_status.progress = 0
    job_status.current_step = "Initializing..."
    
    try:
        finder = ArbitrageFinder(model_provider=model_provider)
        
        # Step 1: Scrape
        job_status.current_step = "Scraping Markets..."
        job_status.progress = 10
        
        def update_progress(msg):
            job_status.current_step = msg
            # Try to parse tqdm percentage if available (e.g. "50%|...")
            if "%" in msg:
                try:
                    # Simple heuristic: extract first number before %
                    parts = msg.split('%')
                    if parts[0].strip().isdigit():
                        # Map 0-100 scraper progress to 10-30 overall progress
                        scraper_pct = int(parts[0].strip())
                        job_status.progress = 10 + int(scraper_pct * 0.2)
                except:
                    pass

        data_dir = await asyncio.to_thread(finder.run_scraper, status_callback=update_progress)
        
        if not data_dir:
            job_status.current_step = "Scraping Failed"
            job_status.is_running = False
            return

        job_status.progress = 30
        
        # Step 2: Analyze
        job_status.current_step = "Analyzing Markets with LLM..."
        results_path = os.path.join("results", f"results_{finder.current_timestamp}")
        os.makedirs(results_path, exist_ok=True)
        
        json_files = glob.glob(os.path.join(data_dir, "*.json"))
        json_files = [f for f in json_files if "all_markets.json" not in f]
        
        total_files = len(json_files)
        for i, f in enumerate(json_files):
            await finder.analyze_file(f, results_path)
            # Update progress
            # Map 30-90% range to analysis progress
            progress_fraction = (i + 1) / total_files
            job_status.progress = 30 + int(progress_fraction * 60)
            job_status.current_step = f"Analyzing {os.path.basename(f)}..."
            await asyncio.sleep(0.5) # Rate limit buffer

        job_status.progress = 100
        job_status.current_step = "Complete"
        job_status.results_dir = results_path
        
    except Exception as e:
        print(f"Task error: {e}")
        job_status.current_step = f"Error: {str(e)}"
    finally:
        job_status.is_running = False

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

@app.post("/api/run")
async def run_arbitrage(background_tasks: BackgroundTasks, model: str = "openai"):
    if job_status.is_running:
        raise HTTPException(status_code=400, detail="Job already running")
    
    background_tasks.add_task(run_arbitrage_task, model)
    return {"message": "Arbitrage job started", "model": model}

@app.get("/api/status")
async def get_status():
    return {
        "is_running": job_status.is_running,
        "progress": job_status.progress,
        "current_step": job_status.current_step,
        "results_dir": job_status.results_dir
    }

@app.get("/api/results")
async def list_results():
    # List all timestamped folders in results/
    if not os.path.exists("results"):
        return []
    dirs = glob.glob(os.path.join("results", "*"))
    dirs.sort(key=os.path.getctime, reverse=True)
    return [os.path.basename(d) for d in dirs]

@app.get("/api/results/{timestamp}")
async def get_result_details(timestamp: str):
    path = os.path.join("results", timestamp)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Aggregate all JSONs in the folder
    aggregated_results = []
    files = glob.glob(os.path.join(path, "*.json"))
    
    for f in files:
        try:
            with open(f, "r") as file:
                data = json.load(file)
                # Expecting {"opportunities": [...]}
                if "opportunities" in data:
                    aggregated_results.extend(data["opportunities"])
        except:
            pass
            
    return {"opportunities": aggregated_results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=214)
