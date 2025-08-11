import dash
from dash import Dash, html, dcc, Input, Output, State, callback_context
import plotly.express as px
import json
from spa_data import WORKERS, SERVICES, DAY_START, SLOT_MIN
from utils import build_schedule_df

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Build quick lookup maps
services_idx = {s["id"]: s for s in SERVICES}
workers_idx = {w["id"]: w for w in WORKERS}

def make_card(task, show_assign_buttons=True, worker_id=None, idx=None):
    # A simple task card
    body = [
        html.Div(task["customer"], className="card-title"),
        html.Div(services_idx[task["service_id"]]["name"], className="card-sub"),
    ]
    buttons = []
    if show_assign_buttons:
        for w in WORKERS:
            buttons.append(html.Button(
                f"Assign → {w['name']}",
                className="btn tiny",
                n_clicks=0,
                id={"role":"assign","task_id":task["id"],"worker_id":w["id"]}
            ))
    else:
        # controls to move/remove inside a worker column
        buttons = [
            html.Button("↑", className="btn tiny", id={"role":"move_up","worker_id":worker_id,"index":idx}, n_clicks=0),
            html.Button("↓", className="btn tiny", id={"role":"move_down","worker_id":worker_id,"index":idx}, n_clicks=0),
            html.Button("Remove", className="btn tiny danger", id={"role":"remove","worker_id":worker_id,"index":idx}, n_clicks=0),
        ]
    return html.Div(body + [html.Div(buttons, className="btn-row")], className="card")

def initial_state():
    # starter backlog with a few customers
    # Each task must have an id so we can reference it in callbacks
    return {
        "seq": 6,  # id counter
        "backlog":[
            {"id":"t1","customer":"Lina","service_id":"svc_thai"},
            {"id":"t2","customer":"Rafi","service_id":"svc_deep"},
            {"id":"t3","customer":"Maya","service_id":"svc_facial"},
            {"id":"t4","customer":"Irfan","service_id":"svc_hot"},
            {"id":"t5","customer":"Sari","service_id":"svc_reflex"},
        ],
        "workers":[
            {"worker_id": w["id"], "tasks": []} for w in WORKERS
        ]
    }

app.layout = html.Div([
    dcc.Store(id="state", data=initial_state()),
    html.H1("Spa Scheduler (Dash)"),
    html.Div([
        html.Div([
            html.H3("Add booking"),
            dcc.Input(id="in_customer", placeholder="Customer name", type="text"),
            dcc.Dropdown(
                id="in_service",
                options=[{"label": f"{s['name']} ({s['duration_min']}m)", "value": s["id"]} for s in SERVICES],
                placeholder="Select service"
            ),
            html.Button("Add to backlog", id="btn_add", n_clicks=0, className="btn primary"),
        ], className="panel"),
        html.Div([
            html.H3("Backlog"),
            html.Div(id="backlog_view")
        ], className="panel grow")
    ], className="row"),
    html.Hr(),
    html.Div([
        html.Div([
            html.H3(w["name"]),
            html.Div(id=f"worker_col_{w['id']}", className="worker-col")
        ], className="panel grow") for w in WORKERS
    ], className="row"),
    html.Hr(),
    html.Div([
        html.H3("Schedule (auto-sequenced by column order)"),
        dcc.Graph(id="gantt")
    ], className="panel")
], className="container")

# ---- Render panels
@app.callback(
    Output("backlog_view","children"),
    [Input("state","data")]
)
def render_backlog(state):
    return [make_card(task, show_assign_buttons=True) for task in state["backlog"]]

for w in WORKERS:
    @app.callback(
        Output(f"worker_col_{w['id']}","children"),
        [Input("state","data")],
        prevent_initial_call=False
    )
    def render_worker_col(state, worker_id=w['id']):
        col = next(col for col in state["workers"] if col["worker_id"] == worker_id)
        if not col["tasks"]:
            return html.Div("No tasks yet.", className="empty")
        return [make_card(t, show_assign_buttons=False, worker_id=worker_id, idx=i) for i, t in enumerate(col["tasks"])]

# ---- Add booking
@app.callback(
    Output("state","data"),
    [Input("btn_add","n_clicks")],
    [State("in_customer","value"), State("in_service","value"), State("state","data")],
    prevent_initial_call=True
)
def add_to_backlog(n, customer, service_id, state):
    if not customer or not service_id:
        return state
    state = state.copy()
    state["seq"] += 1
    task = {"id": f"t{state['seq']}", "customer": customer, "service_id": service_id}
    state["backlog"].append(task)
    return state

# ---- Assign / Move / Remove handlers (pattern-matching IDs)
@app.callback(
    Output("state","data"),
    [Input({"role":"assign","task_id":dash.MATCH,"worker_id":dash.MATCH},"n_clicks"),
     Input({"role":"move_up","worker_id":dash.MATCH,"index":dash.MATCH},"n_clicks"),
     Input({"role":"move_down","worker_id":dash.MATCH,"index":dash.MATCH},"n_clicks"),
     Input({"role":"remove","worker_id":dash.MATCH,"index":dash.MATCH},"n_clicks")],
    [State("state","data")],
    prevent_initial_call=True
)
def handle_actions(*args):
    # Inputs come in as separate lists; we instead inspect the triggered prop_id
    state = args[-1]
    trig = callback_context.triggered[0]["prop_id"]
    if not trig or trig == ".":
        return state
    # prop_id is like {"role":"assign","task_id":"t1","worker_id":"w2"}.n_clicks
    pid = json.loads(trig.split(".")[0])
    role = pid.get("role")

    state = json.loads(json.dumps(state))  # deep copy
    if role == "assign":
        task_id = pid["task_id"]
        dest = pid["worker_id"]
        # pop from backlog if exists
        task = None
        for i,t in enumerate(state["backlog"]):
            if t["id"] == task_id:
                task = state["backlog"].pop(i)
                break
        if task is None:
            # maybe it resides in a worker already; remove it
            for col in state["workers"]:
                for i,t in enumerate(col["tasks"]):
                    if t["id"] == task_id:
                        task = col["tasks"].pop(i)
                        break
                if task:
                    break
        # push into destination
        for col in state["workers"]:
            if col["worker_id"] == dest:
                col["tasks"].append(task)
                break

    elif role in ("move_up","move_down","remove"):
        worker_id = pid["worker_id"]
        idx = pid["index"]
        col = next(c for c in state["workers"] if c["worker_id"] == worker_id)
        if role == "remove":
            col["tasks"].pop(idx)
        else:
            if role == "move_up" and idx > 0:
                col["tasks"][idx-1], col["tasks"][idx] = col["tasks"][idx], col["tasks"][idx-1]
            if role == "move_down" and idx < len(col["tasks"])-1:
                col["tasks"][idx+1], col["tasks"][idx] = col["tasks"][idx], col["tasks"][idx+1]
    return state

# ---- Gantt chart
@app.callback(
    Output("gantt","figure"),
    [Input("state","data")]
)
def update_gantt(state):
    df = build_schedule_df(state, services_idx, workers_idx, DAY_START)
    if df.empty:
        return px.timeline(title="No tasks scheduled yet.")
    fig = px.timeline(
        df, x_start="Start", x_end="Finish",
        y="Worker", color="Service", text="Customer", hover_data=["Duration(min)"]
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(margin=dict(l=20,r=20,t=40,b=20), height=500)
    return fig

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
