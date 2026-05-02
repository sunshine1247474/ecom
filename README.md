# Resale Scanner (MVP)

An independent, private, and secure eBay dropshipping and retail arbitrage research tool. Built to run entirely in **GitHub Codespaces** so your API keys and data remain completely private.

This tool replaces automated but risky "Amazon-to-eBay" copy-cat software with a calculated, margin-first approach.

## Features

1. **Profit Calculator**: Computes exact eBay Final Value Fees (FVF) based on real 2024/2025 category tables, state taxes, and promoted listing rates.
2. **Multi-Source Product Search**: Scans Amazon, Walmart, Target, Home Depot, and Google Shopping simultaneously.
3. **Cashback Engine**: Models cashback not as a guarantee, but as an *expected value* (Probability of tracking × Probability of merchant approval × Probability of non-return).
4. **Risk Scorer**: Automatically scores products on a 0-100 scale based on margin, demand, competition, shipping weight, and IP risk.
5. **Private Database**: All candidates are stored in a local SQLite database (`data/resale_scanner.db`). No cloud subscriptions required.

---

## How to Run in GitHub Codespaces

This repository is pre-configured with a `.devcontainer` to work perfectly in GitHub Codespaces.

1. Click the **Code** button on GitHub, switch to the **Codespaces** tab, and click **Create codespace on main**.
2. Wait for the container to build (it will automatically install Python 3.11 and all requirements).
3. Once the terminal appears, set up your API keys (see below).
4. Run the application:
   ```bash
   streamlit run app.py
   ```
5. Codespaces will automatically forward port `8501` and give you a secure link to view the dashboard in your browser.

---

## API Keys & Security

Your API keys are **never** stored in the code. You have two secure options for setting them:

### Option A: GitHub Secrets (Recommended)
Go to your repository settings on GitHub: `Settings > Secrets and variables > Codespaces`.
Add the following secrets:
- `EBAY_APP_ID`
- `EBAY_CERT_ID`
- `OPENAI_API_KEY` (for future agent integration)
- `SERPAPI_KEY` (for Google Shopping/Target/Home Depot)
- `RAINFOREST_API_KEY` (for Amazon)

*Note: You must rebuild or restart your Codespace after adding secrets.*

### Option B: Local `.env` File
Create a file named `.env` in the root of the project (copy from `.env.example`).
```env
EBAY_APP_ID=your_key_here
EBAY_CERT_ID=your_key_here
SERPAPI_KEY=your_key_here
RAINFOREST_API_KEY=your_key_here
EBAY_ENVIRONMENT=sandbox
```
*(The `.env` file is ignored by Git, so it will never be committed.)*

---

## Workflow Guide

1. **Search**: Go to the **Product Search** page. Enter a keyword (e.g., "drawer organizer").
2. **Analyze**: Find a profitable-looking item from Walmart or Home Depot. Click "Open in Calculator".
3. **Calculate**: Review the real eBay fees. Adjust the sale price until your **Net Margin (before cashback)** is > 12%.
4. **Score & Save**: Check any risk flags (fragile, branded). If the score is 80+ (✅ APPROVE) or 60-79 (🔵 TEST), click **Save to Candidates**.
5. **Manage**: Go to the **Candidates** page to review your approved items, update their status to "live" when you list them, or export them to CSV.

---

## Technical Stack
- **Frontend**: Streamlit
- **Backend**: Python 3.11
- **Database**: SQLite3 (local file)
- **Data Visualization**: Plotly Express
- **APIs**: eBay Browse API, SerpAPI, Rainforest API
