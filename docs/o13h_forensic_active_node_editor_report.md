# O13H Forensic Active Node Editor Report

## Source file

- `desktop/mac/src/app.js` exists: True
- source sha256 short: `9e611a95a105c42a`
- source size: `4266718` bytes

## O13 patch markers present in source

- `O13A`: 91
- `O13B`: 72
- `O13C`: 70
- `O13D`: 62
- `O13E`: 105
- `O13F`: 52
- `O13G`: 49
- `O13H`: 166
- `O13H1`: 26
- `O13H2`: 40
- `O13H3`: 40
- `O13H4`: 16

## Critical render attribute checks

- `generic data-aion-workflow-node-id node.id` present: `True` count `1`
- `O13H4 navigation attr` present: `True` count `3`
- `O13H3 navigation detector` present: `True` count `3`
- `O13H3 router` present: `True` count `3`

## Exact locations for visible generic editor labels


### `What kind of step is this?` hits: [29830, 64608, 65158, 65864, 66470, 67196, 68385, 68976]
```js
29810:                 </span>
29811:               </div>
29812:             `
29813:             : ""
29814:         }
29815: 
29816:         ${
29817:           window.__aionArchitectSettingsMore === true
29818:             ? `
29819:               <div class="aion-architect-human-helper">
29820:                 <strong>Step metadata</strong>
29821:                 <span>Step ID: ${escapeHtml(step.id || "")}</span>
29822:                 <span>Action ID: ${escapeHtml(step.action_id || "not selected")}</span>
29823:                 <span>Dry-run remains enforced. External writes require approval.</span>
29824:               </div>
29825:             `
29826:             : ""
29827:         }
29828: 
29829:         <section class="aion-architect-choice-section">
29830:           <div class="eyebrow">What kind of step is this?</div>
29831:           <div class="aion-architect-kind-grid">
29832:             ${kindOptions.map((item) => `
29833:               <button
29834:                 type="button"
29835:                 class="${String(step.step_kind || "") === item.value ? "active" : ""}"
29836:                 data-aion-architect-step-kind="${escapeHtml(item.value)}"
29837:                 data-aion-architect-step-id="${escapeHtml(step.id)}"
29838:                 title="${escapeHtml(item.description)}"
29839:               >
29840:                 <strong>${escapeHtml(item.label)}</strong>
29841:                 <small>${escapeHtml(item.description)}</small>
29842:               </button>
29843:             `).join("")}
29844:           </div>
29845:         </section>
29846: 
29847:         <section class="aion-architect-choice-section">
29848:           <div class="eyebrow">Selected module</div>
29849:           <div class="aion-architect-selected-module-card">
29850:             <strong>${escapeHtml(step.action_label || "No module selected")}</strong>
29851:             <span>${escapeHtml(step.app || step.connector || "Choose from module picker")} · ${escapeHtml(step.step_kind || "step")}</span>
29852:             <small>${escapeHtml(step.action_id || "No action ID yet")}</small>
29853:             <button type="button" class="secondary-btn" data-aion-architect-open-module-picker="true">
29854:               Change module
29855:             </button>
29856:           </div>
29857:         </section>
29858: 
29859:         <label>
29860:           <span>${String(step.step_kind || "") === "trigger" ? "When this happens" : "What should happen?"}</span>
29861:           <input
29862:             data-aion-architect-step-field="subtitle"
29863:             data-aion-architect-step-id="${escapeHtml(step.id)}"
29864:             value="${escapeHtml(step.subtitle || "")}"
29865:             placeholder="Example: new Gmail email arrives, if lead score is high, scrape price from page"
```
```js
64588: 
64589:     const paramsColumn =
64590:       Array.from(editor.querySelectorAll("*")).find((el) =>
64591:         String(el.textContent || "").trim().startsWith("PARAMETERS"),
64592:       ) || editor;
64593: 
64594:     const panel = document.createElement("section");
64595:     panel.className = "aion-main-node-ai-settings";
64596:     panel.setAttribute("data-aion-main-node-ai-settings", "true");
64597: 
64598:     panel.innerHTML = `
64599:       <div class="aion-main-node-ai-settings-tabs">
64600:         <button type="button" class="active">Node</button>
64601:         <button type="button" data-aion-main-node-open-logic="${node.id}">Logic / Variables</button>
64602:       </div>
64603: 
64604:       <div class="aion-main-node-ai-settings-card">
64605:         <div class="eyebrow">AI canvas settings</div>
64606: 
64607:         <label>
64608:           <span>What kind of step is this?</span>
64609:           <select data-aion-main-node-field="type" data-aion-main-node-id="${node.id}">
64610:             <option value="Step" ${String(node.type || "") === "Step" ? "selected" : ""}>Step</option>
64611:             <option value="Trigger" ${String(node.type || "") === "Trigger" ? "selected" : ""}>Trigger</option>
64612:             <option value="AI / Parser" ${String(node.type || "") === "AI / Parser" ? "selected" : ""}>AI action</option>
64613:             <option value="Tools" ${String(node.type || "") === "Tools" ? "selected" : ""}>Tool / transform</option>
64614:             <option value="Text Parser" ${String(node.type || "") === "Text Parser" ? "selected" : ""}>Text parser</option>
64615:             <option value="Gate" ${String(node.type || "") === "Gate" ? "selected" : ""}>Approval / gate</option>
64616:             <option value="Flow Control" ${String(node.type || "") === "Flow Control" ? "selected" : ""}>Flow control</option>
64617:             <option value="Custom Logic" ${String(node.type || "") === "Custom Logic" ? "selected" : ""}>Custom logic</option>
64618:             <option value="Content Asset" ${String(node.type || "") === "Content Asset" ? "selected" : ""}>Content asset</option>
64619:           </select>
64620:         </label>
64621: 
64622:         <label>
64623:           <span>Use this app / system</span>
64624:           <input
64625:             data-aion-main-node-field="connector"
64626:             data-aion-main-node-id="${node.id}"
64627:             value="${escapeHtml(node.connector || node.type || "")}"
64628:             placeholder="Gmail, Aion, Tools, Text parser, Approval"
64629:           />
64630:         </label>
64631: 
64632:         <label>
64633:           <span>Action ID</span>
64634:           <input
64635:             data-aion-main-node-field="action_id"
64636:             data-aion-main-node-id="${node.id}"
64637:             value="${escapeHtml(node.action_id || node.action || "")}"
64638:             placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
64639:           />
64640:         </label>
64641: 
64642:         <label>
64643:           <span>What should happen?</span>
```
```js
65138:           text.includes("SAVE NODE")
65139:         );
65140:       }) || null
65141:     );
65142:   }
65143: 
65144:   function renderAiSettingsHtml(node) {
65145:     const type = String(node.type || "Step");
65146: 
65147:     return `
65148:       <section class="aion-main-node-ai-settings" data-aion-main-node-ai-settings="true">
65149:         <div class="aion-main-node-ai-settings-tabs">
65150:           <button type="button" class="active">Node</button>
65151:           <button type="button" data-aion-main-node-open-logic="${safeEscape(node.id)}">Logic / Variables</button>
65152:         </div>
65153: 
65154:         <div class="aion-main-node-ai-settings-card">
65155:           <div class="eyebrow">AI canvas settings</div>
65156: 
65157:           <label>
65158:             <span>What kind of step is this?</span>
65159:             <select data-aion-main-node-field="type" data-aion-main-node-id="${safeEscape(node.id)}">
65160:               ${[
65161:                 "Step",
65162:                 "Trigger",
65163:                 "AI / Parser",
65164:                 "Tools",
65165:                 "Text Parser",
65166:                 "Gate",
65167:                 "Flow Control",
65168:                 "Custom Logic",
65169:                 "Content Asset",
65170:               ]
65171:                 .map(
65172:                   (item) =>
65173:                     `<option value="${safeEscape(item)}" ${
65174:                       type === item ? "selected" : ""
65175:                     }>${safeEscape(item)}</option>`,
65176:                 )
65177:                 .join("")}
65178:             </select>
65179:           </label>
65180: 
65181:           <label>
65182:             <span>Use this app / system</span>
65183:             <input
65184:               data-aion-main-node-field="connector"
65185:               data-aion-main-node-id="${safeEscape(node.id)}"
65186:               value="${safeEscape(node.connector || node.type || "")}"
65187:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
65188:             />
65189:           </label>
65190: 
65191:           <label>
65192:             <span>Action ID</span>
65193:             <input
```
```js
65844:           text.includes("NODE EDITOR") &&
65845:           text.includes("PARAMETERS") &&
65846:           text.includes("OUTPUT") &&
65847:           text.includes("TEST NODE") &&
65848:           text.includes("SAVE NODE")
65849:         );
65850:       }) || null
65851:     );
65852:   }
65853: 
65854:   function renderSettings(node) {
65855:     return `
65856:       <section class="aion-main-node-settings-panel" data-aion-main-node-settings-panel="true">
65857:         <div class="aion-main-node-settings-tabs">
65858:           <button type="button" class="active">Step settings</button>
65859:           <button type="button" data-aion-main-open-step-logic="${esc(node.id)}">Logic / variables</button>
65860:         </div>
65861: 
65862:         <div class="aion-main-node-settings-grid">
65863:           <label>
65864:             <span>What kind of step is this?</span>
65865:             <select data-aion-main-node-edit="${esc(node.id)}" data-aion-main-node-field="type">
65866:               ${["Step", "Trigger", "App action", "AI action", "Flow Control", "Tools", "Text Parser", "Approval", "Custom Logic", "Content Asset"]
65867:                 .map(
65868:                   (value) => `
65869:                     <option value="${esc(value)}" ${
65870:                       String(node.type || "Step") === value ? "selected" : ""
65871:                     }>${esc(value)}</option>
65872:                   `,
65873:                 )
65874:                 .join("")}
65875:             </select>
65876:           </label>
65877: 
65878:           <label>
65879:             <span>Use app / system</span>
65880:             <input
65881:               data-aion-main-node-edit="${esc(node.id)}"
65882:               data-aion-main-node-field="connector"
65883:               value="${esc(node.connector || node.app || "")}"
65884:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
65885:             />
65886:           </label>
65887: 
65888:           <label>
65889:             <span>Action ID</span>
65890:             <input
65891:               data-aion-main-node-edit="${esc(node.id)}"
65892:               data-aion-main-node-field="action_id"
65893:               value="${esc(node.action_id || "")}"
65894:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
65895:             />
65896:           </label>
65897: 
65898:           <label>
65899:             <span>What should happen?</span>
```
```js
66450:       .sort((a, b) => a.area - b.area);
66451: 
66452:     return candidates[0]?.el || null;
66453:   }
66454: 
66455:   function renderSettingsPanel(node) {
66456:     const type = String(node.type || "Step");
66457:     const approval = String(node.approval_requirement || "auto");
66458: 
66459:     return `
66460:       <section class="aion-main-node-settings-panel-v3" data-aion-main-node-settings-panel-v3="true">
66461:         <div class="aion-main-node-settings-tabs-v3">
66462:           <button type="button" class="active">Node settings</button>
66463:           <button type="button" data-aion-main-open-step-logic-v3="${esc(node.id)}">Logic / variables</button>
66464:         </div>
66465: 
66466:         <div class="aion-main-node-settings-card-v3">
66467:           <div class="eyebrow">AI canvas settings</div>
66468: 
66469:           <label>
66470:             <span>What kind of step is this?</span>
66471:             <select data-aion-main-node-edit-v3="${esc(node.id)}" data-aion-main-node-field="type">
66472:               ${[
66473:                 "Step",
66474:                 "Trigger",
66475:                 "App action",
66476:                 "AI action",
66477:                 "Tools",
66478:                 "Text Parser",
66479:                 "Flow Control",
66480:                 "Router",
66481:                 "Gate",
66482:                 "Custom Logic",
66483:                 "Content Asset",
66484:               ].map((item) => `
66485:                 <option value="${esc(item)}" ${type === item ? "selected" : ""}>${esc(item)}</option>
66486:               `).join("")}
66487:             </select>
66488:           </label>
66489: 
66490:           <label>
66491:             <span>Use this app / system</span>
66492:             <input
66493:               data-aion-main-node-edit-v3="${esc(node.id)}"
66494:               data-aion-main-node-field="connector"
66495:               value="${esc(node.connector || node.app || node.type || "")}"
66496:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
66497:             />
66498:           </label>
66499: 
66500:           <label>
66501:             <span>Action ID</span>
66502:             <input
66503:               data-aion-main-node-edit-v3="${esc(node.id)}"
66504:               data-aion-main-node-field="action_id"
66505:               value="${esc(node.action_id || node.action || "")}"
```

### `Use this app / system` hits: [64623, 65182, 66491, 67217, 68406, 68997]
```js
64603: 
64604:       <div class="aion-main-node-ai-settings-card">
64605:         <div class="eyebrow">AI canvas settings</div>
64606: 
64607:         <label>
64608:           <span>What kind of step is this?</span>
64609:           <select data-aion-main-node-field="type" data-aion-main-node-id="${node.id}">
64610:             <option value="Step" ${String(node.type || "") === "Step" ? "selected" : ""}>Step</option>
64611:             <option value="Trigger" ${String(node.type || "") === "Trigger" ? "selected" : ""}>Trigger</option>
64612:             <option value="AI / Parser" ${String(node.type || "") === "AI / Parser" ? "selected" : ""}>AI action</option>
64613:             <option value="Tools" ${String(node.type || "") === "Tools" ? "selected" : ""}>Tool / transform</option>
64614:             <option value="Text Parser" ${String(node.type || "") === "Text Parser" ? "selected" : ""}>Text parser</option>
64615:             <option value="Gate" ${String(node.type || "") === "Gate" ? "selected" : ""}>Approval / gate</option>
64616:             <option value="Flow Control" ${String(node.type || "") === "Flow Control" ? "selected" : ""}>Flow control</option>
64617:             <option value="Custom Logic" ${String(node.type || "") === "Custom Logic" ? "selected" : ""}>Custom logic</option>
64618:             <option value="Content Asset" ${String(node.type || "") === "Content Asset" ? "selected" : ""}>Content asset</option>
64619:           </select>
64620:         </label>
64621: 
64622:         <label>
64623:           <span>Use this app / system</span>
64624:           <input
64625:             data-aion-main-node-field="connector"
64626:             data-aion-main-node-id="${node.id}"
64627:             value="${escapeHtml(node.connector || node.type || "")}"
64628:             placeholder="Gmail, Aion, Tools, Text parser, Approval"
64629:           />
64630:         </label>
64631: 
64632:         <label>
64633:           <span>Action ID</span>
64634:           <input
64635:             data-aion-main-node-field="action_id"
64636:             data-aion-main-node-id="${node.id}"
64637:             value="${escapeHtml(node.action_id || node.action || "")}"
64638:             placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
64639:           />
64640:         </label>
64641: 
64642:         <label>
64643:           <span>What should happen?</span>
64644:           <input
64645:             data-aion-main-node-field="title"
64646:             data-aion-main-node-id="${node.id}"
64647:             value="${escapeHtml(node.title || "")}"
64648:             placeholder="Watch emails, Extract details, Create draft"
64649:           />
64650:         </label>
64651: 
64652:         <label>
64653:           <span>Aion should collect / use</span>
64654:           <textarea
64655:             data-aion-main-node-field="fields"
64656:             data-aion-main-node-id="${node.id}"
64657:             placeholder="sender, subject, body, received_at"
64658:           >${escapeHtml(node.fields || node.config?.fields || "")}</textarea>
```
```js
65162:                 "Trigger",
65163:                 "AI / Parser",
65164:                 "Tools",
65165:                 "Text Parser",
65166:                 "Gate",
65167:                 "Flow Control",
65168:                 "Custom Logic",
65169:                 "Content Asset",
65170:               ]
65171:                 .map(
65172:                   (item) =>
65173:                     `<option value="${safeEscape(item)}" ${
65174:                       type === item ? "selected" : ""
65175:                     }>${safeEscape(item)}</option>`,
65176:                 )
65177:                 .join("")}
65178:             </select>
65179:           </label>
65180: 
65181:           <label>
65182:             <span>Use this app / system</span>
65183:             <input
65184:               data-aion-main-node-field="connector"
65185:               data-aion-main-node-id="${safeEscape(node.id)}"
65186:               value="${safeEscape(node.connector || node.type || "")}"
65187:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
65188:             />
65189:           </label>
65190: 
65191:           <label>
65192:             <span>Action ID</span>
65193:             <input
65194:               data-aion-main-node-field="action_id"
65195:               data-aion-main-node-id="${safeEscape(node.id)}"
65196:               value="${safeEscape(node.action_id || node.action || "")}"
65197:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
65198:             />
65199:           </label>
65200: 
65201:           <label>
65202:             <span>What should happen?</span>
65203:             <input
65204:               data-aion-main-node-field="title"
65205:               data-aion-main-node-id="${safeEscape(node.id)}"
65206:               value="${safeEscape(node.title || "")}"
65207:               placeholder="Watch emails, Extract details, Create draft"
65208:             />
65209:           </label>
65210: 
65211:           <label>
65212:             <span>Aion should collect / use</span>
65213:             <textarea
65214:               data-aion-main-node-field="fields"
65215:               data-aion-main-node-id="${safeEscape(node.id)}"
65216:               placeholder="sender, subject, body, received_at"
65217:             >${safeEscape(node.fields || node.config?.fields || "")}</textarea>
```
```js
66471:             <select data-aion-main-node-edit-v3="${esc(node.id)}" data-aion-main-node-field="type">
66472:               ${[
66473:                 "Step",
66474:                 "Trigger",
66475:                 "App action",
66476:                 "AI action",
66477:                 "Tools",
66478:                 "Text Parser",
66479:                 "Flow Control",
66480:                 "Router",
66481:                 "Gate",
66482:                 "Custom Logic",
66483:                 "Content Asset",
66484:               ].map((item) => `
66485:                 <option value="${esc(item)}" ${type === item ? "selected" : ""}>${esc(item)}</option>
66486:               `).join("")}
66487:             </select>
66488:           </label>
66489: 
66490:           <label>
66491:             <span>Use this app / system</span>
66492:             <input
66493:               data-aion-main-node-edit-v3="${esc(node.id)}"
66494:               data-aion-main-node-field="connector"
66495:               value="${esc(node.connector || node.app || node.type || "")}"
66496:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
66497:             />
66498:           </label>
66499: 
66500:           <label>
66501:             <span>Action ID</span>
66502:             <input
66503:               data-aion-main-node-edit-v3="${esc(node.id)}"
66504:               data-aion-main-node-field="action_id"
66505:               value="${esc(node.action_id || node.action || "")}"
66506:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
66507:             />
66508:           </label>
66509: 
66510:           <label>
66511:             <span>What should happen?</span>
66512:             <input
66513:               data-aion-main-node-edit-v3="${esc(node.id)}"
66514:               data-aion-main-node-field="title"
66515:               value="${esc(node.title || node.action_label || "")}"
66516:               placeholder="Watch emails, Extract details, Create draft"
66517:             />
66518:           </label>
66519: 
66520:           <label>
66521:             <span>Aion should collect / use</span>
66522:             <textarea
66523:               data-aion-main-node-edit-v3="${esc(node.id)}"
66524:               data-aion-main-node-field="fields"
66525:               placeholder="sender, subject, body, received_at"
66526:             >${esc(node.fields || node.config?.fields || "")}</textarea>
```
```js
67197:             <select data-aion-main-node-edit-v3="${esc(node.id)}" data-aion-main-node-field="type">
67198:               ${[
67199:                 "Step",
67200:                 "Trigger",
67201:                 "App action",
67202:                 "AI action",
67203:                 "Tools",
67204:                 "Text Parser",
67205:                 "Flow Control",
67206:                 "Router",
67207:                 "Gate",
67208:                 "Custom Logic",
67209:                 "Content Asset",
67210:               ].map((item) => `
67211:                 <option value="${esc(item)}" ${type === item ? "selected" : ""}>${esc(item)}</option>
67212:               `).join("")}
67213:             </select>
67214:           </label>
67215: 
67216:           <label>
67217:             <span>Use this app / system</span>
67218:             <input
67219:               data-aion-main-node-edit-v3="${esc(node.id)}"
67220:               data-aion-main-node-field="connector"
67221:               value="${esc(node.connector || node.app || node.type || "")}"
67222:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
67223:             />
67224:           </label>
67225: 
67226:           <label>
67227:             <span>Action ID</span>
67228:             <input
67229:               data-aion-main-node-edit-v3="${esc(node.id)}"
67230:               data-aion-main-node-field="action_id"
67231:               value="${esc(node.action_id || node.action || "")}"
67232:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
67233:             />
67234:           </label>
67235: 
67236:           <label>
67237:             <span>What should happen?</span>
67238:             <input
67239:               data-aion-main-node-edit-v3="${esc(node.id)}"
67240:               data-aion-main-node-field="title"
67241:               value="${esc(node.title || node.action_label || "")}"
67242:               placeholder="Watch emails, Extract details, Create draft"
67243:             />
67244:           </label>
67245: 
67246:           <label>
67247:             <span>Aion should collect / use</span>
67248:             <textarea
67249:               data-aion-main-node-edit-v3="${esc(node.id)}"
67250:               data-aion-main-node-field="fields"
67251:               placeholder="sender, subject, body, received_at"
67252:             >${esc(node.fields || node.config?.fields || "")}</textarea>
```
```js
68386:             <select data-aion-main-node-edit-v5="${esc(node.id)}" data-aion-main-node-field="type">
68387:               ${[
68388:                 "Step",
68389:                 "Trigger",
68390:                 "App action",
68391:                 "AI action",
68392:                 "Logic / condition",
68393:                 "Router",
68394:                 "Tool / transform",
68395:                 "Text Parser",
68396:                 "Approval",
68397:                 "Custom Logic",
68398:                 "Content Asset",
68399:               ].map((item) => `
68400:                 <option value="${esc(item)}" ${type === item ? "selected" : ""}>${esc(item)}</option>
68401:               `).join("")}
68402:             </select>
68403:           </label>
68404: 
68405:           <label>
68406:             <span>Use this app / system</span>
68407:             <input
68408:               data-aion-main-node-edit-v5="${esc(node.id)}"
68409:               data-aion-main-node-field="connector"
68410:               value="${esc(node.connector || node.app || node.type || "")}"
68411:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
68412:             />
68413:           </label>
68414: 
68415:           <label>
68416:             <span>Action ID</span>
68417:             <input
68418:               data-aion-main-node-edit-v5="${esc(node.id)}"
68419:               data-aion-main-node-field="action_id"
68420:               value="${esc(node.action_id || node.action || "")}"
68421:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
68422:             />
68423:           </label>
68424: 
68425:           <label>
68426:             <span>What should happen?</span>
68427:             <input
68428:               data-aion-main-node-edit-v5="${esc(node.id)}"
68429:               data-aion-main-node-field="title"
68430:               value="${esc(node.title || node.action_label || "")}"
68431:               placeholder="Watch emails, extract details, create draft"
68432:             />
68433:           </label>
68434: 
68435:           <label>
68436:             <span>Aion should collect / use</span>
68437:             <textarea
68438:               data-aion-main-node-edit-v5="${esc(node.id)}"
68439:               data-aion-main-node-field="fields"
68440:               placeholder="sender, subject, body, received_at"
68441:             >${esc(node.fields || node.config?.fields || "")}</textarea>
```

### `Aion should collect / use` hits: [29870, 64653, 65212, 65909, 66521, 67247, 68436, 69027]
```js
29850:             <strong>${escapeHtml(step.action_label || "No module selected")}</strong>
29851:             <span>${escapeHtml(step.app || step.connector || "Choose from module picker")} · ${escapeHtml(step.step_kind || "step")}</span>
29852:             <small>${escapeHtml(step.action_id || "No action ID yet")}</small>
29853:             <button type="button" class="secondary-btn" data-aion-architect-open-module-picker="true">
29854:               Change module
29855:             </button>
29856:           </div>
29857:         </section>
29858: 
29859:         <label>
29860:           <span>${String(step.step_kind || "") === "trigger" ? "When this happens" : "What should happen?"}</span>
29861:           <input
29862:             data-aion-architect-step-field="subtitle"
29863:             data-aion-architect-step-id="${escapeHtml(step.id)}"
29864:             value="${escapeHtml(step.subtitle || "")}"
29865:             placeholder="Example: new Gmail email arrives, if lead score is high, scrape price from page"
29866:           />
29867:         </label>
29868: 
29869:         <label>
29870:           <span>Aion should collect / use</span>
29871:           <textarea
29872:             data-aion-architect-step-field="fields"
29873:             data-aion-architect-step-id="${escapeHtml(step.id)}"
29874:             placeholder="name, email, phone, company, enquiry, page price, condition value"
29875:           >${escapeHtml(step.fields || "")}</textarea>
29876:         </label>
29877: 
29878:         <label>
29879:           <span>Pass this result to next step</span>
29880:           <p class="aion-architect-field-help">
29881:             Give the output a simple name. Examples:
29882:             <code>new_email_event</code>, <code>customer_details</code>, <code>condition_result</code>, <code>scraped_price</code>.
29883:           </p>
29884:           <textarea
29885:             data-aion-architect-step-field="outputs"
29886:             data-aion-architect-step-id="${escapeHtml(step.id)}"
29887:             placeholder="customer_details"
29888:           >${escapeHtml(step.outputs || "")}</textarea>
29889:         </label>
29890: 
29891:         <label>
29892:           <span>Approval / safety</span>
29893:           <select
29894:             data-aion-architect-step-field="approval_requirement"
29895:             data-aion-architect-step-id="${escapeHtml(step.id)}"
29896:           >
29897:             <option value="auto" ${String(step.approval_requirement || "auto") === "auto" ? "selected" : ""}>Auto</option>
29898:             <option value="not_required" ${String(step.approval_requirement || "") === "not_required" ? "selected" : ""}>No approval needed</option>
29899:             <option value="required" ${String(step.approval_requirement || "") === "required" ? "selected" : ""}>Require human approval</option>
29900:             <option value="before_external_write" ${String(step.approval_requirement || "") === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
29901:           </select>
29902:         </label>
29903: 
29904:         <div class="aion-architect-advanced-row">
29905:           <button
```
```js
64633:           <span>Action ID</span>
64634:           <input
64635:             data-aion-main-node-field="action_id"
64636:             data-aion-main-node-id="${node.id}"
64637:             value="${escapeHtml(node.action_id || node.action || "")}"
64638:             placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
64639:           />
64640:         </label>
64641: 
64642:         <label>
64643:           <span>What should happen?</span>
64644:           <input
64645:             data-aion-main-node-field="title"
64646:             data-aion-main-node-id="${node.id}"
64647:             value="${escapeHtml(node.title || "")}"
64648:             placeholder="Watch emails, Extract details, Create draft"
64649:           />
64650:         </label>
64651: 
64652:         <label>
64653:           <span>Aion should collect / use</span>
64654:           <textarea
64655:             data-aion-main-node-field="fields"
64656:             data-aion-main-node-id="${node.id}"
64657:             placeholder="sender, subject, body, received_at"
64658:           >${escapeHtml(node.fields || node.config?.fields || "")}</textarea>
64659:         </label>
64660: 
64661:         <label>
64662:           <span>Pass this to the next step</span>
64663:           <textarea
64664:             data-aion-main-node-field="outputs"
64665:             data-aion-main-node-id="${node.id}"
64666:             placeholder="new_email_event, customer_details, draft_reply"
64667:           >${escapeHtml(node.outputs || node.config?.outputs || "")}</textarea>
64668:         </label>
64669: 
64670:         <label>
64671:           <span>Approval / safety</span>
64672:           <select data-aion-main-node-field="approval_requirement" data-aion-main-node-id="${node.id}">
64673:             <option value="auto" ${String(node.approval_requirement || "auto") === "auto" ? "selected" : ""}>Auto</option>
64674:             <option value="not_required" ${String(node.approval_requirement || "") === "not_required" ? "selected" : ""}>No approval needed</option>
64675:             <option value="required" ${String(node.approval_requirement || "") === "required" ? "selected" : ""}>Require human approval</option>
64676:             <option value="before_external_write" ${String(node.approval_requirement || "") === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
64677:           </select>
64678:         </label>
64679: 
64680:         <button type="button" class="secondary-btn" data-aion-main-node-open-logic="${node.id}">
64681:           Configure logic / variables
64682:         </button>
64683:       </div>
64684:     `;
64685: 
64686:     paramsColumn.appendChild(panel);
64687:   }
64688: 
```
```js
65192:             <span>Action ID</span>
65193:             <input
65194:               data-aion-main-node-field="action_id"
65195:               data-aion-main-node-id="${safeEscape(node.id)}"
65196:               value="${safeEscape(node.action_id || node.action || "")}"
65197:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
65198:             />
65199:           </label>
65200: 
65201:           <label>
65202:             <span>What should happen?</span>
65203:             <input
65204:               data-aion-main-node-field="title"
65205:               data-aion-main-node-id="${safeEscape(node.id)}"
65206:               value="${safeEscape(node.title || "")}"
65207:               placeholder="Watch emails, Extract details, Create draft"
65208:             />
65209:           </label>
65210: 
65211:           <label>
65212:             <span>Aion should collect / use</span>
65213:             <textarea
65214:               data-aion-main-node-field="fields"
65215:               data-aion-main-node-id="${safeEscape(node.id)}"
65216:               placeholder="sender, subject, body, received_at"
65217:             >${safeEscape(node.fields || node.config?.fields || "")}</textarea>
65218:           </label>
65219: 
65220:           <label>
65221:             <span>Pass this to the next step</span>
65222:             <textarea
65223:               data-aion-main-node-field="outputs"
65224:               data-aion-main-node-id="${safeEscape(node.id)}"
65225:               placeholder="new_email_event, customer_details, draft_reply"
65226:             >${safeEscape(node.outputs || node.config?.outputs || "")}</textarea>
65227:           </label>
65228: 
65229:           <label>
65230:             <span>Approval / safety</span>
65231:             <select
65232:               data-aion-main-node-field="approval_requirement"
65233:               data-aion-main-node-id="${safeEscape(node.id)}"
65234:             >
65235:               <option value="auto" ${String(node.approval_requirement || "auto") === "auto" ? "selected" : ""}>Auto</option>
65236:               <option value="not_required" ${String(node.approval_requirement || "") === "not_required" ? "selected" : ""}>No approval needed</option>
65237:               <option value="required" ${String(node.approval_requirement || "") === "required" ? "selected" : ""}>Require human approval</option>
65238:               <option value="before_external_write" ${String(node.approval_requirement || "") === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
65239:             </select>
65240:           </label>
65241: 
65242:           <button type="button" class="secondary-btn" data-aion-main-node-open-logic="${safeEscape(node.id)}">
65243:             Configure logic / variables
65244:           </button>
65245:         </div>
65246:       </section>
65247:     `;
```
```js
65889:             <span>Action ID</span>
65890:             <input
65891:               data-aion-main-node-edit="${esc(node.id)}"
65892:               data-aion-main-node-field="action_id"
65893:               value="${esc(node.action_id || "")}"
65894:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
65895:             />
65896:           </label>
65897: 
65898:           <label>
65899:             <span>What should happen?</span>
65900:             <input
65901:               data-aion-main-node-edit="${esc(node.id)}"
65902:               data-aion-main-node-field="title"
65903:               value="${esc(node.title || "")}"
65904:               placeholder="Watch emails, extract details, create draft"
65905:             />
65906:           </label>
65907: 
65908:           <label>
65909:             <span>Aion should collect / use</span>
65910:             <textarea
65911:               data-aion-main-node-edit="${esc(node.id)}"
65912:               data-aion-main-node-field="fields"
65913:               placeholder="sender, subject, body, received_at"
65914:             >${esc(node.fields || node.config?.fields || "")}</textarea>
65915:           </label>
65916: 
65917:           <label>
65918:             <span>Pass this to next step as</span>
65919:             <textarea
65920:               data-aion-main-node-edit="${esc(node.id)}"
65921:               data-aion-main-node-field="outputs"
65922:               placeholder="new_email_event, customer_details, draft_reply"
65923:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
65924:           </label>
65925: 
65926:           <label>
65927:             <span>Approval / safety</span>
65928:             <select data-aion-main-node-edit="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
65929:               <option value="auto" ${String(node.approval_requirement || "auto") === "auto" ? "selected" : ""}>Auto</option>
65930:               <option value="not_required" ${String(node.approval_requirement || "") === "not_required" ? "selected" : ""}>No approval needed</option>
65931:               <option value="required" ${String(node.approval_requirement || "") === "required" ? "selected" : ""}>Require human approval</option>
65932:               <option value="before_external_write" ${String(node.approval_requirement || "") === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
65933:             </select>
65934:           </label>
65935: 
65936:           <button type="button" data-aion-main-open-step-logic="${esc(node.id)}">
65937:             Configure logic / variables
65938:           </button>
65939:         </div>
65940:       </section>
65941:     `;
65942:   }
65943: 
65944:   function injectSettingsPanel() {
```
```js
66501:             <span>Action ID</span>
66502:             <input
66503:               data-aion-main-node-edit-v3="${esc(node.id)}"
66504:               data-aion-main-node-field="action_id"
66505:               value="${esc(node.action_id || node.action || "")}"
66506:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
66507:             />
66508:           </label>
66509: 
66510:           <label>
66511:             <span>What should happen?</span>
66512:             <input
66513:               data-aion-main-node-edit-v3="${esc(node.id)}"
66514:               data-aion-main-node-field="title"
66515:               value="${esc(node.title || node.action_label || "")}"
66516:               placeholder="Watch emails, Extract details, Create draft"
66517:             />
66518:           </label>
66519: 
66520:           <label>
66521:             <span>Aion should collect / use</span>
66522:             <textarea
66523:               data-aion-main-node-edit-v3="${esc(node.id)}"
66524:               data-aion-main-node-field="fields"
66525:               placeholder="sender, subject, body, received_at"
66526:             >${esc(node.fields || node.config?.fields || "")}</textarea>
66527:           </label>
66528: 
66529:           <label>
66530:             <span>Pass this to next step as</span>
66531:             <textarea
66532:               data-aion-main-node-edit-v3="${esc(node.id)}"
66533:               data-aion-main-node-field="outputs"
66534:               placeholder="new_email_event, customer_details, draft_reply"
66535:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
66536:           </label>
66537: 
66538:           <label>
66539:             <span>Approval / safety</span>
66540:             <select data-aion-main-node-edit-v3="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
66541:               <option value="auto" ${approval === "auto" ? "selected" : ""}>Auto</option>
66542:               <option value="not_required" ${approval === "not_required" ? "selected" : ""}>No approval needed</option>
66543:               <option value="required" ${approval === "required" ? "selected" : ""}>Require human approval</option>
66544:               <option value="before_external_write" ${approval === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
66545:             </select>
66546:           </label>
66547: 
66548:           <button type="button" class="secondary-btn" data-aion-main-open-step-logic-v3="${esc(node.id)}">
66549:             Configure logic / variables
66550:           </button>
66551:         </div>
66552:       </section>
66553:     `;
66554:   }
66555: 
66556:   function injectSettingsPanel() {
```

### `Pass this to next step as` hits: [65918, 66530, 67256, 68445, 69036]
```js
65898:           <label>
65899:             <span>What should happen?</span>
65900:             <input
65901:               data-aion-main-node-edit="${esc(node.id)}"
65902:               data-aion-main-node-field="title"
65903:               value="${esc(node.title || "")}"
65904:               placeholder="Watch emails, extract details, create draft"
65905:             />
65906:           </label>
65907: 
65908:           <label>
65909:             <span>Aion should collect / use</span>
65910:             <textarea
65911:               data-aion-main-node-edit="${esc(node.id)}"
65912:               data-aion-main-node-field="fields"
65913:               placeholder="sender, subject, body, received_at"
65914:             >${esc(node.fields || node.config?.fields || "")}</textarea>
65915:           </label>
65916: 
65917:           <label>
65918:             <span>Pass this to next step as</span>
65919:             <textarea
65920:               data-aion-main-node-edit="${esc(node.id)}"
65921:               data-aion-main-node-field="outputs"
65922:               placeholder="new_email_event, customer_details, draft_reply"
65923:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
65924:           </label>
65925: 
65926:           <label>
65927:             <span>Approval / safety</span>
65928:             <select data-aion-main-node-edit="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
65929:               <option value="auto" ${String(node.approval_requirement || "auto") === "auto" ? "selected" : ""}>Auto</option>
65930:               <option value="not_required" ${String(node.approval_requirement || "") === "not_required" ? "selected" : ""}>No approval needed</option>
65931:               <option value="required" ${String(node.approval_requirement || "") === "required" ? "selected" : ""}>Require human approval</option>
65932:               <option value="before_external_write" ${String(node.approval_requirement || "") === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
65933:             </select>
65934:           </label>
65935: 
65936:           <button type="button" data-aion-main-open-step-logic="${esc(node.id)}">
65937:             Configure logic / variables
65938:           </button>
65939:         </div>
65940:       </section>
65941:     `;
65942:   }
65943: 
65944:   function injectSettingsPanel() {
65945:     const modal = findNodeEditorModal();
65946:     if (!modal) return;
65947: 
65948:     modal
65949:       .querySelectorAll(".aion-architect-node-mini-toolbar, .aion-main-node-mini-toolbar")
65950:       .forEach((el) => { el.style.display = 'none'; el.style.visibility = 'hidden'; });
65951: 
65952:     if (modal.querySelector("[data-aion-main-node-settings-panel='true']")) return;
65953: 
```
```js
66510:           <label>
66511:             <span>What should happen?</span>
66512:             <input
66513:               data-aion-main-node-edit-v3="${esc(node.id)}"
66514:               data-aion-main-node-field="title"
66515:               value="${esc(node.title || node.action_label || "")}"
66516:               placeholder="Watch emails, Extract details, Create draft"
66517:             />
66518:           </label>
66519: 
66520:           <label>
66521:             <span>Aion should collect / use</span>
66522:             <textarea
66523:               data-aion-main-node-edit-v3="${esc(node.id)}"
66524:               data-aion-main-node-field="fields"
66525:               placeholder="sender, subject, body, received_at"
66526:             >${esc(node.fields || node.config?.fields || "")}</textarea>
66527:           </label>
66528: 
66529:           <label>
66530:             <span>Pass this to next step as</span>
66531:             <textarea
66532:               data-aion-main-node-edit-v3="${esc(node.id)}"
66533:               data-aion-main-node-field="outputs"
66534:               placeholder="new_email_event, customer_details, draft_reply"
66535:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
66536:           </label>
66537: 
66538:           <label>
66539:             <span>Approval / safety</span>
66540:             <select data-aion-main-node-edit-v3="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
66541:               <option value="auto" ${approval === "auto" ? "selected" : ""}>Auto</option>
66542:               <option value="not_required" ${approval === "not_required" ? "selected" : ""}>No approval needed</option>
66543:               <option value="required" ${approval === "required" ? "selected" : ""}>Require human approval</option>
66544:               <option value="before_external_write" ${approval === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
66545:             </select>
66546:           </label>
66547: 
66548:           <button type="button" class="secondary-btn" data-aion-main-open-step-logic-v3="${esc(node.id)}">
66549:             Configure logic / variables
66550:           </button>
66551:         </div>
66552:       </section>
66553:     `;
66554:   }
66555: 
66556:   function injectSettingsPanel() {
66557:     const modal = findNodeEditorModal();
66558:     if (!modal) return;
66559: 
66560:     modal
66561:       .querySelectorAll(
66562:         ".aion-main-node-mini-toolbar, .aion-workflow-node-mini-toolbar, .aion-architect-node-mini-toolbar",
66563:       )
66564:       .forEach((el) => { el.style.display = 'none'; el.style.visibility = 'hidden'; });
66565: 
```
```js
67236:           <label>
67237:             <span>What should happen?</span>
67238:             <input
67239:               data-aion-main-node-edit-v3="${esc(node.id)}"
67240:               data-aion-main-node-field="title"
67241:               value="${esc(node.title || node.action_label || "")}"
67242:               placeholder="Watch emails, Extract details, Create draft"
67243:             />
67244:           </label>
67245: 
67246:           <label>
67247:             <span>Aion should collect / use</span>
67248:             <textarea
67249:               data-aion-main-node-edit-v3="${esc(node.id)}"
67250:               data-aion-main-node-field="fields"
67251:               placeholder="sender, subject, body, received_at"
67252:             >${esc(node.fields || node.config?.fields || "")}</textarea>
67253:           </label>
67254: 
67255:           <label>
67256:             <span>Pass this to next step as</span>
67257:             <textarea
67258:               data-aion-main-node-edit-v3="${esc(node.id)}"
67259:               data-aion-main-node-field="outputs"
67260:               placeholder="new_email_event, customer_details, draft_reply"
67261:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
67262:           </label>
67263: 
67264:           <label>
67265:             <span>Approval / safety</span>
67266:             <select data-aion-main-node-edit-v3="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
67267:               <option value="auto" ${approval === "auto" ? "selected" : ""}>Auto</option>
67268:               <option value="not_required" ${approval === "not_required" ? "selected" : ""}>No approval needed</option>
67269:               <option value="required" ${approval === "required" ? "selected" : ""}>Require human approval</option>
67270:               <option value="before_external_write" ${approval === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
67271:             </select>
67272:           </label>
67273: 
67274:           <button type="button" class="secondary-btn" data-aion-main-open-step-logic-v3="${esc(node.id)}">
67275:             Configure logic / variables
67276:           </button>
67277:         </div>
67278:       </section>
67279:     `;
67280:   }
67281: 
67282:   function injectSettingsPanel() {
67283:     const modal = findNodeEditorModal();
67284:     if (!modal) return;
67285: 
67286:     modal
67287:       .querySelectorAll(
67288:         ".aion-main-node-mini-toolbar, .aion-workflow-node-mini-toolbar, .aion-architect-node-mini-toolbar",
67289:       )
67290:       .forEach((el) => { el.style.display = 'none'; el.style.visibility = 'hidden'; });
67291: 
```
```js
68425:           <label>
68426:             <span>What should happen?</span>
68427:             <input
68428:               data-aion-main-node-edit-v5="${esc(node.id)}"
68429:               data-aion-main-node-field="title"
68430:               value="${esc(node.title || node.action_label || "")}"
68431:               placeholder="Watch emails, extract details, create draft"
68432:             />
68433:           </label>
68434: 
68435:           <label>
68436:             <span>Aion should collect / use</span>
68437:             <textarea
68438:               data-aion-main-node-edit-v5="${esc(node.id)}"
68439:               data-aion-main-node-field="fields"
68440:               placeholder="sender, subject, body, received_at"
68441:             >${esc(node.fields || node.config?.fields || "")}</textarea>
68442:           </label>
68443: 
68444:           <label>
68445:             <span>Pass this to next step as</span>
68446:             <textarea
68447:               data-aion-main-node-edit-v5="${esc(node.id)}"
68448:               data-aion-main-node-field="outputs"
68449:               placeholder="new_email_event, customer_details, draft_reply"
68450:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
68451:           </label>
68452: 
68453:           <label>
68454:             <span>Approval / safety</span>
68455:             <select data-aion-main-node-edit-v5="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
68456:               <option value="auto" ${approval === "auto" ? "selected" : ""}>Auto</option>
68457:               <option value="not_required" ${approval === "not_required" ? "selected" : ""}>No approval needed</option>
68458:               <option value="required" ${approval === "required" ? "selected" : ""}>Require human approval</option>
68459:               <option value="before_external_write" ${approval === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
68460:             </select>
68461:           </label>
68462: 
68463:           <button type="button" class="secondary-btn" data-aion-main-open-step-logic-v5="${esc(node.id)}">
68464:             Configure logic / variables
68465:           </button>
68466:         </div>
68467:       </section>
68468:     `;
68469:   }
68470: 
68471:   function injectSettings() {
68472:     const modal = findNodeEditorModal();
68473:     if (!modal) return;
68474: 
68475:     // Remove accidental node toolbar inside the modal.
68476:     modal
68477:       .querySelectorAll(
68478:         [
68479:           ".aion-main-node-mini-toolbar",
68480:           ".aion-workflow-node-mini-toolbar",
```
```js
69016:           <label>
69017:             <span>What should happen?</span>
69018:             <input
69019:               data-aion-main-node-edit-v6="${esc(node.id)}"
69020:               data-aion-main-node-field="title"
69021:               value="${esc(node.title || "")}"
69022:               placeholder="Watch emails, extract details, create draft"
69023:             />
69024:           </label>
69025: 
69026:           <label>
69027:             <span>Aion should collect / use</span>
69028:             <textarea
69029:               data-aion-main-node-edit-v6="${esc(node.id)}"
69030:               data-aion-main-node-field="fields"
69031:               placeholder="sender, subject, body, received_at"
69032:             >${esc(node.fields || node.config?.fields || "")}</textarea>
69033:           </label>
69034: 
69035:           <label>
69036:             <span>Pass this to next step as</span>
69037:             <textarea
69038:               data-aion-main-node-edit-v6="${esc(node.id)}"
69039:               data-aion-main-node-field="outputs"
69040:               placeholder="new_email_event, customer_details, draft_reply"
69041:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
69042:           </label>
69043: 
69044:           <label>
69045:             <span>Approval / safety</span>
69046:             <select data-aion-main-node-edit-v6="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
69047:               <option value="auto" ${approval === "auto" ? "selected" : ""}>Auto</option>
69048:               <option value="not_required" ${approval === "not_required" ? "selected" : ""}>No approval needed</option>
69049:               <option value="required" ${approval === "required" ? "selected" : ""}>Require human approval</option>
69050:               <option value="before_external_write" ${approval === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
69051:             </select>
69052:           </label>
69053: 
69054:           <button type="button" data-aion-main-node-logic-v6="${esc(node.id)}">
69055:             Configure logic / variables
69056:           </button>
69057:         </div>
69058:       </section>
69059:     `;
69060:   }
69061: 
69062:   function inject() {
69063:     const editor = findVisibleNodeEditor();
69064:     if (!editor) return;
69065: 
69066:     editor
69067:       .querySelectorAll(
69068:         ".aion-main-node-mini-toolbar, .aion-workflow-node-mini-toolbar, .aion-architect-node-mini-toolbar",
69069:       )
69070:       .forEach((el) => { el.style.display = 'none'; el.style.visibility = 'hidden'; });
69071: 
```

### `gmail.watch_emails, tools.set_variable, text.match_pattern` hits: [64638, 65197, 65894, 66506, 67232, 68421, 69012]
```js
64618:             <option value="Content Asset" ${String(node.type || "") === "Content Asset" ? "selected" : ""}>Content asset</option>
64619:           </select>
64620:         </label>
64621: 
64622:         <label>
64623:           <span>Use this app / system</span>
64624:           <input
64625:             data-aion-main-node-field="connector"
64626:             data-aion-main-node-id="${node.id}"
64627:             value="${escapeHtml(node.connector || node.type || "")}"
64628:             placeholder="Gmail, Aion, Tools, Text parser, Approval"
64629:           />
64630:         </label>
64631: 
64632:         <label>
64633:           <span>Action ID</span>
64634:           <input
64635:             data-aion-main-node-field="action_id"
64636:             data-aion-main-node-id="${node.id}"
64637:             value="${escapeHtml(node.action_id || node.action || "")}"
64638:             placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
64639:           />
64640:         </label>
64641: 
64642:         <label>
64643:           <span>What should happen?</span>
64644:           <input
64645:             data-aion-main-node-field="title"
64646:             data-aion-main-node-id="${node.id}"
64647:             value="${escapeHtml(node.title || "")}"
64648:             placeholder="Watch emails, Extract details, Create draft"
64649:           />
64650:         </label>
64651: 
64652:         <label>
64653:           <span>Aion should collect / use</span>
64654:           <textarea
64655:             data-aion-main-node-field="fields"
64656:             data-aion-main-node-id="${node.id}"
64657:             placeholder="sender, subject, body, received_at"
64658:           >${escapeHtml(node.fields || node.config?.fields || "")}</textarea>
64659:         </label>
64660: 
64661:         <label>
64662:           <span>Pass this to the next step</span>
64663:           <textarea
64664:             data-aion-main-node-field="outputs"
64665:             data-aion-main-node-id="${node.id}"
64666:             placeholder="new_email_event, customer_details, draft_reply"
64667:           >${escapeHtml(node.outputs || node.config?.outputs || "")}</textarea>
64668:         </label>
64669: 
64670:         <label>
64671:           <span>Approval / safety</span>
64672:           <select data-aion-main-node-field="approval_requirement" data-aion-main-node-id="${node.id}">
64673:             <option value="auto" ${String(node.approval_requirement || "auto") === "auto" ? "selected" : ""}>Auto</option>
```
```js
65177:                 .join("")}
65178:             </select>
65179:           </label>
65180: 
65181:           <label>
65182:             <span>Use this app / system</span>
65183:             <input
65184:               data-aion-main-node-field="connector"
65185:               data-aion-main-node-id="${safeEscape(node.id)}"
65186:               value="${safeEscape(node.connector || node.type || "")}"
65187:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
65188:             />
65189:           </label>
65190: 
65191:           <label>
65192:             <span>Action ID</span>
65193:             <input
65194:               data-aion-main-node-field="action_id"
65195:               data-aion-main-node-id="${safeEscape(node.id)}"
65196:               value="${safeEscape(node.action_id || node.action || "")}"
65197:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
65198:             />
65199:           </label>
65200: 
65201:           <label>
65202:             <span>What should happen?</span>
65203:             <input
65204:               data-aion-main-node-field="title"
65205:               data-aion-main-node-id="${safeEscape(node.id)}"
65206:               value="${safeEscape(node.title || "")}"
65207:               placeholder="Watch emails, Extract details, Create draft"
65208:             />
65209:           </label>
65210: 
65211:           <label>
65212:             <span>Aion should collect / use</span>
65213:             <textarea
65214:               data-aion-main-node-field="fields"
65215:               data-aion-main-node-id="${safeEscape(node.id)}"
65216:               placeholder="sender, subject, body, received_at"
65217:             >${safeEscape(node.fields || node.config?.fields || "")}</textarea>
65218:           </label>
65219: 
65220:           <label>
65221:             <span>Pass this to the next step</span>
65222:             <textarea
65223:               data-aion-main-node-field="outputs"
65224:               data-aion-main-node-id="${safeEscape(node.id)}"
65225:               placeholder="new_email_event, customer_details, draft_reply"
65226:             >${safeEscape(node.outputs || node.config?.outputs || "")}</textarea>
65227:           </label>
65228: 
65229:           <label>
65230:             <span>Approval / safety</span>
65231:             <select
65232:               data-aion-main-node-field="approval_requirement"
```
```js
65874:                 .join("")}
65875:             </select>
65876:           </label>
65877: 
65878:           <label>
65879:             <span>Use app / system</span>
65880:             <input
65881:               data-aion-main-node-edit="${esc(node.id)}"
65882:               data-aion-main-node-field="connector"
65883:               value="${esc(node.connector || node.app || "")}"
65884:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
65885:             />
65886:           </label>
65887: 
65888:           <label>
65889:             <span>Action ID</span>
65890:             <input
65891:               data-aion-main-node-edit="${esc(node.id)}"
65892:               data-aion-main-node-field="action_id"
65893:               value="${esc(node.action_id || "")}"
65894:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
65895:             />
65896:           </label>
65897: 
65898:           <label>
65899:             <span>What should happen?</span>
65900:             <input
65901:               data-aion-main-node-edit="${esc(node.id)}"
65902:               data-aion-main-node-field="title"
65903:               value="${esc(node.title || "")}"
65904:               placeholder="Watch emails, extract details, create draft"
65905:             />
65906:           </label>
65907: 
65908:           <label>
65909:             <span>Aion should collect / use</span>
65910:             <textarea
65911:               data-aion-main-node-edit="${esc(node.id)}"
65912:               data-aion-main-node-field="fields"
65913:               placeholder="sender, subject, body, received_at"
65914:             >${esc(node.fields || node.config?.fields || "")}</textarea>
65915:           </label>
65916: 
65917:           <label>
65918:             <span>Pass this to next step as</span>
65919:             <textarea
65920:               data-aion-main-node-edit="${esc(node.id)}"
65921:               data-aion-main-node-field="outputs"
65922:               placeholder="new_email_event, customer_details, draft_reply"
65923:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
65924:           </label>
65925: 
65926:           <label>
65927:             <span>Approval / safety</span>
65928:             <select data-aion-main-node-edit="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
65929:               <option value="auto" ${String(node.approval_requirement || "auto") === "auto" ? "selected" : ""}>Auto</option>
```
```js
66486:               `).join("")}
66487:             </select>
66488:           </label>
66489: 
66490:           <label>
66491:             <span>Use this app / system</span>
66492:             <input
66493:               data-aion-main-node-edit-v3="${esc(node.id)}"
66494:               data-aion-main-node-field="connector"
66495:               value="${esc(node.connector || node.app || node.type || "")}"
66496:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
66497:             />
66498:           </label>
66499: 
66500:           <label>
66501:             <span>Action ID</span>
66502:             <input
66503:               data-aion-main-node-edit-v3="${esc(node.id)}"
66504:               data-aion-main-node-field="action_id"
66505:               value="${esc(node.action_id || node.action || "")}"
66506:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
66507:             />
66508:           </label>
66509: 
66510:           <label>
66511:             <span>What should happen?</span>
66512:             <input
66513:               data-aion-main-node-edit-v3="${esc(node.id)}"
66514:               data-aion-main-node-field="title"
66515:               value="${esc(node.title || node.action_label || "")}"
66516:               placeholder="Watch emails, Extract details, Create draft"
66517:             />
66518:           </label>
66519: 
66520:           <label>
66521:             <span>Aion should collect / use</span>
66522:             <textarea
66523:               data-aion-main-node-edit-v3="${esc(node.id)}"
66524:               data-aion-main-node-field="fields"
66525:               placeholder="sender, subject, body, received_at"
66526:             >${esc(node.fields || node.config?.fields || "")}</textarea>
66527:           </label>
66528: 
66529:           <label>
66530:             <span>Pass this to next step as</span>
66531:             <textarea
66532:               data-aion-main-node-edit-v3="${esc(node.id)}"
66533:               data-aion-main-node-field="outputs"
66534:               placeholder="new_email_event, customer_details, draft_reply"
66535:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
66536:           </label>
66537: 
66538:           <label>
66539:             <span>Approval / safety</span>
66540:             <select data-aion-main-node-edit-v3="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
66541:               <option value="auto" ${approval === "auto" ? "selected" : ""}>Auto</option>
```
```js
67212:               `).join("")}
67213:             </select>
67214:           </label>
67215: 
67216:           <label>
67217:             <span>Use this app / system</span>
67218:             <input
67219:               data-aion-main-node-edit-v3="${esc(node.id)}"
67220:               data-aion-main-node-field="connector"
67221:               value="${esc(node.connector || node.app || node.type || "")}"
67222:               placeholder="Gmail, Aion, Tools, Text Parser, Approval"
67223:             />
67224:           </label>
67225: 
67226:           <label>
67227:             <span>Action ID</span>
67228:             <input
67229:               data-aion-main-node-edit-v3="${esc(node.id)}"
67230:               data-aion-main-node-field="action_id"
67231:               value="${esc(node.action_id || node.action || "")}"
67232:               placeholder="gmail.watch_emails, tools.set_variable, text.match_pattern"
67233:             />
67234:           </label>
67235: 
67236:           <label>
67237:             <span>What should happen?</span>
67238:             <input
67239:               data-aion-main-node-edit-v3="${esc(node.id)}"
67240:               data-aion-main-node-field="title"
67241:               value="${esc(node.title || node.action_label || "")}"
67242:               placeholder="Watch emails, Extract details, Create draft"
67243:             />
67244:           </label>
67245: 
67246:           <label>
67247:             <span>Aion should collect / use</span>
67248:             <textarea
67249:               data-aion-main-node-edit-v3="${esc(node.id)}"
67250:               data-aion-main-node-field="fields"
67251:               placeholder="sender, subject, body, received_at"
67252:             >${esc(node.fields || node.config?.fields || "")}</textarea>
67253:           </label>
67254: 
67255:           <label>
67256:             <span>Pass this to next step as</span>
67257:             <textarea
67258:               data-aion-main-node-edit-v3="${esc(node.id)}"
67259:               data-aion-main-node-field="outputs"
67260:               placeholder="new_email_event, customer_details, draft_reply"
67261:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
67262:           </label>
67263: 
67264:           <label>
67265:             <span>Approval / safety</span>
67266:             <select data-aion-main-node-edit-v3="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
67267:               <option value="auto" ${approval === "auto" ? "selected" : ""}>Auto</option>
```

### `NODE EDITOR` hits: [64464, 64466, 64467, 64468, 64967, 64971, 64972, 65134, 65607, 65610, 65844, 66323, 66326, 66328, 66435, 67049, 67052, 67054, 67161, 68214]
```js
64444:       background: #f7fee7 !important;
64445:       color: #0f172a !important;
64446:       font-weight: 950 !important;
64447:       letter-spacing: 0.08em !important;
64448:       text-transform: uppercase !important;
64449:       cursor: pointer !important;
64450:     }
64451: 
64452:     [data-aion-main-advanced-modal-host="true"] {
64453:       position: relative !important;
64454:       z-index: 9999 !important;
64455:     }
64456:   `;
64457: 
64458:   if (!document.getElementById(PATCH_ID)) {
64459:     document.head.appendChild(style);
64460:   }
64461: })();
64462: 
64463: 
64464: /* AION PATCH: main node editor AI settings + toolbar modal isolation v1
64465:    Fixes:
64466:    - Prevents mini-toolbar injection inside node editor modal.
64467:    - Adds AI Architect-style settings panel into the existing main node editor.
64468:    - Adds Configure Logic / Variables action from node editor into advanced modal.
64469: */
64470: (function installAionMainNodeEditorAiSettingsBridgeV1() {
64471:   const PATCH_ID = "aion-main-node-editor-ai-settings-bridge-v1";
64472:   if (window.__aionMainNodeEditorAiSettingsBridgeV1 === true) return;
64473:   window.__aionMainNodeEditorAiSettingsBridgeV1 = true;
64474: 
64475:   function getGraph() {
64476:     if (typeof getAionWorkflowDraftState === "function") {
64477:       return getAionWorkflowDraftState();
64478:     }
64479:     return window.__aionWorkflowGraph || { nodes: [], edges: [] };
64480:   }
64481: 
64482:   function getSelectedNode() {
64483:     const graph = getGraph();
64484:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64485:     const selectedId = window.__aionWorkflowSelectedNodeId;
64486:     return nodes.find((node) => String(node.id) === String(selectedId)) || nodes[0] || null;
64487:   }
64488: 
64489:   function safeRequestRender() {
64490:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64491:   }
64492: 
64493:   function persistGraph(graph) {
64494:     window["__aionWorkflowGraph"] = graph;
64495: 
64496:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
64497:       try {
64498:         compileAndAttachAionWorkflowGlyph(graph);
64499:       } catch (error) {
```
```js
64446:       font-weight: 950 !important;
64447:       letter-spacing: 0.08em !important;
64448:       text-transform: uppercase !important;
64449:       cursor: pointer !important;
64450:     }
64451: 
64452:     [data-aion-main-advanced-modal-host="true"] {
64453:       position: relative !important;
64454:       z-index: 9999 !important;
64455:     }
64456:   `;
64457: 
64458:   if (!document.getElementById(PATCH_ID)) {
64459:     document.head.appendChild(style);
64460:   }
64461: })();
64462: 
64463: 
64464: /* AION PATCH: main node editor AI settings + toolbar modal isolation v1
64465:    Fixes:
64466:    - Prevents mini-toolbar injection inside node editor modal.
64467:    - Adds AI Architect-style settings panel into the existing main node editor.
64468:    - Adds Configure Logic / Variables action from node editor into advanced modal.
64469: */
64470: (function installAionMainNodeEditorAiSettingsBridgeV1() {
64471:   const PATCH_ID = "aion-main-node-editor-ai-settings-bridge-v1";
64472:   if (window.__aionMainNodeEditorAiSettingsBridgeV1 === true) return;
64473:   window.__aionMainNodeEditorAiSettingsBridgeV1 = true;
64474: 
64475:   function getGraph() {
64476:     if (typeof getAionWorkflowDraftState === "function") {
64477:       return getAionWorkflowDraftState();
64478:     }
64479:     return window.__aionWorkflowGraph || { nodes: [], edges: [] };
64480:   }
64481: 
64482:   function getSelectedNode() {
64483:     const graph = getGraph();
64484:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64485:     const selectedId = window.__aionWorkflowSelectedNodeId;
64486:     return nodes.find((node) => String(node.id) === String(selectedId)) || nodes[0] || null;
64487:   }
64488: 
64489:   function safeRequestRender() {
64490:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64491:   }
64492: 
64493:   function persistGraph(graph) {
64494:     window["__aionWorkflowGraph"] = graph;
64495: 
64496:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
64497:       try {
64498:         compileAndAttachAionWorkflowGlyph(graph);
64499:       } catch (error) {
64500:         console.warn(`[${PATCH_ID}] compile skipped`, error);
64501:       }
```
```js
64447:       letter-spacing: 0.08em !important;
64448:       text-transform: uppercase !important;
64449:       cursor: pointer !important;
64450:     }
64451: 
64452:     [data-aion-main-advanced-modal-host="true"] {
64453:       position: relative !important;
64454:       z-index: 9999 !important;
64455:     }
64456:   `;
64457: 
64458:   if (!document.getElementById(PATCH_ID)) {
64459:     document.head.appendChild(style);
64460:   }
64461: })();
64462: 
64463: 
64464: /* AION PATCH: main node editor AI settings + toolbar modal isolation v1
64465:    Fixes:
64466:    - Prevents mini-toolbar injection inside node editor modal.
64467:    - Adds AI Architect-style settings panel into the existing main node editor.
64468:    - Adds Configure Logic / Variables action from node editor into advanced modal.
64469: */
64470: (function installAionMainNodeEditorAiSettingsBridgeV1() {
64471:   const PATCH_ID = "aion-main-node-editor-ai-settings-bridge-v1";
64472:   if (window.__aionMainNodeEditorAiSettingsBridgeV1 === true) return;
64473:   window.__aionMainNodeEditorAiSettingsBridgeV1 = true;
64474: 
64475:   function getGraph() {
64476:     if (typeof getAionWorkflowDraftState === "function") {
64477:       return getAionWorkflowDraftState();
64478:     }
64479:     return window.__aionWorkflowGraph || { nodes: [], edges: [] };
64480:   }
64481: 
64482:   function getSelectedNode() {
64483:     const graph = getGraph();
64484:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64485:     const selectedId = window.__aionWorkflowSelectedNodeId;
64486:     return nodes.find((node) => String(node.id) === String(selectedId)) || nodes[0] || null;
64487:   }
64488: 
64489:   function safeRequestRender() {
64490:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64491:   }
64492: 
64493:   function persistGraph(graph) {
64494:     window["__aionWorkflowGraph"] = graph;
64495: 
64496:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
64497:       try {
64498:         compileAndAttachAionWorkflowGlyph(graph);
64499:       } catch (error) {
64500:         console.warn(`[${PATCH_ID}] compile skipped`, error);
64501:       }
64502:     }
```
```js
64448:       text-transform: uppercase !important;
64449:       cursor: pointer !important;
64450:     }
64451: 
64452:     [data-aion-main-advanced-modal-host="true"] {
64453:       position: relative !important;
64454:       z-index: 9999 !important;
64455:     }
64456:   `;
64457: 
64458:   if (!document.getElementById(PATCH_ID)) {
64459:     document.head.appendChild(style);
64460:   }
64461: })();
64462: 
64463: 
64464: /* AION PATCH: main node editor AI settings + toolbar modal isolation v1
64465:    Fixes:
64466:    - Prevents mini-toolbar injection inside node editor modal.
64467:    - Adds AI Architect-style settings panel into the existing main node editor.
64468:    - Adds Configure Logic / Variables action from node editor into advanced modal.
64469: */
64470: (function installAionMainNodeEditorAiSettingsBridgeV1() {
64471:   const PATCH_ID = "aion-main-node-editor-ai-settings-bridge-v1";
64472:   if (window.__aionMainNodeEditorAiSettingsBridgeV1 === true) return;
64473:   window.__aionMainNodeEditorAiSettingsBridgeV1 = true;
64474: 
64475:   function getGraph() {
64476:     if (typeof getAionWorkflowDraftState === "function") {
64477:       return getAionWorkflowDraftState();
64478:     }
64479:     return window.__aionWorkflowGraph || { nodes: [], edges: [] };
64480:   }
64481: 
64482:   function getSelectedNode() {
64483:     const graph = getGraph();
64484:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64485:     const selectedId = window.__aionWorkflowSelectedNodeId;
64486:     return nodes.find((node) => String(node.id) === String(selectedId)) || nodes[0] || null;
64487:   }
64488: 
64489:   function safeRequestRender() {
64490:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64491:   }
64492: 
64493:   function persistGraph(graph) {
64494:     window["__aionWorkflowGraph"] = graph;
64495: 
64496:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
64497:       try {
64498:         compileAndAttachAionWorkflowGlyph(graph);
64499:       } catch (error) {
64500:         console.warn(`[${PATCH_ID}] compile skipped`, error);
64501:       }
64502:     }
64503: 
```
```js
64947:       justify-self: start !important;
64948:       height: 54px !important;
64949:       border-radius: 12px !important;
64950:       border: 1px solid rgba(15,23,42,0.18) !important;
64951:       background: #f7fee7 !important;
64952:       color: #0f172a !important;
64953:       font-weight: 950 !important;
64954:       letter-spacing: 0.08em !important;
64955:       text-transform: uppercase !important;
64956:       padding: 0 16px !important;
64957:       cursor: pointer !important;
64958:     }
64959:   `;
64960: 
64961:   if (!document.getElementById(PATCH_ID)) {
64962:     document.head.appendChild(style);
64963:   }
64964: })();
64965: 
64966: 
64967: /* AION PATCH: force main canvas node editor AI-settings + advanced modal mount v2
64968:    Fixes:
64969:    - Main canvas node tool icon opens Configure Step Logic modal.
64970:    - Configure Step Logic modal is mounted even outside AI Architect canvas.
64971:    - Existing Node Editor receives AI canvas settings section.
64972:    - Removes mini-toolbar overlap inside node editor modal.
64973: */
64974: (function installAionMainCanvasNodeEditorBridgeV2() {
64975:   const PATCH_ID = "aion-main-canvas-node-editor-bridge-v2";
64976:   if (window.__aionMainCanvasNodeEditorBridgeV2 === true) return;
64977:   window.__aionMainCanvasNodeEditorBridgeV2 = true;
64978: 
64979:   function safeEscape(value) {
64980:     if (typeof escapeHtml === "function") return escapeHtml(value);
64981:     return String(value ?? "")
64982:       .replaceAll("&", "&amp;")
64983:       .replaceAll("<", "&lt;")
64984:       .replaceAll(">", "&gt;")
64985:       .replaceAll('"', "&quot;")
64986:       .replaceAll("'", "&#039;");
64987:   }
64988: 
64989:   function getGraph() {
64990:     if (typeof getAionWorkflowDraftState === "function") {
64991:       try {
64992:         return getAionWorkflowDraftState();
64993:       } catch (_) {}
64994:     }
64995: 
64996:     if (!window.__aionWorkflowGraph) {
64997:       window.__aionWorkflowGraph = { nodes: [], edges: [] };
64998:     }
64999: 
65000:     return window["__aionWorkflowGraph"];
65001:   }
65002: 
```

### `Node Editor` hits: [64464, 64466, 64467, 64468, 64967, 64971, 64972, 65134, 65607, 65610, 65844, 66323, 66326, 66328, 66435, 67049, 67052, 67054, 67161, 68214]
```js
64444:       background: #f7fee7 !important;
64445:       color: #0f172a !important;
64446:       font-weight: 950 !important;
64447:       letter-spacing: 0.08em !important;
64448:       text-transform: uppercase !important;
64449:       cursor: pointer !important;
64450:     }
64451: 
64452:     [data-aion-main-advanced-modal-host="true"] {
64453:       position: relative !important;
64454:       z-index: 9999 !important;
64455:     }
64456:   `;
64457: 
64458:   if (!document.getElementById(PATCH_ID)) {
64459:     document.head.appendChild(style);
64460:   }
64461: })();
64462: 
64463: 
64464: /* AION PATCH: main node editor AI settings + toolbar modal isolation v1
64465:    Fixes:
64466:    - Prevents mini-toolbar injection inside node editor modal.
64467:    - Adds AI Architect-style settings panel into the existing main node editor.
64468:    - Adds Configure Logic / Variables action from node editor into advanced modal.
64469: */
64470: (function installAionMainNodeEditorAiSettingsBridgeV1() {
64471:   const PATCH_ID = "aion-main-node-editor-ai-settings-bridge-v1";
64472:   if (window.__aionMainNodeEditorAiSettingsBridgeV1 === true) return;
64473:   window.__aionMainNodeEditorAiSettingsBridgeV1 = true;
64474: 
64475:   function getGraph() {
64476:     if (typeof getAionWorkflowDraftState === "function") {
64477:       return getAionWorkflowDraftState();
64478:     }
64479:     return window.__aionWorkflowGraph || { nodes: [], edges: [] };
64480:   }
64481: 
64482:   function getSelectedNode() {
64483:     const graph = getGraph();
64484:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64485:     const selectedId = window.__aionWorkflowSelectedNodeId;
64486:     return nodes.find((node) => String(node.id) === String(selectedId)) || nodes[0] || null;
64487:   }
64488: 
64489:   function safeRequestRender() {
64490:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64491:   }
64492: 
64493:   function persistGraph(graph) {
64494:     window["__aionWorkflowGraph"] = graph;
64495: 
64496:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
64497:       try {
64498:         compileAndAttachAionWorkflowGlyph(graph);
64499:       } catch (error) {
```
```js
64446:       font-weight: 950 !important;
64447:       letter-spacing: 0.08em !important;
64448:       text-transform: uppercase !important;
64449:       cursor: pointer !important;
64450:     }
64451: 
64452:     [data-aion-main-advanced-modal-host="true"] {
64453:       position: relative !important;
64454:       z-index: 9999 !important;
64455:     }
64456:   `;
64457: 
64458:   if (!document.getElementById(PATCH_ID)) {
64459:     document.head.appendChild(style);
64460:   }
64461: })();
64462: 
64463: 
64464: /* AION PATCH: main node editor AI settings + toolbar modal isolation v1
64465:    Fixes:
64466:    - Prevents mini-toolbar injection inside node editor modal.
64467:    - Adds AI Architect-style settings panel into the existing main node editor.
64468:    - Adds Configure Logic / Variables action from node editor into advanced modal.
64469: */
64470: (function installAionMainNodeEditorAiSettingsBridgeV1() {
64471:   const PATCH_ID = "aion-main-node-editor-ai-settings-bridge-v1";
64472:   if (window.__aionMainNodeEditorAiSettingsBridgeV1 === true) return;
64473:   window.__aionMainNodeEditorAiSettingsBridgeV1 = true;
64474: 
64475:   function getGraph() {
64476:     if (typeof getAionWorkflowDraftState === "function") {
64477:       return getAionWorkflowDraftState();
64478:     }
64479:     return window.__aionWorkflowGraph || { nodes: [], edges: [] };
64480:   }
64481: 
64482:   function getSelectedNode() {
64483:     const graph = getGraph();
64484:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64485:     const selectedId = window.__aionWorkflowSelectedNodeId;
64486:     return nodes.find((node) => String(node.id) === String(selectedId)) || nodes[0] || null;
64487:   }
64488: 
64489:   function safeRequestRender() {
64490:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64491:   }
64492: 
64493:   function persistGraph(graph) {
64494:     window["__aionWorkflowGraph"] = graph;
64495: 
64496:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
64497:       try {
64498:         compileAndAttachAionWorkflowGlyph(graph);
64499:       } catch (error) {
64500:         console.warn(`[${PATCH_ID}] compile skipped`, error);
64501:       }
```
```js
64447:       letter-spacing: 0.08em !important;
64448:       text-transform: uppercase !important;
64449:       cursor: pointer !important;
64450:     }
64451: 
64452:     [data-aion-main-advanced-modal-host="true"] {
64453:       position: relative !important;
64454:       z-index: 9999 !important;
64455:     }
64456:   `;
64457: 
64458:   if (!document.getElementById(PATCH_ID)) {
64459:     document.head.appendChild(style);
64460:   }
64461: })();
64462: 
64463: 
64464: /* AION PATCH: main node editor AI settings + toolbar modal isolation v1
64465:    Fixes:
64466:    - Prevents mini-toolbar injection inside node editor modal.
64467:    - Adds AI Architect-style settings panel into the existing main node editor.
64468:    - Adds Configure Logic / Variables action from node editor into advanced modal.
64469: */
64470: (function installAionMainNodeEditorAiSettingsBridgeV1() {
64471:   const PATCH_ID = "aion-main-node-editor-ai-settings-bridge-v1";
64472:   if (window.__aionMainNodeEditorAiSettingsBridgeV1 === true) return;
64473:   window.__aionMainNodeEditorAiSettingsBridgeV1 = true;
64474: 
64475:   function getGraph() {
64476:     if (typeof getAionWorkflowDraftState === "function") {
64477:       return getAionWorkflowDraftState();
64478:     }
64479:     return window.__aionWorkflowGraph || { nodes: [], edges: [] };
64480:   }
64481: 
64482:   function getSelectedNode() {
64483:     const graph = getGraph();
64484:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64485:     const selectedId = window.__aionWorkflowSelectedNodeId;
64486:     return nodes.find((node) => String(node.id) === String(selectedId)) || nodes[0] || null;
64487:   }
64488: 
64489:   function safeRequestRender() {
64490:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64491:   }
64492: 
64493:   function persistGraph(graph) {
64494:     window["__aionWorkflowGraph"] = graph;
64495: 
64496:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
64497:       try {
64498:         compileAndAttachAionWorkflowGlyph(graph);
64499:       } catch (error) {
64500:         console.warn(`[${PATCH_ID}] compile skipped`, error);
64501:       }
64502:     }
```
```js
64448:       text-transform: uppercase !important;
64449:       cursor: pointer !important;
64450:     }
64451: 
64452:     [data-aion-main-advanced-modal-host="true"] {
64453:       position: relative !important;
64454:       z-index: 9999 !important;
64455:     }
64456:   `;
64457: 
64458:   if (!document.getElementById(PATCH_ID)) {
64459:     document.head.appendChild(style);
64460:   }
64461: })();
64462: 
64463: 
64464: /* AION PATCH: main node editor AI settings + toolbar modal isolation v1
64465:    Fixes:
64466:    - Prevents mini-toolbar injection inside node editor modal.
64467:    - Adds AI Architect-style settings panel into the existing main node editor.
64468:    - Adds Configure Logic / Variables action from node editor into advanced modal.
64469: */
64470: (function installAionMainNodeEditorAiSettingsBridgeV1() {
64471:   const PATCH_ID = "aion-main-node-editor-ai-settings-bridge-v1";
64472:   if (window.__aionMainNodeEditorAiSettingsBridgeV1 === true) return;
64473:   window.__aionMainNodeEditorAiSettingsBridgeV1 = true;
64474: 
64475:   function getGraph() {
64476:     if (typeof getAionWorkflowDraftState === "function") {
64477:       return getAionWorkflowDraftState();
64478:     }
64479:     return window.__aionWorkflowGraph || { nodes: [], edges: [] };
64480:   }
64481: 
64482:   function getSelectedNode() {
64483:     const graph = getGraph();
64484:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64485:     const selectedId = window.__aionWorkflowSelectedNodeId;
64486:     return nodes.find((node) => String(node.id) === String(selectedId)) || nodes[0] || null;
64487:   }
64488: 
64489:   function safeRequestRender() {
64490:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64491:   }
64492: 
64493:   function persistGraph(graph) {
64494:     window["__aionWorkflowGraph"] = graph;
64495: 
64496:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
64497:       try {
64498:         compileAndAttachAionWorkflowGlyph(graph);
64499:       } catch (error) {
64500:         console.warn(`[${PATCH_ID}] compile skipped`, error);
64501:       }
64502:     }
64503: 
```
```js
64947:       justify-self: start !important;
64948:       height: 54px !important;
64949:       border-radius: 12px !important;
64950:       border: 1px solid rgba(15,23,42,0.18) !important;
64951:       background: #f7fee7 !important;
64952:       color: #0f172a !important;
64953:       font-weight: 950 !important;
64954:       letter-spacing: 0.08em !important;
64955:       text-transform: uppercase !important;
64956:       padding: 0 16px !important;
64957:       cursor: pointer !important;
64958:     }
64959:   `;
64960: 
64961:   if (!document.getElementById(PATCH_ID)) {
64962:     document.head.appendChild(style);
64963:   }
64964: })();
64965: 
64966: 
64967: /* AION PATCH: force main canvas node editor AI-settings + advanced modal mount v2
64968:    Fixes:
64969:    - Main canvas node tool icon opens Configure Step Logic modal.
64970:    - Configure Step Logic modal is mounted even outside AI Architect canvas.
64971:    - Existing Node Editor receives AI canvas settings section.
64972:    - Removes mini-toolbar overlap inside node editor modal.
64973: */
64974: (function installAionMainCanvasNodeEditorBridgeV2() {
64975:   const PATCH_ID = "aion-main-canvas-node-editor-bridge-v2";
64976:   if (window.__aionMainCanvasNodeEditorBridgeV2 === true) return;
64977:   window.__aionMainCanvasNodeEditorBridgeV2 = true;
64978: 
64979:   function safeEscape(value) {
64980:     if (typeof escapeHtml === "function") return escapeHtml(value);
64981:     return String(value ?? "")
64982:       .replaceAll("&", "&amp;")
64983:       .replaceAll("<", "&lt;")
64984:       .replaceAll(">", "&gt;")
64985:       .replaceAll('"', "&quot;")
64986:       .replaceAll("'", "&#039;");
64987:   }
64988: 
64989:   function getGraph() {
64990:     if (typeof getAionWorkflowDraftState === "function") {
64991:       try {
64992:         return getAionWorkflowDraftState();
64993:       } catch (_) {}
64994:     }
64995: 
64996:     if (!window.__aionWorkflowGraph) {
64997:       window.__aionWorkflowGraph = { nodes: [], edges: [] };
64998:     }
64999: 
65000:     return window["__aionWorkflowGraph"];
65001:   }
65002: 
```

## Actual workflow node click / selection handlers


### `const nodeEl = event.target.closest?.("[data-aion-workflow-node-id]");` hits: [56826, 116803]
```js
56801: 
56802:   window.AionWorkflowNodeEditor?.installControls?.({
56803:     getAionWorkflowDraftState,
56804:     compileAndAttachAionWorkflowGlyph,
56805:     persistAionWorkflowDraftState,
56806:     requestRender,
56807:     desktopStore,
56808:   });
56809: 
56810:   if (window.__aionWorkflowNodeDragBound === true) return;
56811:   window.__aionWorkflowNodeDragBound = true;
56812: 
56813:   let dragState = null;
56814: 
56815:   document.addEventListener("pointerdown", (event) => {
56816:     if (
56817:       event.target.closest?.(".aion-workflow-inspector") ||
56818:       event.target.closest?.("[data-aion-workflow-node-config-input]")
56819:     ) {
56820:       return;
56821:     }
56822: 
56823:     const deleteButton = event.target.closest?.("[data-aion-workflow-delete-node]");
56824:     if (deleteButton) return;
56825: 
56826:     const nodeEl = event.target.closest?.("[data-aion-workflow-node-id]");
56827:     if (!nodeEl) return;
56828: 
56829:     const nodeId = nodeEl.getAttribute("data-aion-workflow-node-id");
56830:     if (
56831:       typeof window.aionRouteLinkedDepartmentNodeO13H2 === "function" &&
56832:       window.aionRouteLinkedDepartmentNodeO13H2(nodeId, nodeEl)
56833:     ) {
56834:       event.preventDefault();
56835:       event.stopPropagation();
56836:       event.stopImmediatePropagation();
56837:       return;
56838:     }
56839:     if (!nodeId) return;
56840: 
56841:     const graph = getAionWorkflowDraftState();
56842:     const node = Array.isArray(graph.nodes)
56843:       ? graph.nodes.find((item) => item.id === nodeId)
56844:       : null;
56845: 
56846:     if (!node) return;
56847: 
56848:     const view = window.__aionWorkflowCanvasView || { zoom: 1, x: 0, y: 0 };
56849:     const zoom = Math.max(0.1, Number(view.zoom || 1));
56850: 
56851:     dragState = {
56852:       nodeId,
56853:       startClientX: event.clientX,
56854:       startClientY: event.clientY,
56855:       startX: Number(node.x || 0),
56856:       startY: Number(node.y || 0),
56857:       zoom,
56858:       moved: false,
56859:     };
56860: 
56861:     nodeEl.setPointerCapture?.(event.pointerId);
56862:     nodeEl.classList.add("aion-canvas-node-dragging");
56863: 
56864:     event.preventDefault();
56865:   });
56866: 
56867:   document.addEventListener("pointermove", (event) => {
56868:     if (!dragState) return;
56869: 
56870:     const dx = (event.clientX - dragState.startClientX) / dragState.zoom;
56871:     const dy = (event.clientY - dragState.startClientY) / dragState.zoom;
```
```js
116778:   }
116779: 
116780:   function noOpModalFunction() {
116781:     removeGoalSheetModalDom();
116782:     return false;
116783:   }
116784: 
116785:   /*
116786:    * Kill all public modal hooks so old click handlers cannot reopen it.
116787:    */
116788:   window.openGoalSheetInspector = noOpModalFunction;
116789:   window.openGoalSheetDocumentModal = noOpModalFunction;
116790:   window.aionOpenGoalSheetDocumentModalO12T = noOpModalFunction;
116791:   window.aionCloseGoalSheetDocumentModalO12T = noOpModalFunction;
116792:   window.aionOpenGoalSheetDocumentModalO12M = noOpModalFunction;
116793:   window.aionCloseGoalSheetModalO12L = noOpModalFunction;
116794:   window.aionPolishGoalSheetModalO12L = noOpModalFunction;
116795:   window.aionRemoveOldGoalSheetDocumentDomO12T = removeGoalSheetModalDom;
116796:   window.aionRemoveGoalSheetDocumentModalO12U = removeGoalSheetModalDom;
116797: 
116798:   /*
116799:    * Prevent Goal Sheet node clicks from opening any document modal.
116800:    * Keep normal Add Step modal untouched.
116801:    */
116802:   document.addEventListener("click", (event) => {
116803:     const nodeEl = event.target.closest?.("[data-aion-workflow-node-id]");
116804:     if (!nodeEl) return;
116805:     if (!isBoardroomGoalSheetGraph()) return;
116806: 
116807:     removeGoalSheetModalDom();
116808: 
116809:     window.__aionWorkflowSelectedNodeId = nodeEl.getAttribute("data-aion-workflow-node-id") || null;
116810:     window.__aionWorkflowInspectorOpen = false;
116811: 
116812:     event.preventDefault();
116813:     event.stopPropagation();
116814:     event.stopImmediatePropagation();
116815: 
116816:     if (typeof requestRender === "function") {
116817:       window.setTimeout(() => {
116818:         removeGoalSheetModalDom();
116819:       }, 0);
116820:     }
116821:   }, true);
116822: 
116823:   document.addEventListener("pointerdown", (event) => {
116824:     const closeLike = event.target.closest?.(
116825:       "#aion-o12t-goal-sheet-document-modal button, [data-aion-o12t-close='true'], [data-aion-o12l-close='true'], [data-aion-o12m-close='true']"
116826:     );
116827: 
116828:     if (!closeLike) return;
116829: 
116830:     event.preventDefault();
116831:     event.stopPropagation();
116832:     event.stopImmediatePropagation();
116833:     removeGoalSheetModalDom();
116834:   }, true);
116835: 
116836:   document.addEventListener("keydown", (event) => {
116837:     if (event.key !== "Escape") return;
116838:     removeGoalSheetModalDom();
116839:   }, true);
116840: 
116841:   ensureStyle();
116842:   removeGoalSheetModalDom();
116843: 
116844:   [50, 150, 400, 900, 1600].forEach((delay) => {
116845:     window.setTimeout(removeGoalSheetModalDom, delay);
116846:   });
116847: })();
116848:  /* END AION O12U REMOVE GOAL SHEET DOCUMENT MODAL COMPLETELY */
```

### `const node = event.target.closest?.("[data-aion-workflow-node-id]");` hits: [56985]
```js
56960:         window.__aionWorkflowGraph.nodes[window.__aionWorkflowGraph.nodes.length - 1]?.id ||
56961:         null;
56962:     }
56963: 
56964:     if (!window.__aionWorkflowGraph.nodes.length) {
56965:       window.__aionWorkflowPickerMode = "trigger";
56966:       window.__aionWorkflowInspectorOpen = true;
56967:     } else {
56968:       window.__aionWorkflowPickerMode = null;
56969:       window.__aionWorkflowInspectorOpen = false;
56970:     }
56971: 
56972:     persistAionWorkflowDraftState();
56973:     requestRender();
56974:   });
56975: }
56976: 
56977: 
56978: function installAionWorkflowNodeSelection() {
56979:   if (window.__aionWorkflowNodeSelectionBound === true) return;
56980:   window.__aionWorkflowNodeSelectionBound = true;
56981: 
56982:   document.addEventListener("click", (event) => {
56983:     if (event.target.closest?.(".aion-workflow-inspector")) return;
56984: 
56985:     const node = event.target.closest?.("[data-aion-workflow-node-id]");
56986:     if (!node) return;
56987: 
56988:     const nodeId = node.getAttribute("data-aion-workflow-node-id");
56989:     if (
56990:       typeof window.aionRouteLinkedDepartmentNodeO13H2 === "function" &&
56991:       window.aionRouteLinkedDepartmentNodeO13H2(nodeId, node)
56992:     ) {
56993:       event.preventDefault();
56994:       event.stopPropagation();
56995:       event.stopImmediatePropagation();
56996:       return;
56997:     }
56998:     if (!nodeId) return;
56999: 
57000:     if (
57001:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
57002:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
57003:       ) {
57004:         return;
57005:       }
57006:       window.__aionWorkflowSelectedNodeId = nodeId;
57007:     window.__aionWorkflowInspectorOpen = false;
57008: 
57009:     console.log("[aion-workflow] selected node", nodeId);
57010: 
57011:     // Legacy right inspector is retired. Node editing now belongs in the modal.
57012:     requestRender();
57013:   });
57014: }
57015: 
57016: 
57017: function installAionWorkflowSidebarToggle() {
57018:   const shell =
57019:     document.querySelector(".aion-workflow-canvas-shell") ||
57020:     document.querySelector(".surface-shell:has(.aion-main-sidebar)") ||
57021:     document.querySelector(".dashboard-shell:has(.aion-main-sidebar)") ||
57022:     document.body;
57023: 
57024:   const buttons = document.querySelectorAll("[data-aion-workflow-sidebar-toggle='true']");
57025: 
57026:   if (!buttons.length) return;
57027: 
57028:   if (window.__aionWorkflowSidebarOpen === undefined) {
57029:     window.__aionWorkflowSidebarOpen = false;
57030:   }
```

### `window.__aionWorkflowSelectedNodeId = nodeId;` hits: [27769, 57006, 63999, 64551, 65665, 70583, 82912]
```js
27744:         outputs_schema: cloneMasterGlyphValue(item.outputs_schema || compiled.outputs_schema || {}),
27745:         approval_policy: cloneMasterGlyphValue(item.approval_policy || compiled.approval_policy || {}),
27746:         boardroom_events: cloneMasterGlyphValue(item.boardroom_events || compiled.boardroom_events || []),
27747:         compiled_glyph: compiled,
27748:       },
27749:       runtime: {
27750:         input_items: [],
27751:         output_items: [],
27752:         execution_status: "idle",
27753:         last_run_at: null,
27754:         error: null,
27755:       },
27756:     };
27757: 
27758:     graph.nodes.push(stagedNode);
27759:     graph.dirty = true;
27760:     graph.updated_at = new Date().toISOString();
27761: 
27762:     window["__aionWorkflowGraph"] = graph;
27763:     if (
27764:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
27765:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
27766:       ) {
27767:         return;
27768:       }
27769:       window.__aionWorkflowSelectedNodeId = nodeId;
27770: 
27771:     try {
27772:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
27773:         compileAndAttachAionWorkflowGlyph(graph);
27774:       }
27775:     } catch (_) {}
27776: 
27777:     try {
27778:       if (typeof persistAionWorkflowDraftState === "function") {
27779:         persistAionWorkflowDraftState();
27780:       }
27781:     } catch (_) {}
27782: 
27783:     if (typeof safePatchMessage === "function") {
27784:       safePatchMessage(`Staged workflow glyph: ${item.name || childWorkflowId}`, "success");
27785:     }
27786: 
27787:     if (typeof requestRender === "function") requestRender();
27788: 
27789:     return stagedNode;
27790:   }
27791: 
27792:   window.__stageAionMasterGlyphToWorkflowCanvas = stageMasterGlyphToWorkflowCanvas;
27793: 
27794:   document.addEventListener("click", (event) => {
27795:     const open = event.target.closest?.("[data-aion-master-glyph-canvas-open='true']");
27796:     if (open) {
27797:       event.preventDefault();
27798:       event.stopPropagation();
27799:       window.__aionMasterGlyphCanvasOpen = false;
27800: 
27801:       if (typeof window.__openAionWorkflowGlyphLibrary === "function") {
27802:         window.__openAionWorkflowGlyphLibrary();
27803:       } else if (typeof window.__openAionBackendGlyphLibraryModal === "function") {
27804:         window.__openAionBackendGlyphLibraryModal();
27805:       } else if (typeof window.__renderAionWorkflowGlyphLibraryModal === "function") {
27806:         window.__renderAionWorkflowGlyphLibraryModal();
27807:       }
27808: 
27809:       if (typeof requestRender === "function") requestRender();
27810:       return;
27811:     }
27812: 
27813:     const close = event.target.closest?.("[data-aion-master-glyph-canvas-close='true']");
27814:     if (close) {
```
```js
56981: 
56982:   document.addEventListener("click", (event) => {
56983:     if (event.target.closest?.(".aion-workflow-inspector")) return;
56984: 
56985:     const node = event.target.closest?.("[data-aion-workflow-node-id]");
56986:     if (!node) return;
56987: 
56988:     const nodeId = node.getAttribute("data-aion-workflow-node-id");
56989:     if (
56990:       typeof window.aionRouteLinkedDepartmentNodeO13H2 === "function" &&
56991:       window.aionRouteLinkedDepartmentNodeO13H2(nodeId, node)
56992:     ) {
56993:       event.preventDefault();
56994:       event.stopPropagation();
56995:       event.stopImmediatePropagation();
56996:       return;
56997:     }
56998:     if (!nodeId) return;
56999: 
57000:     if (
57001:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
57002:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
57003:       ) {
57004:         return;
57005:       }
57006:       window.__aionWorkflowSelectedNodeId = nodeId;
57007:     window.__aionWorkflowInspectorOpen = false;
57008: 
57009:     console.log("[aion-workflow] selected node", nodeId);
57010: 
57011:     // Legacy right inspector is retired. Node editing now belongs in the modal.
57012:     requestRender();
57013:   });
57014: }
57015: 
57016: 
57017: function installAionWorkflowSidebarToggle() {
57018:   const shell =
57019:     document.querySelector(".aion-workflow-canvas-shell") ||
57020:     document.querySelector(".surface-shell:has(.aion-main-sidebar)") ||
57021:     document.querySelector(".dashboard-shell:has(.aion-main-sidebar)") ||
57022:     document.body;
57023: 
57024:   const buttons = document.querySelectorAll("[data-aion-workflow-sidebar-toggle='true']");
57025: 
57026:   if (!buttons.length) return;
57027: 
57028:   if (window.__aionWorkflowSidebarOpen === undefined) {
57029:     window.__aionWorkflowSidebarOpen = false;
57030:   }
57031: 
57032:   const apply = () => {
57033:     const expanded = window.__aionWorkflowSidebarOpen === true;
57034: 
57035:     /*
57036:      * Sidebar state contract:
57037:      * - Workflow canvas still uses the workflow shell when present.
57038:      * - Main app sidebar uses body class so the global left rail can expand.
57039:      * - The old collapsed class is removed so legacy styles.css collapsed icon rules cannot win.
57040:      */
57041:     shell?.classList?.remove?.("aion-workflow-sidebar-collapsed");
57042:     shell?.classList?.toggle?.("aion-workflow-sidebar-expanded", expanded);
57043:     document.body.classList.toggle("aion-workflow-sidebar-expanded", expanded);
57044:   };
57045: 
57046:   buttons.forEach((button) => {
57047:     if (button.dataset.aionSidebarBound === "true") return;
57048:     button.dataset.aionSidebarBound = "true";
57049: 
57050:     button.addEventListener("click", (event) => {
57051:       event.preventDefault();
```
```js
63974:     if (typeof safeAionDesktopPatch === "function") {
63975:       safeAionDesktopPatch({ message, messageTone: tone });
63976:       return;
63977:     }
63978: 
63979:     if (window.desktopStore?.patch) {
63980:       window.desktopStore.patch({ message, messageTone: tone });
63981:       return;
63982:     }
63983: 
63984:     console.log(`[Aion] ${tone}: ${message}`);
63985:   }
63986: 
63987:   function getNodeIdFromToolbarButton(button) {
63988:     return button?.getAttribute?.("data-aion-main-node-toolbar-node") || "";
63989:   }
63990: 
63991:   function selectNode(nodeId) {
63992:     if (!nodeId) return;
63993:     if (
63994:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
63995:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
63996:       ) {
63997:         return;
63998:       }
63999:       window.__aionWorkflowSelectedNodeId = nodeId;
64000:   }
64001: 
64002:   function removeNode(nodeId) {
64003:     const graph =
64004:       (typeof getAionWorkflowDraftState === "function"
64005:         ? getAionWorkflowDraftState()
64006:         : window.__aionWorkflowGraph) || makeBlankWorkflowGraph();
64007: 
64008:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64009:     const edges = Array.isArray(graph.edges) ? graph.edges : [];
64010: 
64011:     const nextNodes = nodes.filter((node) => String(node.id) !== String(nodeId));
64012:     const nextEdges = edges.filter(
64013:       (edge) => String(edge.from) !== String(nodeId) && String(edge.to) !== String(nodeId),
64014:     );
64015: 
64016:     if (!nextNodes.length) {
64017:       window.__aionWorkflowGraph = makeBlankWorkflowGraph();
64018:       window.__aionWorkflowSelectedNodeId = null;
64019:     } else {
64020:       graph.nodes = nextNodes;
64021:       graph.edges = nextEdges;
64022:       graph.dirty = true;
64023:       window["__aionWorkflowGraph"] = graph;
64024:       window.__aionWorkflowSelectedNodeId = nextNodes[nextNodes.length - 1]?.id || null;
64025:     }
64026: 
64027:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
64028:       try {
64029:         compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
64030:       } catch (error) {
64031:         console.warn(`[${PATCH_ID}] compile after delete skipped`, error);
64032:       }
64033:     }
64034: 
64035:     if (typeof persistAionWorkflowDraftState === "function") {
64036:       try {
64037:         persistAionWorkflowDraftState();
64038:       } catch (error) {
64039:         console.warn(`[${PATCH_ID}] persist after delete skipped`, error);
64040:       }
64041:     }
64042: 
64043:     safePatchMessage("Workflow node removed.", "success");
64044: 
```
```js
64526: 
64527:       return {
64528:         ...node,
64529:         [field]: value,
64530:         config,
64531:       };
64532:     });
64533: 
64534:     graph.dirty = true;
64535:     persistGraph(graph);
64536:   }
64537: 
64538:   function openAdvancedLogicFromMainNode(nodeId) {
64539:     const graph = getGraph();
64540:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64541:     const node = nodes.find((item) => String(item.id) === String(nodeId));
64542: 
64543:     if (!node) return;
64544: 
64545:     if (
64546:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
64547:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
64548:       ) {
64549:         return;
64550:       }
64551:       window.__aionWorkflowSelectedNodeId = nodeId;
64552:     window.__aionArchitectSelectedStepId = nodeId;
64553:     window.__aionArchitectAdvancedConfigOpen = true;
64554:     window.__aionArchitectAdvancedConfigTab = window.__aionArchitectAdvancedConfigTab || "filters";
64555: 
64556:     window.__aionArchitectSteps = [
64557:       {
64558:         id: node.id,
64559:         app: node.connector || node.type || node.title || "workflow",
64560:         connector: node.connector || node.type || "",
64561:         action_id: node.action_id || node.action || "",
64562:         action_label: node.title || node.action_label || "Configure step",
64563:         subtitle: node.meta || node.subtitle || "",
64564:         fields: node.fields || node.config?.fields || "",
64565:         outputs: node.outputs || node.config?.outputs || "",
64566:         approval_requirement:
64567:           node.approval_requirement ||
64568:           (String(node.status || "").toLowerCase().includes("approval") ? "required" : "auto"),
64569:       },
64570:     ];
64571: 
64572:     safeRequestRender();
64573:   }
64574: 
64575:   function injectAiSettingsIntoNodeEditor() {
64576:     const editor =
64577:       document.querySelector(".aion-workflow-node-editor") ||
64578:       document.querySelector("[data-aion-workflow-node-editor='true']");
64579: 
64580:     if (!editor) return;
64581:     if (editor.querySelector("[data-aion-main-node-ai-settings='true']")) return;
64582: 
64583:     const node = getSelectedNode();
64584:     if (!node) return;
64585: 
64586:     // Remove any mini toolbars that accidentally got injected inside the modal.
64587:     editor.querySelectorAll(".aion-main-node-mini-toolbar").forEach((toolbar) => toolbar.remove());
64588: 
64589:     const paramsColumn =
64590:       Array.from(editor.querySelectorAll("*")).find((el) =>
64591:         String(el.textContent || "").trim().startsWith("PARAMETERS"),
64592:       ) || editor;
64593: 
64594:     const panel = document.createElement("section");
64595:     panel.className = "aion-main-node-ai-settings";
64596:     panel.setAttribute("data-aion-main-node-ai-settings", "true");
```
```js
65640:     return window["__aionWorkflowGraph"];
65641:   }
65642: 
65643:   function nodes() {
65644:     const g = graph();
65645:     return Array.isArray(g.nodes) ? g.nodes : [];
65646:   }
65647: 
65648:   function selectedNode() {
65649:     const selectedId = window.__aionWorkflowSelectedNodeId;
65650:     return (
65651:       nodes().find((node) => String(node.id) === String(selectedId)) ||
65652:       nodes()[0] ||
65653:       null
65654:     );
65655:   }
65656: 
65657:   function setSelectedNodeId(nodeId) {
65658:     if (nodeId) {
65659:       if (
65660:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
65661:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
65662:       ) {
65663:         return;
65664:       }
65665:       window.__aionWorkflowSelectedNodeId = nodeId;
65666:     }
65667:   }
65668: 
65669:   function nodeIdFromTarget(target) {
65670:     const holder =
65671:       target.closest?.("[data-aion-workflow-node-id]") ||
65672:       target.closest?.("[data-aion-main-node-id]");
65673: 
65674:     return (
65675:       holder?.getAttribute("data-aion-workflow-node-id") ||
65676:       holder?.getAttribute("data-aion-main-node-id") ||
65677:       window.__aionWorkflowSelectedNodeId ||
65678:       selectedNode()?.id ||
65679:       ""
65680:     );
65681:   }
65682: 
65683:   function patchNode(nodeId, patch) {
65684:     const g = graph();
65685:     g.nodes = nodes().map((node) =>
65686:       String(node.id) === String(nodeId)
65687:         ? {
65688:             ...node,
65689:             ...patch,
65690:             config: {
65691:               ...(node.config || {}),
65692:               ...(patch.config || {}),
65693:             },
65694:           }
65695:         : node,
65696:     );
65697: 
65698:     window.__aionWorkflowGraph = g;
65699: 
65700:     try {
65701:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
65702:         compileAndAttachAionWorkflowGlyph(g);
65703:       }
65704:     } catch (_) {}
65705: 
65706:     try {
65707:       if (typeof persistAionWorkflowDraftState === "function") {
65708:         persistAionWorkflowDraftState();
65709:       }
65710:     } catch (_) {}
```
```js
70558:   function getSettingsTarget(event) {
70559:     const direct = event.target.closest?.('[data-aion-main-node-toolbar="settings"]');
70560:     if (direct) return direct;
70561: 
70562:     const path = typeof event.composedPath === "function" ? event.composedPath() : [];
70563:     return path.find?.(
70564:       (el) => el?.getAttribute?.("data-aion-main-node-toolbar") === "settings",
70565:     );
70566:   }
70567: 
70568:   function openNodeEditorFromSettings(settingsTarget) {
70569:     if (!settingsTarget) return false;
70570: 
70571:     const nodeId =
70572:       settingsTarget.getAttribute("data-aion-main-node-toolbar-node") ||
70573:       settingsTarget.closest?.("[data-aion-workflow-node-id]")?.getAttribute("data-aion-workflow-node-id");
70574: 
70575:     if (!nodeId) return false;
70576: 
70577:     if (
70578:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
70579:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
70580:       ) {
70581:         return;
70582:       }
70583:       window.__aionWorkflowSelectedNodeId = nodeId;
70584: 
70585:     const safeId = window.CSS?.escape ? CSS.escape(nodeId) : nodeId;
70586:     const nodeEl = document.querySelector(`[data-aion-workflow-node-id="${safeId}"]`);
70587: 
70588:     if (!nodeEl) return false;
70589: 
70590:     // Use the existing node double-click path because that already opens
70591:     // the real Input / Parameters / Output modal.
70592:     nodeEl.dispatchEvent(
70593:       new MouseEvent("dblclick", {
70594:         bubbles: true,
70595:         cancelable: true,
70596:         view: window,
70597:       }),
70598:     );
70599: 
70600:     return true;
70601:   }
70602: 
70603:   function handleSettings(event) {
70604:     const settingsTarget = getSettingsTarget(event);
70605:     if (!settingsTarget) return;
70606: 
70607:     event.preventDefault();
70608:     event.stopPropagation();
70609:     event.stopImmediatePropagation();
70610: 
70611:     openNodeEditorFromSettings(settingsTarget);
70612:   }
70613: 
70614:   document.addEventListener("pointerdown", handleSettings, true);
70615:   document.addEventListener("mousedown", handleSettings, true);
70616:   document.addEventListener("click", handleSettings, true);
70617: 
70618:   const style = document.createElement("style");
70619:   style.id = PATCH_ID;
70620:   style.textContent = `
70621:     .aion-canvas-node .aion-main-node-mini-toolbar [data-aion-main-node-toolbar="settings"] {
70622:       pointer-events: auto !important;
70623:       cursor: pointer !important;
70624:       position: relative !important;
70625:       z-index: 1000 !important;
70626:     }
70627:   `;
70628: 
```
```js
82887:         source_glyph_code: glyph.source_glyph_code || null,
82888:         version_hash: glyph.version_hash || glyph.meta?.version_hash || "",
82889:         callable: glyph.callable !== false,
82890:         dry_run_only: true,
82891:         live_send_enabled: false,
82892:         risk_tier: glyph.risk_tier,
82893:         required_connectors: clone(glyph.required_connectors || []),
82894:         input_schema: clone(glyph.input_schema || {}),
82895:         output_schema: clone(glyph.output_schema || {}),
82896:         approval_policy: clone(glyph.approval_policy || {}),
82897:         runtime_plan: clone(glyph.runtime_plan || {}),
82898:         source: "backend_glyph_store",
82899:       },
82900:     });
82901: 
82902:     graph.dirty = true;
82903:     graph.updated_at = new Date().toISOString();
82904: 
82905:     window.__aionWorkflowGraph = graph;
82906:     if (
82907:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
82908:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
82909:       ) {
82910:         return;
82911:       }
82912:       window.__aionWorkflowSelectedNodeId = nodeId;
82913: 
82914:     try {
82915:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
82916:         compileAndAttachAionWorkflowGlyph(graph);
82917:       }
82918:     } catch (_) {}
82919: 
82920:     try {
82921:       if (typeof persistAionWorkflowDraftState === "function") {
82922:         persistAionWorkflowDraftState();
82923:       }
82924:     } catch (_) {}
82925: 
82926:     closeModal();
82927:     notify(`Staged ${glyph.glyph_code} to canvas.`, "success");
82928: 
82929:     if (typeof window["requestRender"] === "function") {
82930:       window["requestRender"]();
82931:     }
82932:   }
82933: 
82934: 
82935:   function buildOpenedGlyphWorkflowGraph(glyph) {
82936:     const code = String(glyph?.glyph_code || glyph?.code || "GLYPH").trim();
82937:     const version = String(glyph?.glyph_version || glyph?.workflow_version || "v1").trim();
82938:     const scope = String(glyph?.scope || glyph?.glyph_scope || "my").trim();
82939:     const readonly = scope === "universal";
82940: 
82941:     const compiled = glyph?.compiled_glyph && typeof glyph.compiled_glyph === "object"
82942:       ? glyph.compiled_glyph
82943:       : {};
82944: 
82945:     const runtimePlan = glyph?.runtime_plan && typeof glyph.runtime_plan === "object"
82946:       ? glyph.runtime_plan
82947:       : {};
82948: 
82949:     const rawSteps =
82950:       Array.isArray(compiled.steps) ? compiled.steps :
82951:       Array.isArray(compiled?.workflow?.steps) ? compiled.workflow.steps :
82952:       Array.isArray(runtimePlan.steps) ? runtimePlan.steps :
82953:       [];
82954: 
82955:     const steps = rawSteps.length ? rawSteps : [
82956:       {
82957:         step_id: "glyph_entry",
```

### `window.__aionWorkflowInspectorOpen = true;` hits: [53153, 56966]
```js
53128:       return;
53129:     }
53130: 
53131:     const dryPollButton = event.target.closest?.("[data-aion-workflow-run-dry-poll='true']");
53132:     if (dryPollButton) {
53133:       event.preventDefault();
53134:       event.stopPropagation();
53135:       event.stopImmediatePropagation();
53136: 
53137:       safeAionDesktopPatch({
53138:         message: "Dry-run poll queued. No external writes will be performed.",
53139:         messageTone: "neutral",
53140:       });
53141: 
53142:       requestRender();
53143:       return;
53144:     }
53145: 
53146:     const stepByStepButton = event.target.closest?.("[data-aion-workflow-build-step-by-step='true']");
53147:     if (stepByStepButton) {
53148:       event.preventDefault();
53149:       event.stopPropagation();
53150:       event.stopImmediatePropagation();
53151: 
53152:       window.__aionWorkflowPickerMode = "action";
53153:       window.__aionWorkflowInspectorOpen = true;
53154: 
53155:       safeAionDesktopPatch({
53156:         message: "Step-by-step builder opened.",
53157:         messageTone: "neutral",
53158:       });
53159: 
53160:       requestRender();
53161:       return;
53162:     }
53163: 
53164:     const approveButton = event.target.closest?.("[data-aion-workflow-approval-approve]");
53165:     if (approveButton) {
53166:       event.preventDefault();
53167:       event.stopPropagation();
53168:       event.stopImmediatePropagation();
53169: 
53170:       const approvalId = approveButton.getAttribute("data-aion-workflow-approval-approve");
53171: 
53172:       if (String(approvalId || "").startsWith("approval_local_")) {
53173:         const approvedApproval = {
53174:           ...(window.__aionWorkflowDryRunResult?.approval_request || {}),
53175:           approval_id: approvalId,
53176:           status: "approved",
53177:           decision: "approved",
53178:           decided_by: "human",
53179:           decided_at: new Date().toISOString(),
53180:           reason: "Approved from local canvas dry-run",
53181:         };
53182: 
53183:         window.__aionWorkflowLastApproval = approvedApproval;
53184: 
53185:         if (window.__aionWorkflowDryRunResult?.approval_request?.approval_id === approvalId) {
53186:           window.__aionWorkflowDryRunResult.approval_request = approvedApproval;
53187:         }
53188: 
53189:         const result = window.__aionWorkflowDryRunResult || {};
53190:         const trace = Array.isArray(result.trace) ? result.trace : [];
53191: 
53192:         window.__aionWorkflowDryRunResult = {
53193:           ...result,
53194:           phase: "resume_after_approval",
53195:           execution_mode: "connector_ready",
53196:           status: "simulated_external_write_ready",
53197:           message: "Approval accepted. External writes are connector-ready only; no live send/write was performed.",
53198:           blocked_external_writes: [],
```
```js
56941: 
56942:     const nodeId = deleteButton.getAttribute("data-aion-workflow-delete-node");
56943:     if (!nodeId || !window.__aionWorkflowGraph) return;
56944: 
56945:     const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
56946:       ? window.__aionWorkflowGraph.nodes
56947:       : [];
56948: 
56949:     const edges = Array.isArray(window.__aionWorkflowGraph.edges)
56950:       ? window.__aionWorkflowGraph.edges
56951:       : [];
56952: 
56953:     window.__aionWorkflowGraph.nodes = nodes.filter((node) => node.id !== nodeId);
56954:     window.__aionWorkflowGraph.edges = edges.filter(
56955:       (edge) => edge.from !== nodeId && edge.to !== nodeId,
56956:     );
56957: 
56958:     if (window.__aionWorkflowSelectedNodeId === nodeId) {
56959:       window.__aionWorkflowSelectedNodeId =
56960:         window.__aionWorkflowGraph.nodes[window.__aionWorkflowGraph.nodes.length - 1]?.id ||
56961:         null;
56962:     }
56963: 
56964:     if (!window.__aionWorkflowGraph.nodes.length) {
56965:       window.__aionWorkflowPickerMode = "trigger";
56966:       window.__aionWorkflowInspectorOpen = true;
56967:     } else {
56968:       window.__aionWorkflowPickerMode = null;
56969:       window.__aionWorkflowInspectorOpen = false;
56970:     }
56971: 
56972:     persistAionWorkflowDraftState();
56973:     requestRender();
56974:   });
56975: }
56976: 
56977: 
56978: function installAionWorkflowNodeSelection() {
56979:   if (window.__aionWorkflowNodeSelectionBound === true) return;
56980:   window.__aionWorkflowNodeSelectionBound = true;
56981: 
56982:   document.addEventListener("click", (event) => {
56983:     if (event.target.closest?.(".aion-workflow-inspector")) return;
56984: 
56985:     const node = event.target.closest?.("[data-aion-workflow-node-id]");
56986:     if (!node) return;
56987: 
56988:     const nodeId = node.getAttribute("data-aion-workflow-node-id");
56989:     if (
56990:       typeof window.aionRouteLinkedDepartmentNodeO13H2 === "function" &&
56991:       window.aionRouteLinkedDepartmentNodeO13H2(nodeId, node)
56992:     ) {
56993:       event.preventDefault();
56994:       event.stopPropagation();
56995:       event.stopImmediatePropagation();
56996:       return;
56997:     }
56998:     if (!nodeId) return;
56999: 
57000:     if (
57001:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
57002:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
57003:       ) {
57004:         return;
57005:       }
57006:       window.__aionWorkflowSelectedNodeId = nodeId;
57007:     window.__aionWorkflowInspectorOpen = false;
57008: 
57009:     console.log("[aion-workflow] selected node", nodeId);
57010: 
57011:     // Legacy right inspector is retired. Node editing now belongs in the modal.
```

### `window.__aionWorkflowInspectorOpen = false;` hits: [29485, 52130, 52289, 53977, 54542, 55793, 56010, 56311, 56453, 56548, 56702, 56715, 56969, 57007, 57074, 61674, 62287, 62708, 63034, 63614, 63952, 79400, 115178, 115546, 115980, 116521, 116810, 117629, 120754, 120957]
```js
29460:           })),
29461:         ]
29462:     : [];
29463: 
29464:   const shouldPreserveLayout =
29465:     isBranchInsert ||
29466:     hasAionWorkflowBranchingEdges(edges) ||
29467:     (
29468:       typeof isAionWorkflowMergeNode === "function" &&
29469:       isAionWorkflowMergeNode(newNode)
29470:     );
29471: 
29472:   const reflowedNodes = shouldPreserveLayout
29473:     ? nextNodes
29474:     : nextNodes.map((node, index) => ({
29475:         ...node,
29476:         x: 160 + index * 275,
29477:         y: Number(node.y || anchorNode.y || 240),
29478:       }));
29479: 
29480:   graph.nodes = reflowedNodes;
29481:   graph.edges = [...remainingEdges, ...insertedEdges];
29482: 
29483:   window.__aionWorkflowSelectedNodeId = newNode.id;
29484:   window.__aionWorkflowPickerMode = "";
29485:   window.__aionWorkflowInspectorOpen = false;
29486: 
29487:   if (typeof persistAionWorkflowDraftState === "function") {
29488:     persistAionWorkflowDraftState();
29489:   }
29490: 
29491:   return true;
29492: }
29493: 
29494: 
29495: function getAionArchitectModuleById(moduleId) {
29496:   return getAionArchitectModuleCatalogue()
29497:     .flatMap((group) => group.modules.map((module) => ({ ...module, group: group.group, group_id: group.group_id })))
29498:     .find((module) => module.id === moduleId || module.action_id === moduleId);
29499: }
29500: 
29501: function renderAionArchitectModulePicker() {
29502:   if (window.__aionArchitectModulePickerOpen !== true) {
29503:     return "";
29504:   }
29505: 
29506:   const activeGroup = window.__aionArchitectModulePickerGroup || "apps";
29507:   const catalogue = getAionArchitectModuleCatalogue();
29508:   const selectedGroup = catalogue.find((group) => group.group_id === activeGroup) || catalogue[0];
29509: 
29510:   return `
29511:     <div class="aion-architect-module-picker-backdrop" data-aion-architect-module-picker-backdrop="true">
29512:       <aside class="aion-architect-module-picker" data-aion-architect-module-picker="true">
29513:         <div class="aion-architect-module-picker-head">
29514:           <div>
29515:             <h2>Add a step</h2>
29516:             <p>Choose what kind of module this step should be. After selection, Aion opens the specific settings for that module.</p>
29517:           </div>
29518:           <button type="button" title="Close" data-aion-architect-close-module-picker="true">×</button>
29519:         </div>
29520: 
29521:         <div class="aion-architect-module-picker-body">
29522:           <nav class="aion-architect-module-groups">
29523:             ${catalogue.map((group) => `
29524:               <button
29525:                 type="button"
29526:                 class="${group.group_id === activeGroup ? "active" : ""}"
29527:                 data-aion-architect-module-group="${escapeHtml(group.group_id)}"
29528:               >
29529:                 <strong>${escapeHtml(group.group)}</strong>
29530:                 <small>${escapeHtml(group.description)}</small>
```
```js
52105:             ]
52106:         : [];
52107: 
52108:       const shouldPreserveLayout =
52109:     isBranchInsert ||
52110:     hasAionWorkflowBranchingEdges(edges) ||
52111:     (
52112:       typeof isAionWorkflowMergeNode === "function" &&
52113:       isAionWorkflowMergeNode(newNode)
52114:     );
52115: 
52116:   const reflowedNodes = shouldPreserveLayout
52117:     ? nextNodes
52118:     : nextNodes.map((node, index) => ({
52119:         ...node,
52120:         x: 160 + index * 275,
52121:         y: Number(node.y || anchorNode.y || 240),
52122:       }));
52123: 
52124:       window.__aionWorkflowGraph.nodes = reflowedNodes;
52125:       window.__aionWorkflowGraph.edges = [...remainingEdges, ...insertedEdges];
52126: 
52127:       window.__aionWorkflowSelectedNodeId = newNode.id;
52128:       window.__aionWorkflowPendingBranchCondition = "";
52129:       window.__aionWorkflowPickerMode = null;
52130:       window.__aionWorkflowInspectorOpen = false;
52131:       persistAionWorkflowDraftState();
52132: 
52133:       requestRender();
52134:     },
52135:     true,
52136:   );
52137: }
52138: 
52139: 
52140: 
52141: function installAionLegacyToolControls() {
52142:   if (window.__aionLegacyToolControlsBound === true) return;
52143:   window.__aionLegacyToolControlsBound = true;
52144: 
52145:   document.addEventListener(
52146:     "pointerdown",
52147:     (event) => {
52148:       const port = event.target.closest?.("[data-aion-port-node-id]");
52149:       if (!port) return;
52150: 
52151:       const direction = port.getAttribute("data-aion-port-direction");
52152:       if (direction !== "output") return;
52153: 
52154:       event.preventDefault();
52155:       event.stopPropagation();
52156:       event.stopImmediatePropagation();
52157: 
52158:       const nodeId = port.getAttribute("data-aion-port-node-id");
52159:       const condition = port.getAttribute("data-aion-port-condition") || "success";
52160:       const role = port.getAttribute("data-aion-port-role") || "main";
52161: 
52162:       window.__aionDraggingConnector = {
52163:         from: nodeId,
52164:         condition,
52165:         role,
52166:         startedAt: Date.now(),
52167:       };
52168: 
52169:       window.__aionPendingConnector = {
52170:         from: nodeId,
52171:         condition,
52172:         role,
52173:       };
52174: 
52175:       window.__aionPendingConnectorMouse = {
```
```js
52264: 
52265:       const toolButton = event.target.closest?.("[data-aion-legacy-tool]");
52266:       if (!toolButton) return;
52267: 
52268:       event.preventDefault();
52269:       event.stopPropagation();
52270:       event.stopImmediatePropagation();
52271: 
52272:       const tool = toolButton.getAttribute("data-aion-legacy-tool");
52273: 
52274:       const labels = {
52275:         browser_recorder: "Teach Aion a browser skill",
52276:         browser_skills: "Saved browser micro-skills",
52277:         workflow_chain: "Chain browser micro-skills",
52278:         task_templates: "Start from a workflow",
52279:         step_builder: "Build custom agent",
52280:         generic_workflows: "Saved generic workflows",
52281:         trained_tasks: "Trained Tasks",
52282:         test_run_output: "Test run output",
52283:       };
52284: 
52285:       window.__aionLegacyToolOpen = tool;
52286:       window.__aionLegacyToolOpenLabel = labels[tool] || "Legacy tool";
52287: 
52288:       // Keep canvas state intact. This is just an overlay.
52289:       window.__aionWorkflowInspectorOpen = false;
52290:       window.__aionWorkflowPickerMode = null;
52291: 
52292:       requestRender();
52293:     },
52294:     true,
52295:   );
52296: }
52297: 
52298: 
52299: 
52300: 
52301: 
52302: /* AION PATCH: local dry-run executor for Architect/generated canvas workflows */
52303: function isAionWorkflowGeneratedCanvasGraph(graph) {
52304:   if (!graph || typeof graph !== "object") return false;
52305: 
52306:   if (graph.architect_review?.loaded_from_valid_review === true) return true;
52307: 
52308:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
52309:   return nodes.some((node) =>
52310:     node?.architect?.generated === true ||
52311:     node?.config?.step_id ||
52312:     node?.config?.node_type ||
52313:     node?.config?.kind ||
52314:     node?.config?.permission?.action
52315:   );
52316: }
52317: 
52318: function normaliseAionWorkflowLocalStepOp(node) {
52319:   const config = node?.config && typeof node.config === "object" ? node.config : {};
52320:   const action = String(
52321:     node?.node_type ||
52322:     node?.architect?.node_type ||
52323:     config?.permission?.action ||
52324:     config?.node_type ||
52325:     config?.kind ||
52326:     node?.type ||
52327:     node?.title ||
52328:     "workflow_step"
52329:   ).toLowerCase();
52330: 
52331:   if (action.includes("gmail.read") || action.includes("read_email") || action.includes("read")) {
52332:     return "read_email";
52333:   }
52334: 
```
```js
53952: 
53953:       document.body.classList.remove("aion-connector-dragging");
53954:       document
53955:         .querySelectorAll("[data-aion-port-connect-drop-target='true']")
53956:         .forEach((item) => item.removeAttribute("data-aion-port-connect-drop-target"));
53957: 
53958:       if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
53959:     },
53960:     true,
53961:   );
53962: 
53963:   document.addEventListener(
53964:     "click",
53965:     (event) => {
53966:       const button = event.target.closest?.(
53967:         "[data-aion-workflow-open-architect='true'], [data-aion-workflow-open-architect-modal='true']",
53968:       );
53969:       if (!button) return;
53970: 
53971:       event.preventDefault();
53972:       event.stopPropagation();
53973:       event.stopImmediatePropagation();
53974: 
53975:       window.__aionWorkflowArchitectModalOpen = true;
53976:       window.__aionWorkflowArchitectOpen = true;
53977:       window.__aionWorkflowInspectorOpen = false;
53978:       window.__aionWorkflowPickerMode = null;
53979: 
53980:       const provider = getWorkflowArchitectSelectedProvider?.() || getWorkflowArchitectReviewState?.()?.provider || "mock";
53981:       setWorkflowArchitectSelectedProvider?.(provider);
53982: 
53983:       setWorkflowArchitectReviewState({
53984:         loading: false,
53985:         provider,
53986:         errors: [],
53987:         warnings: [],
53988:       });
53989: 
53990:       safeAionDesktopPatch({
53991:         message: "AI Workflow Architect opened.",
53992:         messageTone: "neutral",
53993:       });
53994: 
53995:       requestRender();
53996:     },
53997:     true,
53998:   );
53999: }
54000: 
54001: 
54002: 
54003: 
54004: function installAionWorkflowBottomToolbarControls() {
54005:   if (window.__aionWorkflowBottomToolbarControlsBound === true) return;
54006:   window.__aionWorkflowBottomToolbarControlsBound = true;
54007: 
54008:   document.addEventListener(
54009:     "click",
54010:     async (event) => {
54011:       const architectButton = event.target.closest?.(
54012:         "[data-aion-workflow-open-architect-modal='true'], [data-aion-workflow-open-architect='true']",
54013:       );
54014: 
54015:       if (architectButton) {
54016:         event.preventDefault();
54017:         event.stopPropagation();
54018:         event.stopImmediatePropagation();
54019: 
54020:         const reviewState = getWorkflowArchitectReviewState?.() || {};
54021:         const provider =
54022:           getWorkflowArchitectSelectedProvider?.() ||
```
```js
54517:       : [];
54518: 
54519:     const nextGraph = {
54520:       workflow_id: String(canvas.canonical_key || "workflow_architect_generated"),
54521:       business_container: getAionWorkflowBusinessContainerId(),
54522:       name: String(canvas.display_name || spec.workflow_name || review.workflow_name || "Architect generated workflow"),
54523:       status: "draft",
54524:       nodes,
54525:       edges,
54526:       compiled_glyph: null,
54527:       architect_review: {
54528:         loaded_from_valid_review: true,
54529:         provider: result?.provider?.provider || reviewState.provider || getWorkflowArchitectSelectedProvider(),
54530:         dry_run_only: true,
54531:         live_send_enabled: false,
54532:         connectors_required: Array.isArray(review.connectors_required) ? review.connectors_required : [],
54533:         missing_connectors: Array.isArray(review.missing_connectors) ? review.missing_connectors : [],
54534:       },
54535:     };
54536: 
54537:     window.__aionWorkflowGraph = nextGraph;
54538:     fitAionWorkflowCanvasToGeneratedNodes(nodes);
54539:     window.__aionWorkflowSelectedNodeId = nodes[0]?.id || null;
54540:     window.__aionWorkflowArchitectModalOpen = false;
54541:     window.__aionWorkflowPickerMode = "";
54542:     window.__aionWorkflowInspectorOpen = false;
54543: 
54544:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
54545:       compileAndAttachAionWorkflowGlyph(nextGraph);
54546:     }
54547: 
54548:     if (typeof persistAionWorkflowDraftState === "function") {
54549:       persistAionWorkflowDraftState();
54550:     }
54551: 
54552:     setWorkflowArchitectReviewState({
54553:       workflowGoal: (window.__syncedArchitectInput || {}).workflowGoal,
54554:       provider: (window.__syncedArchitectInput || {}).provider,
54555:       result,
54556:       ok: true,
54557:       loading: false,
54558:     });
54559: 
54560:     safeAionDesktopPatch({
54561:       message: `Loaded Architect workflow onto canvas: ${nodes.length} nodes · ${edges.length} links`,
54562:       messageTone: "success",
54563:     });
54564: 
54565:     requestRender();
54566:   }, true);
54567: }
54568: 
54569: 
54570: 
54571: 
54572: function fitAionWorkflowCanvasToGeneratedGraph_DISABLED_DUPLICATE(graph) {
54573:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
54574:   if (!nodes.length) return;
54575: 
54576:   const xs = nodes.map((node) => Number(node.x || node.position?.x || 0));
54577:   const ys = nodes.map((node) => Number(node.y || node.position?.y || 0));
54578: 
54579:   const minX = Math.min(...xs);
54580:   const maxX = Math.max(...xs);
54581:   const minY = Math.min(...ys);
54582:   const maxY = Math.max(...ys);
54583: 
54584:   const width = Math.max(1, maxX - minX + 420);
54585:   const height = Math.max(1, maxY - minY + 320);
54586: 
54587:   const shell = document.querySelector(".aion-workflow-canvas-shell") ||
```
```js
55768:         })),
55769:       ]
55770:     : [];
55771: 
55772:   const shouldPreserveLayout =
55773:         hasAionWorkflowBranchingEdges(edges) ||
55774:         (
55775:           typeof isAionWorkflowMergeNode === "function" &&
55776:           isAionWorkflowMergeNode(newNode)
55777:         );
55778: 
55779:       const reflowedNodes = shouldPreserveLayout
55780:         ? nextNodes
55781:         : nextNodes.map((node, index) => ({
55782:             ...node,
55783:             x: 160 + index * 275,
55784:             y: Number(node.y || anchorNode.y || 240),
55785:           }));
55786: 
55787:   window.__aionWorkflowGraph.nodes = reflowedNodes;
55788:   window.__aionWorkflowGraph.edges = [...remainingEdges, ...insertedEdges];
55789: 
55790:   window.__aionWorkflowSelectedNodeId = newNode.id;
55791:   window.__aionWorkflowPendingBranchCondition = "";
55792:   window.__aionWorkflowPickerMode = null;
55793:   window.__aionWorkflowInspectorOpen = false;
55794:   window.__aionArchitectModulePickerOpen = false;
55795:   window.__aionArchitectSettingsOpen = false;
55796: 
55797:   requestRender();
55798:   return true;
55799: }
55800: 
55801: 
55802: function installAionWorkflowActionControls() {
55803:   if (window.__aionWorkflowActionControlsBound === true) return;
55804:   window.__aionWorkflowActionControlsBound = true;
55805: 
55806:   document.addEventListener(
55807:     "pointerdown",
55808:     (event) => {
55809:       const port = event.target.closest?.("[data-aion-port-node-id]");
55810:       if (!port) return;
55811: 
55812:       const direction = port.getAttribute("data-aion-port-direction");
55813:       if (direction !== "output") return;
55814: 
55815:       event.preventDefault();
55816:       event.stopPropagation();
55817:       event.stopImmediatePropagation();
55818: 
55819:       const nodeId = port.getAttribute("data-aion-port-node-id");
55820:       const condition = port.getAttribute("data-aion-port-condition") || "success";
55821:       const role = port.getAttribute("data-aion-port-role") || "main";
55822: 
55823:       window.__aionDraggingConnector = {
55824:         from: nodeId,
55825:         condition,
55826:         role,
55827:         startedAt: Date.now(),
55828:       };
55829: 
55830:       window.__aionPendingConnector = {
55831:         from: nodeId,
55832:         condition,
55833:         role,
55834:       };
55835: 
55836:       window.__aionPendingConnectorMouse = {
55837:         x: event.clientX,
55838:         y: event.clientY,
```
```js
55985:         const branchCondition =
55986:           openUnifiedModulePicker.getAttribute?.("data-aion-workflow-branch-condition") || "";
55987: 
55988:         const branchAnchor =
55989:           openUnifiedModulePicker.getAttribute?.("data-aion-workflow-branch-anchor") || "";
55990: 
55991:         if (isEmptyStart) {
55992:           window.__aionWorkflowPendingInsertMode = "empty_start";
55993:           window.__aionWorkflowPendingBranchAnchor = "";
55994:           window.__aionWorkflowPendingBranchCondition = "success";
55995:           window.__aionWorkflowSelectedNodeId = null;
55996:         }
55997: 
55998:         if (branchCondition) {
55999:           window.__aionWorkflowPendingBranchCondition = String(branchCondition).toLowerCase();
56000: 
56001:           if (branchAnchor) {
56002:             window.__aionWorkflowSelectedNodeId = branchAnchor;
56003:           }
56004:         } else {
56005:           window.__aionWorkflowPendingBranchCondition = "";
56006:         }
56007: 
56008:         // Do not open the old right-side drawer from + anymore.
56009:         window.__aionWorkflowPickerMode = "";
56010:         window.__aionWorkflowInspectorOpen = false;
56011: 
56012:         // Open the new unified Add Step modal.
56013:         window.__aionArchitectModulePickerOpen = true;
56014:         window.__aionArchitectModulePickerGroup = window.__aionArchitectModulePickerGroup || "apps";
56015: 
56016:         requestRender();
56017:         return;
56018:       }
56019: 
56020:       const actionButton = event.target.closest?.("[data-aion-workflow-create-action]");
56021:       if (!actionButton) return;
56022: 
56023:       event.preventDefault();
56024:       event.stopPropagation();
56025:       event.stopImmediatePropagation();
56026: 
56027:       const rawActionType = actionButton.getAttribute("data-aion-workflow-create-action");
56028:       const actionType =
56029:         typeof window.__resolveAionGoalEngineWorkflowActionAlias === "function"
56030:           ? window.__resolveAionGoalEngineWorkflowActionAlias(rawActionType)
56031:           : rawActionType;
56032: 
56033:       const actionMap = {
56034:         ai_extract_fields: {
56035:           title: "Extract fields",
56036:           type: "AI / Parser",
56037:           icon: "AI",
56038:           status: "Dry-run",
56039:           meta: "Name, email, service, town",
56040:           tone: "blue",
56041:         },
56042:         ai_classify: {
56043:           title: "Classify enquiry",
56044:           type: "AI / Router",
56045:           icon: "◇",
56046:           status: "Draft",
56047:           meta: "Service, urgency, route",
56048:           tone: "blue",
56049:         },
56050:         ai_draft_reply: {
56051:           title: "Draft reply",
56052:           type: "Action",
56053:           icon: "✎",
56054:           status: "Prepared only",
56055:           meta: "No send without approval",
```
```js
56286:               })),
56287:             ]
56288:         : [];
56289: 
56290:       const shouldPreserveLayout =
56291:     isBranchInsert ||
56292:     hasAionWorkflowBranchingEdges(edges) ||
56293:     (
56294:       typeof isAionWorkflowMergeNode === "function" &&
56295:       isAionWorkflowMergeNode(newNode)
56296:     );
56297: 
56298:   const reflowedNodes = shouldPreserveLayout
56299:     ? nextNodes
56300:     : nextNodes.map((node, index) => ({
56301:         ...node,
56302:         x: 160 + index * 275,
56303:         y: Number(node.y || anchorNode.y || 240),
56304:       }));
56305: 
56306:       window.__aionWorkflowGraph.nodes = reflowedNodes;
56307:       window.__aionWorkflowGraph.edges = [...remainingEdges, ...insertedEdges];
56308: 
56309:       window.__aionWorkflowSelectedNodeId = newNode.id;
56310:       window.__aionWorkflowPickerMode = "";
56311:       window.__aionWorkflowInspectorOpen = false;
56312: 
56313:       // Close unified Add Step modal immediately after adding the real canvas node.
56314:       window.__aionArchitectModulePickerOpen = false;
56315:       window.__aionArchitectSettingsOpen = false;
56316: 
56317:       safeAionDesktopPatch({
56318:         message: `Added ${newNode.title || "step"} to the workflow canvas.`,
56319:         messageTone: "success",
56320:       });
56321: 
56322:       requestRender();
56323: 
56324:       window.requestAnimationFrame?.(() => {
56325:         window.__aionArchitectModulePickerOpen = false;
56326:         if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
56327:       });
56328:     },
56329:     true,
56330:   );
56331: }
56332: 
56333: 
56334: function installAionWorkflowFirstStepControls() {
56335:   if (window.__aionWorkflowFirstStepControlsBound === true) return;
56336:   window.__aionWorkflowFirstStepControlsBound = true;
56337: 
56338:   document.addEventListener(
56339:     "pointerdown",
56340:     (event) => {
56341:       const port = event.target.closest?.("[data-aion-port-node-id]");
56342:       if (!port) return;
56343: 
56344:       const direction = port.getAttribute("data-aion-port-direction");
56345:       if (direction !== "output") return;
56346: 
56347:       event.preventDefault();
56348:       event.stopPropagation();
56349:       event.stopImmediatePropagation();
56350: 
56351:       const nodeId = port.getAttribute("data-aion-port-node-id");
56352:       const condition = port.getAttribute("data-aion-port-condition") || "success";
56353:       const role = port.getAttribute("data-aion-port-role") || "main";
56354: 
56355:       window.__aionDraggingConnector = {
56356:         from: nodeId,
```

## Actual selected-node render blocks


### pattern `selectedNodeId\s*=\s*window\.__aionWorkflowSelectedNodeId` hits: [29356, 31631, 52007, 55685, 56189, 64133, 79509]
```js
29331:   const mappedNode = getAionUnifiedRealNodeFromModule(module);
29332:   if (!mappedNode) return false;
29333: 
29334:   if (mappedNode.locked === true) {
29335:     safeAionDesktopPatch({
29336:       message: `${mappedNode.title || "This module"} is visible but not wired yet.`,
29337:       messageTone: "info",
29338:     });
29339:     return false;
29340:   }
29341: 
29342:   if (!window.__aionWorkflowGraph) {
29343:     window.__aionWorkflowGraph = {
29344:       workflow_id: createAionWorkflowId(),
29345:       name: "Untitled workflow",
29346:       status: "draft",
29347:       nodes: [],
29348:       edges: [],
29349:     };
29350:   }
29351: 
29352:   const graph = window.__aionWorkflowGraph;
29353:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
29354:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
29355: 
29356:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
29357:   const selectedNode = selectedNodeId
29358:     ? nodes.find((node) => node.id === selectedNodeId)
29359:     : null;
29360: 
29361:   const anchorNode =
29362:     selectedNode ||
29363:     nodes[nodes.length - 1] ||
29364:     { id: null, x: 160, y: 240 };
29365: 
29366:   const safeId = String(mappedNode.config?.action_id || mappedNode.title || "step")
29367:     .replace(/[^a-z0-9_]+/gi, "_")
29368:     .replace(/^_+|_+$/g, "")
29369:     .toLowerCase();
29370: 
29371:   const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
29372:   const isBranchInsert =
29373:     anchorNode?.id &&
29374:     (
29375:       (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
29376:       (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
29377:     );
29378: 
29379:   const routerRoutes =
29380:     typeof getAionWorkflowRouterRoutes === "function"
29381:       ? getAionWorkflowRouterRoutes(anchorNode)
29382:       : [];
29383: 
29384:   const routerRouteIndex = routerRoutes.findIndex(
29385:     (route) => String(route.id).toLowerCase() === pendingBranchCondition,
29386:   );
29387: 
29388:   const branchYOffset =
29389:     typeof isAionWorkflowRouterNode === "function" &&
29390:     isAionWorkflowRouterNode(anchorNode) &&
29391:     routerRouteIndex >= 0
29392:       ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
29393:       : pendingBranchCondition === "false" || pendingBranchCondition === "else"
29394:         ? 170
29395:         : pendingBranchCondition === "true"
29396:           ? -130
29397:           : 0;
29398: 
29399:   const mergePlacement = getAionWorkflowMergePlacement(nodes, anchorNode);
29400: 
29401:   const newNode = {
29402:     id: `node_${safeId}_${Date.now()}`,
29403:     ...mappedNode,
29404:     x: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.x : Number(anchorNode.x || 160) + (isBranchInsert ? 320 : 275),
29405:     y: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.y : Number(anchorNode.y || 240) + branchYOffset,
29406:   };
29407: 
29408:   const newIsMerge = isAionWorkflowNewMergeNode(newNode);
29409: 
29410:   const anchorIndex = anchorNode?.id
29411:     ? nodes.findIndex((node) => node.id === anchorNode.id)
```
```js
31606:   if (window.__aionWorkflowArchitectCanvasMode === true) {
31607:     return renderAionArchitectCanvasMode();
31608:   }
31609: 
31610:   maybeLoadAionWorkflowFromBusinessContainerOnce();
31611:   const graph =
31612:     typeof getAionWorkflowRenderGraphO12C === "function"
31613:       ? getAionWorkflowRenderGraphO12C()
31614:       : getAionWorkflowDraftState();
31615: 
31616:   window["__aionWorkflowGraph"] = graph;
31617: 
31618:   if (typeof syncAionGoalSheetGraphIntoWorkflowStateO12C === "function" && isAionGoalSheetGraphO12C?.(graph)) {
31619:     syncAionGoalSheetGraphIntoWorkflowStateO12C(graph);
31620:   }
31621: 
31622:   compileAndAttachAionWorkflowGlyph(graph);
31623: 
31624:   if (typeof fitAionGoalSheetWorkflowOnceO12C === "function" && isAionGoalSheetGraphO12C?.(graph)) {
31625:     fitAionGoalSheetWorkflowOnceO12C(graph);
31626:   }
31627: 
31628:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
31629:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
31630: 
31631:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
31632:   let selectedNode =
31633:     nodes.find((node) => node.id === selectedNodeId) ||
31634: 
31635:     nodes[nodes.length - 1] ||
31636:     nodes[0] ||
31637:     null;
31638: 
31639:   const firstStepPickerHtml = `
31640:     <div class="aion-first-step-picker">
31641:       <div class="aion-inspector-head">
31642:         <div>
31643:           <div class="eyebrow">Start workflow</div>
31644:           <h3>What starts this workflow?</h3>
31645:           <p>Choose a trigger, app event, browser skill, or AI starter.</p>
31646:         </div>
31647:       </div>
31648: 
31649:       <div class="aion-workflow-search">⌕ Search triggers, apps, or modules...</div>
31650: 
31651:       <div class="aion-picker-section">
31652:         <div class="aion-picker-section-title">Recommended</div>
31653: 
31654:         <button class="aion-picker-row" data-aion-workflow-create-trigger="manual" type="button">
31655:           <span class="aion-picker-icon">◎</span>
31656:           <span>
31657:             <strong>Trigger manually</strong>
31658:             <small>Start the workflow when the user clicks Run once.</small>
31659:           </span>
31660:           <em>Active</em>
31661:         </button>
31662: 
31663:         <button class="aion-picker-row" data-aion-workflow-create-trigger="gmail_new_email" type="button">
31664:           <span class="aion-picker-icon">✉</span>
31665:           <span>
31666:             <strong>Gmail new email</strong>
31667:             <small>Start when a new Gmail email arrives. Connection required later.</small>
31668:           </span>
31669:           <em>Mock</em>
31670:         </button>
31671: 
31672:         <button class="aion-picker-row" data-aion-workflow-create-trigger="schedule" type="button">
31673:           <span class="aion-picker-icon">◷</span>
31674:           <span>
31675:             <strong>Schedule</strong>
31676:             <small>Run every hour, day, week, or custom interval.</small>
31677:           </span>
31678:           <em>Draft</em>
31679:         </button>
31680: 
31681:         <button class="aion-picker-row" data-aion-workflow-create-trigger="webhook" type="button">
31682:           <span class="aion-picker-icon">⑂</span>
31683:           <span>
31684:             <strong>Webhook / API call</strong>
31685:             <small>Start when another system sends Aion an HTTP request.</small>
31686:           </span>
```
```js
51982:           message: "This action is listed for the roadmap but is not active yet.",
51983:           messageTone: "info",
51984:         });
51985:         requestRender();
51986:         return;
51987:       }
51988: 
51989:       if (!window.__aionWorkflowGraph) {
51990:         window.__aionWorkflowGraph = {
51991:           workflow_id: createAionWorkflowId(),
51992:           name: "Untitled workflow",
51993:           status: "draft",
51994:           nodes: [],
51995:           edges: [],
51996:         };
51997:       }
51998: 
51999:       const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
52000:         ? window.__aionWorkflowGraph.nodes
52001:         : [];
52002: 
52003:       const edges = Array.isArray(window.__aionWorkflowGraph.edges)
52004:         ? window.__aionWorkflowGraph.edges
52005:         : [];
52006: 
52007:       const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
52008:       const selectedNode = selectedNodeId
52009:         ? nodes.find((node) => node.id === selectedNodeId)
52010:         : null;
52011: 
52012:       const anchorNode =
52013:         selectedNode ||
52014:         nodes[nodes.length - 1] ||
52015:         { id: null, x: 160, y: 240 };
52016: 
52017:       const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
52018:       const isBranchInsert =
52019:         anchorNode?.id &&
52020:         (
52021:           (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
52022:           (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
52023:         );
52024: 
52025:       const routerRoutes =
52026:         typeof getAionWorkflowRouterRoutes === "function"
52027:           ? getAionWorkflowRouterRoutes(anchorNode)
52028:           : [];
52029: 
52030:       const routerRouteIndex = routerRoutes.findIndex(
52031:         (route) => String(route.id).toLowerCase() === pendingBranchCondition,
52032:       );
52033: 
52034:       const branchYOffset =
52035:         typeof isAionWorkflowRouterNode === "function" &&
52036:         isAionWorkflowRouterNode(anchorNode) &&
52037:         routerRouteIndex >= 0
52038:           ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
52039:           : pendingBranchCondition === "false" || pendingBranchCondition === "else"
52040:             ? 170
52041:             : pendingBranchCondition === "true"
52042:               ? -130
52043:               : 0;
52044: 
52045:       const newNode = {
52046:         id: `node_${actionType}_${Date.now()}`,
52047:         ...actionMap[actionType],
52048:         x: Number(anchorNode.x || 160) + (isBranchInsert ? 320 : 275),
52049:         y: Number(anchorNode.y || 240) + branchYOffset,
52050:       };
52051: 
52052:       const newIsMerge = isAionWorkflowNewMergeNode(newNode);
52053: 
52054:       const anchorIndex = anchorNode?.id
52055:         ? nodes.findIndex((node) => node.id === anchorNode.id)
52056:         : -1;
52057: 
52058:       const nextNodes =
52059:         anchorIndex >= 0
52060:           ? [
52061:               ...nodes.slice(0, anchorIndex + 1),
52062:               newNode,
```
```js
55660:       message: "This module is visible but not wired to a working node yet.",
55661:       messageTone: "info",
55662:     });
55663:     requestRender();
55664:     return false;
55665:   }
55666: 
55667:   if (!window.__aionWorkflowGraph) {
55668:     window.__aionWorkflowGraph = {
55669:       workflow_id: createAionWorkflowId(),
55670:       name: "Untitled workflow",
55671:       status: "draft",
55672:       nodes: [],
55673:       edges: [],
55674:     };
55675:   }
55676: 
55677:   const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
55678:     ? window.__aionWorkflowGraph.nodes
55679:     : [];
55680: 
55681:   const edges = Array.isArray(window.__aionWorkflowGraph.edges)
55682:     ? window.__aionWorkflowGraph.edges
55683:     : [];
55684: 
55685:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
55686:   const selectedNode = selectedNodeId
55687:     ? nodes.find((node) => node.id === selectedNodeId)
55688:     : null;
55689: 
55690:   const anchorNode =
55691:     selectedNode ||
55692:     nodes[nodes.length - 1] ||
55693:     { id: null, x: 160, y: 240 };
55694: 
55695:   const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
55696:   const isBranchInsert =
55697:     anchorNode?.id &&
55698:     (
55699:       (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
55700:       (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
55701:     );
55702: 
55703:   const routerRoutes =
55704:     typeof getAionWorkflowRouterRoutes === "function"
55705:       ? getAionWorkflowRouterRoutes(anchorNode)
55706:       : [];
55707: 
55708:   const routerRouteIndex = routerRoutes.findIndex(
55709:     (route) => String(route.id).toLowerCase() === pendingBranchCondition,
55710:   );
55711: 
55712:   const branchYOffset =
55713:     typeof isAionWorkflowRouterNode === "function" &&
55714:     isAionWorkflowRouterNode(anchorNode) &&
55715:     routerRouteIndex >= 0
55716:       ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
55717:       : pendingBranchCondition === "false" || pendingBranchCondition === "else"
55718:         ? 170
55719:         : pendingBranchCondition === "true"
55720:           ? -130
55721:           : 0;
55722: 
55723:   const newNode = {
55724:     id: `node_${actionType}_${Date.now()}`,
55725:     ...base,
55726:     action_id: module.action_id || actionType,
55727:     module_id: module.id || "",
55728:     module_group: module.group || "",
55729:     module_kind: module.kind || "",
55730:     x: Number(anchorNode.x || 160) + 320,
55731:     y: Number(anchorNode.y || 240) + branchYOffset,
55732:   };
55733: 
55734:   const newIsMerge = isAionWorkflowNewMergeNode(newNode);
55735: 
55736:   const anchorIndex = anchorNode?.id
55737:     ? nodes.findIndex((node) => node.id === anchorNode.id)
55738:     : -1;
55739: 
55740:   const nextNodes =
```
```js
56164:           message: "This action is listed for the roadmap but is not active yet.",
56165:           messageTone: "info",
56166:         });
56167:         requestRender();
56168:         return;
56169:       }
56170: 
56171:       if (!window.__aionWorkflowGraph) {
56172:         window.__aionWorkflowGraph = {
56173:           workflow_id: createAionWorkflowId(),
56174:           name: "Untitled workflow",
56175:           status: "draft",
56176:           nodes: [],
56177:           edges: [],
56178:         };
56179:       }
56180: 
56181:       const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
56182:         ? window.__aionWorkflowGraph.nodes
56183:         : [];
56184: 
56185:       const edges = Array.isArray(window.__aionWorkflowGraph.edges)
56186:         ? window.__aionWorkflowGraph.edges
56187:         : [];
56188: 
56189:       const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
56190:       const selectedNode = selectedNodeId
56191:         ? nodes.find((node) => node.id === selectedNodeId)
56192:         : null;
56193: 
56194:       const anchorNode =
56195:         selectedNode ||
56196:         nodes[nodes.length - 1] ||
56197:         { id: null, x: 160, y: 240 };
56198: 
56199:       const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
56200:       const isBranchInsert =
56201:         anchorNode?.id &&
56202:         (
56203:           (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
56204:           (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
56205:         );
56206: 
56207:       const routerRoutes =
56208:         typeof getAionWorkflowRouterRoutes === "function"
56209:           ? getAionWorkflowRouterRoutes(anchorNode)
56210:           : [];
56211: 
56212:       const routerRouteIndex = routerRoutes.findIndex(
56213:         (route) => String(route.id).toLowerCase() === pendingBranchCondition,
56214:       );
56215: 
56216:       const branchYOffset =
56217:         typeof isAionWorkflowRouterNode === "function" &&
56218:         isAionWorkflowRouterNode(anchorNode) &&
56219:         routerRouteIndex >= 0
56220:           ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
56221:           : pendingBranchCondition === "false" || pendingBranchCondition === "else"
56222:             ? 170
56223:             : pendingBranchCondition === "true"
56224:               ? -130
56225:               : 0;
56226: 
56227:       const newNode = {
56228:         id: `node_${actionType}_${Date.now()}`,
56229:         ...actionMap[actionType],
56230:         x: Number(anchorNode.x || 160) + (isBranchInsert ? 320 : 275),
56231:         y: Number(anchorNode.y || 240) + branchYOffset,
56232:       };
56233: 
56234:       const newIsMerge = isAionWorkflowNewMergeNode(newNode);
56235: 
56236:       const anchorIndex = anchorNode?.id
56237:         ? nodes.findIndex((node) => node.id === anchorNode.id)
56238:         : -1;
56239: 
56240:       const nextNodes =
56241:         anchorIndex >= 0
56242:           ? [
56243:               ...nodes.slice(0, anchorIndex + 1),
56244:               newNode,
```
```js
64108:       nodeEl.style.position = nodeEl.style.position || "relative";
64109: 
64110:       const toolbar = document.createElement("div");
64111:       toolbar.className = "aion-main-node-mini-toolbar";
64112:       toolbar.innerHTML = `
64113:         <span role="button" tabindex="0" title="Step settings" data-aion-main-node-toolbar="settings" data-aion-main-node-toolbar-node="${nodeId}">⚙</span>
64114:         <span role="button" tabindex="0" title="Configure logic / variables" data-aion-main-node-toolbar="logic" data-aion-main-node-toolbar-node="${nodeId}">⑂</span>
64115:         <span role="button" tabindex="0" title="Remove step" data-aion-main-node-toolbar="delete" data-aion-main-node-toolbar-node="${nodeId}">×</span>
64116: 
64117:       `;
64118: 
64119:       nodeEl.appendChild(toolbar);
64120:     });
64121: 
64122:     injectLogicTabIntoNodeEditor();
64123:   }
64124: 
64125:   function injectLogicTabIntoNodeEditor() {
64126:     const editor =
64127:       document.querySelector(".aion-workflow-node-editor") ||
64128:       document.querySelector(".aion-workflow-execution-panel") ||
64129:       document.querySelector("[data-aion-workflow-node-editor='true']");
64130: 
64131:     if (!editor || editor.querySelector(".aion-main-node-editor-logic-tab")) return;
64132: 
64133:     const selectedNodeId = window.__aionWorkflowSelectedNodeId || "";
64134:     if (!selectedNodeId) return;
64135: 
64136:     const closeButton =
64137:       editor.querySelector("[data-aion-workflow-node-editor-close='true']") ||
64138:       editor.querySelector("[data-aion-dry-run-close='true']") ||
64139:       editor.querySelector("button");
64140: 
64141:     const tab = document.createElement("button");
64142:     tab.type = "button";
64143:     tab.className = "aion-main-node-editor-logic-tab";
64144:     tab.setAttribute("data-aion-main-node-toolbar", "logic");
64145:     tab.setAttribute("data-aion-main-node-toolbar-node", selectedNodeId);
64146:     tab.textContent = "Logic / Variables";
64147: 
64148:     if (closeButton?.parentElement) {
64149:       closeButton.parentElement.insertBefore(tab, closeButton);
64150:     } else {
64151:       editor.insertBefore(tab, editor.firstChild);
64152:     }
64153:   }
64154: 
64155:   function ensureAdvancedModalMounted() {
64156:     if (window.__aionArchitectAdvancedConfigOpen !== true) return;
64157:     if (document.querySelector("[data-aion-architect-advanced-backdrop='true']")) return;
64158:     if (typeof renderAionArchitectAdvancedConfigModal !== "function") return;
64159: 
64160:     const html = renderAionArchitectAdvancedConfigModal();
64161:     if (!html) return;
64162: 
64163:     const host = document.createElement("div");
64164:     host.setAttribute("data-aion-main-advanced-modal-host", "true");
64165:     host.innerHTML = html;
64166:     document.body.appendChild(host);
64167:   }
64168: 
64169:   function postRenderPatch() {
64170:     forceBlankStarterIfNeeded();
64171:     injectMiniToolbars();
64172:     ensureAdvancedModalMounted();
64173:   }
64174: 
64175:   document.addEventListener(
64176:     "pointerdown",
64177:     (event) => {
64178:       const port = event.target.closest?.("[data-aion-port-node-id]");
64179:       if (!port) return;
64180: 
64181:       const direction = port.getAttribute("data-aion-port-direction");
64182:       if (direction !== "output") return;
64183: 
64184:       event.preventDefault();
64185:       event.stopPropagation();
64186:       event.stopImmediatePropagation();
64187: 
64188:       const nodeId = port.getAttribute("data-aion-port-node-id");
```

### pattern `selectedNode\s*=` hits: [29357, 31632, 52008, 55686, 56190, 80320, 92710]
```js
29332:   if (!mappedNode) return false;
29333: 
29334:   if (mappedNode.locked === true) {
29335:     safeAionDesktopPatch({
29336:       message: `${mappedNode.title || "This module"} is visible but not wired yet.`,
29337:       messageTone: "info",
29338:     });
29339:     return false;
29340:   }
29341: 
29342:   if (!window.__aionWorkflowGraph) {
29343:     window.__aionWorkflowGraph = {
29344:       workflow_id: createAionWorkflowId(),
29345:       name: "Untitled workflow",
29346:       status: "draft",
29347:       nodes: [],
29348:       edges: [],
29349:     };
29350:   }
29351: 
29352:   const graph = window.__aionWorkflowGraph;
29353:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
29354:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
29355: 
29356:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
29357:   const selectedNode = selectedNodeId
29358:     ? nodes.find((node) => node.id === selectedNodeId)
29359:     : null;
29360: 
29361:   const anchorNode =
29362:     selectedNode ||
29363:     nodes[nodes.length - 1] ||
29364:     { id: null, x: 160, y: 240 };
29365: 
29366:   const safeId = String(mappedNode.config?.action_id || mappedNode.title || "step")
29367:     .replace(/[^a-z0-9_]+/gi, "_")
29368:     .replace(/^_+|_+$/g, "")
29369:     .toLowerCase();
29370: 
29371:   const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
29372:   const isBranchInsert =
29373:     anchorNode?.id &&
29374:     (
29375:       (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
29376:       (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
29377:     );
29378: 
29379:   const routerRoutes =
29380:     typeof getAionWorkflowRouterRoutes === "function"
29381:       ? getAionWorkflowRouterRoutes(anchorNode)
29382:       : [];
29383: 
29384:   const routerRouteIndex = routerRoutes.findIndex(
29385:     (route) => String(route.id).toLowerCase() === pendingBranchCondition,
29386:   );
29387: 
29388:   const branchYOffset =
29389:     typeof isAionWorkflowRouterNode === "function" &&
29390:     isAionWorkflowRouterNode(anchorNode) &&
29391:     routerRouteIndex >= 0
29392:       ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
29393:       : pendingBranchCondition === "false" || pendingBranchCondition === "else"
29394:         ? 170
29395:         : pendingBranchCondition === "true"
29396:           ? -130
29397:           : 0;
29398: 
29399:   const mergePlacement = getAionWorkflowMergePlacement(nodes, anchorNode);
29400: 
29401:   const newNode = {
29402:     id: `node_${safeId}_${Date.now()}`,
29403:     ...mappedNode,
29404:     x: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.x : Number(anchorNode.x || 160) + (isBranchInsert ? 320 : 275),
29405:     y: isAionWorkflowNewMergeNode(mappedNode) ? mergePlacement.y : Number(anchorNode.y || 240) + branchYOffset,
29406:   };
29407: 
29408:   const newIsMerge = isAionWorkflowNewMergeNode(newNode);
29409: 
29410:   const anchorIndex = anchorNode?.id
29411:     ? nodes.findIndex((node) => node.id === anchorNode.id)
29412:     : -1;
```
```js
31607:     return renderAionArchitectCanvasMode();
31608:   }
31609: 
31610:   maybeLoadAionWorkflowFromBusinessContainerOnce();
31611:   const graph =
31612:     typeof getAionWorkflowRenderGraphO12C === "function"
31613:       ? getAionWorkflowRenderGraphO12C()
31614:       : getAionWorkflowDraftState();
31615: 
31616:   window["__aionWorkflowGraph"] = graph;
31617: 
31618:   if (typeof syncAionGoalSheetGraphIntoWorkflowStateO12C === "function" && isAionGoalSheetGraphO12C?.(graph)) {
31619:     syncAionGoalSheetGraphIntoWorkflowStateO12C(graph);
31620:   }
31621: 
31622:   compileAndAttachAionWorkflowGlyph(graph);
31623: 
31624:   if (typeof fitAionGoalSheetWorkflowOnceO12C === "function" && isAionGoalSheetGraphO12C?.(graph)) {
31625:     fitAionGoalSheetWorkflowOnceO12C(graph);
31626:   }
31627: 
31628:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
31629:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
31630: 
31631:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
31632:   let selectedNode =
31633:     nodes.find((node) => node.id === selectedNodeId) ||
31634: 
31635:     nodes[nodes.length - 1] ||
31636:     nodes[0] ||
31637:     null;
31638: 
31639:   const firstStepPickerHtml = `
31640:     <div class="aion-first-step-picker">
31641:       <div class="aion-inspector-head">
31642:         <div>
31643:           <div class="eyebrow">Start workflow</div>
31644:           <h3>What starts this workflow?</h3>
31645:           <p>Choose a trigger, app event, browser skill, or AI starter.</p>
31646:         </div>
31647:       </div>
31648: 
31649:       <div class="aion-workflow-search">⌕ Search triggers, apps, or modules...</div>
31650: 
31651:       <div class="aion-picker-section">
31652:         <div class="aion-picker-section-title">Recommended</div>
31653: 
31654:         <button class="aion-picker-row" data-aion-workflow-create-trigger="manual" type="button">
31655:           <span class="aion-picker-icon">◎</span>
31656:           <span>
31657:             <strong>Trigger manually</strong>
31658:             <small>Start the workflow when the user clicks Run once.</small>
31659:           </span>
31660:           <em>Active</em>
31661:         </button>
31662: 
31663:         <button class="aion-picker-row" data-aion-workflow-create-trigger="gmail_new_email" type="button">
31664:           <span class="aion-picker-icon">✉</span>
31665:           <span>
31666:             <strong>Gmail new email</strong>
31667:             <small>Start when a new Gmail email arrives. Connection required later.</small>
31668:           </span>
31669:           <em>Mock</em>
31670:         </button>
31671: 
31672:         <button class="aion-picker-row" data-aion-workflow-create-trigger="schedule" type="button">
31673:           <span class="aion-picker-icon">◷</span>
31674:           <span>
31675:             <strong>Schedule</strong>
31676:             <small>Run every hour, day, week, or custom interval.</small>
31677:           </span>
31678:           <em>Draft</em>
31679:         </button>
31680: 
31681:         <button class="aion-picker-row" data-aion-workflow-create-trigger="webhook" type="button">
31682:           <span class="aion-picker-icon">⑂</span>
31683:           <span>
31684:             <strong>Webhook / API call</strong>
31685:             <small>Start when another system sends Aion an HTTP request.</small>
31686:           </span>
31687:           <em>Draft</em>
```
```js
51983:           messageTone: "info",
51984:         });
51985:         requestRender();
51986:         return;
51987:       }
51988: 
51989:       if (!window.__aionWorkflowGraph) {
51990:         window.__aionWorkflowGraph = {
51991:           workflow_id: createAionWorkflowId(),
51992:           name: "Untitled workflow",
51993:           status: "draft",
51994:           nodes: [],
51995:           edges: [],
51996:         };
51997:       }
51998: 
51999:       const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
52000:         ? window.__aionWorkflowGraph.nodes
52001:         : [];
52002: 
52003:       const edges = Array.isArray(window.__aionWorkflowGraph.edges)
52004:         ? window.__aionWorkflowGraph.edges
52005:         : [];
52006: 
52007:       const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
52008:       const selectedNode = selectedNodeId
52009:         ? nodes.find((node) => node.id === selectedNodeId)
52010:         : null;
52011: 
52012:       const anchorNode =
52013:         selectedNode ||
52014:         nodes[nodes.length - 1] ||
52015:         { id: null, x: 160, y: 240 };
52016: 
52017:       const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
52018:       const isBranchInsert =
52019:         anchorNode?.id &&
52020:         (
52021:           (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
52022:           (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
52023:         );
52024: 
52025:       const routerRoutes =
52026:         typeof getAionWorkflowRouterRoutes === "function"
52027:           ? getAionWorkflowRouterRoutes(anchorNode)
52028:           : [];
52029: 
52030:       const routerRouteIndex = routerRoutes.findIndex(
52031:         (route) => String(route.id).toLowerCase() === pendingBranchCondition,
52032:       );
52033: 
52034:       const branchYOffset =
52035:         typeof isAionWorkflowRouterNode === "function" &&
52036:         isAionWorkflowRouterNode(anchorNode) &&
52037:         routerRouteIndex >= 0
52038:           ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
52039:           : pendingBranchCondition === "false" || pendingBranchCondition === "else"
52040:             ? 170
52041:             : pendingBranchCondition === "true"
52042:               ? -130
52043:               : 0;
52044: 
52045:       const newNode = {
52046:         id: `node_${actionType}_${Date.now()}`,
52047:         ...actionMap[actionType],
52048:         x: Number(anchorNode.x || 160) + (isBranchInsert ? 320 : 275),
52049:         y: Number(anchorNode.y || 240) + branchYOffset,
52050:       };
52051: 
52052:       const newIsMerge = isAionWorkflowNewMergeNode(newNode);
52053: 
52054:       const anchorIndex = anchorNode?.id
52055:         ? nodes.findIndex((node) => node.id === anchorNode.id)
52056:         : -1;
52057: 
52058:       const nextNodes =
52059:         anchorIndex >= 0
52060:           ? [
52061:               ...nodes.slice(0, anchorIndex + 1),
52062:               newNode,
52063:               ...nodes.slice(anchorIndex + 1),
```
```js
55661:       messageTone: "info",
55662:     });
55663:     requestRender();
55664:     return false;
55665:   }
55666: 
55667:   if (!window.__aionWorkflowGraph) {
55668:     window.__aionWorkflowGraph = {
55669:       workflow_id: createAionWorkflowId(),
55670:       name: "Untitled workflow",
55671:       status: "draft",
55672:       nodes: [],
55673:       edges: [],
55674:     };
55675:   }
55676: 
55677:   const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
55678:     ? window.__aionWorkflowGraph.nodes
55679:     : [];
55680: 
55681:   const edges = Array.isArray(window.__aionWorkflowGraph.edges)
55682:     ? window.__aionWorkflowGraph.edges
55683:     : [];
55684: 
55685:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
55686:   const selectedNode = selectedNodeId
55687:     ? nodes.find((node) => node.id === selectedNodeId)
55688:     : null;
55689: 
55690:   const anchorNode =
55691:     selectedNode ||
55692:     nodes[nodes.length - 1] ||
55693:     { id: null, x: 160, y: 240 };
55694: 
55695:   const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
55696:   const isBranchInsert =
55697:     anchorNode?.id &&
55698:     (
55699:       (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
55700:       (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
55701:     );
55702: 
55703:   const routerRoutes =
55704:     typeof getAionWorkflowRouterRoutes === "function"
55705:       ? getAionWorkflowRouterRoutes(anchorNode)
55706:       : [];
55707: 
55708:   const routerRouteIndex = routerRoutes.findIndex(
55709:     (route) => String(route.id).toLowerCase() === pendingBranchCondition,
55710:   );
55711: 
55712:   const branchYOffset =
55713:     typeof isAionWorkflowRouterNode === "function" &&
55714:     isAionWorkflowRouterNode(anchorNode) &&
55715:     routerRouteIndex >= 0
55716:       ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
55717:       : pendingBranchCondition === "false" || pendingBranchCondition === "else"
55718:         ? 170
55719:         : pendingBranchCondition === "true"
55720:           ? -130
55721:           : 0;
55722: 
55723:   const newNode = {
55724:     id: `node_${actionType}_${Date.now()}`,
55725:     ...base,
55726:     action_id: module.action_id || actionType,
55727:     module_id: module.id || "",
55728:     module_group: module.group || "",
55729:     module_kind: module.kind || "",
55730:     x: Number(anchorNode.x || 160) + 320,
55731:     y: Number(anchorNode.y || 240) + branchYOffset,
55732:   };
55733: 
55734:   const newIsMerge = isAionWorkflowNewMergeNode(newNode);
55735: 
55736:   const anchorIndex = anchorNode?.id
55737:     ? nodes.findIndex((node) => node.id === anchorNode.id)
55738:     : -1;
55739: 
55740:   const nextNodes =
55741:     anchorIndex >= 0
```
```js
56165:           messageTone: "info",
56166:         });
56167:         requestRender();
56168:         return;
56169:       }
56170: 
56171:       if (!window.__aionWorkflowGraph) {
56172:         window.__aionWorkflowGraph = {
56173:           workflow_id: createAionWorkflowId(),
56174:           name: "Untitled workflow",
56175:           status: "draft",
56176:           nodes: [],
56177:           edges: [],
56178:         };
56179:       }
56180: 
56181:       const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
56182:         ? window.__aionWorkflowGraph.nodes
56183:         : [];
56184: 
56185:       const edges = Array.isArray(window.__aionWorkflowGraph.edges)
56186:         ? window.__aionWorkflowGraph.edges
56187:         : [];
56188: 
56189:       const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
56190:       const selectedNode = selectedNodeId
56191:         ? nodes.find((node) => node.id === selectedNodeId)
56192:         : null;
56193: 
56194:       const anchorNode =
56195:         selectedNode ||
56196:         nodes[nodes.length - 1] ||
56197:         { id: null, x: 160, y: 240 };
56198: 
56199:       const pendingBranchCondition = String(window.__aionWorkflowPendingBranchCondition || "").toLowerCase();
56200:       const isBranchInsert =
56201:         anchorNode?.id &&
56202:         (
56203:           (typeof isAionWorkflowBranchNode === "function" && isAionWorkflowBranchNode(anchorNode)) ||
56204:           (typeof isAionWorkflowRouterNode === "function" && isAionWorkflowRouterNode(anchorNode))
56205:         );
56206: 
56207:       const routerRoutes =
56208:         typeof getAionWorkflowRouterRoutes === "function"
56209:           ? getAionWorkflowRouterRoutes(anchorNode)
56210:           : [];
56211: 
56212:       const routerRouteIndex = routerRoutes.findIndex(
56213:         (route) => String(route.id).toLowerCase() === pendingBranchCondition,
56214:       );
56215: 
56216:       const branchYOffset =
56217:         typeof isAionWorkflowRouterNode === "function" &&
56218:         isAionWorkflowRouterNode(anchorNode) &&
56219:         routerRouteIndex >= 0
56220:           ? getAionWorkflowRouterRouteOffset(routerRouteIndex, routerRoutes.length)
56221:           : pendingBranchCondition === "false" || pendingBranchCondition === "else"
56222:             ? 170
56223:             : pendingBranchCondition === "true"
56224:               ? -130
56225:               : 0;
56226: 
56227:       const newNode = {
56228:         id: `node_${actionType}_${Date.now()}`,
56229:         ...actionMap[actionType],
56230:         x: Number(anchorNode.x || 160) + (isBranchInsert ? 320 : 275),
56231:         y: Number(anchorNode.y || 240) + branchYOffset,
56232:       };
56233: 
56234:       const newIsMerge = isAionWorkflowNewMergeNode(newNode);
56235: 
56236:       const anchorIndex = anchorNode?.id
56237:         ? nodes.findIndex((node) => node.id === anchorNode.id)
56238:         : -1;
56239: 
56240:       const nextNodes =
56241:         anchorIndex >= 0
56242:           ? [
56243:               ...nodes.slice(0, anchorIndex + 1),
56244:               newNode,
56245:               ...nodes.slice(anchorIndex + 1),
```
```js
80295:     body.aion-workflow-dark-mode .aion-master-glyph-connection-row small {
80296:       color: #cbd5e1;
80297:     }
80298:   `;
80299:   document.head.appendChild(style);
80300: 
80301:   document.addEventListener("click", (event) => {
80302:     /*
80303:      * SOURCE FIX V16:
80304:      * Ignore clicks inside canonical call_workflow_glyph inspector so details
80305:      * accordions do not trigger legacy connection preview/confirm panels.
80306:      */
80307:     if (event.target?.closest?.("[data-aion-call-workflow-glyph-contract-inspector-v3='true']")) {
80308:       return;
80309:     }
80310: 
80311:     const close = event.target.closest?.("[data-aion-master-glyph-connection-preview-close='true']");
80312:     if (close) {
80313:       event.preventDefault();
80314:       event.stopPropagation();
80315:       window.__aionMasterGlyphConnectionPreviewOpen = false;
80316:       removePreview();
80317:       return;
80318:     }
80319: 
80320:     const selectedNode = event.target.closest?.("[data-aion-workflow-node-id]");
80321:     if (selectedNode) {
80322:       window.setTimeout(() => {
80323:         const node = getSelectedNode();
80324:         if (isStagedWorkflowGlyphNode(node)) {
80325:           window.__aionMasterGlyphSelectedStagedNodeId = String(node.id || "");
80326:           window.__aionMasterGlyphConnectionPreviewOpen = true;
80327:           syncPreview();
80328:         }
80329:       }, 100);
80330:     }
80331:   }, true);
80332: 
80333:   window.addEventListener("aion:workflow-rendered", syncPreview);
80334:   window.addEventListener("aion:workflow-selection-changed", syncPreview);
80335: 
80336:   window.renderAionMasterGlyphConnectionPreview = renderAionMasterGlyphConnectionPreview;
80337:   window.__syncAionMasterGlyphConnectionPreview = syncPreview;
80338:   window.__aionMasterGlyphConnectionPreviewOpen =
80339:     window.__aionMasterGlyphConnectionPreviewOpen || false;
80340: 
80341:   console.log("[AION] Workflow Glyph connection preview installed");
80342: })();
80343: 
80344: 
80345: })();
80346: 
80347: /* AION PATCH: Workflow Glyph staged connection confirm
80348:    Purpose:
80349:    - Allow explicit user confirmation of a previewed glyph connection.
80350:    - Create draft-only canvas edges.
80351:    - Do not execute workflows.
80352:    - Do not call child glyphs.
80353:    - Do not mutate saved glyphs.
80354:    - Do not perform external writes.
80355: */
80356: (function installAionMasterGlyphConnectionStagePatch() {
80357:   const PATCH_ID = "aion-master-glyph-connection-stage-v5";
80358: 
80359:   if (window.__aionMasterGlyphConnectionStagePatchInstalled === true) return;
80360:   window.__aionMasterGlyphConnectionStagePatchInstalled = true;
80361: 
80362:   function esc(value) {
80363:     if (typeof escapeHtml === "function") return escapeHtml(value);
80364:     return String(value ?? "")
80365:       .replaceAll("&", "&amp;")
80366:       .replaceAll("<", "&lt;")
80367:       .replaceAll(">", "&gt;")
80368:       .replaceAll('"', "&quot;")
80369:       .replaceAll("'", "&#039;");
80370:   }
80371: 
80372:   function getGraph() {
80373:     if (typeof getAionWorkflowDraftState === "function") {
80374:       try {
80375:         const graph = getAionWorkflowDraftState();
```

### pattern `renderWorkflowArchitectNodeEditorModal` hits: [30075, 33246]
```js
30050:         </div>
30051: 
30052:         <div class="aion-architect-topbar-actions">
30053:           <button type="button" class="secondary-btn" data-workflow-architect-close-canvas-mode="true">Back to canvas</button>
30054:           <button type="button" class="secondary-btn" data-aion-architect-build-mode="describe">Describe workflow</button>
30055:           <button type="button" class="primary-btn" data-workflow-architect-build-review="true">Build review</button>
30056:           <button type="button" class="secondary-btn" data-workflow-architect-load-valid-review="true" disabled>Load to canvas</button>
30057:           <span class="aion-architect-safety-badge" title="Execution: dry-run only. Live send disabled. External writes approval gated. Save requires valid dry-run + confirmation.">
30058:             🔒 Safety locked
30059:           </span>
30060:         </div>
30061:       </div>
30062: 
30063:       <main class="aion-architect-full-canvas">
30064:         ${nodeCanvas}
30065:       </main>
30066: 
30067:       ${settingsModal}
30068:       ${renderAionArchitectModulePicker()}
30069:       ${renderAionArchitectAdvancedConfigModal()}
30070:     </section>
30071:   `;
30072: }
30073: 
30074: 
30075: function renderWorkflowArchitectNodeEditorModal() {
30076:   if (window.__aionWorkflowArchitectCanvasMode === true) {
30077:     return renderAionArchitectCanvasMode();
30078:   }
30079: 
30080:   return "";
30081: }
30082: 
30083: 
30084: 
30085: 
30086: function getAionArchitectUserStepsPayload() {
30087:   const steps =
30088:     Array.isArray(ensureAionArchitectHasOneBlankStep())
30089:       ? ensureAionArchitectHasOneBlankStep()
30090:       : Array.isArray(window.__aionWorkflowArchitectGuidedSteps?.steps)
30091:         ? window.__aionWorkflowArchitectGuidedSteps.steps
30092:         : [];
30093: 
30094:   return {
30095:     user_steps: steps.map((step, index) => ({
30096:       step_id: step.id || `step_${index + 1}`,
30097:       order: index + 1,
30098:       app: step.app || step.connector || "aion",
30099:       connector: step.connector || step.app || "aion",
30100:       action_id: step.action_id || "",
30101:       action_label: step.action_label || step.action || "",
30102:       action: step.action || step.action_label || "",
30103:       source: step.source || "",
30104:       fields: step.fields || "",
30105:       outputs: step.outputs || "",
30106:       approval_requirement: step.approval_requirement || "auto",
30107:       requires_approval:
30108:         step.approval_requirement === "required" ||
30109:         step.approval_requirement === "before_external_write",
30110:       dry_run: true,
30111:     })),
30112:   };
30113: }
30114: 
30115: 
30116: 
30117: function getAionArchitectCapabilityManifest() {
30118:   return {
30119:     version: "aion_workflow_architect_capability_manifest_v1",
30120:     purpose:
30121:       "Tool/function catalogue available to the AI Workflow Architect when generating workflows from plain English or visual step-builder nodes.",
30122:     safety_contract: {
30123:       execution: "dry_run_only",
30124:       live_send: "disabled",
30125:       external_writes: "approval_gated",
30126:       canvas_load: "valid_review_required",
30127:       save: "requires_valid_dry_run_plus_confirmation",
30128:     },
30129:     workflow_rule:
30130:       "The AI should translate human workflow intent into safe user_steps using connector, action_id, source, fields, outputs, approval policy, and dry-run policy.",
```
```js
33221:                   class="aion-workflow-picker-drawer"
33222:                   data-aion-workflow-picker-drawer="true"
33223:                 >
33224:                   <button
33225:                     class="aion-workflow-picker-drawer-close"
33226:                     data-aion-workflow-picker-close="true"
33227:                     type="button"
33228:                     title="Close add step panel"
33229:                   >
33230:                     ×
33231:                   </button>
33232:                   ${pickerHtml}
33233:                 </aside>
33234:               `
33235:               : "";
33236:           })()
33237:         }
33238:       </div>
33239:       ${window.AionWorkflowNodeEditor?.renderModal?.({ nodes }) || ""}
33240:       ${renderAionWorkflowDryRunTraceFloatingDock()}
33241:       ${renderAionWorkflowGlyphDebugExecutionPanel()}
33242:       ${renderAionUnifiedCanvasBuilderControls()}
33243:       ${renderAionWorkflowFloatingToolbar()}
33244:       ${typeof renderAionWorkflowDryRunResultPanelFallback === "function" ? renderAionWorkflowDryRunResultPanelFallback() : ""}
33245:       ${typeof renderAionArchitectModulePicker === "function" ? renderAionArchitectModulePicker() : ""}
33246:           ${renderWorkflowArchitectNodeEditorModal()}
33247:     </section>
33248:   `;
33249: }
33250: 
33251: 
33252: function renderBrowserMicroSkillLibrary() {
33253:   const bridge = state.browserDesktopBridge || {};
33254:   const skills = Array.isArray(bridge.skills) ? bridge.skills : [];
33255: 
33256:   if (!skills.length) {
33257:     return "";
33258:   }
33259: 
33260:   return `
33261:     <div class="train-section-panel" style="margin-top:16px;">
33262:       <div class="train-section-head">
33263:         <div>
33264:           <div class="eyebrow">Browser skill library</div>
33265:           <h2>Reusable browser functions</h2>
33266:           <p class="muted" style="margin:6px 0 0;">
33267:             These are short browser workflow recordings saved as contracts.
33268:             They can later be chained into larger operators.
33269:           </p>
33270:         </div>
33271: 
33272:         <span class="badge">${escapeHtml(skills.length)} skill${skills.length === 1 ? "" : "s"}</span>
33273:       </div>
33274: 
33275:       <div class="train-section-body">
33276:         <div style="display:grid; gap:14px;">
33277:           ${skills
33278:             .map((skill, index) => {
33279:               const summary = summariseBrowserSkillContract(skill);
33280:               const steps = Array.isArray(skill.recorded_steps)
33281:                 ? skill.recorded_steps
33282:                 : [];
33283:               const inputs = Array.isArray(skill.inputs) ? skill.inputs : [];
33284:               const outputs = Array.isArray(skill.outputs) ? skill.outputs : [];
33285:               const permissions = skill.permissions || {};
33286:               const approvalGates = skill.approval_gates || {};
33287:               const replay = skill.replay || {};
33288: 
33289:               return `
33290:                 <div class="mini-card train-browser-skill-card" style="display:grid; gap:14px;">
33291:                   <div style="display:flex; justify-content:space-between; gap:10px; align-items:flex-start;">
33292:                     <div>
33293:                       <div class="eyebrow">Browser micro-skill ${escapeHtml(index + 1)}</div>
33294:                       <strong>${escapeHtml(skill.name || "Browser skill")}</strong>
33295:                       <p class="muted" style="margin:6px 0 0;">
33296:                         ${escapeHtml(skill.description || "Reusable browser function.")}
33297:                       </p>
33298:                     </div>
33299: 
33300:                     <div class="badge-row" style="justify-content:flex-end;">
33301:                       <span class="badge">${escapeHtml(skill.status || "draft")}</span>
```

### pattern `openNodeEditor` hits: [64085, 64294, 70568, 70611]
```js
64060:         : window.__aionWorkflowGraph) || {};
64061:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64062:     const node = nodes.find((item) => String(item.id) === String(nodeId));
64063: 
64064:     if (node) {
64065:       window.__aionArchitectSteps = [
64066:         {
64067:           id: node.id,
64068:           app: node.connector || node.type || node.title || "workflow",
64069:           connector: node.connector || node.type || "",
64070:           action_id: node.action_id || node.action || "",
64071:           action_label: node.title || node.action_label || "Configure step",
64072:           subtitle: node.meta || node.subtitle || "",
64073:           fields: node.fields || node.config?.fields || "",
64074:           outputs: node.outputs || node.config?.outputs || "",
64075:           approval_requirement:
64076:             node.approval_requirement ||
64077:             (String(node.status || "").toLowerCase().includes("approval") ? "required" : "auto"),
64078:         },
64079:       ];
64080:     }
64081: 
64082:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64083:   }
64084: 
64085:   function openNodeEditor(nodeId) {
64086:     selectNode(nodeId);
64087: 
64088:     const nodeEl = document.querySelector(
64089:       `[data-aion-workflow-node-id="${window.CSS?.escape ? CSS.escape(nodeId) : nodeId}"]`,
64090:     );
64091: 
64092:     // Let the existing node click/editor behaviour run.
64093:     if (nodeEl) {
64094:       nodeEl.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
64095:       return;
64096:     }
64097: 
64098:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64099:   }
64100: 
64101:   function injectMiniToolbars() {
64102:     document.querySelectorAll("[data-aion-workflow-node-id]").forEach((nodeEl) => {
64103:       if (nodeEl.querySelector(".aion-main-node-mini-toolbar")) return;
64104: 
64105:       const nodeId = nodeEl.getAttribute("data-aion-workflow-node-id");
64106:       if (!nodeId) return;
64107: 
64108:       nodeEl.style.position = nodeEl.style.position || "relative";
64109: 
64110:       const toolbar = document.createElement("div");
64111:       toolbar.className = "aion-main-node-mini-toolbar";
64112:       toolbar.innerHTML = `
64113:         <span role="button" tabindex="0" title="Step settings" data-aion-main-node-toolbar="settings" data-aion-main-node-toolbar-node="${nodeId}">⚙</span>
64114:         <span role="button" tabindex="0" title="Configure logic / variables" data-aion-main-node-toolbar="logic" data-aion-main-node-toolbar-node="${nodeId}">⑂</span>
64115:         <span role="button" tabindex="0" title="Remove step" data-aion-main-node-toolbar="delete" data-aion-main-node-toolbar-node="${nodeId}">×</span>
64116: 
64117:       `;
64118: 
64119:       nodeEl.appendChild(toolbar);
64120:     });
64121: 
64122:     injectLogicTabIntoNodeEditor();
64123:   }
64124: 
64125:   function injectLogicTabIntoNodeEditor() {
64126:     const editor =
64127:       document.querySelector(".aion-workflow-node-editor") ||
64128:       document.querySelector(".aion-workflow-execution-panel") ||
64129:       document.querySelector("[data-aion-workflow-node-editor='true']");
64130: 
64131:     if (!editor || editor.querySelector(".aion-main-node-editor-logic-tab")) return;
64132: 
64133:     const selectedNodeId = window.__aionWorkflowSelectedNodeId || "";
64134:     if (!selectedNodeId) return;
64135: 
64136:     const closeButton =
64137:       editor.querySelector("[data-aion-workflow-node-editor-close='true']") ||
64138:       editor.querySelector("[data-aion-dry-run-close='true']") ||
64139:       editor.querySelector("button");
64140: 
```
```js
64269: 
64270:       document.body.classList.remove("aion-connector-dragging");
64271:       document
64272:         .querySelectorAll("[data-aion-port-connect-drop-target='true']")
64273:         .forEach((item) => item.removeAttribute("data-aion-port-connect-drop-target"));
64274: 
64275:       if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
64276:     },
64277:     true,
64278:   );
64279: 
64280:   document.addEventListener(
64281:     "click",
64282:     (event) => {
64283:       const toolbarButton = event.target.closest?.("[data-aion-main-node-toolbar]");
64284:       if (!toolbarButton) return;
64285: 
64286:       event.preventDefault();
64287:       event.stopPropagation();
64288:       event.stopImmediatePropagation();
64289: 
64290:       const action = toolbarButton.getAttribute("data-aion-main-node-toolbar");
64291:       const nodeId = getNodeIdFromToolbarButton(toolbarButton);
64292: 
64293:       if (action === "settings") {
64294:         openNodeEditor(nodeId);
64295:         return;
64296:       }
64297: 
64298:       if (action === "logic") {
64299:         openAdvancedLogic(nodeId);
64300:         return;
64301:       }
64302: 
64303:       if (action === "delete") {
64304:         const resolvedNodeId =
64305:           toolbarButton.getAttribute("data-aion-main-node-toolbar-node") ||
64306:           toolbarButton.closest?.("[data-aion-workflow-node-id]")?.getAttribute("data-aion-workflow-node-id") ||
64307:           nodeId;
64308: 
64309:         if (!resolvedNodeId) return;
64310: 
64311:         const graph =
64312:           (typeof getAionWorkflowDraftState === "function"
64313:             ? getAionWorkflowDraftState()
64314:             : window.__aionWorkflowGraph) || {};
64315: 
64316:         const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
64317:         const edges = Array.isArray(graph.edges) ? graph.edges : [];
64318: 
64319:         const nextNodes = nodes.filter(
64320:           (node) => String(node.id) !== String(resolvedNodeId),
64321:         );
64322: 
64323:         const nextEdges = edges.filter((edge) => {
64324:           const from = edge.from || edge.source;
64325:           const to = edge.to || edge.target;
64326:           return String(from) !== String(resolvedNodeId) && String(to) !== String(resolvedNodeId);
64327:         });
64328: 
64329:         if (!nextNodes.length && typeof makeBlankWorkflowGraph === "function") {
64330:           window.__aionWorkflowGraph = makeBlankWorkflowGraph();
64331:           window.__aionWorkflowSelectedNodeId = null;
64332:         } else {
64333:           graph.nodes = nextNodes;
64334:           graph.edges = nextEdges;
64335:           graph.dirty = true;
64336:           window["__aionWorkflowGraph"] = graph;
64337: 
64338:           if (window.__aionWorkflowSelectedNodeId === resolvedNodeId) {
64339:             window.__aionWorkflowSelectedNodeId =
64340:               nextNodes[nextNodes.length - 1]?.id || nextNodes[0]?.id || null;
64341:           }
64342:         }
64343: 
64344:         try {
64345:           if (typeof compileAndAttachAionWorkflowGlyph === "function") {
64346:             compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
64347:           }
64348:         } catch (error) {
64349:           console.warn("[workflow-delete] compile skipped", error);
```
```js
70543:     }
70544:   `;
70545: 
70546:   document.head.appendChild(style);
70547: })();
70548: 
70549: /* AION PATCH: mini-toolbar settings opens node editor modal v1
70550:    Fix:
70551:    Clicking the settings icon should open the same Input / Parameters / Output
70552:    node editor modal as double-clicking the node.
70553: */
70554: (function installAionMiniToolbarSettingsOpensNodeEditorV1() {
70555:   const PATCH_ID = "aion-mini-toolbar-settings-opens-node-editor-v1";
70556:   if (document.getElementById(PATCH_ID)) return;
70557: 
70558:   function getSettingsTarget(event) {
70559:     const direct = event.target.closest?.('[data-aion-main-node-toolbar="settings"]');
70560:     if (direct) return direct;
70561: 
70562:     const path = typeof event.composedPath === "function" ? event.composedPath() : [];
70563:     return path.find?.(
70564:       (el) => el?.getAttribute?.("data-aion-main-node-toolbar") === "settings",
70565:     );
70566:   }
70567: 
70568:   function openNodeEditorFromSettings(settingsTarget) {
70569:     if (!settingsTarget) return false;
70570: 
70571:     const nodeId =
70572:       settingsTarget.getAttribute("data-aion-main-node-toolbar-node") ||
70573:       settingsTarget.closest?.("[data-aion-workflow-node-id]")?.getAttribute("data-aion-workflow-node-id");
70574: 
70575:     if (!nodeId) return false;
70576: 
70577:     if (
70578:         typeof window.aionRouteLinkedDepartmentNavigationNodeO13H3 === "function" &&
70579:         window.aionRouteLinkedDepartmentNavigationNodeO13H3(nodeId)
70580:       ) {
70581:         return;
70582:       }
70583:       window.__aionWorkflowSelectedNodeId = nodeId;
70584: 
70585:     const safeId = window.CSS?.escape ? CSS.escape(nodeId) : nodeId;
70586:     const nodeEl = document.querySelector(`[data-aion-workflow-node-id="${safeId}"]`);
70587: 
70588:     if (!nodeEl) return false;
70589: 
70590:     // Use the existing node double-click path because that already opens
70591:     // the real Input / Parameters / Output modal.
70592:     nodeEl.dispatchEvent(
70593:       new MouseEvent("dblclick", {
70594:         bubbles: true,
70595:         cancelable: true,
70596:         view: window,
70597:       }),
70598:     );
70599: 
70600:     return true;
70601:   }
70602: 
70603:   function handleSettings(event) {
70604:     const settingsTarget = getSettingsTarget(event);
70605:     if (!settingsTarget) return;
70606: 
70607:     event.preventDefault();
70608:     event.stopPropagation();
70609:     event.stopImmediatePropagation();
70610: 
70611:     openNodeEditorFromSettings(settingsTarget);
70612:   }
70613: 
70614:   document.addEventListener("pointerdown", handleSettings, true);
70615:   document.addEventListener("mousedown", handleSettings, true);
70616:   document.addEventListener("click", handleSettings, true);
70617: 
70618:   const style = document.createElement("style");
70619:   style.id = PATCH_ID;
70620:   style.textContent = `
70621:     .aion-canvas-node .aion-main-node-mini-toolbar [data-aion-main-node-toolbar="settings"] {
70622:       pointer-events: auto !important;
70623:       cursor: pointer !important;
```
```js
70586:     const nodeEl = document.querySelector(`[data-aion-workflow-node-id="${safeId}"]`);
70587: 
70588:     if (!nodeEl) return false;
70589: 
70590:     // Use the existing node double-click path because that already opens
70591:     // the real Input / Parameters / Output modal.
70592:     nodeEl.dispatchEvent(
70593:       new MouseEvent("dblclick", {
70594:         bubbles: true,
70595:         cancelable: true,
70596:         view: window,
70597:       }),
70598:     );
70599: 
70600:     return true;
70601:   }
70602: 
70603:   function handleSettings(event) {
70604:     const settingsTarget = getSettingsTarget(event);
70605:     if (!settingsTarget) return;
70606: 
70607:     event.preventDefault();
70608:     event.stopPropagation();
70609:     event.stopImmediatePropagation();
70610: 
70611:     openNodeEditorFromSettings(settingsTarget);
70612:   }
70613: 
70614:   document.addEventListener("pointerdown", handleSettings, true);
70615:   document.addEventListener("mousedown", handleSettings, true);
70616:   document.addEventListener("click", handleSettings, true);
70617: 
70618:   const style = document.createElement("style");
70619:   style.id = PATCH_ID;
70620:   style.textContent = `
70621:     .aion-canvas-node .aion-main-node-mini-toolbar [data-aion-main-node-toolbar="settings"] {
70622:       pointer-events: auto !important;
70623:       cursor: pointer !important;
70624:       position: relative !important;
70625:       z-index: 1000 !important;
70626:     }
70627:   `;
70628: 
70629:   document.head.appendChild(style);
70630: })();
70631: 
70632: /* AION PATCH: consolidated workflow bottom dock v1
70633:    One bottom dock: Execute, builder modes, Save, Glyph, Add.
70634:    Ask/Describe expand above the dock. Manual only shows active green light.
70635: */
70636: (function installAionConsolidatedWorkflowBottomDockV1() {
70637:   const PATCH_ID = "aion-consolidated-workflow-bottom-dock-v1";
70638:   if (document.getElementById(PATCH_ID)) return;
70639: 
70640:   const style = document.createElement("style");
70641:   style.id = PATCH_ID;
70642:   style.textContent = `
70643:     .aion-unified-builder-tabs,
70644:     .aion-unified-builder-note {
70645:       display: none !important;
70646:     }
70647: 
70648:     .aion-unified-builder-controls-compact {
70649:       position: fixed !important;
70650:       left: 50% !important;
70651:       bottom: 112px !important;
70652:       transform: translateX(-50%) !important;
70653:       width: min(1120px, calc(100vw - 180px)) !important;
70654:       z-index: 86 !important;
70655:       pointer-events: none !important;
70656:       margin: 0 !important;
70657:       padding: 0 !important;
70658:       background: transparent !important;
70659:       border: 0 !important;
70660:       box-shadow: none !important;
70661:     }
70662: 
70663:     .aion-unified-builder-controls-compact.aion-unified-builder-manual-active {
70664:       display: none !important;
70665:     }
70666: 
```

### pattern `findVisibleNodeEditor` hits: [68895, 69063, 104745, 104855]
```js
68870:     } catch (_) {}
68871:   }
68872: 
68873:   function patchNode(nodeId, field, value) {
68874:     const graph = getGraph();
68875:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
68876: 
68877:     graph.nodes = nodes.map((node) => {
68878:       if (String(node.id) !== String(nodeId)) return node;
68879: 
68880:       return {
68881:         ...node,
68882:         [field]: value,
68883:         config: {
68884:           ...(node.config || {}),
68885:           ...(field === "fields" || field === "outputs" ? { [field]: value } : {}),
68886:         },
68887:       };
68888:     });
68889: 
68890:     graph.dirty = true;
68891:     graph.updated_at = new Date().toISOString();
68892:     persistGraph(graph);
68893:   }
68894: 
68895:   function findVisibleNodeEditor() {
68896:     const candidates = Array.from(document.querySelectorAll("div, section, aside, main"))
68897:       .filter((el) => {
68898:         const rect = el.getBoundingClientRect?.();
68899:         if (!rect) return false;
68900:         if (rect.width < 600 || rect.height < 400) return false;
68901: 
68902:         const style = window.getComputedStyle(el);
68903:         if (style.display === "none" || style.visibility === "hidden") return false;
68904: 
68905:         const text = String(el.textContent || "");
68906:         return (
68907:           text.includes("NODE EDITOR") &&
68908:           text.includes("INPUT") &&
68909:           text.includes("PARAMETERS") &&
68910:           text.includes("OUTPUT") &&
68911:           text.includes("TEST NODE") &&
68912:           text.includes("SAVE NODE")
68913:         );
68914:       });
68915: 
68916:     return candidates.sort((a, b) => {
68917:       const ar = a.getBoundingClientRect();
68918:       const br = b.getBoundingClientRect();
68919:       return ar.width * ar.height - br.width * br.height;
68920:     })[0] || null;
68921:   }
68922: 
68923:   function findParametersColumn(editor) {
68924:     if (!editor) return null;
68925: 
68926:     const rect = editor.getBoundingClientRect();
68927: 
68928:     const possible = Array.from(editor.querySelectorAll("div, section, aside"))
68929:       .filter((el) => {
68930:         const r = el.getBoundingClientRect?.();
68931:         if (!r) return false;
68932: 
68933:         const text = String(el.textContent || "");
68934:         return (
68935:           text.includes("PARAMETERS") &&
68936:           text.includes("Settings") &&
68937:           text.includes("TEST NODE") &&
68938:           text.includes("SAVE NODE") &&
68939:           r.left > rect.left + rect.width * 0.25 &&
68940:           r.left < rect.left + rect.width * 0.72 &&
68941:           r.width > 250 &&
68942:           r.height > 250
68943:         );
68944:       });
68945: 
68946:     if (possible.length) {
68947:       return possible.sort((a, b) => {
68948:         const ar = a.getBoundingClientRect();
68949:         const br = b.getBoundingClientRect();
68950:         return ar.width * ar.height - br.width * br.height;
```
```js
69038:               data-aion-main-node-edit-v6="${esc(node.id)}"
69039:               data-aion-main-node-field="outputs"
69040:               placeholder="new_email_event, customer_details, draft_reply"
69041:             >${esc(node.outputs || node.config?.outputs || "")}</textarea>
69042:           </label>
69043: 
69044:           <label>
69045:             <span>Approval / safety</span>
69046:             <select data-aion-main-node-edit-v6="${esc(node.id)}" data-aion-main-node-field="approval_requirement">
69047:               <option value="auto" ${approval === "auto" ? "selected" : ""}>Auto</option>
69048:               <option value="not_required" ${approval === "not_required" ? "selected" : ""}>No approval needed</option>
69049:               <option value="required" ${approval === "required" ? "selected" : ""}>Require human approval</option>
69050:               <option value="before_external_write" ${approval === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
69051:             </select>
69052:           </label>
69053: 
69054:           <button type="button" data-aion-main-node-logic-v6="${esc(node.id)}">
69055:             Configure logic / variables
69056:           </button>
69057:         </div>
69058:       </section>
69059:     `;
69060:   }
69061: 
69062:   function inject() {
69063:     const editor = findVisibleNodeEditor();
69064:     if (!editor) return;
69065: 
69066:     editor
69067:       .querySelectorAll(
69068:         ".aion-main-node-mini-toolbar, .aion-workflow-node-mini-toolbar, .aion-architect-node-mini-toolbar",
69069:       )
69070:       .forEach((el) => { el.style.display = 'none'; el.style.visibility = 'hidden'; });
69071: 
69072:     if (editor.querySelector("[data-aion-main-node-ai-settings-v6='true']")) return;
69073: 
69074:     const column = findParametersColumn(editor);
69075:     if (!column) return;
69076: 
69077:     const node = getSelectedNode();
69078: 
69079:     const emptyText = Array.from(column.querySelectorAll("*")).find((el) =>
69080:       String(el.textContent || "").trim() === "No custom parameters for this node yet.",
69081:     );
69082: 
69083:     if (emptyText) {
69084:       emptyText.remove();
69085:     }
69086: 
69087:     const wrap = document.createElement("div");
69088:     wrap.innerHTML = renderSettings(node);
69089: 
69090:     column.appendChild(wrap.firstElementChild);
69091:   }
69092: 
69093:   function openLogic(nodeId) {
69094:     const node = getSelectedNode();
69095: 
69096:     window.__aionWorkflowSelectedNodeId = nodeId || node.id;
69097:     window.__aionArchitectSelectedStepId = nodeId || node.id;
69098:     window.__aionArchitectAdvancedConfigOpen = true;
69099:     window.__aionArchitectAdvancedConfigTab = window.__aionArchitectAdvancedConfigTab || "filters";
69100: 
69101:     if (!window.__aionDraggingConnector && typeof requestRender === "function") requestRender();
69102:   }
69103: 
69104:   document.addEventListener(
69105:     "input",
69106:     (event) => {
69107:       const input = event.target.closest?.("[data-aion-main-node-edit-v6]");
69108:       if (!input) return;
69109: 
69110:       const nodeId = input.getAttribute("data-aion-main-node-edit-v6");
69111:       const field = input.getAttribute("data-aion-main-node-field");
69112:       if (!nodeId || !field) return;
69113: 
69114:       patchNode(nodeId, field, input.value);
69115:     },
69116:     true,
69117:   );
69118: 
```
```js
104720:       }
104721: 
104722:       .aion-phase19e-real-custom-function-actions {
104723:         display: flex !important;
104724:         justify-content: flex-end !important;
104725:         gap: 10px !important;
104726:       }
104727: 
104728:       .aion-phase19e-real-custom-function-actions button {
104729:         height: 38px !important;
104730:         padding: 0 14px !important;
104731:         border: 1px solid rgba(15,23,42,0.14) !important;
104732:         background: #1f1f1f !important;
104733:         color: white !important;
104734:         font-weight: 900 !important;
104735:         cursor: pointer !important;
104736:       }
104737: 
104738:       [data-aion-phase19e-generic-params-hidden="true"] {
104739:         display: none !important;
104740:       }
104741:     `;
104742:     document.head.appendChild(style);
104743:   }
104744: 
104745:   function findVisibleNodeEditor() {
104746:     const candidates = Array.from(document.querySelectorAll("div, section, article, aside"))
104747:       .filter((el) => {
104748:         const text = String(el.textContent || "");
104749:         if (!text.includes("NODE EDITOR")) return false;
104750:         if (!text.includes("PARAMETERS")) return false;
104751:         if (!text.includes("INPUT")) return false;
104752:         if (!text.includes("OUTPUT")) return false;
104753: 
104754:         const rect = el.getBoundingClientRect();
104755:         return rect.width > 600 && rect.height > 300;
104756:       })
104757:       .sort((a, b) => (b.getBoundingClientRect().width * b.getBoundingClientRect().height) - (a.getBoundingClientRect().width * a.getBoundingClientRect().height));
104758: 
104759:     return candidates[0] || null;
104760:   }
104761: 
104762:   function findParametersColumn(editor) {
104763:     const candidates = Array.from(editor.querySelectorAll("div, section, article"))
104764:       .filter((el) => {
104765:         const text = String(el.textContent || "");
104766:         const rect = el.getBoundingClientRect();
104767:         return (
104768:           text.includes("PARAMETERS") &&
104769:           (text.includes("FIELD") || text.includes("OPERATOR") || text.includes("VALUE") || text.includes("EXECUTE STEP")) &&
104770:           rect.width > 250 &&
104771:           rect.height > 200
104772:         );
104773:       })
104774:       .sort((a, b) => (a.getBoundingClientRect().width * a.getBoundingClientRect().height) - (b.getBoundingClientRect().width * b.getBoundingClientRect().height));
104775: 
104776:     return candidates[0] || null;
104777:   }
104778: 
104779:   function editorHtml(node) {
104780:     const config = node.config || {};
104781:     return `
104782:       <div class="aion-phase19e-real-custom-function-editor" data-aion-phase19e-real-custom-function-editor="true" data-aion-node-id="${esc(node.id || "")}">
104783:         <div class="aion-phase19e-real-custom-function-banner">
104784:           <div class="eyebrow">Custom function</div>
104785:           <h3>Code transform · dry-run only</h3>
104786:           <p>
104787:             Receives JSON from the previous node, transforms it, and returns JSON to the next node.
104788:             This editor saves configuration only. It does not eval code, send messages, create bookings,
104789:             take payments, or perform external writes.
104790:           </p>
104791:         </div>
104792: 
104793:         <div class="aion-phase19e-real-custom-function-grid">
104794:           <label>
104795:             Language
104796:             <select data-aion-phase19e-real-custom-function-input="language">
104797:               <option value="javascript" ${String(config.language || "javascript") === "javascript" ? "selected" : ""}>JavaScript</option>
104798:               <option value="python" ${String(config.language || "") === "python" ? "selected" : ""}>Python later</option>
104799:               <option value="json" ${String(config.language || "") === "json" ? "selected" : ""}>JSON transform</option>
104800:             </select>
```
```js
104830:           </label>
104831:         </div>
104832: 
104833:         <div class="aion-phase19e-real-custom-function-safety">
104834:           <span>✓ Dry-run only</span>
104835:           <span>✓ No frontend code execution</span>
104836:           <span>✓ No external writes</span>
104837:           <span>✓ Requires approval before any future live runner</span>
104838:         </div>
104839: 
104840:         <div class="aion-phase19e-real-custom-function-actions">
104841:           <button type="button" data-aion-phase19e-real-custom-function-save="true">Save custom function</button>
104842:         </div>
104843:       </div>
104844:     `;
104845:   }
104846: 
104847:   function applyTakeover() {
104848:     ensureStyle();
104849: 
104850:     const node = selectedNode();
104851:     if (!isCustomFunctionNode(node)) return false;
104852: 
104853:     normaliseCustomFunctionNode(node);
104854: 
104855:     const editor = findVisibleNodeEditor();
104856:     if (!editor) return false;
104857: 
104858:     const text = String(editor.textContent || "").toLowerCase();
104859:     if (!text.includes("custom function") && !text.includes("custom logic")) return false;
104860: 
104861:     if (editor.querySelector("[data-aion-phase19e-real-custom-function-editor='true']")) return true;
104862: 
104863:     const params = findParametersColumn(editor);
104864:     if (!params) return false;
104865: 
104866:     params.setAttribute("data-aion-phase19e-generic-params-hidden", "true");
104867: 
104868:     const mount = document.createElement("div");
104869:     mount.setAttribute("data-aion-phase19e-real-custom-function-mount", "true");
104870:     mount.innerHTML = editorHtml(node);
104871: 
104872:     params.parentNode.insertBefore(mount, params.nextSibling);
104873: 
104874:     persistGraph("phase19e_real_node_editor_takeover_mounted");
104875:     return true;
104876:   }
104877: 
104878:   function saveVisibleEditor() {
104879:     const mount = document.querySelector("[data-aion-phase19e-real-custom-function-editor='true']");
104880:     if (!mount) return false;
104881: 
104882:     const nodeId = mount.getAttribute("data-aion-node-id");
104883:     const graph = getGraph();
104884:     const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
104885:     const node = nodes.find((item) => String(item.id) === String(nodeId)) || selectedNode();
104886: 
104887:     if (!node) return false;
104888: 
104889:     normaliseCustomFunctionNode(node);
104890: 
104891:     mount.querySelectorAll("[data-aion-phase19e-real-custom-function-input]").forEach((input) => {
104892:       const key = input.getAttribute("data-aion-phase19e-real-custom-function-input");
104893:       if (!key) return;
104894:       node.config[key] = input.value;
104895:     });
104896: 
104897:     node.config.safety_mode = "dry_run_only";
104898:     node.config.external_writes_enabled = false;
104899:     node.config.live_execution_enabled = false;
104900:     node.config.requires_human_approval = true;
104901:     node.dry_run_only = true;
104902:     node.external_writes_enabled = false;
104903:     node.live_execution_enabled = false;
104904:     node.meta = "Custom function configured for dry-run only. This editor never enables live execution.";
104905: 
104906:     persistGraph("phase19e_real_custom_function_saved");
104907:     return true;
104908:   }
104909: 
104910:   document.addEventListener("click", (event) => {
```

### pattern `injectAiSettingsIntoNodeEditor` hits: [64575, 64699, 65250, 65486]
```js
64550:       }
64551:       window.__aionWorkflowSelectedNodeId = nodeId;
64552:     window.__aionArchitectSelectedStepId = nodeId;
64553:     window.__aionArchitectAdvancedConfigOpen = true;
64554:     window.__aionArchitectAdvancedConfigTab = window.__aionArchitectAdvancedConfigTab || "filters";
64555: 
64556:     window.__aionArchitectSteps = [
64557:       {
64558:         id: node.id,
64559:         app: node.connector || node.type || node.title || "workflow",
64560:         connector: node.connector || node.type || "",
64561:         action_id: node.action_id || node.action || "",
64562:         action_label: node.title || node.action_label || "Configure step",
64563:         subtitle: node.meta || node.subtitle || "",
64564:         fields: node.fields || node.config?.fields || "",
64565:         outputs: node.outputs || node.config?.outputs || "",
64566:         approval_requirement:
64567:           node.approval_requirement ||
64568:           (String(node.status || "").toLowerCase().includes("approval") ? "required" : "auto"),
64569:       },
64570:     ];
64571: 
64572:     safeRequestRender();
64573:   }
64574: 
64575:   function injectAiSettingsIntoNodeEditor() {
64576:     const editor =
64577:       document.querySelector(".aion-workflow-node-editor") ||
64578:       document.querySelector("[data-aion-workflow-node-editor='true']");
64579: 
64580:     if (!editor) return;
64581:     if (editor.querySelector("[data-aion-main-node-ai-settings='true']")) return;
64582: 
64583:     const node = getSelectedNode();
64584:     if (!node) return;
64585: 
64586:     // Remove any mini toolbars that accidentally got injected inside the modal.
64587:     editor.querySelectorAll(".aion-main-node-mini-toolbar").forEach((toolbar) => toolbar.remove());
64588: 
64589:     const paramsColumn =
64590:       Array.from(editor.querySelectorAll("*")).find((el) =>
64591:         String(el.textContent || "").trim().startsWith("PARAMETERS"),
64592:       ) || editor;
64593: 
64594:     const panel = document.createElement("section");
64595:     panel.className = "aion-main-node-ai-settings";
64596:     panel.setAttribute("data-aion-main-node-ai-settings", "true");
64597: 
64598:     panel.innerHTML = `
64599:       <div class="aion-main-node-ai-settings-tabs">
64600:         <button type="button" class="active">Node</button>
64601:         <button type="button" data-aion-main-node-open-logic="${node.id}">Logic / Variables</button>
64602:       </div>
64603: 
64604:       <div class="aion-main-node-ai-settings-card">
64605:         <div class="eyebrow">AI canvas settings</div>
64606: 
64607:         <label>
64608:           <span>What kind of step is this?</span>
64609:           <select data-aion-main-node-field="type" data-aion-main-node-id="${node.id}">
64610:             <option value="Step" ${String(node.type || "") === "Step" ? "selected" : ""}>Step</option>
64611:             <option value="Trigger" ${String(node.type || "") === "Trigger" ? "selected" : ""}>Trigger</option>
64612:             <option value="AI / Parser" ${String(node.type || "") === "AI / Parser" ? "selected" : ""}>AI action</option>
64613:             <option value="Tools" ${String(node.type || "") === "Tools" ? "selected" : ""}>Tool / transform</option>
64614:             <option value="Text Parser" ${String(node.type || "") === "Text Parser" ? "selected" : ""}>Text parser</option>
64615:             <option value="Gate" ${String(node.type || "") === "Gate" ? "selected" : ""}>Approval / gate</option>
64616:             <option value="Flow Control" ${String(node.type || "") === "Flow Control" ? "selected" : ""}>Flow control</option>
64617:             <option value="Custom Logic" ${String(node.type || "") === "Custom Logic" ? "selected" : ""}>Custom logic</option>
64618:             <option value="Content Asset" ${String(node.type || "") === "Content Asset" ? "selected" : ""}>Content asset</option>
64619:           </select>
64620:         </label>
64621: 
64622:         <label>
64623:           <span>Use this app / system</span>
64624:           <input
64625:             data-aion-main-node-field="connector"
64626:             data-aion-main-node-id="${node.id}"
64627:             value="${escapeHtml(node.connector || node.type || "")}"
64628:             placeholder="Gmail, Aion, Tools, Text parser, Approval"
64629:           />
64630:         </label>
```
```js
64674:             <option value="not_required" ${String(node.approval_requirement || "") === "not_required" ? "selected" : ""}>No approval needed</option>
64675:             <option value="required" ${String(node.approval_requirement || "") === "required" ? "selected" : ""}>Require human approval</option>
64676:             <option value="before_external_write" ${String(node.approval_requirement || "") === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
64677:           </select>
64678:         </label>
64679: 
64680:         <button type="button" class="secondary-btn" data-aion-main-node-open-logic="${node.id}">
64681:           Configure logic / variables
64682:         </button>
64683:       </div>
64684:     `;
64685: 
64686:     paramsColumn.appendChild(panel);
64687:   }
64688: 
64689:   function cleanToolbarFromModals() {
64690:     document
64691:       .querySelectorAll(
64692:         ".aion-workflow-node-editor .aion-main-node-mini-toolbar, [data-aion-workflow-node-editor='true'] .aion-main-node-mini-toolbar, .aion-workflow-execution-panel .aion-main-node-mini-toolbar",
64693:       )
64694:       .forEach((toolbar) => toolbar.remove());
64695:   }
64696: 
64697:   function postRender() {
64698:     cleanToolbarFromModals();
64699:     injectAiSettingsIntoNodeEditor();
64700:   }
64701: 
64702:   document.addEventListener(
64703:     "input",
64704:     (event) => {
64705:       const input = event.target.closest?.("[data-aion-main-node-field]");
64706:       if (!input) return;
64707: 
64708:       const nodeId = input.getAttribute("data-aion-main-node-id");
64709:       const field = input.getAttribute("data-aion-main-node-field");
64710: 
64711:       if (!nodeId || !field) return;
64712: 
64713:       updateNodeField(nodeId, field, input.value);
64714:     },
64715:     true,
64716:   );
64717: 
64718:   document.addEventListener(
64719:     "change",
64720:     (event) => {
64721:       const input = event.target.closest?.("[data-aion-main-node-field]");
64722:       if (!input) return;
64723: 
64724:       const nodeId = input.getAttribute("data-aion-main-node-id");
64725:       const field = input.getAttribute("data-aion-main-node-field");
64726: 
64727:       if (!nodeId || !field) return;
64728: 
64729:       updateNodeField(nodeId, field, input.value);
64730:       safeRequestRender();
64731:     },
64732:     true,
64733:   );
64734: 
64735:   document.addEventListener(
64736:     "pointerdown",
64737:     (event) => {
64738:       const port = event.target.closest?.("[data-aion-port-node-id]");
64739:       if (!port) return;
64740: 
64741:       const direction = port.getAttribute("data-aion-port-direction");
64742:       if (direction !== "output") return;
64743: 
64744:       event.preventDefault();
64745:       event.stopPropagation();
64746:       event.stopImmediatePropagation();
64747: 
64748:       const nodeId = port.getAttribute("data-aion-port-node-id");
64749:       const condition = port.getAttribute("data-aion-port-condition") || "success";
64750:       const role = port.getAttribute("data-aion-port-role") || "main";
64751: 
64752:       window.__aionDraggingConnector = {
64753:         from: nodeId,
64754:         condition,
```
```js
65225:               placeholder="new_email_event, customer_details, draft_reply"
65226:             >${safeEscape(node.outputs || node.config?.outputs || "")}</textarea>
65227:           </label>
65228: 
65229:           <label>
65230:             <span>Approval / safety</span>
65231:             <select
65232:               data-aion-main-node-field="approval_requirement"
65233:               data-aion-main-node-id="${safeEscape(node.id)}"
65234:             >
65235:               <option value="auto" ${String(node.approval_requirement || "auto") === "auto" ? "selected" : ""}>Auto</option>
65236:               <option value="not_required" ${String(node.approval_requirement || "") === "not_required" ? "selected" : ""}>No approval needed</option>
65237:               <option value="required" ${String(node.approval_requirement || "") === "required" ? "selected" : ""}>Require human approval</option>
65238:               <option value="before_external_write" ${String(node.approval_requirement || "") === "before_external_write" ? "selected" : ""}>Require approval before external write</option>
65239:             </select>
65240:           </label>
65241: 
65242:           <button type="button" class="secondary-btn" data-aion-main-node-open-logic="${safeEscape(node.id)}">
65243:             Configure logic / variables
65244:           </button>
65245:         </div>
65246:       </section>
65247:     `;
65248:   }
65249: 
65250:   function injectAiSettingsIntoNodeEditor() {
65251:     const modal = findNodeEditorModal();
65252:     if (!modal) return;
65253: 
65254:     modal
65255:       .querySelectorAll(".aion-main-node-mini-toolbar, .aion-workflow-node-mini-toolbar")
65256:       .forEach((item) => item.remove());
65257: 
65258:     if (modal.querySelector("[data-aion-main-node-ai-settings='true']")) return;
65259: 
65260:     const node = selectedNode();
65261:     if (!node) return;
65262: 
65263:     const parameterHeaders = Array.from(modal.querySelectorAll("*")).filter((el) =>
65264:       String(el.textContent || "").trim().startsWith("PARAMETERS"),
65265:     );
65266: 
65267:     const anchor =
65268:       parameterHeaders[0]?.parentElement ||
65269:       Array.from(modal.querySelectorAll("*")).find((el) =>
65270:         String(el.textContent || "").includes("No custom parameters"),
65271:       )?.parentElement ||
65272:       modal;
65273: 
65274:     const wrap = document.createElement("div");
65275:     wrap.innerHTML = renderAiSettingsHtml(node);
65276: 
65277:     anchor.appendChild(wrap.firstElementChild);
65278:   }
65279: 
65280:   function forceMountAdvancedModal() {
65281:     if (window.__aionArchitectAdvancedConfigOpen !== true) return;
65282: 
65283:     if (document.querySelector("[data-aion-architect-advanced-backdrop='true']")) {
65284:       return;
65285:     }
65286: 
65287:     if (typeof renderAionArchitectAdvancedConfigModal !== "function") {
65288:       console.warn(`[${PATCH_ID}] renderAionArchitectAdvancedConfigModal not found`);
65289:       return;
65290:     }
65291: 
65292:     const html = renderAionArchitectAdvancedConfigModal();
65293:     if (!html) return;
65294: 
65295:     const mount = document.createElement("div");
65296:     mount.setAttribute("data-aion-main-forced-advanced-mount", "true");
65297:     mount.innerHTML = html;
65298:     document.body.appendChild(mount);
65299:   }
65300: 
65301:   function cleanupForcedAdvancedMount() {
65302:     if (window.__aionArchitectAdvancedConfigOpen === true) return;
65303: 
65304:     document
65305:       .querySelectorAll("[data-aion-main-forced-advanced-mount='true']")
```
```js
65461: 
65462:       if (!nodeId || !field) return;
65463:       updateNode(nodeId, field, input.value);
65464:     },
65465:     true,
65466:   );
65467: 
65468:   document.addEventListener(
65469:     "change",
65470:     (event) => {
65471:       const input = event.target.closest?.("[data-aion-main-node-field]");
65472:       if (!input) return;
65473: 
65474:       const nodeId = input.getAttribute("data-aion-main-node-id");
65475:       const field = input.getAttribute("data-aion-main-node-field");
65476: 
65477:       if (!nodeId || !field) return;
65478:       updateNode(nodeId, field, input.value);
65479:       request();
65480:     },
65481:     true,
65482:   );
65483: 
65484:   function postRender() {
65485:     cleanupForcedAdvancedMount();
65486:     injectAiSettingsIntoNodeEditor();
65487:     forceMountAdvancedModal();
65488:   }
65489: 
65490:   const observer = new MutationObserver(() => {
65491:     window.requestAnimationFrame?.(postRender) || setTimeout(postRender, 0);
65492:   });
65493: 
65494:   observer.observe(document.documentElement, {
65495:     childList: true,
65496:     subtree: true,
65497:   });
65498: 
65499:   const style = document.createElement("style");
65500:   style.id = PATCH_ID;
65501:   style.textContent = `
65502:     [data-aion-main-forced-advanced-mount='true'] {
65503:       position: relative !important;
65504:       z-index: 999999 !important;
65505:     }
65506: 
65507:     .aion-workflow-node-editor .aion-main-node-mini-toolbar,
65508:     .aion-workflow-execution-panel .aion-main-node-mini-toolbar,
65509:     [data-aion-workflow-node-editor='true'] .aion-main-node-mini-toolbar {
65510:       display: none !important;
65511:     }
65512: 
65513:     .aion-main-node-ai-settings {
65514:       margin-top: 22px !important;
65515:       padding-top: 18px !important;
65516:       border-top: 1px solid rgba(15,23,42,0.12) !important;
65517:       display: grid !important;
65518:       gap: 14px !important;
65519:     }
65520: 
65521:     .aion-main-node-ai-settings-tabs {
65522:       display: flex !important;
65523:       gap: 8px !important;
65524:       align-items: center !important;
65525:     }
65526: 
65527:     .aion-main-node-ai-settings-tabs button {
65528:       height: 38px !important;
65529:       border-radius: 12px !important;
65530:       border: 1px solid rgba(15,23,42,0.14) !important;
65531:       background: rgba(255,255,255,0.92) !important;
65532:       color: #0f172a !important;
65533:       padding: 0 14px !important;
65534:       font-weight: 950 !important;
65535:       letter-spacing: 0.08em !important;
65536:       text-transform: uppercase !important;
65537:       cursor: pointer !important;
65538:     }
65539: 
65540:     .aion-main-node-ai-settings-tabs button.active {
65541:       background: #0f172a !important;
```

## Packed app candidates


### App bundle: `desktop/mac/dist/mac-arm64/Tessaris.app`
- app.js files found: 0

### App bundle: `/Applications/Tessaris.app`
- app.js files found: 0