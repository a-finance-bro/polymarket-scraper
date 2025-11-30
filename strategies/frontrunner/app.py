from flask import Flask, render_template, request, jsonify
import threading
import time
from agent import ContextAgent
from loop import ResolutionLoop

app = Flask(__name__)

# In-memory storage
watchlist = []
polling_threads = {}
polling_status = {}

agent = ContextAgent()
loop = ResolutionLoop("../mistral_key.txt")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/watchlist', methods=['GET', 'POST'])
def handle_watchlist():
    if request.method == 'POST':
        data = request.json
        market = data.get('market')
        if market and not any(m['id'] == market['id'] for m in watchlist):
            # Generate Prompt immediately upon adding? Or let user trigger?
            # User flow: Add -> Paste URL -> Start.
            # We need the prompt first. Let's assume we get it when starting or separate step.
            # Let's add a "Generate Prompt" step in UI.
            market['prompt'] = None 
            watchlist.append(market)
        return jsonify({"status": "success", "watchlist": watchlist})
    return jsonify(watchlist)

@app.route('/api/generate_prompt', methods=['POST'])
def generate_prompt_endpoint():
    data = request.json
    market_id = data.get('id')
    market_url = data.get('url') # Polymarket URL
    
    # Find market
    market = next((m for m in watchlist if m['id'] == market_id), None)
    if not market: return jsonify({"error": "Market not found"}), 404
    
    # Generate
    prompt = agent.generate_prompt(market_url)
    if prompt:
        market['prompt'] = prompt
        return jsonify({"status": "success", "prompt": prompt})
    return jsonify({"error": "Failed to generate prompt"}), 500

@app.route('/api/start_polling', methods=['POST'])
def start_polling():
    data = request.json
    market_id = data.get('id')
    results_url = data.get('results_url')
    
    market = next((m for m in watchlist if m['id'] == market_id), None)
    if not market or not market.get('prompt'):
        return jsonify({"error": "Market or prompt missing"}), 400
        
    if market_id in polling_threads and polling_threads[market_id].is_alive():
        return jsonify({"status": "already_running"})

    def poll_task():
        polling_status[market_id] = {"status": "running", "last_check": None, "result": None}
        while True:
            # Check if stopped (simple flag)
            if polling_status[market_id].get("stop"): break
            
            res = loop.poll(results_url, market['prompt'])
            polling_status[market_id]["last_check"] = time.time()
            polling_status[market_id]["result"] = res
            
            if res and res.get("resolved"):
                polling_status[market_id]["status"] = "resolved"
                # Stop polling if resolved? Or keep checking?
                # User said "once the game ends it should give a probability of 1".
                # Maybe keep polling to confirm?
                pass
            
            time.sleep(60) # Poll every minute

    t = threading.Thread(target=poll_task)
    t.daemon = True
    t.start()
    polling_threads[market_id] = t
    
    return jsonify({"status": "started"})

@app.route('/api/status/<market_id>')
def get_status(market_id):
    return jsonify(polling_status.get(market_id, {"status": "idle"}))

@app.route('/api/search', methods=['GET'])
def search_markets():
    query = request.args.get('q', '').lower()
    # Mock results for now, or use DomeClient if I import it
    results = [
        {"title": "Will Trump win?", "id": "1", "url": "https://polymarket.com/event/presidential-election-winner-2024"},
        {"title": "Will Biden drop out?", "id": "2", "url": "https://polymarket.com/event/biden-drops-out"}
    ]
    return jsonify([m for m in results if query in m['title'].lower()])

if __name__ == '__main__':
    app.run(debug=True, port=5001)
