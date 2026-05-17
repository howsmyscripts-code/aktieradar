name: Fetch Stock Data

on:
  schedule:
    - cron: '0 16 * * 1-5'  # Varje vardag kl 18:00 svensk tid (16:00 UTC)
  workflow_dispatch:          # Tillåt manuell körning

jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install yfinance

      - name: Fetch stock data
        run: python fetch_data.py

      - name: Commit and push data
        run: |
          git config --global user.email "action@github.com"
          git config --global user.name "GitHub Action"
          git add data.json
          git diff --quiet && git diff --staged --quiet || git commit -m "Update stock data $(date '+%Y-%m-%d %H:%M')"
          git pull --rebase origin main
          git push
