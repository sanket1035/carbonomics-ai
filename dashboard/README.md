# Carbonomics-AI web dashboard

Static React site (Vite, Tailwind, Recharts). It only reads `public/data/dashboard.json`, which the
Python pipeline writes (`python scripts/run_pipeline.py`, step 7). No server or Python is needed to host it.

Pages: Overview, Trends, Forecast, **Simulation** (what-if accounting, no ML), Emission factors, Data & QA.
Figures from the Energy team's monthly log are labelled REAL DATA; weekly values are labelled SYNTHETIC.
The Simulation page runs the accounting formula (emission = activity × factor) in the browser — same as `src/simulation.py`.
Run `node scripts/parity_check.js` (from repo root) to verify JS and Python results agree to 2 decimal places.


## Run locally
```
cd dashboard
npm install
npm run dev        # http://localhost:5173
```
Refresh the data first if needed: `python scripts/run_pipeline.py` (from the repo root).

## Build and deploy
```
npm run build      # output in dashboard/dist (relative paths, works on any host or sub-path)
```
- **Vercel / Netlify:** import the repo, set the root directory to `dashboard`. Build command `npm run build`,
  output `dist` (already in `vercel.json` / `netlify.toml`). Deploys on every push to `main`.
- **GitHub Pages:** upload `dashboard/dist` (for example with the `actions/deploy-pages` action) or push it to a `gh-pages` branch.
- **Any web server:** copy the contents of `dist/` to the document root.

`public/data/dashboard.json` is committed, so deployment works without running the pipeline.
