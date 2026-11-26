// Recovery material stays in this dialog only; never browser storage or a server upload.
const escapeHTML=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function recoveryFile(username,key,origin,admin=true){
 if(!admin)return `INTUITION — PRIVATE USER RECOVERY KEY\n\nUser login: ${origin}/exchange/\nUsername: ${username}\nRecovery key: ${key}\nSaved: ${new Date().toISOString()}\n\nKeep this file private. This key can reset your demo account password.\nOnly the latest recovery key works. This key cannot recover administrator accounts.\nAfter resetting your password, download the replacement key; this file is not updated automatically.\nNo password is included. Demo IQ has no cash value.\n`;
 return `INTUITION — PRIVATE ADMIN RECOVERY KEY\n\nAdmin login: ${origin}/exchange/admin.html\nAdmin username: ${username}\nRecovery key: ${key}\nSaved: ${new Date().toISOString()}\n\nKeep this file private. This key can reset your administrator password.\nIt replaces all previous admin recovery keys and cannot recover normal user accounts.\nAfter using it, download the new replacement key shown on screen; this file is not updated automatically.\nNo password is included in this file.\n`;
}
export function showAdminRecovery(dialog,username,key){return showRecovery(dialog,username,key,true);}
export function showUserRecovery(dialog,username,key,signup=false){return showRecovery(dialog,username,key,false,signup);}
function showRecovery(dialog,username,key,admin,signup=false){
 const content=dialog.querySelector('#dialog-content');
 content.innerHTML=`<h2 id="dialog-title">${admin?'Save your replacement admin recovery key':'Save your private recovery key'}</h2><p>${signup?'Your demo account is ready. Save this key so you can recover your account if you forget your password.':'Your password has been reset. Save this new key before continuing; the previous key no longer works.'}</p><p>${admin?'Admin username':'Username'}: <b>${escapeHTML(username)}</b></p><textarea readonly aria-label="${admin?'Private admin recovery key':'Private recovery key'}">${escapeHTML(key)}</textarea><div class="modal-actions"><button class="button" type="button" data-download-admin-key>Download recovery key (.txt)</button><button class="outline" type="button" data-admin-key-saved>I have saved my key</button></div><p data-key-status role="status">Download the file or store this key securely, then confirm you have saved it.</p><p class="fine">Keep the file private. ${admin?'This is for administrator recovery only.':'This is for your demo user account only, not administrator access.'} Your password is not included.</p>`;
 const status=content.querySelector('[data-key-status]');
 let saved=false;
 const beforeUnload=e=>{if(!saved){e.preventDefault();e.returnValue='';}};
 const cancel=e=>{if(!saved){e.preventDefault();status.textContent='Please save your key and select “I have saved my key” before closing.';}};
 const click=e=>{
  if(e.target.closest('[data-download-admin-key]')){
   const blob=new Blob([recoveryFile(username,key,location.origin,admin)],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
   a.href=url;a.download=`INTUITION-${admin?'admin':'user'}-recovery-${new Date().toISOString().replace(/[:.]/g,'-')}.txt`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
   status.textContent='Download requested. Check your Downloads folder, then confirm you have saved the key.';
  }else if(e.target.closest('[data-admin-key-saved]')){saved=true;dialog.close();}
  else if(e.target.closest('.close')){e.stopImmediatePropagation();status.textContent='Please save your key and select “I have saved my key” before closing.';}
 };
 const cleanup=()=>{key='';content.innerHTML='';window.removeEventListener('beforeunload',beforeUnload);dialog.removeEventListener('cancel',cancel);dialog.removeEventListener('click',click,true);};
 dialog.addEventListener('click',click,true);dialog.addEventListener('cancel',cancel);dialog.addEventListener('close',cleanup,{once:true});window.addEventListener('beforeunload',beforeUnload);dialog.showModal();
}
