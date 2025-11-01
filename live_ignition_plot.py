importjson
importmatplotlib.pyplotasplt
importmatplotlib.animationasanimation
importos

# Path to the ignition trace JSON file
TRACE_FILE="data/hyperdrive_logs/hyperdrive_ignition_trace_engine-A.json"

# Function to read only the latest data from the file
defload_recent_trace(file_path,window=500):
    ifnotos.path.exists(file_path):
        return[]

withopen(file_path,"r")asf:
        try:
            data=json.load(f)
exceptjson.JSONDecodeError:
            return[]# file still being written, skip this frame

returndata[-window:]# keep only the last N ticks

# Compute resonance & drift (simple example using dummy keys; adjust if needed)
defcompute_resonance_drift(trace):
    resonance=[tick.get("resonance",0)fortickintrace]
drift=[tick.get("drift",0)fortickintrace]
returnresonance,drift

# Set up the plot
fig,ax=plt.subplots()
line_res,=ax.plot([],[],label="Resonance Phase",color="cyan")
line_drift,=ax.plot([],[],label="Drift",color="orange")
ax.set_xlabel("Tick")
ax.set_ylabel("Value")
ax.set_title("Live Ignition Trace")
ax.legend()

# Animation update function
defupdate(frame):
    trace=load_recent_trace(TRACE_FILE)
ifnottrace:
        returnline_res,line_drift

resonance,drift=compute_resonance_drift(trace)
ticks=list(range(len(resonance)))

line_res.set_data(ticks,resonance)
line_drift.set_data(ticks,drift)

ax.relim()
ax.autoscale_view()
returnline_res,line_drift

ani=animation.FuncAnimation(fig,update,interval=1000)# refresh every 1 sec
plt.show()