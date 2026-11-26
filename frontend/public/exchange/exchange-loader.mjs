// Deployment-controlled switch: enabling shared mode never falls back to local money.
const main=document.getElementById('main');
try {
  const response=await fetch('/api/iq-connection',{cache:'no-store'});
  if(!response.ok)throw Error('Connection settings unavailable');
  const config=await response.json();
  if(config.mode==='shared-simulated') await import('./hosted-exchange.mjs');
  else if(config.mode==='legacy-browser-demo') await import('./exchange.mjs');
  else throw Error('Unknown exchange mode');
} catch {
  if(main)main.innerHTML='<section class="panel panel-body"><h1>Connection unavailable</h1><p>The exchange could not check its connection settings. Refresh to try again. No trading or balance changes have been made.</p></section>';
}
