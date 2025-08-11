# Spa Scheduler — Dash (with Streamlit test)

A simple scheduling web app for a Spa: **workers** are resources and **services** are tasks with fixed durations. 
Drag-and-drop is approximated by quick **Assign → Worker** buttons and **↑/↓** to reorder within a worker column. 
The right-hand Gantt updates live.

> If you truly need browser-native drag & drop, see the *Advanced: add DnD* section below.

---

## ✨ Features
- Define 4 workers: Ayu, Budi, Citra, Dewa
- Common spa services with durations (Thai Massage 60m, Deep Tissue 120m, etc.)
- Backlog of bookings; assign to workers; reorder; remove
- Auto-sequenced Gantt timeline by worker column order
- Streamlit app to validate schedule logic side-by-side

---

## 📦 Project structure
```
spa-scheduler-dash/
├─ app.py                # Dash app (main)
├─ spa_data.py           # Workers, services, business rules
├─ utils.py              # Scheduling utilities
├─ streamlit_app.py      # Streamlit viewer/test
├─ requirements.txt
├─ Procfile
├─ runtime.txt
├─ assets/
│  └─ styles.css
└─ README.md
```

---

## ▶️ Run locally
```bash
python -m venv .venv && source .venv/bin/activate  # (On Windows: .venv\Scripts\activate)
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:8050
```

### Run the Streamlit test app
```bash
streamlit run streamlit_app.py
```

---

## ☁️ Deploy from GitHub
1. **Create a new GitHub repo** and push this folder.
2. **Render (Dash app):**
   - Create a *Web Service* on [Render].
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:server`
3. **Streamlit Community Cloud (Streamlit app):**
   - New app → point to your repo → `streamlit_app.py` as the entry file.
   - Streamlit will auto-install `requirements.txt`.

> Heroku works too with `Procfile` + `runtime.txt`.

---

## 🧠 How scheduling is computed
- The left-to-right order within each worker column becomes the execution order.
- The day starts at **09:00**; each task takes its service duration; next task starts when the previous ends.
- The Gantt chart simply visualizes those computed intervals.

---

## 🛠️ Advanced: add browser drag & drop (optional)
If you want true drag-and-drop cards between columns, you can integrate a small JS DnD layer using **`dash-extensions`** (EventListener) or a 3rd-party component like `dash-draggable` (React Grid Layout) or `dash-sortable` (SortableJS). The simplest path is:

- Keep the *state model* identical to `state = {backlog: [...], workers:[...]}.
- Use a DnD layer to emit `(task_id, destination_worker_id, index)` on drop.
- In Dash, a callback updates the same `dcc.Store("state")` — all rendering stays the same.

This separation lets you swap controls without rewriting business logic or the Gantt.

---

## 🧩 Extending the model
- Add prices per service and compute daily revenue.
- Support overlapping rooms (another resource type) and check conflicts.
- Persist bookings to a database (SQLite / Supabase).

Enjoy! 💆‍♀️
