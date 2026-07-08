
# The Robinhood Project


##  Build a Python stock screener that finds stocks forming the first three strokes of a capital "W" (a forming double bottom): an initial decline, a bounce up, and a second decline that brings price back near the first low.


##  Data & universe
	Pull ~2 years of daily OHLCV bars from Yahoo Finance (yfinance), cached locally (parquet/CSV) so re-runs are fast.
	Filter the universe to stocks with market cap ≥ $300mm and 60-day average volume ≥ 500k shares.

##  Pattern detection (the core)
	For each ticker, try several trailing windows (e.g. 40/55/75/100/130 bars). Within each window, split the closing prices into 3 legs at two interior pivots (first bottom, bounce peak), searching local minima/maxima as pivot candidates (neighborhood order ~3). Require each leg ≥ 5 bars.

	Fit an independent linear regression to each leg. Compute per-leg slope (%/bar), R², and residual standard deviation as a % of price.

	Hard requirement: leg slopes must be negative / positive / negative (down, up, down). Reject any other sign combination outright.

	Compute a continuous 0–1 shape_score from weighted components: directional slope conviction (~0.26), straightness/R² (~0.26), leg balance/symmetry (~0.15), nearness of current price to the first low (~0.13), bounce amplitude vs. leg-1 drop (~0.12), and depth of the first drop (~0.08). Keep the best-scoring decomposition per ticker across all windows.

##  Quality + relaxation
    Add an independent quality gate: reject if any leg's residual std exceeds a tunable % of price (default 4%, adjustable 0.5%–12%).
    Define ~6 ordered "relaxation levels" from strict to very loose, each a set of hard gates (min mean R², min weakest-leg R², min |slope| per leg, max nearness to the low, min bounce retrace, min leg-1 drop %, min leg-length balance). Start strict; if fewer than ~10 stocks pass, drop to the next looser level and retry. Relaxation loosens magnitudes only — never the down/up/down shape.

##  Output & GUI
    Rank passing stocks by shape_score, export results to CSV.
    Plot each match: the price series with the 3 fitted regression lines, a ±2σ channel band, and the detected pivots dated on the x-axis.
    Provide a simple GUI (Tkinter) with a slider for the residual-tolerance gate and a button to run the screen / regenerate charts.
    Keep all tunable parameters in a single config.py (paths, filters, windows, weights, relaxation levels) and put the detection math in its own module.


##  Extras

Python script that could place an order to buy if morning and after-noon tasks to record price have completed.
Save API Token in .secets to connect

##
 * Look at todays 8 am price
 * Look at todays noon price
 * Lood at afterhours price 

###
I wanted to run an elevator pitch by you with a single page business plan for automating my Robinhood trading. The idea is to use a simple Python script that can automatically place a buy order based on certain conditions.	

###
test with secrets.dev and secrets.prod
	- secrets.dev is for development and testing
	- secrets.prod is for production
	API_KEY = "rh-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx="
	BASE64_PRIVATE_KEY = "xXXXXXXXXXXXXXXXXXXXXXXXXXXX="
	TEST = "false"


###
Sign up today.

Notes: Must have a Robinhood account.
		Must have Python installed on your machine.
			Must have pip installed to install dependencies.
				1. Clone the repo
				2. Create a virtual environment (optional but recommended)
				3. Install dependencies using `pip install -r requirements.txt`
				4. Create a `.secrets` file with your Robinhood API token in it.
				5. Run the script using `python robinhood.py`
                

##	Install Instructions 101

	GUI for Python3 implementation 

	Setup 
		env file
		your data
		your secrets
		your Docker env


##	Install Instructions .env 


#   pip install yfinance==1.4.1 pandas==3.0.3 numpy==1.24.0 scipy==1.10.0 matplotlib>=3.7.0 pyarrow>=12.0.0 lxml>=4.9.0

# ─────────────────────────────────────────────
# Development Environment Variables (Safe)
# Roku‑Book Project : Instructions pip install -- run once, then comment out of this file.
# ─────────────────────────────────────────────

# API keys (use test keys only)
ROBINHOOD_API_KEY_TEST=dev_test_key_here
BASE64_PRIVATE_KEY_TEST=dev_test_private_key_here

# App configuration
APP_ENV=development
DEBUG=true
LOG_LEVEL=info

# Local database (dev only)
DB_HOST=localhost
DB_PORT=5432
DB_USER=dev_user
DB_PASSWORD=dev_password
DB_NAME=dev_db

# Optional: service endpoints
API_BASE_URL=https://sandbox.api.example.com



##	In the .vscode folder add these files 
		config.json
		launch.json
		settings.json
		tasks.json

	{
    "name": "Robinhood Debug",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/screener.py",
    "console": "integratedTerminal",
    "python": "${workspaceFolder}/.venv/Scripts/python.exe"
}


##	launch.json

{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python Debugger: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "console": "integratedTerminal"
        },
        {
            "name": "Python Debugger: Main.py",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "console": "integratedTerminal",
            "python": "${workspaceFolder}/.venv/Scripts/python.exe"
        },
        {
            "name": "Robinhood Debug",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/screener.py",
            "console": "integratedTerminal",
            "python": "${workspaceFolder}/.venv/Scripts/python.exe"
        }
    ]
}


##	settings.json

{
    "python-envs.pythonProjects": [
        {
            "path": "main.py",
            "envManager": "ms-python.python:system",
            "packageManager": "ms-python.python:pip",
            "python.analysis.extraPaths": ["./src"]
        }
    ],
    "python-envs.defaultEnvManager": "ms-python.python:venv",
    "python-envs.workspaceSearchPaths": [
        ".venv",
        "*/.venv",
        ""
    ]
}


##	tasks.json

{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "build-dev"
    }
]
}