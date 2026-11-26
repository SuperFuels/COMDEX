// Recovery material stays in this dialog only; never browser storage or a server upload.
const escapeHTML=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function recoveryFile(username,key,origin){
 return `INTUITION — PRIVATE ADMIN RECOVERY KEY\n\nAdmin login: ${origin}/exchange/admin.html\nAdmin username: ${username}\nRecovery key: ${key}\nSaved: ${new Date().toISOString()}\n\nKeep this file private. This key can reset your administrator password.\nIt replaces all previous admin recovery keys and cannot recover normal user accounts.\nAfter using it, download the new replacement key shown on screen; this file is not updated automatically.\nNo password is included in this file.\n`;
}
export function showAdminRecovery(dialog,username,key){
 const content=dialog.querySelector('#dialog-content');
 content.innerHTML=`<h2 id="dialog-title">Save your replacement admin recovery key</h2><p>Your password has been reset. Save this new key before continuing; the previous key no longer works.</p><p>Admin username: <b>${escapeHTML(username)}</b></p><textarea readonly aria-label="Private admin recovery key">${escapeHTML(key)}</textarea><div class="modal-actions"><button class="button" type="button" data-download-admin-key>Download recovery key (.txt)</button><button class="outline" type="button" data-admin-key-saved>I have saved my key</button></div><p data-key-status role="status">Download the file or store this key securely, then confirm you have saved it.</p><p class="fine">Keep the file private. This is for administrator recovery only. Your password is not included.</p>`;
 const status=content.querySelector('[data-key-status]');
 let saved=false;
 const beforeUnload=e=>{if(!saved){e.preventDefault();e.returnValue='';}};
 const cancel=e=>{if(!saved){e.preventDefault();status.textContent='Please save your key and select “I have saved my key” before closing.';}};
 const click=e=>{
  if(e.target.closest('[data-download-admin-key]')){
   const blob=new Blob([recoveryFile(username,key,location.origin)],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
   a.href=url;a.download=`INTUITION-admin-recovery-${new Date().toISOString().replace(/[:.]/g,'-')}.txt`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
   status.textContent='Download requested. Check your Downloads folder, then confirm you have saved the key.';
  }else if(e.target.closest('[data-admin-key-saved]')){saved=true;dialog.close();}
  else if(e.target.closest('.close')){e.stopImmediatePropagation();status.textContent='Please save your key and select “I have saved my key” before closing.';}
 };
 const cleanup=()=>{key='';content.innerHTML='';window.removeEventListener('beforeunload',beforeUnload);dialog.removeEventListener('cancel',cancel);dialog.removeEventListener('click',click,true);};
 dialog.addEventListener('click',click,true);dialog.addEventListener('cancel',cancel);dialog.addEventListener('close',cleanup,{once:true});window.addEventListener('beforeunload',beforeUnload);dialog.showModal();
}
