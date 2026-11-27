import os, secrets, hashlib, hmac, calendar
from datetime import date, timedelta
from fastapi import Request, FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel
engine=create_engine(os.getenv('DATABASE_URL','sqlite:///housing.db'))
app=FastAPI(title='Housing Hub')
app.add_middleware(CORSMiddleware,allow_origins=[x for x in os.getenv('CORS_ORIGINS','http://localhost:8000').split(',') if x],allow_methods=['*'],allow_headers=['*'])
DDL=['users (id VARCHAR(64) PRIMARY KEY, name VARCHAR(100), email VARCHAR(150) UNIQUE, password VARCHAR(200))','sessions (id VARCHAR(64) PRIMARY KEY, user_id VARCHAR(64))','hubs (id VARCHAR(64) PRIMARY KEY, owner VARCHAR(64), name VARCHAR(100))','members (hub VARCHAR(64), user_id VARCHAR(64), PRIMARY KEY(hub,user_id))','invites (id VARCHAR(64) PRIMARY KEY, hub VARCHAR(64), expires VARCHAR(10))','categories (id VARCHAR(64) PRIMARY KEY, hub VARCHAR(64), name VARCHAR(100), icon VARCHAR(40))','tasks (id VARCHAR(64) PRIMARY KEY, hub VARCHAR(64), category VARCHAR(64), assignee VARCHAR(64), due VARCHAR(10), done INTEGER)','groceries (id VARCHAR(64) PRIMARY KEY, hub VARCHAR(64), name VARCHAR(100), done INTEGER)','bills (id VARCHAR(64) PRIMARY KEY, hub VARCHAR(64), name VARCHAR(100), cents INTEGER, due VARCHAR(10), done INTEGER)']
with engine.begin() as c:
 for ddl in DDL: c.execute(text('CREATE TABLE IF NOT EXISTS '+ddl))
def uid(): return secrets.token_hex(16)
def query(sql,**p):
 with engine.begin() as c:
  r=c.execute(text(sql),p)
  return [dict(x) for x in r.mappings()] if r.returns_rows else []
def one(sql,**p):
 r=query(sql,**p); return r[0] if r else None
def fail(msg,code=400): raise HTTPException(code,msg)
def password(p,s): return hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(s),200000).hex()
def user(authorization:str=Header('')):
 r=one('SELECT user_id FROM sessions WHERE id=:id',id=authorization.removeprefix('Bearer '));
 if not r: fail('Sign in required',401)
 return r['user_id']
def access(h,u,master=False):
 r=one('SELECT * FROM hubs WHERE id=:h',h=h)
 if not r or (r['owner']!=u and (master or not one('SELECT * FROM members WHERE hub=:h AND user_id=:u',h=h,u=u))): fail('Access denied',403)
 return r['owner']==u
class Auth(BaseModel):
 email:str; password:str; name:str=''
class Item(BaseModel):
 property_type:str='Apartment'; bedrooms:int=2; bathrooms:int=1
 name:str=''; icon:str='✨'; category:str=''; assignee:str=''; due:str=''; cents:int=0; done:bool=True
@app.post('/register')
def register(a:Auth):
 if len(a.password)<8 or not a.name.strip() or '@' not in a.email: fail('Name, email and 8-character password required')
 if one('SELECT id FROM users WHERE email=:e',e=a.email.lower()): fail('Email already registered')
 s=secrets.token_hex(16); query('INSERT INTO users VALUES (:i,:n,:e,:p)',i=uid(),n=a.name,e=a.email.lower(),p=s+':'+password(a.password,s)); return login(a)
@app.post('/login')
def login(a:Auth):
 r=one('SELECT * FROM users WHERE email=:e',e=a.email.lower())
 if not r: fail('Invalid credentials',401)
 s,p=r['password'].split(':')
 if not hmac.compare_digest(p,password(a.password,s)): fail('Invalid credentials',401)
 t=secrets.token_hex(32); query('INSERT INTO sessions VALUES (:t,:u)',t=t,u=r['id']); return {'token':t,'id':r['id'],'name':r['name']}
with engine.begin() as c:
 c.execute(text('CREATE TABLE IF NOT EXISTS home_plans (hub VARCHAR(64) PRIMARY KEY, property_type VARCHAR(20), bedrooms INTEGER, bathrooms INTEGER)'))
def plan(h):
 return one('SELECT property_type,bedrooms,bathrooms FROM home_plans WHERE hub=:h',h=h)
@app.get('/hubs')
def hubs(u=Depends(user)):
 rows=query('SELECT * FROM hubs WHERE owner=:u OR id IN (SELECT hub FROM members WHERE user_id=:u)',u=u)
 for r in rows: r['plan']=plan(r['id'])
 return rows

@app.post('/hubs')
def create(a:Item,u=Depends(user)):
 if not a.name.strip(): fail('Name required')
 if len(query('SELECT id FROM hubs WHERE owner=:u',u=u))>=10: fail('Ten hub limit')
 validate_plan(a)
 h=uid()
 with engine.begin() as c:
  c.execute(text('INSERT INTO hubs VALUES (:h,:u,:n)'),dict(h=h,u=u,n=a.name))
  c.execute(text('INSERT INTO home_plans VALUES (:h,:t,:b,:w)'),dict(h=h,t=a.property_type,b=a.bedrooms,w=a.bathrooms))
 return {'id':h}
def validate_plan(a):
 if a.property_type not in ('House','Apartment') or not 0<=a.bedrooms<=6 or not 1<=a.bathrooms<=4: fail('Choose a valid home layout')
@app.put('/hubs/{h}/plan')
def update_plan(h:str,a:Item,u=Depends(user)):
 access(h,u,True); validate_plan(a)
 with engine.begin() as c:
  c.execute(text('DELETE FROM home_plans WHERE hub=:h'),dict(h=h))
  c.execute(text('INSERT INTO home_plans VALUES (:h,:t,:b,:w)'),dict(h=h,t=a.property_type,b=a.bedrooms,w=a.bathrooms))
 return plan(h)

@app.post('/hubs/{h}/invite')
def invite(h:str,request:Request,u=Depends(user)):
 access(h,u,True); t=uid(); query('INSERT INTO invites VALUES (:t,:h,:e)',t=t,h=h,e=str(date.today()+timedelta(days=7))); return {'link':(os.getenv('PUBLIC_BASE_URL') or str(request.base_url).rstrip('/'))+'/web/?join='+t,'code':t}
@app.post('/join/{t}')
def join(t:str,u=Depends(user)):
 r=one('SELECT * FROM invites WHERE id=:t',t=t)
 if not r or r['expires']<str(date.today()): fail('Invalid or expired invitation')
 h=r['hub']; owner=one('SELECT owner FROM hubs WHERE id=:h',h=h)['owner']
 if owner==u or one('SELECT * FROM members WHERE hub=:h AND user_id=:u',h=h,u=u): return {'id':h}
 if len(query('SELECT * FROM members WHERE hub=:h',h=h))>=12: fail('Twelve guest limit')
 from datetime import datetime, timezone
 with engine.begin() as c:
  c.execute(text('INSERT INTO members VALUES (:h,:u)'),dict(h=h,u=u))
  c.execute(text('INSERT INTO membership_starts VALUES (:h,:u,:t)'),dict(h=h,u=u,t=datetime.now(timezone.utc).isoformat()))
 return {'id':h}
@app.get('/hubs/{h}')
def board(h:str,u=Depends(user)):
 master=access(h,u); tasks=query('SELECT tasks.*,categories.name,categories.icon FROM tasks JOIN categories ON tasks.category=categories.id WHERE tasks.hub=:h'+('' if master else ' AND assignee=:u'),h=h,u=u)
 bills=query('SELECT * FROM bills WHERE hub=:h',h=h); today=str(date.today()); done=sum(t['done'] for t in tasks)
 return dict(plan=plan(h),master=master,members=query('SELECT id,name FROM users WHERE id IN (SELECT user_id FROM members WHERE hub=:h) OR id=(SELECT owner FROM hubs WHERE id=:h)',h=h),categories=query('SELECT * FROM categories WHERE hub=:h',h=h),tasks=tasks,groceries=query('SELECT * FROM groceries WHERE hub=:h',h=h),bills=bills,analytics={'total':len(tasks),'completed':done,'rate':round(100*done/max(1,len(tasks)),1)},reminders=[b['name']+' due '+b['due'] for b in bills if not b['done'] and b['due']<=str(date.today()+timedelta(days=3))])
# V3 additive migration: existing household records remain intact.
with engine.begin() as c:
 c.execute(text('CREATE TABLE IF NOT EXISTS messages (id VARCHAR(64) PRIMARY KEY, hub VARCHAR(64), sender VARCHAR(64), recipient VARCHAR(64), body VARCHAR(1000), sent VARCHAR(40))'))
with engine.begin() as c:
 c.execute(text('CREATE TABLE IF NOT EXISTS membership_starts (hub VARCHAR(64), user_id VARCHAR(64), joined VARCHAR(40), PRIMARY KEY(hub,user_id))'))
@app.delete('/hubs/{h}/members/{member}')
def remove_member(h:str,member:str,u=Depends(user)):
 access(h,u,True)
 if member==u: fail('Cannot remove owner')
 with engine.begin() as c:
  p=dict(h=h,m=member)
  if not c.execute(text('DELETE FROM members WHERE hub=:h AND user_id=:m'),p).rowcount: fail('Member not found',404)
  c.execute(text('DELETE FROM membership_starts WHERE hub=:h AND user_id=:m'),p)
  c.execute(text('DELETE FROM invites WHERE hub=:h'),p)
 return {'ok':True}
class Profile(BaseModel):
 name:str
class Message(BaseModel):
 recipient:str
 body:str
@app.get('/profile')
def profile(u=Depends(user)):
 return one('SELECT id,name,email FROM users WHERE id=:u',u=u)
@app.patch('/profile')
def edit_profile(a:Profile,u=Depends(user)):
 n=a.name.strip()
 if not 1<=len(n)<=100: fail('Name must contain 1–100 characters')
 query('UPDATE users SET name=:n WHERE id=:u',n=n,u=u)
 return profile(u)
@app.get('/hubs/{h}/messages')
def messages(h:str,u=Depends(user)):
 access(h,u)
 start=one('SELECT joined FROM membership_starts WHERE hub=:h AND user_id=:u',h=h,u=u)
 return query("SELECT messages.*, users.name AS sender_name FROM messages JOIN users ON users.id=messages.sender WHERE hub=:h AND (sender=:u OR recipient=:u OR recipient='group') AND sent>=:t ORDER BY sent,id",h=h,u=u,t=start['joined'] if start else '')
@app.post('/hubs/{h}/messages')
def send_message(h:str,a:Message,u=Depends(user)):
 master=access(h,u); owner=one('SELECT owner FROM hubs WHERE id=:h',h=h)['owner']
 if a.recipient==u or (a.recipient!='group' and a.recipient not in residents(h)): fail('Invalid recipient',403)
 body=a.body.strip()
 if not 1<=len(body)<=1000: fail('Message must contain 1–1000 characters')
 from datetime import datetime, timezone
 query('INSERT INTO messages VALUES (:i,:h,:s,:r,:b,:t)',i=uid(),h=h,s=u,r=a.recipient,b=body,t=datetime.now(timezone.utc).isoformat())
 return {'ok':True}
@app.post('/hubs/{h}/{kind}')
def add(h:str,kind:str,a:Item,u=Depends(user)):
 if kind not in ['categories','tasks','groceries','bills']: fail('Unknown module',404)
 access(h,u,kind!='groceries'); i=uid()
 if kind!='tasks' and not a.name.strip(): fail('Name required')
 if kind=='categories':
  if len(query('SELECT id FROM categories WHERE hub=:h',h=h))>=12: fail('Twelve category limit')
  query('INSERT INTO categories VALUES (:i,:h,:n,:v)',i=i,h=h,n=a.name,v=a.icon)
 elif kind=='tasks':
  if not one('SELECT id FROM categories WHERE id=:c AND hub=:h',c=a.category,h=h): fail('Invalid category')
  if not one('SELECT id FROM users WHERE id=:u AND (id IN (SELECT user_id FROM members WHERE hub=:h) OR id=(SELECT owner FROM hubs WHERE id=:h))',u=a.assignee,h=h): fail('Invalid assignee')
  try: date.fromisoformat(a.due)
  except ValueError: fail('Use YYYY-MM-DD')
  query('INSERT INTO tasks VALUES (:i,:h,:c,:u,:d,0)',i=i,h=h,c=a.category,u=a.assignee,d=a.due)
 elif kind=='groceries': query('INSERT INTO groceries VALUES (:i,:h,:n,0)',i=i,h=h,n=a.name)
 else:
  if a.cents<=0: fail('Positive amount required')
  d=date.today(); due=a.due or str(d.replace(day=calendar.monthrange(d.year,d.month)[1]))
  try: date.fromisoformat(due)
  except ValueError: fail('Invalid date')
  query('INSERT INTO bills VALUES (:i,:h,:n,:c,:d,0)',i=i,h=h,n=a.name,c=a.cents,d=due)
 return {'id':i}
@app.patch('/hubs/{h}/{kind}/{i}')
def complete(h:str,kind:str,i:str,a:Item,u=Depends(user)):
 if kind not in ['tasks','groceries','bills']: fail('Unknown module',404)
 master=access(h,u,kind=='bills'); r=one(f'SELECT * FROM {kind} WHERE id=:i AND hub=:h',i=i,h=h)
 if not r or (kind=='tasks' and not master and r['assignee']!=u): fail('Access denied',403)
 if kind=='bills' and one('SELECT bill FROM contributions WHERE bill=:i',i=i): fail('Use individual payment controls')
 query(f'UPDATE {kind} SET done=:d WHERE id=:i AND hub=:h',d=int(a.done),i=i,h=h); return {'ok':True}

# V2: workload recommendation and fairness (Jain index, equal task weights).
@app.get('/hubs/{h}/insights')
def insights(h:str,u=Depends(user)):
 access(h,u,True)
 month=date.today().strftime('%Y-%m')
 members=query('SELECT id,name FROM users WHERE id IN (SELECT user_id FROM members WHERE hub=:h) OR id=(SELECT owner FROM hubs WHERE id=:h)',h=h)
 tasks=query('SELECT * FROM tasks WHERE hub=:h AND due LIKE :m',h=h,m=month+'%')
 loads=[dict(id=m['id'],name=m['name'],assigned=sum(t['assignee']==m['id'] for t in tasks),pending=sum(t['assignee']==m['id'] and not t['done'] for t in tasks)) for m in members]
 counts=[m['assigned'] for m in loads]; squares=sum(x*x for x in counts)
 score=round(100*sum(counts)**2/(len(counts)*squares),1) if squares else None
 return dict(month=month,fairness=score,loads=loads,recommended=min(loads,key=lambda m:(m['assigned'],m['pending'],m['id'])) if loads else None,overdue=sum(not t['done'] and t['due']<str(date.today()) for t in tasks))
@app.patch('/hubs/{h}/studio/category/{i}')
def rename_category(h:str,i:str,a:Item,u=Depends(user)):
 access(h,u,True)
 if not a.name.strip() or not one('SELECT id FROM categories WHERE hub=:h AND id=:i',h=h,i=i): fail('Invalid category or name')
 query('UPDATE categories SET name=:n,icon=:v WHERE hub=:h AND id=:i',h=h,i=i,n=a.name, v=a.icon); return {'ok':True}
from fastapi.staticfiles import StaticFiles
from pathlib import Path
app.mount('/web',StaticFiles(directory=Path(__file__).parent/'web',html=True),name='web')

# V4: individual contributions, additive schema.
with engine.begin() as c:
 c.execute(text('CREATE TABLE IF NOT EXISTS contributions (bill VARCHAR(64), user_id VARCHAR(64), cents INTEGER, paid INTEGER, PRIMARY KEY(bill,user_id))'))
@app.post('/logout')
def logout(authorization:str=Header(''),u=Depends(user)):
 query('DELETE FROM sessions WHERE id=:i',i=authorization.removeprefix('Bearer ')); return {'ok':True}
@app.get('/hubs/{h}/finance')
def finance(h:str,u=Depends(user)):
 access(h,u); bills=query('SELECT * FROM bills WHERE hub=:h',h=h)
 for b in bills:
  b['shares']=query('SELECT contributions.*,users.name FROM contributions JOIN users ON users.id=contributions.user_id WHERE bill=:b ORDER BY user_id',b=b['id'])
 return bills
@app.post('/hubs/{h}/finance/{i}/split')
def split(h:str,i:str,u=Depends(user)):
 access(h,u,True)
 with engine.begin() as c:
  b=c.execute(text('SELECT * FROM bills WHERE id=:i AND hub=:h'),dict(i=i,h=h)).mappings().first()
  if not b: fail('Bill not found',404)
  if c.execute(text('SELECT bill FROM contributions WHERE bill=:i'),dict(i=i)).first(): fail('Already split')
  people=c.execute(text('SELECT id FROM users WHERE id IN (SELECT user_id FROM members WHERE hub=:h) OR id=(SELECT owner FROM hubs WHERE id=:h) ORDER BY id'),dict(h=h)).scalars().all()
  q,r=divmod(b['cents'],len(people))
  for j,m in enumerate(people): c.execute(text('INSERT INTO contributions VALUES (:i,:u,:c,:p)'),dict(i=i,u=m,c=q+int(j<r),p=int(b['done'])))
 return {'ok':True}
@app.patch('/hubs/{h}/finance/{i}/{member}')
def payment(h:str,i:str,member:str,a:Item,u=Depends(user)):
 access(h,u,True)
 with engine.begin() as c:
  if not c.execute(text('SELECT bill FROM contributions JOIN bills ON bills.id=contributions.bill WHERE bill=:i AND user_id=:m AND hub=:h'),dict(i=i,m=member,h=h)).first(): fail('Share not found',404)
  c.execute(text('UPDATE contributions SET paid=:p WHERE bill=:i AND user_id=:m'),dict(p=int(a.done),i=i,m=member))
  pending=c.execute(text('SELECT COUNT(*) FROM contributions WHERE bill=:i AND paid=0'),dict(i=i)).scalar()
  c.execute(text('UPDATE bills SET done=:d WHERE id=:i'),dict(d=int(not pending),i=i))
 return {'ok':True}

# Separate expense ledger; legacy bills remain intact.
with engine.begin() as c:
 c.execute(text('CREATE TABLE IF NOT EXISTS expenses (id VARCHAR(64) PRIMARY KEY, hub VARCHAR(64), name VARCHAR(100), payer VARCHAR(64), cents INTEGER)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS expense_shares (expense VARCHAR(64), member VARCHAR(64), cents INTEGER, PRIMARY KEY(expense,member))'))
 c.execute(text('CREATE TABLE IF NOT EXISTS settlements (id VARCHAR(64) PRIMARY KEY, hub VARCHAR(64), sender VARCHAR(64), recipient VARCHAR(64), cents INTEGER)'))
class Expense(BaseModel):
 name:str; payer:str; cents:int; shares:dict[str,int]
class Settlement(BaseModel):
 sender:str; recipient:str; cents:int
def residents(h):
 return {x['id']:x['name'] for x in query('SELECT id,name FROM users WHERE id IN (SELECT user_id FROM members WHERE hub=:h) OR id=(SELECT owner FROM hubs WHERE id=:h)',h=h)}
@app.get('/hubs/{h}/ledger/summary')
def ledger(h:str,u=Depends(user)):
 access(h,u); names=residents(h); balances={k:0 for k in names}; expenses=query('SELECT * FROM expenses WHERE hub=:h',h=h); settlements=query('SELECT * FROM settlements WHERE hub=:h',h=h)
 for e in expenses:
  e['shares']=query('SELECT * FROM expense_shares WHERE expense=:i',i=e['id']); balances[e['payer']]=balances.get(e['payer'],0)+e['cents']
  for x in e['shares']: balances[x['member']]=balances.get(x['member'],0)-x['cents']
 for x in settlements: balances[x['sender']]=balances.get(x['sender'],0)+x['cents']; balances[x['recipient']]=balances.get(x['recipient'],0)-x['cents']
 return dict(expenses=expenses,settlements=settlements,balances=[dict(id=k,name=names.get(k,'Former member'),cents=v) for k,v in balances.items()])
@app.post('/hubs/{h}/ledger/expense')
def expense(h:str,a:Expense,u=Depends(user)):
 access(h,u,True); names=residents(h)
 if not a.name.strip() or len(a.name)>100 or not 0<a.cents<=100000000 or a.payer not in names or not a.shares or not set(a.shares)<=set(names) or any(v<0 for v in a.shares.values()) or sum(a.shares.values())!=a.cents: fail('Invalid expense or allocation')
 i=uid()
 with engine.begin() as c:
  c.execute(text('INSERT INTO expenses VALUES (:i,:h,:n,:p,:v)'),dict(i=i,h=h,n=a.name,p=a.payer,v=a.cents))
  for m,v in a.shares.items(): c.execute(text('INSERT INTO expense_shares VALUES (:i,:m,:v)'),dict(i=i,m=m,v=v))
 return {'id':i}
@app.post('/hubs/{h}/ledger/settlement')
def settle(h:str,a:Settlement,u=Depends(user)):
 access(h,u,True); b={x['id']:x['cents'] for x in ledger(h,u)['balances']}
 if a.sender==a.recipient or a.sender not in b or a.recipient not in b or not 0<a.cents<=min(-b[a.sender],b[a.recipient]): fail('Settlement exceeds outstanding balance')
 query('INSERT INTO settlements VALUES (:i,:h,:s,:r,:v)',i=uid(),h=h,s=a.sender,r=a.recipient,v=a.cents); return {'ok':True}
