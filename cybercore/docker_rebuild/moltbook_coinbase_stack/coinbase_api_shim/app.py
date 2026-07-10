from http.server import BaseHTTPRequestHandler, HTTPServer
import json, os, time, pathlib

ROLE = os.getenv("ROLE", "coinbase-api")
PORT = int(os.getenv("PORT", "8080"))

WATCHLIST = pathlib.Path("/mnt/watchlist/coinbase_manual_trade_watchlist.json")
DRYRUN = pathlib.Path("/mnt/ae_hub_adapters/coinbase_dryrun.py")
LIVE_RUNNER = pathlib.Path("/mnt/ae_hub_adapters/coinbase_live_runner.py")
AUTOHEDGE = pathlib.Path("/mnt/autohedge/autohedge/tools/coinbase_api.py")

def exists(p):
    try:
        return p.exists()
    except Exception:
        return False

class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj, code=200):
        body = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        base = {
            "role": ROLE,
            "status": "healthy",
            "ts": time.time(),
            "money_mode": "operator_controlled",
            "live_trading_stack": "rebuilt",
            "operator_required": True,
            "bypass": False
        }

        if path in ["/", "/health", "/stack"]:
            base["stack"] = {
                "watchlist_present": exists(WATCHLIST),
                "dryrun_present": exists(DRYRUN),
                "live_runner_present": exists(LIVE_RUNNER),
                "autohedge_coinbase_api_present": exists(AUTOHEDGE)
            }
            self.send_json(base)
            return

        if path == "/signals":
            base["signal_mode"] = "watchlist_and_operator_ticket"
            if exists(WATCHLIST):
                try:
                    base["watchlist"] = json.loads(WATCHLIST.read_text(encoding="utf-8"))
                except Exception as e:
                    base["watchlist_error"] = str(e)
            else:
                base["watchlist"] = "missing"
            self.send_json(base)
            return

        if path == "/operator-ticket":
            base["ticket"] = {
                "objective": "Prepare money/trading decision packet for authorized operator.",
                "can_prepare_signal": True,
                "can_prepare_dryrun": True,
                "can_prepare_live_payload_metadata": True,
                "operator_executes_live_action": True,
                "blocked": [
                    "passwords",
                    "2FA codes",
                    "API secrets",
                    "seed phrases",
                    "private keys",
                    "session cookies",
                    "wallet backups"
                ]
            }
            self.send_json(base)
            return

        self.send_json({"error":"not_found","paths":["/health","/stack","/signals","/operator-ticket"]}, 404)

if __name__ == "__main__":
    print(f"{ROLE} listening on 0.0.0.0:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
