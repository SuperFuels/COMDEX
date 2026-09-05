from __future__ import annotations

import html
import json
import math
import threading
import time
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class GodViewData:
    """Bounded, keyless public-evidence gateway for Pilot's planet view."""

    def __init__(self, opener: Callable[..., Any] = urlopen) -> None:
        self._opener = opener
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._blob_cache: dict[str, tuple[float, bytes]] = {}
        self._lock = threading.Lock()

    def _json(self, url: str, *, ttl: int, limit: int = 1_500_000) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            cached = self._cache.get(url)
            if cached and now - cached[0] <= ttl:
                return cached[1]
        request = Request(url, headers={"User-Agent": "Pilot-God-View/0.20 (local household intelligence)"})
        with self._opener(request, timeout=8) as response:
            raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("Public evidence response exceeded the safety limit")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, (dict, list)):
            raise ValueError("Public evidence returned an unsupported structure")
        wrapped = payload if isinstance(payload, dict) else {"items": payload}
        with self._lock:
            self._cache[url] = (now, wrapped)
        return wrapped

    @staticmethod
    def _coordinates(latitude: Any, longitude: Any) -> tuple[float, float]:
        lat, lon = float(latitude), float(longitude)
        if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError("Invalid coordinates")
        return round(lat, 5), round(lon, 5)

    def geocode(self, query: str) -> dict[str, Any]:
        cleaned = " ".join(str(query).split())[:120]
        if len(cleaned) < 2:
            raise ValueError("Enter a place to explore")
        params = urlencode({"q": cleaned, "format": "jsonv2", "limit": 5, "addressdetails": 1})
        data = self._json(f"https://nominatim.openstreetmap.org/search?{params}", ttl=86_400)
        matches = []
        for item in list(data.get("items") or [])[:5]:
            try:
                lat, lon = self._coordinates(item.get("lat"), item.get("lon"))
            except (TypeError, ValueError):
                continue
            matches.append({"name": str(item.get("display_name") or cleaned)[:240], "lat": lat, "lon": lon})
        return {
            "status": "LIVE",
            "source": "OpenStreetMap Nominatim",
            "source_url": "https://nominatim.openstreetmap.org/",
            "retrieved_at": int(time.time()),
            "matches": matches,
        }

    def weather(self, latitude: Any, longitude: Any) -> dict[str, Any]:
        lat, lon = self._coordinates(latitude, longitude)
        params = urlencode(
            {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "forecast_days": 5,
                "timezone": "auto",
            }
        )
        payload = self._json(f"https://api.open-meteo.com/v1/forecast?{params}", ttl=600)
        return {
            "status": "FORECAST",
            "source": "Open-Meteo",
            "source_url": "https://open-meteo.com/",
            "retrieved_at": int(time.time()),
            "latitude": lat,
            "longitude": lon,
            "current": dict(payload.get("current") or {}),
            "daily": dict(payload.get("daily") or {}),
            "timezone": str(payload.get("timezone") or ""),
        }

    def flights(self, latitude: Any, longitude: Any) -> dict[str, Any]:
        lat, lon = self._coordinates(latitude, longitude)
        # adsb.lol publishes an ODbL point API. Keep the radius and result set bounded.
        payload = self._json(f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/250", ttl=15)
        aircraft = []
        for item in list(payload.get("ac") or [])[:160]:
            try:
                aircraft_lat, aircraft_lon = self._coordinates(item.get("lat"), item.get("lon"))
            except (TypeError, ValueError):
                continue
            aircraft.append(
                {
                    "hex": str(item.get("hex") or "")[:12],
                    "flight": str(item.get("flight") or item.get("r") or "Unknown").strip()[:24],
                    "lat": aircraft_lat,
                    "lon": aircraft_lon,
                    "altitude_ft": item.get("alt_baro") if isinstance(item.get("alt_baro"), (int, float)) else None,
                    "speed_knots": item.get("gs") if isinstance(item.get("gs"), (int, float)) else None,
                    "track": item.get("track") if isinstance(item.get("track"), (int, float)) else 0,
                }
            )
        return {
            "status": "LIVE",
            "freshness_seconds": 15,
            "source": "adsb.lol contributors (ODbL)",
            "source_url": "https://adsb.lol/",
            "retrieved_at": int(time.time()),
            "latitude": lat,
            "longitude": lon,
            "aircraft": aircraft,
        }

    def nasa_earth(self) -> dict[str, Any]:
        """Return the newest NASA DSCOVR EPIC natural-colour Earth image."""
        payload = self._json("https://epic.gsfc.nasa.gov/api/natural", ttl=900)
        items = list(payload.get("items") or [])
        if not items:
            raise ValueError("NASA EPIC has not published an image yet")
        newest = dict(items[0])
        captured = str(newest.get("date") or "")[:19]
        image_id = str(newest.get("image") or "")[:100]
        if len(captured) < 10 or not image_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("NASA EPIC returned incomplete image metadata")
        year, month, day = captured[:10].split("-")
        return {
            "status": "RECENT SATELLITE IMAGE",
            "source": "NASA DSCOVR EPIC",
            "source_url": "https://epic.gsfc.nasa.gov/",
            "captured_at": captured.replace(" ", "T") + "Z",
            "retrieved_at": int(time.time()),
            "image_url": f"https://epic.gsfc.nasa.gov/archive/natural/{year}/{month}/{day}/png/{image_id}.png",
            "caption": str(newest.get("caption") or "Natural-colour view of Earth")[:300],
        }

    def nasa_earth_image(self) -> bytes:
        metadata = self.nasa_earth()
        url = str(metadata["image_url"])
        now = time.time()
        with self._lock:
            cached = self._blob_cache.get(url)
            if cached and now - cached[0] <= 900:
                return cached[1]
        request = Request(url, headers={"User-Agent": "Pilot-God-View/0.20 (local household intelligence)"})
        with self._opener(request, timeout=12) as response:
            image = response.read(8_000_001)
        if len(image) > 8_000_000 or not image.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("NASA EPIC image was invalid or exceeded the safety limit")
        with self._lock:
            self._blob_cache[url] = (now, image)
        return image

    def map_tile(self, zoom: Any, tile_x: Any, tile_y: Any) -> bytes:
        """Proxy one bounded OpenStreetMap tile for television-safe fallback navigation."""
        z, x, y = int(zoom), int(tile_x), int(tile_y)
        if not 0 <= z <= 8:
            raise ValueError("Unsupported map zoom")
        edge = 1 << z
        if not 0 <= x < edge or not 0 <= y < edge:
            raise ValueError("Invalid map tile")
        url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        now = time.time()
        with self._lock:
            cached = self._blob_cache.get(url)
            if cached and now - cached[0] <= 86_400:
                return cached[1]
        request = Request(
            url,
            headers={
                "User-Agent": "Pilot-God-View/0.20 (local household intelligence; cached TV map fallback)",
                "Referer": "http://localhost/Pilot-God-View",
            },
        )
        with self._opener(request, timeout=8) as response:
            image = response.read(1_000_001)
        if len(image) > 1_000_000 or not image.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Map tile was invalid or exceeded the safety limit")
        with self._lock:
            self._blob_cache[url] = (now, image)
        return image

    def iss_position(self) -> dict[str, Any]:
        """Return a tightly cached, keyless current ISS ground position."""
        payload = self._json("https://api.wheretheiss.at/v1/satellites/25544", ttl=5)
        lat, lon = self._coordinates(payload.get("latitude"), payload.get("longitude"))
        return {
            "status": "LIVE POSITION",
            "source": "Where the ISS at (NORAD 25544)",
            "source_url": "https://wheretheiss.at/",
            "retrieved_at": int(time.time()),
            "timestamp": int(payload.get("timestamp") or time.time()),
            "latitude": lat,
            "longitude": lon,
            "altitude_km": round(float(payload.get("altitude") or 0), 1),
            "velocity_kmh": round(float(payload.get("velocity") or 0)),
            "visibility": str(payload.get("visibility") or "unknown")[:30],
        }


def god_view_html(token: str) -> bytes:
    safe_token = html.escape(token, quote=True)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pilot God View</title><link rel="stylesheet" href="https://cesium.com/downloads/cesiumjs/releases/1.129/Build/Cesium/Widgets/widgets.css">
<script src="https://cesium.com/downloads/cesiumjs/releases/1.129/Build/Cesium/Cesium.js"></script><script>if(window.Cesium){{const NativeViewer=Cesium.Viewer;Cesium.Viewer=function(container,options){{const fixed=Object.assign({{}},options);if(fixed.imageryProvider){{fixed.baseLayer=new Cesium.ImageryLayer(fixed.imageryProvider);delete fixed.imageryProvider}}return new NativeViewer(container,fixed)}};Cesium.Viewer.prototype=NativeViewer.prototype}}</script><style>
.cockpit{{display:none;position:absolute;inset:12vh 8vw 7vh;border-left:.16vw solid #69e7ff99;border-right:.16vw solid #69e7ff99;clip-path:polygon(0 0,19% 0,25% 48%,40% 74%,60% 74%,75% 48%,81% 0,100% 0,100% 100%,0 100%);box-shadow:inset 0 -8vh 10vh #001020aa}}.cockpit:before{{content:'PILOT MODE · VIEWING CAMERA · GAMEPAD FLIGHT CONTROL';position:absolute;top:1vh;left:50%;transform:translateX(-50%);font-size:.7vw;letter-spacing:.18em;color:#7aeeff;white-space:nowrap}}body.pilot .cockpit{{display:block}}body.pilot .crosshair{{width:3.4vw;height:3.4vw;border-color:#73f4ff}}body.pilot .panel{{width:29vw}}#pilot-mode{{background:linear-gradient(135deg,#0d66bd,#18b7e5)}}
*{{box-sizing:border-box}}html,body,#globe{{width:100%;height:100%;margin:0;overflow:hidden;background:#020711;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#f5f8ff}}#globe{{position:absolute;inset:0}}.hud{{position:absolute;z-index:4;inset:0;pointer-events:none;background:radial-gradient(circle at 50% 45%,transparent 25%,#02071135 70%,#020711a8 100%)}}.top{{position:absolute;top:2.6vh;left:2.3vw;right:2.3vw;display:flex;justify-content:space-between;align-items:flex-start;gap:2vw}}.brand{{text-shadow:0 2px 16px #000;font-size:1vw;letter-spacing:.2em;font-weight:850;text-transform:uppercase;color:#88c9ff}}.title{{font-size:2.3vw;font-weight:900;letter-spacing:-.05em;text-shadow:0 4px 24px #000}}.truth{{display:flex;gap:.6vw;flex-wrap:wrap;justify-content:flex-end}}.badge{{padding:.55vw .85vw;border:1px solid #5bc8ff66;border-radius:99px;background:#06162cbb;color:#b9e8ff;font-size:.72vw;font-weight:850;letter-spacing:.08em}}.badge.live{{color:#77f4b5;border-color:#4fe3a066}}.panel{{position:absolute;pointer-events:auto;left:2.3vw;bottom:3vh;width:34vw;padding:1.1vw;border:1px solid #71cfff55;border-radius:1.25vw;background:#051225dd;box-shadow:0 1vw 4vw #0008;backdrop-filter:blur(18px)}}.search{{display:grid;grid-template-columns:1fr auto;gap:.65vw}}input,button{{font:inherit;border-radius:.8vw;border:1px solid #5b8fbb66}}input{{padding:.85vw 1vw;background:#071a31;color:white;font-size:1vw;outline:none}}button{{padding:.75vw 1vw;background:#0e4fa3;color:white;font-weight:800;cursor:pointer}}button:focus{{outline:.2vw solid #71d5ff;outline-offset:.15vw}}.quick{{display:flex;gap:.55vw;margin-top:.7vw;flex-wrap:wrap}}.quick button{{background:#0a203b;font-size:.78vw;padding:.58vw .75vw}}#readout{{margin-top:.8vw;color:#c8d7e9;font-size:.86vw;line-height:1.45;min-height:2.5em}}#weather{{position:absolute;pointer-events:auto;right:2.3vw;bottom:3vh;width:22vw;padding:1vw 1.1vw;border:1px solid #71cfff55;border-radius:1.25vw;background:#051225dd;box-shadow:0 1vw 4vw #0008;display:none}}#weather strong{{font-size:1.7vw}}#weather span{{display:block;color:#b8c9dd;margin-top:.3vh;font-size:.82vw}}.crosshair{{position:absolute;left:50%;top:50%;width:1.5vw;height:1.5vw;transform:translate(-50%,-50%);border:.1vw solid #68d7ff88;border-radius:50%}}.crosshair:before,.crosshair:after{{content:'';position:absolute;background:#68d7ff88}}.crosshair:before{{height:.1vw;width:2.4vw;left:-.5vw;top:.65vw}}.crosshair:after{{width:.1vw;height:2.4vw;left:.65vw;top:-.5vw}}.credit{{position:absolute;right:2.3vw;top:8vh;color:#a9bbcf;font-size:.65vw;text-align:right;text-shadow:0 2px 8px #000}}.cesium-viewer-bottom{{left:auto!important;right:0!important}}@media(max-width:800px){{.panel{{width:55vw}}#weather{{width:35vw}}}}
</style></head><body><div id="globe"></div><div class="hud"><div class="top"><div><div class="brand">Tessaris · Pilot planetary intelligence</div><div class="title">God View</div></div><div class="truth"><span class="badge live">● LIVE PUBLIC SIGNALS</span><span class="badge">FORECASTS LABELLED</span><span class="badge">NO PAID AI</span></div></div><div class="credit">Open globe · © OpenStreetMap contributors<br>Live layers retain source and freshness</div><div class="crosshair"></div><div class="cockpit"></div><section class="panel"><div class="search"><input id="place" value="Lapland" aria-label="Place to explore"><button id="go">Fly there</button></div><div class="quick"><button data-place="Lapland">Lapland</button><button data-place="Albox, Almería">Home region</button><button id="flights">Live aircraft</button><button id="pilot-mode">✈ Pilot Mode</button><button id="earth">Whole Earth</button><button id="home">Pilot Home</button></div><div id="readout">Ask Pilot to take you anywhere on Earth.</div></section><section id="weather"><div class="badge">FORECAST · OPEN-METEO</div><strong id="temperature">—</strong><span id="conditions">Loading current conditions…</span><span id="forecast"></span></section></div><script>
const base='/tv/{safe_token}/god-view';let viewer,focus={{lat:67.92,lon:26.5,name:'Lapland'}},flightEntities=[];const readout=document.getElementById('readout'),weather=document.getElementById('weather');function status(text){{readout.textContent=text}}function init(){{if(!window.Cesium){{status('The 3D engine could not load. Check the television internet connection.');return}}Cesium.Ion.defaultAccessToken=undefined;viewer=new Cesium.Viewer('globe',{{animation:false,timeline:false,baseLayerPicker:false,geocoder:false,homeButton:false,navigationHelpButton:false,sceneModePicker:false,fullscreenButton:false,infoBox:false,selectionIndicator:false,imageryProvider:new Cesium.OpenStreetMapImageryProvider({{url:'https://tile.openstreetmap.org/'}})}});viewer.scene.globe.enableLighting=true;viewer.scene.skyAtmosphere.show=true;viewer.scene.fog.enabled=true;viewer.camera.flyTo({{destination:Cesium.Cartesian3.fromDegrees(12,32,19000000),duration:0}});setTimeout(()=>fly('Lapland'),900)}}async function api(path){{const r=await fetch(base+path,{{cache:'no-store'}});const j=await r.json();if(!r.ok)throw new Error(j.error||'Public evidence unavailable');return j}}async function fly(query){{status('Locating '+query+'…');try{{const data=await api('/geocode?query='+encodeURIComponent(query)),m=data.matches&&data.matches[0];if(!m)throw new Error('No matching location found');focus={{lat:m.lat,lon:m.lon,name:m.name}};viewer.camera.flyTo({{destination:Cesium.Cartesian3.fromDegrees(m.lon,m.lat,120000),orientation:{{heading:0,pitch:Cesium.Math.toRadians(-62),roll:0}},duration:3}});status('LIVE PLACE · '+m.name+' · Source: OpenStreetMap');loadWeather()}}catch(e){{status(e.message)}}}}async function loadWeather(){{try{{const data=await api('/weather?lat='+focus.lat+'&lon='+focus.lon),c=data.current||{{}},d=data.daily||{{}};weather.style.display='block';document.getElementById('temperature').textContent=Math.round(c.temperature_2m)+'°C';document.getElementById('conditions').textContent='Feels '+Math.round(c.apparent_temperature)+'°C · Wind '+Math.round(c.wind_speed_10m||0)+' km/h · Current observation';const days=(d.time||[]).slice(0,5).map((x,i)=>x.slice(5)+' '+Math.round((d.temperature_2m_min||[])[i])+'–'+Math.round((d.temperature_2m_max||[])[i])+'°').join('  ·  ');document.getElementById('forecast').textContent=days+' · Updated '+new Date(data.retrieved_at*1000).toLocaleTimeString([],{{hour:'2-digit',minute:'2-digit'}})}}catch(e){{weather.style.display='none'}}}}async function loadFlights(){{status('Reading nearby public aircraft signals…');try{{const data=await api('/flights?lat='+focus.lat+'&lon='+focus.lon);flightEntities.forEach(x=>viewer.entities.remove(x));flightEntities=[];(data.aircraft||[]).forEach(a=>{{const altitude=Math.max(300,Number(a.altitude_ft||10000)*.3048);flightEntities.push(viewer.entities.add({{position:Cesium.Cartesian3.fromDegrees(a.lon,a.lat,altitude),point:{{pixelSize:8,color:Cesium.Color.CYAN,outlineColor:Cesium.Color.WHITE,outlineWidth:1}},label:{{text:a.flight,font:'12px sans-serif',fillColor:Cesium.Color.WHITE,showBackground:true,backgroundColor:new Cesium.Color(0.01,0.05,0.12,.75),pixelOffset:new Cesium.Cartesian2(0,-17),distanceDisplayCondition:new Cesium.DistanceDisplayCondition(0,700000)}}}}))}});status('LIVE AIRCRAFT · '+flightEntities.length+' signals within 250 nautical miles · adsb.lol · ≤15s source cache')}}catch(e){{status('Aircraft layer unavailable · '+e.message)}}}}function rotate(dx,dy){{if(!viewer)return;viewer.camera.rotateRight(dx);viewer.camera.rotateUp(dy)}}document.getElementById('go').onclick=()=>fly(document.getElementById('place').value);document.getElementById('place').onkeydown=e=>{{if(e.key==='Enter')fly(e.target.value)}};document.querySelectorAll('[data-place]').forEach(b=>b.onclick=()=>{{document.getElementById('place').value=b.dataset.place;fly(b.dataset.place)}});document.getElementById('flights').onclick=loadFlights;document.getElementById('earth').onclick=()=>viewer.camera.flyTo({{destination:Cesium.Cartesian3.fromDegrees(12,28,19000000),duration:2.5}});document.getElementById('home').onclick=()=>location.href='/tv/{safe_token}';document.addEventListener('keydown',e=>{{if(e.target.tagName==='INPUT')return;if(e.key==='ArrowLeft')rotate(.035,0);else if(e.key==='ArrowRight')rotate(-.035,0);else if(e.key==='ArrowUp')viewer.camera.zoomIn(viewer.camera.positionCartographic.height*.12);else if(e.key==='ArrowDown')viewer.camera.zoomOut(viewer.camera.positionCartographic.height*.12);else return;e.preventDefault()}});let held='',last=0;function pads(t){{const p=[...(navigator.getGamepads?navigator.getGamepads():[])].find(Boolean);if(p){{const x=p.axes[0]||0,y=p.axes[1]||0,k=Math.abs(x)>.3?(x>0?'r':'l'):Math.abs(y)>.3?(y>0?'d':'u'):'';if(k&&(k!==held||t-last>110)){{last=t;if(k==='l')rotate(.025,0);if(k==='r')rotate(-.025,0);if(k==='u')viewer.camera.zoomIn(viewer.camera.positionCartographic.height*.08);if(k==='d')viewer.camera.zoomOut(viewer.camera.positionCartographic.height*.08)}}held=k}}requestAnimationFrame(pads)}}window.addEventListener('load',()=>{{init();requestAnimationFrame(pads)}});
</script><script>window.addEventListener('load',()=>{{setTimeout(()=>{{if(viewer){{viewer.scene.globe.show=true;viewer.scene.globe.enableLighting=false;viewer.scene.globe.baseColor=Cesium.Color.fromCssColorString('#173b63');viewer.imageryLayers.removeAll();viewer.imageryLayers.addImageryProvider(new Cesium.OpenStreetMapImageryProvider({{url:'https://tile.openstreetmap.org/'}}))}}}},250);setTimeout(()=>{{if(viewer) viewer.camera.flyHome(0)}},4200)}});document.getElementById('pilot-mode').onclick=()=>{{const active=document.body.classList.toggle('pilot');const h=viewer&&viewer.camera.positionCartographic.height;if(active&&viewer){{viewer.trackedEntity=undefined;viewer.camera.flyTo({{destination:Cesium.Cartesian3.fromDegrees(focus.lon,focus.lat,Math.min(18000,Math.max(4500,h||12000))),orientation:{{heading:viewer.camera.heading,pitch:Cesium.Math.toRadians(-18),roll:0}},duration:2}})}}status(active?'PILOT MODE · Viewing-camera simulation · Use the gamepad stick or TV arrows to bank, dive and climb.':'GOD VIEW · Planet navigation restored.')}};</script><script>
const visual=document.createElement('img');visual.id='earth-visual';visual.className='earth-fallback';visual.src=base+'/earth.png';visual.alt='Rendered full Earth';document.body.insertBefore(visual,document.querySelector('.hud'));
const visualStyle=document.createElement('style');visualStyle.textContent='.earth-fallback{{position:absolute;z-index:2;pointer-events:none;left:50%;top:49%;width:min(62vw,72vh);height:min(62vw,72vh);transform:translate(-50%,-50%);object-fit:contain;filter:drop-shadow(0 0 4vw #2d7ed066);transition:transform 1.4s cubic-bezier(.2,.8,.2,1),filter .5s ease,opacity .7s ease;animation:planet-breathe 12s ease-in-out infinite}}body.pilot .earth-fallback{{filter:drop-shadow(0 0 5vw #35d8ff88) saturate(1.15)}}body.satellite .earth-fallback{{width:min(67vw,78vh);height:min(67vw,78vh);animation:none}}#map-fallback{{display:none;position:absolute;z-index:2;inset:0;overflow:hidden;background:#071322;opacity:0;transition:opacity .8s ease}}#map-fallback.visible{{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);opacity:1;animation:map-arrive 1.8s cubic-bezier(.15,.8,.2,1)}}#map-fallback img{{width:100%;height:100%;object-fit:cover;transform:scale(1.015)}}#map-vignette{{position:absolute;z-index:2;inset:0;pointer-events:none;background:radial-gradient(circle at 50% 48%,transparent 18%,#02071155 72%,#020711dd 100%)}}#iss-marker{{position:absolute;z-index:3;display:none;left:50%;top:44%;transform:translate(-50%,-50%);font-size:3vw;filter:drop-shadow(0 0 1vw #5bdcff);transition:left .7s ease,top .7s ease}}@keyframes planet-breathe{{0%,100%{{filter:drop-shadow(0 0 4vw #2d7ed055)}}50%{{filter:drop-shadow(0 0 5vw #3c92df88)}}}}@keyframes map-arrive{{0%{{transform:scale(1.65);filter:blur(6px);opacity:0}}100%{{transform:scale(1);filter:none;opacity:1}}}}';document.head.appendChild(visualStyle);const mapLayer=document.createElement('div');mapLayer.id='map-fallback';mapLayer.innerHTML='<div id="map-vignette"></div>';document.body.insertBefore(mapLayer,document.querySelector('.hud'));const issMarker=document.createElement('div');issMarker.id='iss-marker';issMarker.textContent='🛰️';document.body.insertBefore(issMarker,document.querySelector('.hud'));
const truth=document.querySelector('.truth'),renderBadge=document.createElement('span');renderBadge.className='badge';renderBadge.textContent='RENDERED PLANET';truth.appendChild(renderBadge);
const quick=document.querySelector('.quick'),nasa=document.createElement('button');nasa.id='nasa-earth';nasa.textContent='NASA Earth Now';quick.insertBefore(nasa,document.getElementById('pilot-mode'));const iss=document.createElement('button');iss.id='iss-track';iss.textContent='Track ISS';quick.insertBefore(iss,document.getElementById('pilot-mode'));const liveIss=document.createElement('button');liveIss.id='iss-live';liveIss.textContent='Live View from Space';quick.insertBefore(liveIss,iss);const videoLayer=document.createElement('div');videoLayer.id='iss-video';videoLayer.style.cssText='display:none;position:absolute;z-index:3;inset:9vh 8vw 8vh;background:#000;border:1px solid #5bc8ff88;border-radius:1.4vw;overflow:hidden;box-shadow:0 2vw 6vw #000';videoLayer.innerHTML='<iframe title="Live 4K Earth video from SEN STV-1 on the International Space Station" src="about:blank" referrerpolicy="strict-origin-when-cross-origin" style="width:100%;height:100%;border:0" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe><div style="position:absolute;left:1vw;top:1vw;padding:.55vw .8vw;border-radius:99px;background:#07162ddd;color:#7cf3b7;font-size:.72vw;font-weight:850">● LIVE EARTH 4K · SEN STV-1 · ISS</div><button id="close-iss-video" style="position:absolute;right:1vw;top:1vw">Back to God View</button>';document.body.insertBefore(videoLayer,document.querySelector('.hud'));const closeFeed=()=>{{videoLayer.style.display='none';videoLayer.querySelector('iframe').src='about:blank';if(typeof mapLayer!=='undefined')mapLayer.classList.remove('visible');visual.style.opacity='1';visual.style.transform='';renderBadge.textContent='RENDERED PLANET';status('GOD VIEW · Live video closed')}};videoLayer.querySelector('#close-iss-video').onclick=closeFeed;
const placeMarker=document.createElement('div');placeMarker.id='place-marker';placeMarker.style.cssText='display:none;position:absolute;z-index:3;left:50%;top:48%;transform:translate(-50%,-50%);padding:.55vw .85vw;border-radius:99px;background:#06162ddd;border:1px solid #72d7ff;color:white;font-size:.82vw;font-weight:850;box-shadow:0 0 2vw #37aaff';document.body.insertBefore(placeMarker,document.querySelector('.hud'));function showMapTiles(m){{const z=6,n=1<<z,lat=Math.max(-85.0511,Math.min(85.0511,Number(m.lat))),lon=Number(m.lon),cx=Math.floor((lon+180)/360*n),rad=lat*Math.PI/180,cy=Math.floor((1-Math.asinh(Math.tan(rad))/Math.PI)/2*n);mapLayer.querySelectorAll('img').forEach(x=>x.remove());for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){{const img=document.createElement('img');img.alt='Map tile';img.src=base+'/tile/'+z+'/'+((cx+dx+n)%n)+'/'+Math.max(0,Math.min(n-1,cy+dy))+'.png';mapLayer.insertBefore(img,mapLayer.firstChild)}}mapLayer.classList.remove('visible');void mapLayer.offsetWidth;mapLayer.classList.add('visible')}}window.showPlaceFallback=m=>{{closeFeed();visual.src=base+'/earth.png';document.body.classList.remove('satellite');issMarker.style.display='none';visual.style.transform='translate(-50%,-50%) scale(2.4) rotate('+(-Number(m.lon)/9)+'deg)';setTimeout(()=>{{visual.style.opacity='0';showMapTiles(m)}},650);placeMarker.style.display='block';placeMarker.textContent='📍 '+String(m.name||'Selected place').split(',')[0];renderBadge.textContent='LIVE LOCAL MAP'}};
const globeFly=fly;fly=async query=>{{await globeFly(query);window.showPlaceFallback(focus);status('LIVE PLACE · '+focus.name+' · Source: OpenStreetMap')}};
nasa.onclick=async()=>{{closeFeed();mapLayer.classList.remove('visible');visual.style.opacity='1';visual.style.transform='';placeMarker.style.display='none';status('Requesting the newest NASA DSCOVR EPIC image…');try{{const data=await api('/nasa-earth');visual.src=base+'/nasa-earth/image.png?v='+data.retrieved_at;issMarker.style.display='none';document.body.classList.add('satellite');renderBadge.textContent='RECENT NASA SATELLITE';const stamp=new Date(data.captured_at).toLocaleString();status('RECENT SATELLITE IMAGE · Captured '+stamp+' · NASA DSCOVR EPIC (not a continuous live feed)')}}catch(e){{status('NASA Earth image unavailable · '+e.message)}}}};
iss.onclick=async()=>{{mapLayer.classList.remove('visible');visual.style.opacity='1';visual.style.transform='';placeMarker.style.display='none';status('Locating the International Space Station…');try{{const data=await api('/iss');visual.src=base+'/earth.png';document.body.classList.remove('satellite');renderBadge.textContent='LIVE ISS POSITION';issMarker.style.display='block';issMarker.style.left=(50+Math.max(-22,Math.min(22,data.longitude/8)))+'%';issMarker.style.top=(46-Math.max(-18,Math.min(18,data.latitude/5)))+'%';status('LIVE ISS · '+data.latitude.toFixed(2)+'°, '+data.longitude.toFixed(2)+'° · '+Math.round(data.altitude_km)+' km high · '+Math.round(data.velocity_kmh).toLocaleString()+' km/h · '+data.visibility+' · Source: Where the ISS at')}}catch(e){{status('ISS position unavailable · '+e.message)}}}};
liveIss.onclick=()=>{{mapLayer.classList.remove('visible');visual.style.opacity='0';placeMarker.style.display='none';issMarker.style.display='none';videoLayer.style.display='block';videoLayer.querySelector('iframe').src='https://www.youtube-nocookie.com/embed/fO9e9jnhYK8?autoplay=1&mute=1&controls=1&playsinline=1&rel=0';renderBadge.textContent='LIVE EARTH 4K';status('LIVE VIEW FROM SPACE · SEN STV-1 4K cameras on the ISS · source: sen.com/live')}};
document.getElementById('earth').onclick=()=>{{closeFeed();mapLayer.classList.remove('visible');visual.style.opacity='1';visual.src=base+'/earth.png';issMarker.style.display='none';placeMarker.style.display='none';document.body.classList.remove('satellite');renderBadge.textContent='RENDERED PLANET';visual.style.transform='';if(viewer)viewer.camera.flyTo({{destination:Cesium.Cartesian3.fromDegrees(12,28,19000000),duration:2}});status('WHOLE EARTH · Planet view restored')}};
const controls=()=>[...document.querySelectorAll('.panel input,.panel button')].filter(x=>!x.disabled&&getComputedStyle(x).display!=='none');
function moveControl(step){{const items=controls();if(!items.length)return;let index=items.indexOf(document.activeElement);if(index<0)index=step>0?-1:0;const selected=items[(index+step+items.length)%items.length];selected.focus();status('CONTROLLER · Selected '+(selected.textContent||selected.value||'control').trim()+' · press OK')}}
function selectControl(){{const active=document.activeElement;if(active&&controls().includes(active)){{if(active.tagName==='INPUT')document.getElementById('go').click();else active.click()}}else moveControl(1)}}
document.addEventListener('keydown',event=>{{if(document.body.classList.contains('pilot')){{if(event.key==='Escape'||event.key==='Backspace'){{document.getElementById('pilot-mode').click();event.preventDefault();event.stopImmediatePropagation()}}return}}if(event.key==='ArrowRight'||event.key==='ArrowDown'){{moveControl(1)}}else if(event.key==='ArrowLeft'||event.key==='ArrowUp'){{moveControl(-1)}}else if(event.key==='Enter'||event.key==='OK'){{selectControl()}}else return;event.preventDefault();event.stopImmediatePropagation()}},true);
let menuHeld='',menuLast=0;function controlPads(now){{const pad=[...(navigator.getGamepads?navigator.getGamepads():[])].find(Boolean);if(pad){{const b=pad.buttons||[],a=pad.axes||[];let command='';if(!document.body.classList.contains('pilot')){{if((b[15]&&b[15].pressed)||(b[13]&&b[13].pressed)||(a[0]||0)>.55||(a[1]||0)>.55)command='next';else if((b[14]&&b[14].pressed)||(b[12]&&b[12].pressed)||(a[0]||0)<-.55||(a[1]||0)<-.55)command='previous';else if((b[0]&&b[0].pressed)||(b[9]&&b[9].pressed))command='select'}}else if((b[1]&&b[1].pressed)||(b[8]&&b[8].pressed))command='exit';if(command&&(command!==menuHeld||now-menuLast>360)){{menuLast=now;if(command==='next')moveControl(1);else if(command==='previous')moveControl(-1);else if(command==='select')selectControl();else document.getElementById('pilot-mode').click()}}menuHeld=command}}requestAnimationFrame(controlPads)}}requestAnimationFrame(controlPads);
const launch=new URLSearchParams(location.search),launchMode=launch.get('mode'),launchPlace=(launch.get('place')||'').trim();if(launchMode==='fly'&&launchPlace){{document.getElementById('place').value=launchPlace;setTimeout(()=>fly(launchPlace),1300)}}else if(launchMode==='nasa_earth'){{setTimeout(()=>nasa.click(),1300)}}else if(launchMode==='iss_live'){{setTimeout(()=>liveIss.click(),1300)}}else if(launchMode==='iss_track'){{setTimeout(()=>iss.click(),1300)}}else setTimeout(()=>{{const items=controls();if(items.length)items[0].focus()}},1500);
let viewHeading=0,viewScale=1.34;function movePilot(name){{if(name==='left')viewHeading-=5;else if(name==='right')viewHeading+=5;else if(name==='up')viewScale=Math.min(1.9,viewScale+.08);else if(name==='down')viewScale=Math.max(.9,viewScale-.08);visual.style.transform='translate(-50%,-50%) scale('+viewScale+') rotate('+viewHeading+'deg)';status('PILOT CONTROL · heading '+((viewHeading%360)+360)%360+'° · view '+Math.round(viewScale*100)+'%')}}let controlSequence=0,controlBusy=false;async function pollFabricControl(){{if(controlBusy)return;controlBusy=true;try{{const command=await api('/control');if(Number(command.sequence)>controlSequence){{controlSequence=Number(command.sequence);const name=command.command;if(name==='back'&&videoLayer.style.display!=='none')closeFeed();else if(name==='pilot'){{closeFeed();visual.style.transform='';viewHeading=0;viewScale=1.34;document.getElementById('pilot-mode').click()}}else if(name==='earth')document.getElementById('earth').click();else if(name==='nasa')nasa.click();else if(name==='iss')liveIss.click();else if(name==='track_iss')iss.click();else if(name==='lapland')fly('Lapland');else if(name==='home_region')fly('Albox, Almería');else if(document.body.classList.contains('pilot')){{if(['left','right','up','down'].includes(name)){{movePilot(name);if(name==='left')rotate(.05,0);else if(name==='right')rotate(-.05,0);else if(name==='up'&&viewer)viewer.camera.zoomIn(viewer.camera.positionCartographic.height*.14);else if(name==='down'&&viewer)viewer.camera.zoomOut(viewer.camera.positionCartographic.height*.14)}}else if(name==='back'||name==='select'){{visual.style.transform='';viewHeading=0;viewScale=1.34;document.getElementById('pilot-mode').click()}}}}else{{if(name==='left'||name==='up')moveControl(-1);else if(name==='right'||name==='down')moveControl(1);else if(name==='select')selectControl();else if(name==='back')location.href='/tv/{safe_token}'}}}}}}catch(e){{status('Controller temporarily disconnected · reconnecting')}}finally{{controlBusy=false}}}}setInterval(pollFabricControl,260);pollFabricControl();
</script></body></html>""".encode("utf-8")
