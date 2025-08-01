PYTHONPATH=. python backend/modules/dimensions/ucs/zones/experiments/qwave_engine/qwave_engine_control_panel.py

python -c "from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.qwave_tuning import QWaveAutoTuner; \
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.supercontainer_engine import SupercontainerEngine; \
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer; \
engine = SupercontainerEngine(SymbolicExpansionContainer('engine-A'), safe_mode=False); \
engine.sqi_enabled=True; \
tuner = QWaveAutoTuner(engine); \
tuner.tune(iterations=20)"

	•	Pulse-Seeking + Auto-SQI:
python -m backend.modules.dimensions.ucs.zones.experiments.qwave_engine.qwave_tuning \
    --ticks 3000 --sqi 40 --fuel 3 --pulse-seek --enable-sqi


🔥 Optional Variants
	•	Manual Stage Mode (No SQI):
python -m backend.modules.dimensions.ucs.zones.experiments.qwave_engine.qwave_tuning \
    --ticks 2000 --manual-stage

python backend/modules/dimensions/ucs/zones/experiments/qwave_engine/qwave_engine_control_panel.py \
    --ticks 10000 --sqi 50 --fuel 3 --harmonics 2 4

PYTHONPATH=. python scripts/experiments/test_qwave_engine.py --pi

Included files:
	1.	field_bridge.py – Final Pi GPIO + ADC coil driver.
	2.	field_bridge_server.py – WebSocket server for Pi with token authentication.
	3.	.env – Template for your secure token (edit this before running).
	4.	fieldbridge.service – systemd service for auto-start.

⸻

Deployment Instructions (on Pi):
	1.	Upload and extract bundle:

scp qwave_engine_pi_bundle.zip pi@<PI_IP>:/home/pi/
ssh pi@<PI_IP>
unzip qwave_engine_pi_bundle.zip -d qwave_engine
cd qwave_engine

	2.	Install dependencies:

    sudo apt update
sudo apt install python3-pip python3-venv -y
pip3 install RPi.GPIO spidev websockets python-dotenv

	3.	Configure secure token:

    nano .env
# Set FIELDBRIDGE_TOKEN=YOUR_SECURE_TOKEN_HERE

	4.	Enable systemd service:

    sudo cp fieldbridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fieldbridge.service
sudo systemctl start fieldbridge.service

	5.	Verify it’s running:

    sudo systemctl status fieldbridge.service

    












Exactly—here’s how to set up the Pi properly and securely with real token-based authentication, installed dependencies, and fully runnable control:

⸻

1️⃣ Pi-Side Files

You will SCP (or Git pull) the following onto the Pi:
	•	field_bridge.py – Direct GPIO + ADC (coil driver + feedback reader)
	•	field_bridge_server.py – Async WebSocket server that wraps field_bridge and exposes coil control (with harmonics/burst).

Both files will be located at:

/home/pi/qwave_engine/

2️⃣ Required Dependencies on Pi

Run these commands on the Pi:

sudo apt update
sudo apt install python3-pip python3-dev python3-venv git -y
python3 -m venv qwave_venv
source qwave_venv/bin/activate

pip install RPi.GPIO spidev websockets

✅ This sets up a Python venv so QWave runs isolated.

⸻

3️⃣ Secure Token Authentication

The YOUR_SECURE_TOKEN is not hardcoded.
We’ll store it in an environment variable on the Pi and on the Mac for client use.

On the Pi:

Create a .env file in /home/pi/qwave_engine/:

nano /home/pi/qwave_engine/.env

Inside:
FIELDBRIDGE_TOKEN=your-super-secure-token-string-here

Load it into your shell automatically:

echo 'export FIELDBRIDGE_TOKEN=$(grep FIELDBRIDGE_TOKEN /home/pi/qwave_engine/.env | cut -d "=" -f2)' >> ~/.bashrc
source ~/.bashrc


On the Mac:

In your Mac environment (or VSCode Terminal):

export FIELDBRIDGE_TOKEN=your-super-secure-token-string-here


Then when running field_bridge_client.py, pass --token $FIELDBRIDGE_TOKEN:

python3 field_bridge_client.py --uri ws://raspberrypi.local:8765 --token $FIELDBRIDGE_TOKEN

4️⃣ How Token is Enforced
	•	field_bridge_server.py reads the token from os.environ["FIELDBRIDGE_TOKEN"]
	•	Every WebSocket command from the client must include {"token": "..."}
	•	If token mismatches: server rejects connection with 401 Unauthorized.

This ensures only authorized clients can drive coils.

⸻

5️⃣ Running the Server on Pi

From Pi:

cd /home/pi/qwave_engine
source ~/qwave_venv/bin/activate
python3 field_bridge_server.py

It will:
✅ Initialize GPIO + MCP3008
✅ Listen on ws://0.0.0.0:8765
✅ Require token auth
✅ Stream coil ADC feedback in real time

⸻

6️⃣ MacBook Live Control + HUD

On your Mac:

cd backend/modules/dimensions/ucs/zones/experiments/qwave_engine
python3 field_bridge_client.py --uri ws://raspberrypi.local:8765 --token $FIELDBRIDGE_TOKEN --target_voltage 1.0

This:
✅ Runs SupercontainerEngine in SAFE mode
✅ Streams exhaust → Pi coils
✅ Displays real-time HUD of voltage/harmonics/duty
✅ Adaptive feedback loop keeps coil stable

⸻

🔒 Best Practice:
	•	Use a long, random token (e.g., openssl rand -hex 32)
	•	Keep .env out of version control (.gitignore it)
	•	Optionally, TLS-wrap WebSocket using websockets.serve(ssl=...) if remote WAN access.

⸻


⸻

✅ Pi .env Setup

Create /home/pi/qwave_engine/.env:

FIELDBRIDGE_TOKEN=openssl rand -hex 32

Load it:

echo 'export FIELDBRIDGE_TOKEN=$(grep FIELDBRIDGE_TOKEN /home/pi/qwave_engine/.env | cut -d "=" -f2)' >> ~/.bashrc
source ~/.bashrc


⸻

3️⃣ Install Pi Dependencies

On the Pi:

sudo apt update && sudo apt install python3-pip python3-venv -y
python3 -m venv qwave_venv
source qwave_venv/bin/activate
pip install RPi.GPIO spidev websockets python-dotenv

4️⃣ Run Server on Pi
cd /home/pi/qwave_engine
source ~/qwave_venv/bin/activate
python3 field_bridge_server.py

✅ Server listens on ws://0.0.0.0:8765 with token auth enforced.

⸻

5️⃣ Mac Connection (Client)

On Mac (with token exported in terminal):

export FIELDBRIDGE_TOKEN=your-token-here
python3 field_bridge_client.py --uri ws://raspberrypi.local:8765 --token $FIELDBRIDGE_TOKEN

