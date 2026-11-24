import os,tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as d:
 os.environ['DATABASE_URL']='sqlite:///'+str(Path(d)/'test.db')
 from main import app
 from fastapi.testclient import TestClient
 c=TestClient(app)
 def reg(n):
  r=c.post('/register',json={'name':n,'email':n+'@test.com','password':'testpass123'});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['token']}
 a=reg('Owner');b=reg('Guest');h=c.post('/hubs',headers=a,json={'name':'Home','property_type':'House','bedrooms':3,'bathrooms':2}).json()['id'];assert c.get('/hubs/'+h,headers=a).json()['plan']['bedrooms']==3
 r=c.post('/hubs/'+h+'/invite',headers=a);assert r.status_code==200,r.text;v=r.json();assert v['link'].endswith(v['code']);assert c.post('/join/'+v['code'],headers=b).status_code==200
 assert c.put('/hubs/'+h+'/plan',headers=b,json={'bedrooms':4}).status_code==403
 assert c.put('/hubs/'+h+'/plan',headers=a,json={'bedrooms':4}).status_code==200
 assert c.patch('/profile',headers=b,json={'name':'New name'}).json()['name']=='New name'
 bill=c.post('/hubs/'+h+'/bills',headers=a,json={'name':'Electricity','cents':101}).json()['id'];assert c.post('/hubs/'+h+'/finance/'+bill+'/split',headers=a).status_code==200
 shares=c.get('/hubs/'+h+'/finance',headers=a).json()[0]['shares'];assert sum(x['cents'] for x in shares)==101
 assert c.get('/web/').status_code==200;assert c.get('/web/assets/house.png').status_code==200
 print('PASS: registration, layout, invitation, join, permission, profile, bill rounding, web assets')
