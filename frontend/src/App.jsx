import { useEffect, useState } from 'react'
import { ArrowDownLeft, ArrowUpRight, BadgeCheck, Bell, ChevronDown, History, Landmark, LayoutDashboard, LockKeyhole, LogOut, Menu, Send, ShieldCheck, Users, X } from 'lucide-react'
import './index.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'
const money = (cents) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(cents / 100)

function api(path, options = {}) {
  const token = localStorage.getItem('ll_token')
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: 'Bearer ' + token } : {}),
    ...options.headers
  }
  return fetch(API + path, { ...options, headers })
    .then(async response => {
      const data = await response.json().catch(() => ({}))
      if (response.status === 401) {
        localStorage.removeItem('ll_token')
        window.dispatchEvent(new Event('ledgerline:unauthorized'))
      }
      if (!response.ok) throw new Error(data.error || 'Something went wrong')
      return data
    })
}

function Brand() {
  return <div className="brand"><div className="brand-mark"><span></span><span></span><span></span></div><b>LedgerLine</b></div>
}

function Auth({ onLogin }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (e) => {
    e.preventDefault(); setError(''); setBusy(true)
    try { const data = await api(`/auth/${mode}`, { method: 'POST', body: JSON.stringify(form) }); localStorage.setItem('ll_token', data.token); onLogin(data.user) }
    catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  const demo = async () => { setForm({ email: 'aarav@ledgerline.demo', password: 'Demo@1234' }); try { const data = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email: 'aarav@ledgerline.demo', password: 'Demo@1234' }) }); localStorage.setItem('ll_token', data.token); onLogin(data.user) } catch (err) { setError(err.message) } }
  return <main className="auth-page"><section className="auth-showcase"><Brand/><div className="auth-copy"><div className="eyebrow"><ShieldCheck size={15}/> Secure financial operations</div><h1>Your money.<br/><em>Your control.</em></h1><p>A transparent transaction platform with auditable security decisions at every step.</p><div className="feature-row"><div><BadgeCheck/><span><b>Protected</b>Transfers</span></div><div><History/><span><b>Complete</b>Audit trail</span></div></div></div><div className="demo-disc"><LockKeyhole size={16}/> Educational simulation — no real money</div></section><section className="auth-panel"><div className="auth-box"><div className="mobile-brand"><Brand/></div><h2>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2><p>{mode === 'login' ? 'Sign in to manage your LedgerLine account.' : 'Start your secure demo account in seconds.'}</p><div className="tabs"><button className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>Sign in</button><button className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>Register</button></div>{error && <div className="alert error">{error}</div>}<form onSubmit={submit}>{mode === 'register' && <label>Full name<input value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="Your full name" required/></label>}<label>Email address<input type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} placeholder="you@example.com" required/></label><label>Password<input type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} placeholder="••••••••" required/></label><button className="primary" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in securely' : 'Create account'}</button></form>{mode === 'login' && <button className="demo-button" onClick={demo}>Try the demo account</button>}<small><LockKeyhole size={13}/> Passwords encrypted & sessions protected</small></div></section></main>
}

function Sidebar({ page, setPage, user, logout, open, setOpen }) {
  const items = [{id:'overview', label:'Dashboard', icon:LayoutDashboard},{id:'accounts', label:'Accounts', icon:Landmark},{id:'transfer', label:'Send Money', icon:Send},{id:'history', label:'Transactions', icon:History}, ...(user.role === 'admin' ? [{id:'audit', label:'Audit Log', icon:ShieldCheck},{id:'users', label:'User directory', icon:Users}] : [])]
  return <aside className={`sidebar ${open ? 'open' : ''}`}><div className="sidebar-head"><Brand/><button className="icon-button close" onClick={() => setOpen(false)} aria-label="Close navigation"><X/></button></div><nav>{items.map(({id,label,icon:Icon}) => <button key={id} className={page===id?'active':''} onClick={() => {setPage(id); setOpen(false)}}><Icon/><span>{label}</span></button>)}</nav><div className="sidebar-user"><div className="avatar">{user.name.split(' ').map(x=>x[0]).slice(0,2).join('')}</div><div><b>{user.name}</b><span>{user.role === 'admin' ? 'Administrator' : 'Personal account'}</span></div><button onClick={logout} title="Sign out" aria-label="Sign out"><LogOut/></button></div></aside>
}

function Overview({ dashboardData, setPage, onSelect }) {
  const u = dashboardData.user; const transactions = dashboardData.transactions
  const incoming = transactions.filter(t=>t.type==='credit').reduce((n,t)=>n+t.amountCents,0)
  const outgoing = transactions.filter(t=>t.type==='debit').reduce((n,t)=>n+t.amountCents,0)
  return <>
    <div className="dashboard-heading"><div><span>Dashboard</span><h1>Good morning, {u.name.split(' ')[0]}</h1><p>Account summary and recent activity</p></div><div className="dashboard-actions"><button className="primary compact" onClick={()=>setPage('transfer')}><Send/> Send Money</button><button className="secondary-button" onClick={()=>setPage('history')}><History/> View Transactions</button></div></div>
    <div className="dashboard-summary final-summary">
      <div className="summary-card balance-card"><div><span>Available Balance</span><strong>{money(u.balanceCents)}</strong></div><small>{u.accountNumber} · Primary account</small></div>
      <div className="summary-card"><div className="summary-icon received"><ArrowDownLeft/></div><div><span>Money Received</span><strong>{money(incoming)}</strong></div></div>
      <div className="summary-card"><div className="summary-icon sent"><ArrowUpRight/></div><div><span>Money Sent</span><strong>{money(outgoing)}</strong></div></div>
    </div>
    <section className="panel activity recent-panel"><div className="panel-head"><div><h2>Recent transactions</h2><p>Latest account activity</p></div><button onClick={()=>setPage('history')}>View all transactions</button></div><TransactionList rows={transactions.slice(0,5)} empty="No transactions yet" onSelect={onSelect}/></section>
  </>
}

function TransactionList({ rows, empty, onSelect }) {
  if (!rows.length) return <div className="empty"><History/><h3>{empty}</h3><p>Account activity will appear here.</p></div>
  return <div className="transaction-table-wrap"><table className="transaction-table"><thead><tr><th>Transaction</th><th>Date</th><th>Status</th><th className="amount-column">Amount</th></tr></thead><tbody>{rows.map(tx => {
    const date = new Date(tx.createdAt)
    return <tr key={tx.id} onClick={() => onSelect?.(tx.id)}>
      <td><div className="table-transaction"><div className={`tx-icon ${tx.type}`}>{tx.type==='credit'?<ArrowDownLeft/>:<ArrowUpRight/>}</div><div><b>{tx.counterparty}</b><span>{tx.description}</span></div></div></td>
      <td><span className="table-date">{date.toLocaleDateString(undefined,{day:'2-digit',month:'short',year:'numeric'})}</span><small>{date.toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'})}</small></td>
      <td><span className="transaction-status">Completed</span></td>
      <td className={`amount-column ${tx.type}`}><strong>{tx.type==='credit'?'+':'−'}{money(tx.amountCents)}</strong><small>{tx.type==='credit'?'Received':'Sent'}</small></td>
    </tr>
  })}</tbody></table></div>
}

function Accounts({ dashboardData, setPage }) {
  const u = dashboardData.user
  return <><div className="page-title"><div><span>Banking</span><h1>Accounts</h1><p>Details for your LedgerLine simulation account.</p></div></div><section className="panel account-detail"><div className="account-detail-head"><div className="account-symbol"><Landmark/></div><div><span>Primary account</span><h2>{money(u.balanceCents)}</h2></div><span className="account-state">Active</span></div><dl><div><dt>Account holder</dt><dd>{u.name}</dd></div><div><dt>Account number</dt><dd>{u.accountNumber}</dd></div><div><dt>Account type</dt><dd>Personal simulation</dd></div><div><dt>Currency</dt><dd>Indian Rupee (INR)</dd></div></dl><button className="secondary-button" onClick={()=>setPage('transfer')}><Send/> Make a transfer</button></section></>
}

function Transfer({ recipients, refresh, setPage }) {
  const [form,setForm]=useState({recipientId:'',amount:'',description:''}); const [error,setError]=useState(''); const [success,setSuccess]=useState(''); const [busy,setBusy]=useState(false)
  const submit=async e=>{e.preventDefault();setError('');setSuccess('');setBusy(true);try{const data=await api('/transfers',{method:'POST',body:JSON.stringify({...form,amount:Number(form.amount)})});setSuccess(`${data.message} · ${data.transactionId}`);setForm({recipientId:'',amount:'',description:''});await refresh();setTimeout(()=>setPage('history'),1200)}catch(err){setError(err.message)}finally{setBusy(false)}}
  return <><div className="page-title"><div><span>Payments</span><h1>Transfer money</h1><p>Send simulation funds securely to another account.</p></div></div><div className="transfer-layout"><form className="panel transfer-form" onSubmit={submit}><h2>Transfer details</h2>{error&&<div className="alert error">{error}</div>}{success&&<div className="alert success">{success}</div>}<label>Recipient<select value={form.recipientId} onChange={e=>setForm({...form,recipientId:e.target.value})} required><option value="">Select recipient</option>{recipients.map(r=><option key={r.id} value={r.id}>{r.name} · {r.accountNumber}</option>)}</select></label><label>Amount <small>INR</small><div className="amount-input"><span>₹</span><input type="number" min="0.01" step="0.01" value={form.amount} onChange={e=>setForm({...form,amount:e.target.value})} required/></div></label><label>Reference note<input maxLength="120" value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="What is this payment for?"/></label><button className="primary" disabled={busy}><Send/>{busy?'Processing securely…':'Review & transfer'}</button></form><aside className="panel security-note"><div className="security-ring"><ShieldCheck/></div><h2>Protected by design</h2><ul><li>Identity verified by JWT</li><li>Balance checked before debit</li><li>Atomic database transaction</li><li>Every decision written to audit</li></ul><div className="simulation"><LockKeyhole/>Simulation only · No real funds</div></aside></div></>
}

function HistoryPage({ transactions, onSelect }) { const [filter,setFilter]=useState('all'); const rows=transactions.filter(t=>filter==='all'||t.type===filter); return <><div className="page-title"><div><span>Activity</span><h1>Transactions</h1><p>Review and trace every account movement.</p></div></div><section className="panel"><div className="history-toolbar"><h2>Transaction history</h2><div className="segmented"><button className={filter==='all'?'active':''} onClick={()=>setFilter('all')}>All</button><button className={filter==='credit'?'active':''} onClick={()=>setFilter('credit')}>Received</button><button className={filter==='debit'?'active':''} onClick={()=>setFilter('debit')}>Sent</button></div></div><TransactionList rows={rows} empty="No matching transactions" onSelect={onSelect}/></section></> }

function Admin({ type }) {
 const [rows,setRows]=useState([]); const [error,setError]=useState('')
 useEffect(()=>{api(type==='audit'?'/admin/audit':'/admin/users').then(setRows).catch(e=>setError(e.message))},[type])
 return <><div className="page-title"><div><span>Administrator</span><h1>{type==='audit'?'Security audit':'User directory'}</h1><p>{type==='audit'?'Immutable record of authentication and authorization decisions.':'All registered LedgerLine accounts.'}</p></div></div>{error&&<div className="alert error">{error}</div>}<section className="panel table-wrap"><table><thead><tr>{type==='audit'?<><th>Time</th><th>Actor</th><th>Action</th><th>Decision</th><th>Details</th></>:<><th>User</th><th>Email</th><th>Role</th><th>Account</th><th>Balance</th></>}</tr></thead><tbody>{rows.map((r,i)=><tr key={r.id||i}>{type==='audit'?<><td>{new Date(r.created_at).toLocaleString()}</td><td>{r.user_name||'Anonymous'}<small>{r.ip_address}</small></td><td>{r.action}</td><td><span className={`decision ${r.decision.toLowerCase()}`}>{r.decision}</span></td><td>{r.details}</td></>:<><td><b>{r.name}</b></td><td>{r.email}</td><td>{r.role}</td><td>{r.account_number}</td><td>{money(r.balance_cents)}</td></>}</tr>)}</tbody></table>{!rows.length&&!error&&<div className="empty"><ShieldCheck/><p>Loading records…</p></div>}</section></>
}

export default function App(){
 const [user,setUser]=useState(null);const [page,setPage]=useState('overview');const [dashboardData,setDashboardData]=useState(null);const [recipients,setRecipients]=useState([]);const [transactions,setTransactions]=useState([]); const [menu,setMenu]=useState(false);const [loading,setLoading]=useState(()=>Boolean(localStorage.getItem('ll_token'))); const [transactionDetail,setTransactionDetail]=useState(null); const [detailError,setDetailError]=useState(''); const [headerMenu,setHeaderMenu]=useState(null)
 const pageTitles={overview:'Dashboard',transfer:'Transfer',history:'Transactions',accounts:'Accounts',audit:'Audit Log',users:'User directory'}
 const refresh=async()=>{const data=await api('/dashboard');setDashboardData(data);setTransactions(data.transactions);setUser(data.user)}
 // Session restoration is asynchronous and belongs in this mount effect.
 // oxlint-disable-next-line react/set-state-in-effect
 useEffect(()=>{if(localStorage.getItem('ll_token'))refresh().catch(()=>localStorage.removeItem('ll_token')).finally(()=>setLoading(false))},[]) ; useEffect(()=>{if(user){api('/recipients').then(setRecipients).catch(()=>{})}},[user])
 const logout=()=>{api('/auth/logout',{method:'POST'}).catch(()=>{}).finally(()=>{localStorage.removeItem('ll_token');setUser(null);setDashboardData(null);setPage('overview')})}
 useEffect(()=>{const expire=()=>{setUser(null);setDashboardData(null);setPage('overview');setLoading(false)};window.addEventListener('ledgerline:unauthorized',expire);return()=>window.removeEventListener('ledgerline:unauthorized',expire)},[])
 if(loading)return <div className="loading"><Brand/><div className="spinner"/></div>
 if(!user||!dashboardData)return <Auth onLogin={u=>{setUser(u);refresh().catch(()=>{})}} />
 const openTransaction=async id=>{setDetailError('');try{setTransactionDetail(await api(`/transactions/${encodeURIComponent(id)}`))}catch(error){setDetailError(error.message)}}
 return <div className="app-shell"><Sidebar page={page} setPage={setPage} user={user} logout={logout} open={menu} setOpen={setMenu}/>{menu&&<div className="overlay" onClick={()=>setMenu(false)}/>}<main className="main"><header className="topbar"><button className="icon-button menu" onClick={()=>setMenu(true)} aria-label="Open navigation"><Menu/></button><div className="topbar-context"><span>LedgerLine banking</span><b>{pageTitles[page]}</b></div><div className="topbar-actions"><span className="secure-status"><i></i>Session secure</span><div className="header-popover-wrap"><button className={`notification-button ${headerMenu==='notifications'?'active':''}`} aria-label="Notifications" aria-expanded={headerMenu==='notifications'} onClick={()=>setHeaderMenu(headerMenu==='notifications'?null:'notifications')}><Bell/></button>{headerMenu==='notifications'&&<div className="header-popover notification-popover"><b>Notifications</b><p>No new security alerts.</p><small>Your session is protected.</small></div>}</div><div className="header-popover-wrap"><button className={`profile-button ${headerMenu==='profile'?'active':''}`} aria-label="Account menu" aria-expanded={headerMenu==='profile'} onClick={()=>setHeaderMenu(headerMenu==='profile'?null:'profile')}><div className="avatar small">{user.name.split(' ').map(x=>x[0]).slice(0,2).join('')}</div><span><b>{user.name}</b><small>{user.role === 'admin' ? 'Administrator' : 'Personal account'}</small></span><ChevronDown/></button>{headerMenu==='profile'&&<div className="header-popover profile-popover"><button onClick={()=>{setHeaderMenu(null);setPage('accounts')}}><Landmark/> Account details</button><button onClick={()=>{setHeaderMenu(null);logout()}}><LogOut/> Sign out</button></div>}</div></div></header><div className="content">{page==='overview'&&<Overview dashboardData={dashboardData} setPage={setPage} onSelect={openTransaction}/>} {page==='transfer'&&<Transfer recipients={recipients} refresh={refresh} setPage={setPage}/>} {page==='history'&&<HistoryPage transactions={transactions} onSelect={openTransaction}/>} {page==='accounts'&&<Accounts dashboardData={dashboardData} setPage={setPage}/>} {page==='audit'&&<Admin type="audit"/>} {page==='users'&&<Admin type="users"/>}</div></main>{(transactionDetail||detailError)&&<div className="detail-backdrop" role="presentation" onMouseDown={()=>{setTransactionDetail(null);setDetailError('')}}><section className="detail-modal" role="dialog" aria-modal="true" aria-label="Transaction details" onMouseDown={event=>event.stopPropagation()}><button className="icon-button detail-close" onClick={()=>{setTransactionDetail(null);setDetailError('')}} aria-label="Close"><X/></button><div className="detail-heading"><div className="security-ring"><BadgeCheck/></div><div><span>Transaction receipt</span><h2>{transactionDetail?.id||'Unavailable'}</h2></div></div>{detailError?<div className="alert error">{detailError}</div>:<><div className="detail-amount">{money(transactionDetail.amountCents)}</div><dl><div><dt>Sender</dt><dd>{transactionDetail.senderName}<small>{transactionDetail.senderAccount}</small></dd></div><div><dt>Recipient</dt><dd>{transactionDetail.recipientName}<small>{transactionDetail.recipientAccount}</small></dd></div><div><dt>Status</dt><dd><span className="decision allowed">{transactionDetail.status}</span></dd></div><div><dt>Reference</dt><dd>{transactionDetail.description}</dd></div><div><dt>Completed</dt><dd>{new Date(transactionDetail.createdAt).toLocaleString()}</dd></div></dl></>}</section></div>}</div>
}
