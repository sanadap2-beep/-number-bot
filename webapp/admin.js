const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }
let currentView = "overview";
const panel = document.getElementById("panel");
const metrics = document.getElementById("metrics");
const message = document.getElementById("message");
const esc = (value) => String(value ?? "—").replace(/[&<>'"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
function headers(){ const h={"Content-Type":"application/json"}; if(tg?.initData) h.Authorization=`tma ${tg.initData}`; return h; }
async function api(path){ const r=await fetch(`/api/v1${path}`,{headers:headers()}); const body=await r.json().catch(()=>({})); if(!r.ok) throw new Error(body.detail || "تعذر تحميل البيانات"); return body; }
function notice(text,error=false){message.textContent=text;message.classList.toggle("hidden",!text);message.style.color=error?"var(--danger)":"var(--brand)";}
function money(value){return `${Number(value||0).toFixed(2)}$`;}
async function loadOverview(){
  const data=await api("/admin/overview");
  const cards=[["المستخدمون",data.users],["طلبات نشطة",data.active_orders],["شحنات معلقة",data.pending_deposits],["تذاكر مفتوحة",data.open_tickets],["منتجات فعالة",data.active_products],["حجم شراء اليوم",money(data.today_purchase_volume_usd)],["أرصدة المستخدمين",money(data.total_user_balance_usd)]];
  metrics.innerHTML=cards.map(([label,value])=>`<article class="metric"><small>${label}</small><strong>${esc(value)}</strong></article>`).join("");
  panel.innerHTML=`<h2>ملخص تشغيلي <button class="refresh" onclick="load()">تحديث</button></h2><p>آخر تحديث: ${esc(data.generated_at)}</p><p>المزودون الفعالون: <b>${esc(data.active_providers)}</b></p><p>تستطيع متابعة الطلبات والشحنات من تبويبات لوحة القيادة.</p>`;
}
async function loadTable(view){
  metrics.innerHTML="";
  const data=await api(view==="users"?"/admin/users":`/admin/${view}`);
  if(view === "quality") {
    const rows=[...(data.sms||[]).map(r=>({...r,kind:"SMS"})), ...(data.api||[]).map(r=>({...r,kind:"API"}))];
    panel.innerHTML=`<h2>جودة المزودين <button class="refresh" onclick="load()">تحديث</button></h2>${rows.length?`<div class="table-wrap"><table class="table"><thead><tr><th>النوع</th><th>المزود</th><th>الإجمالي</th><th>ناجحة</th><th>فاشلة</th><th>نسبة النجاح</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.kind)}</td><td>${esc(r.provider||r.provider_id)}</td><td>${esc(r.total)}</td><td>${esc(r.success)}</td><td>${esc(r.failed)}</td><td>${esc(r.success_rate)}%</td></tr>`).join("")}</tbody></table></div>`:'<div class="empty">لا توجد طلبات كافية بعد.</div>'}`;
    return;
  }
  if(!data.length){panel.innerHTML='<div class="empty">لا توجد بيانات لعرضها.</div>';return;}
  const configs={
    orders:["الطلب","المنتج","المستخدم","السعر","الحالة","التاريخ"],
    providers:["المزود","النوع","البروتوكول","الخدمات","الرصيد","الحالة"],
    users:["Telegram ID","الاسم","الرصيد","النقاط","حظر","أدمن"],
    promotions:["العرض","المنتج","الخصم","الاستخدام","ينتهي","الحالة"],
    audit:["الفعل","الكيان","الوصف","التاريخ"]
  };
  const heads=configs[view]||[];
  const cells={
    orders:r=>[r.id,r.product,r.user_id,money(r.price_usd),r.status,r.created_at],
    providers:r=>[r.name,r.type,r.protocol,r.total_services,r.balance?`${r.balance} ${r.currency}`:"—",r.is_active?"فعال":"متوقف"],
    users:r=>[r.telegram_id,r.full_name||r.username,money(r.balance_usd),r.loyalty_points,r.is_banned?"نعم":"لا",r.is_admin?"نعم":"لا"],
    promotions:r=>[r.name,r.product,`${r.discount_value} ${r.discount_type}`,`${r.used_count}/${r.max_uses||"∞"}`,r.ends_at,r.is_active?"فعال":"متوقف"],
    audit:r=>[r.action,`${r.entity_type} #${r.entity_id||"—"}`,r.description,r.created_at]
  };
  panel.innerHTML=`<h2>${({orders:"الطلبات",providers:"المزودون",users:"المستخدمون",promotions:"العروض",audit:"السجل"}[view]||view)} <button class="refresh" onclick="load()">تحديث</button></h2><div class="table-wrap"><table class="table"><thead><tr>${heads.map(h=>`<th>${h}</th>`).join("")}</tr></thead><tbody>${data.map(r=>`<tr>${cells[view](r).map((v,i)=>`<td class="${i===heads.length-1&&String(v).includes("متوقف")?"status bad":""}">${esc(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
async function load(){try{notice(""); if(currentView==="overview") await loadOverview(); else await loadTable(currentView);}catch(e){notice(e.message,true);}}
document.querySelectorAll(".tabs button").forEach((button)=>button.onclick=()=>{currentView=button.dataset.view;document.querySelectorAll(".tabs button").forEach(b=>b.classList.toggle("active",b===button));load();});
load();
