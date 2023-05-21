from datetime import datetime,date,timedelta
import os

from flask import Flask, redirect,render_template, request, session,url_for,Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin,login_user,LoginManager,login_required,logout_user,current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail,Message
from sqlalchemy import func,desc
from celery import Celery
from celery.schedules import crontab
import pdfkit

import pandas as pd
import matplotlib.pyplot as plt
import re
import math
import random
import io,csv
import base64

current_dir=os.path.abspath(os.path.dirname(__file__))
app=Flask(__name__)
bcrypt=Bcrypt(app)
mail = Mail(app)

app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///"+os.path.join(current_dir,"main.sqlite3")
app.config['SECRET_KEY']='thisismysecretkey'
db=SQLAlchemy(app)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME']='Your Email Address'
app.config['MAIL_PASSWORD']='Your Authentication Key'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER']='Your Email Address'
mail = Mail(app)

app.config['CELERY_BROKER_URL'] ='redis://localhost:6379'
app.config['CELERY_RESULT_BACKEND'] ='redis://localhost:6379'
app.config['TIMEZONE']='Asia/Calcutta'
def make_celery(app):
    celery = Celery(
        "app",
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
celery = make_celery(app)

def checkemail(email):
  regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
  if(re.fullmatch(regex, email)):
      return 'true'
  else:
      return 'false'

reg_otp={}
def send_otp(email):
  digits = "0123456789"
  OTP = ""
  for i in range(6) :
        OTP += digits[math.floor(random.random() * 10)]
  message_to_send=f"<b>{OTP}</b>"

  msg = Message("Your Registeration OTP")
  msg.recipients=[email]
  msg.html=message_to_send
  mail.send(msg)
  reg_otp[email]=OTP
  return 'true'

def standardizingListWithCards():
  alllistid=List_table.query.with_entities(List_table.id,List_table.status).filter_by(uid=current_user.id).all()
  new_alllistid=[]
  newdict_alllistid={}
  for i in alllistid:
    new_alllistid.append(i[0])
    newdict_alllistid[i[0]]=i[1]
  for i in new_alllistid:
    total_cards=Card_table.query.with_entities(Card_table.id).filter_by(lid=i).all()
    status=Card_table.query.with_entities(Card_table.status).filter_by(lid=i).all()
    newstatus=[]
    for j in status:
      newstatus.append(j[0])
    newstatus=set(newstatus)
    newstatus=list(newstatus)
    if((len(newstatus)==1) and (newstatus[0]=='Completed') and newdict_alllistid[i]!=newstatus):
      updated_list=List_table.query.filter_by(id=i).first()
      updated_list.status='Completed'
    elif((len(newstatus)==1) and (newstatus[0]=='Active') and newdict_alllistid[i]!=newstatus):
      updated_list=List_table.query.filter_by(id=i).first()
      updated_list.status='Active'
    elif((len(newstatus)==2) and (newdict_alllistid[i]=='Completed')):
      updated_list=List_table.query.filter_by(id=i).first()
      updated_list.status='Active'
    elif(len(total_cards)==0):
      updated_list=List_table.query.filter_by(id=i).first()
      updated_list.status='Completed'
    try:
      db.session.add(updated_list)
      db.session.flush()        
    except Exception as error:
      db.session.rollback()
    db.session.commit()

def standardizeprojectswithlist():
  allprojectid=Project_table.query.with_entities(Project_table.id,Project_table.status).filter(Project_table.project_lead==current_user.id).all()
  new_allprojectid=[]
  newdict_allprojectid={}
  for i in allprojectid:
    new_allprojectid.append(i[0])
    newdict_allprojectid[i[0]]=i[1]
  for i in new_allprojectid:
    total_lists=List_table.query.with_entities(List_table.id).filter_by(pid=i).all()
    status=List_table.query.with_entities(List_table.status).filter_by(pid=i).all()
    newstatus=[]
    for j in status:
      newstatus.append(j[0])
    newstatus=set(newstatus)
    newstatus=list(newstatus)
    updated_project=Project_table.query.filter_by(id=i).first()
    if((len(newstatus)==1) and (newstatus[0]=='Completed') and (newdict_allprojectid[i]!=newstatus)):
      updated_project.status='Completed'
    elif((len(newstatus)==1) and (newstatus[0]=='Active') and newdict_allprojectid[i]!=newstatus):
      updated_project.status='Active'
    elif((len(newstatus)==2) and (newdict_allprojectid[i]=='Completed')):
      updated_project.status='Active'
    elif(len(total_lists)==0):
      updated_project.status='Completed'
    try:
      db.session.add(updated_project)
      db.session.flush()        
    except Exception as error:
      db.session.rollback()
    db.session.commit()
  return('True')
  
login_manager=LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(id):
  return User_registeration.query.get(int(id))

class User_registeration(db.Model,UserMixin):
  __tablename__='user_registeration'
  id=db.Column(db.Integer,primary_key=True,autoincrement=True)
  firstname=db.Column(db.String,nullable=False)
  lastname=db.Column(db.String,nullable=False)
  dateofbirth=db.Column(db.Date,nullable=False)
  emailid=db.Column(db.String,nullable=False)
  username=db.Column(db.String(20),nullable=False,unique=True)
  password=db.Column(db.String(80),nullable=False)
class Project_table(db.Model):
  __tablename__="project_table"
  id=db.Column(db.Integer,primary_key=True,autoincrement=True)
  project_name=db.Column(db.String,nullable=False)
  project_description=db.Column(db.String,nullable=False)
  created_on=db.Column(db.Date)
  status=db.Column(db.String,nullable=False,default='Completed')
  project_lead=db.Column(db.Integer,db.ForeignKey('user_registeration.id'))
class List_table(db.Model):
  __tablename__="list_table"
  id=db.Column(db.Integer,primary_key=True,autoincrement=True)
  list_name=db.Column(db.String,nullable=False)
  list_description=db.Column(db.String,nullable=False)
  created_on=db.Column(db.Date)
  status=db.Column(db.String,nullable=False,default='Completed')
  pid=db.Column(db.Integer,db.ForeignKey('project_table.id'))
  uid=db.Column(db.Integer,db.ForeignKey('user_registeration.id'))
class Card_table(db.Model):
  __tablename__="card_table"
  id=db.Column(db.Integer,primary_key=True,autoincrement=True)
  card_name=db.Column(db.String,nullable=False)
  card_description=db.Column(db.String,nullable=False)
  created_on=db.Column(db.Date)
  due_by=db.Column(db.Date,nullable=False)
  completed_on=db.Column(db.Date)
  status=db.Column(db.String,nullable=False,default='Active')
  lid=db.Column(db.Integer,db.ForeignKey('list_table.id'))
  uid=db.Column(db.Integer,db.ForeignKey('user_registeration.id'))
class Roles_table(db.Model):
  __tablename__='roles_table'
  id=db.Column(db.Integer,primary_key=True,autoincrement=True)
  lid=db.Column(db.Integer,db.ForeignKey('list_table.id'))
  lead_id=db.Column(db.Integer,db.ForeignKey('user_registeration.id'))
  uid=db.Column(db.Integer,db.ForeignKey('user_registeration.id'))
class Follow_table(db.Model):
  __tablename__='follow_table'
  id=db.Column(db.Integer,primary_key=True,autoincrement=True)
  follower_id=db.Column(db.Integer,db.ForeignKey('user_registeration.id'))
  followee_id=db.Column(db.Integer,db.ForeignKey('user_registeration.id'))

@app.route('/',methods=['GET','POST'])
def login():
  if request.method=='GET':
    return render_template('Login.html')
  elif request.method=='POST':
    (username,password)=(request.form['login-username'],request.form['login-password'])
    logindata=[{'login-username':username,'login-password':password}]
    if username:
      if password:
        user=User_registeration.query.filter_by(username=username).first()
        if user is None:
          return render_template('Login.html',datapassed='true',usernotfound='true',data=logindata)
        else:
          if bcrypt.check_password_hash(user.password,password):
            login_user(user)
            return redirect(url_for('dashboard'))
          else:
            return render_template('Login.html',datapassed='true',incorrectpassword='true',data=logindata)
      else:
        return render_template('Login.html',datapassed='true',passwordnotentered='true',data=logindata)
    else:
      return render_template('Login.html',datapassed='true',usernotentered='true',data=logindata)



@app.route('/Registeration',methods=['GET','POST'])
def registeration():
  if request.method=='GET':
    return render_template('Registeration.html')
  elif request.method=='POST':
    (fname,lname,dob,email,username,password,repass,otp)=(request.form['firstname'],request.form['lastname'],request.form['dob'],request.form['emailid'],request.form['registeration-username'],request.form['registeration-password'],request.form['registeration-repassword'],request.form['OTP'])
    userdata=[{'firstname':fname,'lastname':lname,'dob':dob,'emailid':email,'registeration-username':username,'registeration-password':password,'registeration-repassword':repass}]
    if fname:
      if lname:
        if dob:
          x=datetime.strptime(dob,'%Y-%m-%d')
          y=datetime.today()
          if(x<y):
            if email:
              if username:
                if password:
                  if repass:
                    if checkemail(email)!='true':
                      return render_template('Registeration.html',datapassed='true',invalidEmailid='true',data=userdata)
                    if password!=repass:
                      return render_template('Registeration.html',datapassed='true',incorrectPassword='true',data=userdata)
                    userexist=User_registeration.query.filter_by(username=username).first()
                    if userexist:
                      return render_template('Registeration.html',datapassed='true',invalidUsername='true',data=userdata)
                    emailexists=User_registeration.query.filter_by(emailid=email).first()
                    if emailexists:
                      return render_template('Registeration.html',datapassed='true',mailAlreadyExists='true',data=userdata)
                    else:
                      if otp=="******":
                        if(send_otp(email)=='true'):
                          return render_template('Registeration.html',datapassed='true',otpsend='true',data=userdata)
                        else:
                          return render_template('Registeration.html',datapassed='true',generalerror="Error in sendgin OTP",data=userdata)
                      else:
                        if(otp.isnumeric() and len(otp)==6):
                          if(reg_otp[email]==otp):
                            del reg_otp[email]
                            hashedpassword=bcrypt.generate_password_hash(password)
                            dob=datetime.strptime(dob,'%Y-%m-%d')
                            new_user=User_registeration(firstname=fname,lastname=lname,dateofbirth=dob,emailid=email,username=username,password=hashedpassword)
                            try:
                              db.session.add(new_user)
                              db.session.flush()        
                            except Exception as error:
                              db.session.rollback()
                              return render_template('Registeration.html',datapassed='true',generalerror="Cannot login at this point please try again later",data=userdata)
                            db.session.commit()
                            db.session.close()
                            return redirect(url_for('login'))
                          else:
                            return render_template('Registeration.html',datapassed='true',otpsend='true',otperror='true',data=userdata)
                        else:
                          return render_template('Registeration.html',datapassed='true',otpsend='true',otperror='true',data=userdata)
                  else:
                    return render_template('Registeration.html',datapassed='true',repasswordnotfound='true',data=userdata)
                else:
                  return render_template('Registeration.html',datapassed='true',passwordnotfound='true',data=userdata)
              else:
                return render_template('Registeration.html',datapassed='true',usernamenotfound='true',data=userdata)
            else:
              return render_template('Registeration.html',datapassed='true',emailnotfound='true',data=userdata)
          else:
            return render_template('Registeration.html',datapassed='true',dobnotfound='true',data=userdata)
        else:
          return render_template('Registeration.html',datapassed='true',dobnotfound='true',data=userdata)
      else:
        return render_template('Registeration.html',datapassed='true',lnamenotfound='true',data=userdata)
    else:
      return render_template('Registeration.html',datapassed='true',fnamenotfound='true',data=userdata)

@app.route('/Dashboard',methods=['GET','POST'])
@login_required
def dashboard():
  if request.method=='GET':
    standardizingListWithCards()
    standardizeprojectswithlist()
    allactiveprojects=Project_table.query.with_entities(Project_table.id,Project_table.project_name,Project_table.project_description).filter(Project_table.status=='Active',Project_table.project_lead==current_user.id).all()
    for i in range(len(allactiveprojects)):
      allactiveprojects[i]=list(allactiveprojects[i])
    indiviuallistsactive=List_table.query.with_entities(List_table.id,Project_table.project_name,List_table.list_name,List_table.list_description).join(Roles_table,List_table.id==Roles_table.lid).join(Project_table,Project_table.id==List_table.pid).filter(Roles_table.lead_id!=Roles_table.uid,Roles_table.uid==current_user.id,List_table.status=='Active').all()
    for i in range(len(indiviuallistsactive)):
      indiviuallistsactive[i]=list(indiviuallistsactive[i])
    final_activeproject=[]
    if(len(allactiveprojects)!=0):
      for i in allactiveprojects:
        allactivelist=List_table.query.with_entities(List_table.id,List_table.list_name,List_table.list_description).filter(List_table.pid==i[0],List_table.status=='Active').all()
        for j in range(len(allactivelist)):
          allactivelist[j]=list(allactivelist[j])
        final_perlist=[]
        for k in allactivelist:
          allactivecard=Card_table.query.with_entities(Card_table.id,Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by).filter(Card_table.lid==k[0],Card_table.status=='Active').all()
          for m in range(len(allactivecard)):
            allactivecard[m]=list(allactivecard[m])
          final_perlist.append([k[0],k[1],k[2],allactivecard])
        final_activeproject.append([i[0],i[1],i[2],final_perlist])
    final_collablist=[]
    if(len(indiviuallistsactive)!=0):
      for k in indiviuallistsactive:
        allactivecard=Card_table.query.with_entities(Card_table.id,Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by).filter(Card_table.lid==k[0],Card_table.status=='Active').all()
        for m in range(len(allactivecard)):
          allactivecard[m]=list(allactivecard[m])
        final_cardlist=[]
        for m in allactivecard:
          final_cardlist.append(m)
        final_collablist.append([k[0],k[1],k[2],k[3],final_cardlist])
    return render_template("Dashboard.html",datapassed='True',activeprojects=final_activeproject,collabwork=final_collablist)
  else:
    return render_template("Dashboard.html")

@app.route('/UserSearch',methods=['GET','POST','DELETE'])
@login_required
def usersearch():
  if request.method=='GET':
    return render_template('UserSearch.html')
  elif request.method=='POST':
    (searchname)=(request.form['user-name'])
    if(searchname):
      userexists=User_registeration.query.with_entities(User_registeration.id).filter_by(username=searchname).first()
      if(userexists!=None):
        x=int(userexists[0])
        new_follow=Follow_table(follower_id=current_user.id,followee_id=x)
        try:
          db.session.add(new_follow)
          db.session.flush()        
        except Exception as error:
          db.session.rollback()
          return render_template('UserSearch.html',datapassed='True',generalerror='Cannot be allowed right now, please try again later',usersearch=searchname)
        db.session.commit()
        db.session.close()
        return redirect(url_for('dashboard'))
      else:
        return render_template('UserSearch.html',datapassed='True',generalerror='User does not exists',usersearch=searchname)
    else:
      return render_template('UserSearch.html',datapassed='True',generalerror='Enter a username')
    
@app.route('/UserProfile',methods=['GET','POST'])
@login_required
def userprofile():
  if request.method=='GET':
    user=User_registeration.query.with_entities(User_registeration.firstname,User_registeration.lastname,User_registeration.dateofbirth,User_registeration.emailid,User_registeration.username).filter(User_registeration.id==current_user.id).first()
    return render_template('UserProfile.html',fname=user[0],lname=user[1],dob=user[2],email=user[3],username=user[4])
  elif request.method=='POST':
    (fname,lname,dob,email,username,password,repassword)=(request.form['fname'],request.form['lname'],request.form['dob'],request.form['email'],request.form['username'],request.form['password'],request.form['repassword'])
    user=User_registeration.query.filter(User_registeration.id==current_user.id).first()
    x=datetime.strptime(dob,'%Y-%m-%d')
    y=datetime.today()
    dob=datetime.strptime(dob,'%Y-%m-%d')
    if fname:
      if lname:
        if(dob and (x<y)):
          if email:
            if username:
              if((password) and (repassword)):
                if(password==repassword):
                  user.firstname=fname
                  user.lastname=lname
                  user.dateofbirth=dob.date()
                  user.username=username
                  hashedpassword=bcrypt.generate_password_hash(password)
                  user.password=hashedpassword
                  db.session.commit()
                  db.session.close()
                  return redirect(url_for('dashboard'))
                else:
                  return render_template('UserProfile.html',datapassed='True',generalerror='Enter the correct password and Re-entered password',fname=fname,lname=lname,dob=dob,email=email,username=username,password=password,repassword=repassword)
              else:
                user.firstname=fname
                user.lastname=lname
                user.dateofbirth=dob
                user.username=username
                db.session.commit()
                db.session.close()
                return redirect(url_for('dashboard'))
            else:
              return render_template('UserProfile.html',datapassed='True',generalerror='Enter the username',fname=fname,lname=lname,dob=dob,email=email,password=password,repassword=repassword)
          else:
            return render_template('UserProfile.html',datapassed='True',generalerror='Enter the email address',fname=fname,lname=lname,dob=dob,username=username,password=password,repassword=repassword)
        else:
          return render_template('UserProfile.html',datapassed='True',generalerror='Enter the correct Date of Birth',fname=fname,lname=lname,email=email,username=username,password=password,repassword=repassword)
      else:
        return render_template('UserProfile.html',datapassed='True',generalerror='Enter the Last Name',fname=fname,dob=dob,email=email,username=username,password=password,repassword=repassword)
    else:
      return render_template('UserProfile.html',datapassed='True',generalerror='Enter the First Name',lname=lname,dob=dob,email=email,username=username,password=password,repassword=repassword)



@app.route('/ProjectAdder',methods=['GET','POST','PUT','DELETE'])
@login_required
def projectadder():
  if request.method=='GET':
    return render_template('ProjectAdder.html')
  elif request.method=='POST':
    (projectname,projectdescription,nextpage)=(request.form['project-name'],request.form['projectDescription'],request.form['Addbutton'])
    projectdata=[{'projectname':projectname,'projectDescription':projectdescription}]
    if projectname:
      if projectdescription:
        new_project=Project_table(project_name=projectname,project_description=projectdescription,created_on=date.today(),project_lead=current_user.id)
        try:
          db.session.add(new_project)
          db.session.flush()        
        except Exception as error:
          db.session.rollback()
          return render_template('ProjectAdder.html',generalerror="Cannot add list at this point please try again later",datapassed='True',data=projectdata)
        db.session.commit()
        db.session.close()
        if(nextpage=='Add...'):
          return redirect(url_for('dashboard'))
        elif(nextpage=='Create a list'):
          return redirect(url_for('listadder'))
      else:
        return render_template('ProjectAdder.html',generalerror='Enter the description of the Project',datapassed='True',data=projectdata)
    else:
      return render_template('ProjectAdder.html',generalerror='Enter the name of Project',datapassed='True',data=projectdata)

@app.route('/EditProject/<int:project_id>',methods=['GET','POST'])
@login_required
def edit_Project(project_id):
  if request.method=='GET':
    pid=int(project_id)
    project=Project_table.query.filter(Project_table.id==pid).first()
    projectname=project.project_name
    projectdescription=project.project_description
    return render_template('EditProject.html',datapassed='True',pid=pid,projectname=projectname,projectdescription=projectdescription)
  elif request.method=='POST':
    pid=int(project_id)
    (projectname,projectdescription)=(request.form['project-name'],request.form['projectDescription'])
    project=Project_table.query.filter(Project_table.id==pid).first()
    project.project_name=projectname
    project.project_description=projectdescription
    db.session.commit()
    db.session.close()
    return redirect(url_for('dashboard'))

@app.route('/DeleteProject',methods=['POST'])
@login_required
def deleteproject():
  if request.method=='POST':
    (pid)=(request.form['projectid'])
    project=Project_table.query.filter(Project_table.id==pid).first()
    allprojectlist=List_table.query.filter(List_table.pid==pid).all()
    for i in allprojectlist:
      allcardsinlist=Card_table.query.filter(Card_table.lid==i.id).all()
      for j in allcardsinlist:
        db.session.delete(j)
      db.session.commit()
      allroles=Roles_table.query.filter(Roles_table.lid==i.id).all()
      for j in allroles:
        db.session.delete(j)
      db.session.commit()
    for i in allprojectlist:
      db.session.delete(i)
    db.session.delete(project)
    db.session.commit()
    return redirect(request.referrer)

@app.route('/ExportProject',methods=['POST'])
@login_required
def exportproject():
  projectid=request.form['projectid']
  data=[]
  data.append(['Project Name','Project Description','Project Status','List name','List Description','List Created On','List Status','Card name','Card Description','Card Status','Card Created On','Card Due by'])
  projectdata=Project_table.query.with_entities(Project_table.project_name,Project_table.project_description,Project_table.status).filter(Project_table.id==projectid).first()
  projectdata=list(projectdata)
  print(projectdata)
  alllist_active=List_table.query.with_entities(List_table.id,List_table.list_name,List_table.list_description,List_table.created_on,List_table.status).filter(List_table.pid==projectid,List_table.status=='Active').order_by(List_table.created_on).all()
  for i in alllist_active:
    i=list(i)
  for i in alllist_active:
    allcards_perlist=Card_table.query.with_entities(Card_table.card_name,Card_table.card_description,Card_table.status,Card_table.created_on,Card_table.due_by).filter(Card_table.lid==i[0]).order_by(Card_table.created_on).all()
    for j in allcards_perlist:
      j=list(j)
    for j in allcards_perlist:
      data.append([projectdata[0],projectdata[1],projectdata[2],i[1],i[2],i[3],i[4],j[0],j[1],j[2],j[3],j[4]])
  alllist_completed=List_table.query.with_entities(List_table.id,List_table.list_name,List_table.list_description,List_table.created_on,List_table.status).filter(List_table.pid==projectid,List_table.status=='Completed').order_by(List_table.created_on).all()
  for i in alllist_completed:
    i=list(i)
  for i in alllist_completed:
    allcards_perlist=Card_table.query.with_entities(Card_table.card_name,Card_table.card_description,Card_table.status,Card_table.created_on,Card_table.due_by).filter(Card_table.lid==i[0]).order_by(Card_table.created_on).all()
    for j in allcards_perlist:
      j=list(j)
    for j in allcards_perlist:
      data.append([projectdata[0],projectdata[1],projectdata[2],i[1],i[2],i[3],i[4],j[0],j[1],j[2],j[3],j[4]])
  output=io.StringIO()
  writer=csv.writer(output)
  for i in range(len(data)):
    writer.writerow(data[i])
  output.seek(0)
  return Response(output,mimetype="text/csv",headers={"Content-Disposition":f"attachment;filename={projectdata[1]}.csv"})


@app.route('/ListAdder',methods=['GET','POST','PUT','DELETE'])
@login_required
def listadder():
  if request.method=='GET':
    user_project=Project_table.query.with_entities(Project_table.id,Project_table.project_name).filter_by(project_lead=current_user.id).all()
    user_followee=Follow_table.query.with_entities(Follow_table.followee_id,User_registeration.username).join(User_registeration,User_registeration.id==Follow_table.followee_id).filter(Follow_table.follower_id==current_user.id).all()
    return render_template('ListAdder.html',projectdata=user_project,contributordata=user_followee)
  elif request.method=='POST':
    (projects,contributors,listname,listdescription,nextpage)=(request.form.getlist('project-name'),request.form.getlist('contributor-name'),request.form['list-name'],request.form['ListDescription'],request.form['Addbutton'])
    user_project=Project_table.query.with_entities(Project_table.id,Project_table.project_name).filter_by(project_lead=current_user.id).all()
    user_followee=Follow_table.query.with_entities(Follow_table.followee_id,User_registeration.username).join(User_registeration,User_registeration.id==Follow_table.followee_id).filter(Follow_table.follower_id==current_user.id).all()
    if(len(projects)!=0):
      if(listname):
        if(listdescription):
          for i in projects:
            new_list=List_table(list_name=listname,list_description=listdescription,created_on=date.today(),pid=int(i),uid=current_user.id)
            try:
              db.session.add(new_list)
              db.session.flush()        
            except Exception as error:
              db.session.rollback()
              return render_template('ListAdder.html',datapassed='True',generalerror="Cannot add list at this point please try again later",projectdata=user_project,contributordata=user_followee,listname=listname,listdescription=listdescription)
            db.session.commit()
            new_list_id=new_list.id
            new_role=Roles_table(lid=new_list_id,lead_id=current_user.id,uid=current_user.id)
            try:
              db.session.add(new_role)
              db.session.flush()        
            except Exception as error:
              db.session.rollback()
              return render_template('ListAdder.html',datapassed='True',generalerror="Cannot add list at this point please try again later",projectdata=user_project,contributordata=user_followee,listname=listname,listdescription=listdescription)
            db.session.commit()
            for j in contributors:
              new_role=Roles_table(lid=new_list_id,lead_id=current_user.id,uid=j)
              try:
                db.session.add(new_role)
                db.session.flush()        
              except Exception as error:
                db.session.rollback()
                return render_template('ListAdder.html',datapassed='True',generalerror="Cannot add list at this point please try again later",projectdata=user_project,contributordata=user_followee,listname=listname,listdescription=listdescription)
              db.session.commit()
          db.session.close()
          if(nextpage=='Add...'):
            return redirect(url_for('dashboard'))
          elif(nextpage=='Create a Card'):
            return redirect(url_for('create_card'))
        else:
          return render_template('ListAdder.html',datapassed='True',generalerror='Enter the description of the list',projectdata=user_project,contributordata=user_followee,listname=listname,listdescription=listdescription)
      else:
        return render_template('ListAdder.html',datapassed='True',generalerror='Enter the name of the list',projectdata=user_project,contributordata=user_followee,listname=listname,listdescription=listdescription)
    else:
      return render_template('ListAdder.html',datapassed='True',generalerror='Please select a project to add list',projectdata=user_project,contributordata=user_followee,listname=listname,listdescription=listdescription)

@app.route('/EditList/<int:list_id>',methods=['GET','POST'])
@login_required
def edit_List(list_id):
  if request.method=='GET':
    listid=int(list_id)
    list=List_table.query.filter_by(id=listid).first()
    list_name=list.list_name 
    list_description=list.list_description
    user_followee=Follow_table.query.with_entities(Follow_table.followee_id,User_registeration.username).join(User_registeration,User_registeration.id==Follow_table.followee_id).filter(Follow_table.follower_id==current_user.id).all()
    return render_template('EditList.html',datapassed='True',contributordata=user_followee,listid=listid,listname=list_name,listdescription=list_description)
  elif request.method=='POST':
    (contributors,listname,listdescription)=(request.form.getlist('contributor-name'),request.form['list-name'],request.form['ListDescription'])
    user_followee=Follow_table.query.with_entities(Follow_table.followee_id,User_registeration.username).join(User_registeration,User_registeration.id==Follow_table.followee_id).filter(Follow_table.follower_id==current_user.id).all()
    if(listname):
      if(listdescription):
        listid=int(list_id)
        editlist=List_table.query.filter(List_table.id==listid).first()
        editlist.list_name=listname
        editlist.list_description=listdescription
        db.session.commit()

        allroles=Roles_table.query.filter(Roles_table.lid==listid).all()
        for i in allroles:
          db.session.delete(i)
        db.session.commit()

        leadrole=Roles_table(lid=listid,lead_id=current_user.id,uid=current_user.id)
        try:
          db.session.add(leadrole)
          db.session.flush()
        except Exception as error:
          db.session.rollback()
          return render_template('EditList.html',datapassed='True',contributordata=user_followee,listid=listid,listname=listname,listdescription=listdescription)
        db.session.commit()

        for j in contributors:
          new_role=Roles_table(lid=listid,lead_id=current_user.id,uid=j)
          try:
            db.session.add(new_role)
            db.session.flush()        
          except Exception as error:
            db.session.rollback()
            return render_template('EditList.html',datapassed='True',contributordata=user_followee,listid=listid,listname=listname,listdescription=listdescription)
          db.session.commit()
        db.session.close()
        return redirect(url_for('dashboard'))
      else:
       return render_template('EditList.html',datapassed='True',contributordata=user_followee,listid=listid,listname=listname,listdescription=listdescription)
    else:
      return render_template('EditList.html',datapassed='True',contributordata=user_followee,listid=listid,listname=listname,listdescription=listdescription)

@app.route('/DeleteList',methods=['POST'])
@login_required
def deletelist():
  if request.method=='POST':
    (listid)=(request.form['listid'])
    allroles=Roles_table.query.filter(Roles_table.lid==listid).all()
    for i in allroles:
      db.session.delete(i)
    db.session.commit()

    allcards=Card_table.query.filter(Card_table.lid==listid).all()
    for i in allcards:
      db.session.delete(i)
    db.session.commit()

    list=List_table.query.filter_by(id=listid).first()
    db.session.delete(list)
    db.session.commit()
    db.session.close()
    return redirect(request.referrer)
  
@app.route('/ExportList',methods=['POST'])
@login_required
def exportlist():
  listid=request.form['listid']
  Listdata=List_table.query.with_entities(List_table.list_name,List_table.list_description).filter_by(id=listid).first()
  Carddata=Card_table.query.with_entities(Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by,Card_table.status).filter(Card_table.lid==listid,Card_table.status=='Active').order_by(Card_table.created_on).all()
  data=[]
  if(Carddata):
    for i in range(len(Carddata)):
      data.append([Listdata[0],Listdata[1]])
    for i in range(len(Carddata)):
      for j in Carddata[i]:
        data[i].append(j)
  Carddata2=Card_table.query.with_entities(Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by,Card_table.status).filter(Card_table.lid==listid,Card_table.status=='Completed').order_by(Card_table.created_on).all()
  if(Carddata2):
    for i in range(len(Carddata2)):
      data.append([Listdata[0],Listdata[1]])
    for i in range(len(Carddata2)):
      for j in Carddata2[i]:
        data[len(Carddata)+i].append(j)
  output=io.StringIO()
  writer=csv.writer(output)
  writer.writerow(['List Name','List Description','Card Title','Card Description','Created On','Due by','Card Status'])
  if(data):
    for i in data:
      writer.writerow(i)
    output.seek(0)
  return Response(output,mimetype="text/csv",headers={"Content-Disposition":f"attachment;filename={Listdata[0]}.csv"})

@app.route('/CardAdder',methods=['GET','POST'])
@login_required
def create_card():
  if request.method=='GET':
    listdata=List_table.query.with_entities(List_table.id,List_table.list_name,Project_table.project_name).join(Project_table,Project_table.id==List_table.pid).join(Roles_table,Roles_table.lid==List_table.id).filter(Roles_table.uid==current_user.id).all()
    return render_template('CardAdder.html',get='true',listdata=listdata)
  elif request.method=='POST':
    listdata=List_table.query.with_entities(List_table.id,List_table.list_name,Project_table.project_name).join(Project_table,Project_table.id==List_table.pid).join(Roles_table,Roles_table.lid==List_table.id).filter(Roles_table.uid==current_user.id).all()
    (lists,name,description,due,status)=(request.form.getlist('list-name'),request.form['card-name'],request.form['CardDiscription'],request.form['deadline'],request.form.getlist('Status'))
    if(len(lists)>0):
      if name:
        if description:
          if due:
            if(len(status)<=0):
              mark_status=None
            else:
              mark_status='Completed'
            for i in lists:
              if mark_status==None:
                new_card=Card_table(card_name=name,card_description=description,created_on=date.today(),due_by=datetime.strptime(due,'%Y-%m-%d').date(),completed_on=date.today(),lid=int(i),uid=int(current_user.id))
              else:
                new_card=Card_table(card_name=name,card_description=description,created_on=date.today(),due_by=datetime.strptime(due,'%Y-%m-%d').date(),completed_on=date.today(),status=mark_status,lid=int(i),uid=int(current_user.id))
              try:
                db.session.add(new_card)
                db.session.flush()        
              except Exception as error:
                print(error)
                db.session.rollback()
                return render_template('CardAdder.html',datapassed='True',generalerror='Card cannot be created at this moment',listdata=listdata,title=name,description=description,due=due)
              db.session.commit()
            db.session.close()
            return redirect(url_for('dashboard'))
          else:
            return render_template('CardAdder.html',datapassed='True',generalerror='Enter a due date ',listdata=listdata,title=name,description=description,due=due)
        else:
          return render_template('CardAdder.html',datapassed='True',generalerror='Enter a description to the card',listdata=listdata,title=name,description=description,due=due)
      else:
        return render_template('CardAdder.html',datapassed='True',generalerror='Enter a title to the card',listdata=listdata,title=name,description=description,due=due)
    else:
      return render_template('CardAdder.html',datapassed='True',generalerror='Select a list to add card',listdata=listdata,title=name,description=description,due=due)


@app.route('/EditCard/<int:card_id>',methods=['GET','POST'])
@login_required
def edit_Card(card_id):
  if request.method=='GET':
    #print('in')
    cardid=int(card_id)
    card=Card_table.query.filter_by(id=cardid).first()
    card_name=card.card_name 
    card_description=card.card_description
    card_due_by=card.due_by
    return render_template('EditCard.html',datapassed='True',cardid=cardid,title=card_name,description=card_description,due=card_due_by)
  elif request.method=='POST':
    (name,description,due,status)=(request.form['card-name'],request.form['CardDiscription'],request.form['deadline'],request.form.getlist('Status'))
    cardid=int(card_id)
    print(status)
    if name:
      if description:
        if due:
          if(len(status)<=0):
            mark_status='Active'
          else:
            mark_status='Completed'
          cardid=card_id
          card=Card_table.query.filter_by(id=cardid).first()
          card.card_name=name
          card.card_description=description
          card.due_by=datetime.strptime(due,'%Y-%m-%d').date()
          if(mark_status=='Completed' and card.status!='Completed'):
            card.status=mark_status
            card.completed_on=date.today()
          elif(mark_status=='Active' and card.status!='Active'):
            card.status=mark_status
          else:
            card.status=mark_status
          db.session.commit()
          db.session.close()
          return redirect(url_for('dashboard'))
        else:
          return render_template('EditCard.html',datapassed='True',generalerror='Enter a due date ',title=name,description=description,due=due)
      else:
        return render_template('EditCard.html',datapassed='True',generalerror='Enter a description to the card',title=name,description=description,due=due)
    else:
      return render_template('EditCard.html',datapassed='True',generalerror='Enter a title to the card',title=name,description=description,due=due)

@app.route('/DeleteCard',methods=['POST'])
@login_required
def deletecard():
  if request.method=='POST':
    cardid=request.form['cardid']
    card=Card_table.query.filter_by(id=cardid).first()
    db.session.delete(card)
    db.session.commit()
    db.session.close()
    return redirect(request.referrer)

@app.route('/ListSummary',methods=['GET'])
@login_required
def listsummary():
  if request.method=='GET':
    standardizingListWithCards()
    standardizeprojectswithlist()
    allactiveprojects=Project_table.query.with_entities(Project_table.id,Project_table.project_name,Project_table.project_description).filter(Project_table.status=='Active',Project_table.project_lead==current_user.id).all()
    for i in range(len(allactiveprojects)):
      allactiveprojects[i]=list(allactiveprojects[i])
    allcompletedprojects=Project_table.query.with_entities(Project_table.id,Project_table.project_name,Project_table.project_description).filter(Project_table.status=='Completed',Project_table.project_lead==current_user.id).all()
    for i in range(len(allcompletedprojects)):
      allcompletedprojects[i]=list(allcompletedprojects[i])
    final_activeproject=[]
    final_completedproject=[]
    final_collablist=[]
    for i in allactiveprojects:
      allactivelist=List_table.query.with_entities(List_table.id,List_table.list_name,List_table.list_description,List_table.status).filter(List_table.pid==i[0],List_table.status=='Active').all()
      for j in range(len(allactivelist)):
        allactivelist[j]=list(allactivelist[j])
      allcompletedlist=List_table.query.with_entities(List_table.id,List_table.list_name,List_table.list_description,List_table.status).filter(List_table.pid==i[0],List_table.status=='Completed').all()
      for j in range(len(allcompletedlist)):
        allcompletedlist[j]=list(allcompletedlist[j])
      final_perlist=[]
      for k in allactivelist:
        allactivecard=Card_table.query.with_entities(Card_table.id,Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by,Card_table.status).filter(Card_table.lid==k[0],Card_table.status=='Active').all()
        for m in range(len(allactivecard)):
          allactivecard[m]=list(allactivecard[m])
        allcompletedcard=Card_table.query.with_entities(Card_table.id,Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by,Card_table.status).filter(Card_table.lid==k[0],Card_table.status=='Completed').all()
        for m in range(len(allcompletedcard)):
          allcompletedcard[m]=list(allcompletedcard[m])   
        final_cardlist=[]
        for m in allactivecard:
          final_cardlist.append(m)
        for m in allcompletedcard:
          final_cardlist.append(m)
        final_perlist.append([k[0],k[1],k[2],k[3],final_cardlist])
      for k in allcompletedlist:
        allcompletedcard=Card_table.query.with_entities(Card_table.id,Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by,Card_table.status).filter(Card_table.lid==k[0],Card_table.status=='Completed').all()
        for m in range(len(allcompletedcard)):
          allcompletedcard[m]=list(allcompletedcard[m])   
        final_cardlist=[]
        for m in range(len(allcompletedcard)):
          final_cardlist.append(allcompletedcard[m])
        final_perlist.append([k[0],k[1],k[2],k[3],final_cardlist])
      final_activeproject.append([i[0],i[1],i[2],final_perlist])

    for i in allcompletedprojects:
      allcompletedlist=List_table.query.with_entities(List_table.id,List_table.list_name,List_table.list_description,List_table.status).filter(List_table.pid==i[0],List_table.status=='Completed').all()
      for j in range(len(allcompletedlist)):
        allcompletedlist[j]=list(allcompletedlist[j])
      final_perlist=[]
      for k in allcompletedlist:
        allcompletedcard=Card_table.query.with_entities(Card_table.id,Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by,Card_table.status).filter(Card_table.lid==k[0],Card_table.status=='Completed').all()
        for m in range(len(allcompletedcard)):
          allcompletedcard[m]=list(allcompletedcard[m])   
        final_cardlist=[]
        for m in range(len(allcompletedcard)):
          final_cardlist.append(allcompletedcard[m])
        final_perlist.append([k[0],k[1],k[2],k[3],final_cardlist])
      final_completedproject.append([i[0],i[1],i[2],final_perlist])
    
    indiviuallistsactive=List_table.query.with_entities(List_table.id,Project_table.project_name,List_table.list_name,List_table.list_description,List_table.status).join(Roles_table,List_table.id==Roles_table.lid).join(Project_table,Project_table.id==List_table.pid).filter(Roles_table.lead_id!=Roles_table.uid,Roles_table.uid==current_user.id,List_table.status=='Active').all()
    for i in range(len(indiviuallistsactive)):
      indiviuallistsactive[i]=list(indiviuallistsactive[i])
    indiviuallistscompleted=List_table.query.with_entities(List_table.id,Project_table.project_name,List_table.list_name,List_table.list_description,List_table.status).join(Roles_table,List_table.id==Roles_table.lid).join(Project_table,Project_table.id==List_table.pid).filter(Roles_table.lead_id!=Roles_table.uid,Roles_table.uid==current_user.id,List_table.status=='Completed').all()
    for i in range(len(indiviuallistscompleted)):
      indiviuallistscompleted[i]=list(indiviuallistscompleted[i])
    final_perlist=[]
    for k in indiviuallistsactive:
      allactivecard=Card_table.query.with_entities(Card_table.id,Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by,Card_table.status).filter(Card_table.lid==k[0],Card_table.status=='Active').all()
      for m in range(len(allactivecard)):
        allactivecard[m]=list(allactivecard[m])
      allcompletedcard=Card_table.query.with_entities(Card_table.id,Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by,Card_table.status).filter(Card_table.lid==k[0],Card_table.status=='Completed').all()
      for m in range(len(allcompletedcard)):
        allcompletedcard[m]=list(allcompletedcard[m])   
      final_cardlist=[]
      for m in allactivecard:
        final_cardlist.append(m)
      for m in allcompletedcard:
        final_cardlist.append(m)
      final_collablist.append([k[0],k[1],k[2],k[3],k[4],final_cardlist])
    for k in indiviuallistscompleted:
      allcompletedcard=Card_table.query.with_entities(Card_table.id,Card_table.card_name,Card_table.card_description,Card_table.created_on,Card_table.due_by,Card_table.status).filter(Card_table.lid==k[0],Card_table.status=='Completed').all()
      for m in range(len(allcompletedcard)):
        allcompletedcard[m]=list(allcompletedcard[m])   
      final_cardlist=[]
      for m in range(len(allcompletedcard)):
        final_cardlist.append(allcompletedcard[m])
      final_collablist.append([k[0],k[1],k[2],k[3],k[4],final_cardlist])
    return render_template('ListSummary.html',activeprojects=final_activeproject,completedprojects=final_completedproject,collablist=final_collablist)

@app.route('/ListReport',methods=['GET'])
@login_required
def listreport():
  if request.method=='GET':
    allprojectsofuser=Project_table.query.with_entities(Project_table.id,Project_table.project_name,Project_table.project_description).filter(Project_table.project_lead==current_user.id).all()
    for i in range(len(allprojectsofuser)):
      allprojectsofuser[i]=list(allprojectsofuser[i])
    project_list=[]
    if(len(allprojectsofuser)!=0):
      for i in allprojectsofuser:
        alllistsofproject_completed=List_table.query.with_entities(List_table.id,List_table.list_name,List_table.list_description).filter(List_table.pid==i[0],List_table.uid==current_user.id,List_table.status=='Completed').all()
        for j in range(len(alllistsofproject_completed)):
          alllistsofproject_completed[j]=list(alllistsofproject_completed[j])
        completed_perlist=[]
        alllistsofproject_active=List_table.query.with_entities(List_table.id,List_table.list_name,List_table.list_description).filter(List_table.pid==i[0],List_table.uid==current_user.id,List_table.status=='Active').all()
        for j in range(len(alllistsofproject_active)):
          alllistsofproject_active[j]=list(alllistsofproject_active[j])
        active_perlist=[]
        if(len(alllistsofproject_completed)!=0 or len(alllistsofproject_active)!=0):
          for j in alllistsofproject_completed:
            totalcards=Card_table.query.with_entities(Card_table.id,Card_table.due_by,Card_table.completed_on).filter(Card_table.lid==j[0]).all()
            if(len(totalcards)!=0):
              defaulter=0
              ontime=0
              for k in range(len(totalcards)):
                totalcards[k]=list(totalcards[k])
              for k in totalcards:
                if((k[1]-k[2]).days>=0):
                  ontime=ontime+1
                else:
                  defaulter=defaulter+1
              df = pd.DataFrame({'assignments': [ontime,defaulter]},index=['Ontime', 'Defaulter',])
              plot=df.plot.pie(y='assignments', figsize=(2.7, 2.7))
              fig=plot.get_figure()
              fig.savefig(f'static/my_pie_{j[0]}.png')
              piechart1=''
              with open(f'static/my_pie_{j[0]}.png', "rb") as img_file:
                piechart1 = base64.b64encode(img_file.read()).decode('utf8')
              totalcards_dict={}
              for k in totalcards:
                if k[2] in totalcards_dict.keys():
                  totalcards_dict[k[2]]=totalcards_dict[k[2]]+1
                else:
                  totalcards_dict[k[2]]=1
              df=pd.DataFrame({'frequency': totalcards_dict.values()}, index=totalcards_dict.keys())
              ax=df.plot.bar(rot=0,figsize=(2.7, 2.7))
              fig=ax.get_figure()
              fig.savefig(f'static/bar_{j[0]}.jpg')
              barchart1={}
              with open(f'static/bar_{j[0]}.jpg', "rb") as img_file:
                barchart1 = base64.b64encode(img_file.read()).decode('utf8')
              completed_perlist.append([j[0],j[1],j[2],piechart1,barchart1])
              print(completed_perlist)

          for j in alllistsofproject_active:
            remainingcards=Card_table.query.with_entities(Card_table.id).filter(Card_table.lid==j[0],Card_table.status=='Active').all()
            completedcards=Card_table.query.with_entities(Card_table.id).filter(Card_table.lid==j[0],Card_table.status=='Completed').all()
            df = pd.DataFrame({'Completion Status': [len(remainingcards),len(completedcards)]},index=['Active', 'Completed',])
            plot=df.plot.pie(y='Completion Status', figsize=(2.7, 2.7))
            fig=plot.get_figure()
            fig.savefig(f'static/my_pie_1_{j[0]}.png')
            piechart2=''
            with open(f'static/my_pie_1_{j[0]}.png', "rb") as img_file:
              piechart2 = base64.b64encode(img_file.read()).decode('utf8')
            
            totalcards=Card_table.query.with_entities(Card_table.id,Card_table.due_by,Card_table.completed_on).filter(Card_table.lid==j[0],Card_table.status=='Completed').all()
            if(len(totalcards)!=0):
              defaulter=0
              ontime=0
              for k in range(len(totalcards)):
                totalcards[k]=list(totalcards[k])
              for k in totalcards:
                if((k[1]-k[2]).days>=0):
                  ontime=ontime+1
                else:
                  defaulter=defaulter+1
              df = pd.DataFrame({'assignments': [ontime,defaulter]},index=['Ontime', 'Defaulter',])
              plot=df.plot.pie(y='assignments', figsize=(2.7, 2.7))
              fig=plot.get_figure()
              fig.savefig(f'static/my_pie_2_{j[0]}.png')
              piechart3=''
              with open(f'static/my_pie_2_{j[0]}.png', "rb") as img_file:
                piechart3 = base64.b64encode(img_file.read()).decode('utf8')

              totalcards_dict={}
              for k in totalcards:
                if k[2] in totalcards_dict.keys():
                  totalcards_dict[k[2]]=totalcards_dict[k[2]]+1
                else:
                  totalcards_dict[k[2]]=1
              df=pd.DataFrame({'frequency': totalcards_dict.values()}, index=totalcards_dict.keys())
              ax=df.plot.bar(rot=0,figsize=(2.7, 2.7))
              fig=ax.get_figure()
              fig.savefig(f'static/bar_1_{j[0]}.jpg')
              barchart2={}
              with open(f'static/bar_1_{j[0]}.jpg', "rb") as img_file:
                barchart2 = base64.b64encode(img_file.read()).decode('utf8')
              active_perlist.append([j[0],j[1],j[2],piechart2,piechart3,barchart2])
          project_list.append([i[0],i[1],i[2],completed_perlist,active_perlist])
        else:
          pass
      return render_template('ListReport.html',datapassed='True',projectreport=project_list)
    else:
      return render_template('ListReport.html')

@app.route('/RemoveRoles',methods=['GET','POST'])
@login_required
def removeroles():
  if request.method=='GET':
    roles=Roles_table.query.with_entities(Roles_table.id,List_table.list_name,User_registeration.username).join(List_table,List_table.id==Roles_table.lid).join(User_registeration,User_registeration.id==Roles_table.uid).filter(Roles_table.lead_id==current_user.id,Roles_table.lead_id!=Roles_table.uid).all()
    for i in roles:
      i=list[i]
    return render_template('RemoveRoles.html',roles=roles)
  if request.method=='POST':
    roleid=request.form['roleid']
    role=Roles_table.query.filter(Roles_table.id==roleid).first()
    if(role):
      db.session.delete(role)
      db.session.commit()
      db.session.close()
      return redirect(request.referrer)
    else:
      return redirect(request.referrer)


@app.route('/Logout',methods=['GET'])
@login_required
def logout():
  if request.method=='GET':
    logout_user()
    return redirect(url_for('login'))


@celery.task()
def dailyemails():
  users=User_registeration.query.with_entities(User_registeration.id,User_registeration.username,User_registeration.emailid).all()
  for i in users:
    projects_list=List_table.query.with_entities(Project_table.project_name,List_table.list_name,Card_table.card_name,Card_table.due_by).join(Project_table,Project_table.id==List_table.pid).join(Roles_table,Roles_table.lid==List_table.id).join(Card_table,Card_table.lid==List_table.id).filter(List_table.status=='Active',Project_table.status=='Active',Card_table.status=='Active',Roles_table.uid==i[0]).order_by(Card_table.due_by).all()
    for j in projects_list:
      j=list(j)
    print(projects_list)
    msg = Message(f"Good Morning, {i[1]} !")
    msg.recipients=[i[2]]
    msg.html=render_template('DailyEmails.html',data=projects_list)
    mail.send(msg)
    print('True')

@celery.task()
def montlyemails():
  users=User_registeration.query.with_entities(User_registeration.id,User_registeration.emailid,User_registeration.username).all()
  for i in users:
    thismonth=len(Card_table.query.with_entities(Card_table.id).filter(Card_table.uid==i[0],Card_table.created_on.between(datetime.now()-timedelta(days=30),datetime.now())).all())
    this_1month=len(Card_table.query.with_entities(Card_table.id).filter(Card_table.uid==i[0],Card_table.created_on.between(datetime.now()-timedelta(days=60),datetime.now()-timedelta(days=30))).all())
    this_2month=len(Card_table.query.with_entities(Card_table.id).filter(Card_table.uid==i[0],Card_table.created_on.between(datetime.now()-timedelta(days=90),datetime.now()-timedelta(days=60))).all())
    chart1={'Month-2':this_2month,'Month-1':this_1month,'Month-0':thismonth}
    if((thismonth>0) or (this_1month>0) or (this_2month>0)):
      df=pd.DataFrame({'frequency': chart1.values()}, index=chart1.keys())
      ax=df.plot.bar(rot=0,figsize=(2.7, 2.7))
      fig=ax.get_figure()
      fig.savefig(f'static/monthlyreport_chart1_{i[0]}.jpg')
      barchart1=''
      with open(f'static/monthlyreport_chart1_{i[0]}.jpg', "rb") as img_file:
        barchart1 = base64.b64encode(img_file.read()).decode('utf8')
    else:
      pass
    totalactivecards=len(Card_table.query.with_entities(Card_table.id).filter(Card_table.uid==i[0],Card_table.due_by.between(datetime.now()-timedelta(days=30),datetime.now()),Card_table.status=='Active').all())
    totalcompletedcards=len(Card_table.query.with_entities(Card_table.id).filter(Card_table.uid==i[0],Card_table.due_by.between(datetime.now()-timedelta(days=30),datetime.now()),Card_table.status=='Completed').all())
    if((totalactivecards>0) or (totalcompletedcards>0)):
      df = pd.DataFrame({'Completion Status': [totalactivecards,totalcompletedcards]},index=['Active', 'Completed',])
      plot=df.plot.pie(y='Completion Status', figsize=(2.7, 2.7))
      fig=plot.get_figure()
      fig.savefig(f'static/monthlyreport_chart2_{i[0]}.png')
      piechart1=''
      with open(f'static/monthlyreport_chart2_{i[0]}.png', "rb") as img_file:
        piechart1 = base64.b64encode(img_file.read()).decode('utf8')
    else:
      pass

    activeyetdefaulted=len(Card_table.query.with_entities(Card_table.id).filter(Card_table.uid==i[0],Card_table.status=='Active',Card_table.due_by.between(datetime.now()-timedelta(days=30),datetime.now())).all())
    completedyetdefaulted=len(Card_table.query.with_entities(Card_table.id).filter(Card_table.uid==i[0],Card_table.completed_on>Card_table.due_by,Card_table.due_by.between(datetime.now()-timedelta(days=30),datetime.now()),Card_table.status=='Completed').all())
    if((activeyetdefaulted>0) or (completedyetdefaulted>0)):
      df = pd.DataFrame({'Defaulting Status': [activeyetdefaulted,completedyetdefaulted]},index=['Active', 'Completed',])
      plot=df.plot.pie(y='Defaulting Status', figsize=(2.7, 2.7))
      fig=plot.get_figure()
      fig.savefig(f'static/monthlyreport_chart3_{i[0]}.png')
      piechart2=''
      with open(f'static/monthlyreport_chart3_{i[0]}.png', "rb") as img_file:
        piechart2 = base64.b64encode(img_file.read()).decode('utf8')
    else:
      pass

    if(barchart1):
      if(piechart1):
        if(piechart2):
          ren=render_template('MonthlyEmails.html',chart1=barchart1,chart2=piechart1,chart3=piechart2,data1=[[this_2month,this_1month,thismonth]],data2=[[totalactivecards,totalcompletedcards]],data4=[[activeyetdefaulted,completedyetdefaulted]])
        else:
          ren=render_template('MonthlyEmails.html',chart1=barchart1,chart2=piechart1,data1=[[this_2month,this_1month,thismonth]],data2=[[totalactivecards,totalcompletedcards]],data4=[[activeyetdefaulted,completedyetdefaulted]])
      else:
        if(piechart2):
          ren=render_template('MonthlyEmails.html',chart1=barchart1,chart3=piechart2,data1=[[this_2month,this_1month,thismonth]],data2=[[totalactivecards,totalcompletedcards]],data4=[[activeyetdefaulted,completedyetdefaulted]])
        else:
          ren=render_template('MonthlyEmails.html',chart1=barchart1,data1=[[this_2month,this_1month,thismonth]],data2=[[totalactivecards,totalcompletedcards]],data4=[[activeyetdefaulted,completedyetdefaulted]])
    else:
      if(piechart1):
        if(piechart2):
          ren=render_template('MonthlyEmails.html',chart2=piechart1,chart3=piechart2,data1=[[this_2month,this_1month,thismonth]],data2=[[totalactivecards,totalcompletedcards]],data4=[[activeyetdefaulted,completedyetdefaulted]])
        else:
          ren=render_template('MonthlyEmails.html',chart2=piechart1,data1=[[this_2month,this_1month,thismonth]],data2=[[totalactivecards,totalcompletedcards]],data4=[[activeyetdefaulted,completedyetdefaulted]])
      else:
        if(piechart2):
          ren=render_template('MonthlyEmails.html',chart3=piechart2,data1=[[this_2month,this_1month,thismonth]],data2=[[totalactivecards,totalcompletedcards]],data4=[[activeyetdefaulted,completedyetdefaulted]])
        else:
          ren=render_template('MonthlyEmails.html',data1=[[this_2month,this_1month,thismonth]],data2=[[totalactivecards,totalcompletedcards]],data4=[[activeyetdefaulted,completedyetdefaulted]])
    
    pdf=pdfkit.from_string(ren,False)
    msg = Message("Monthly Introspect!")
    msg.recipients=[i[1]]
    msg.html=render_template('Monthlyemailtemplate.html',username=i[2])
    msg.attach('MonthlyReport.pdf','application/pdf',pdf)
    mail.send(msg)
    print('Send')



@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    # sender.add_periodic_task(10.0, return_random.s(), name='add every 10')

    # Calls test('world') every 30 seconds
    # sender.add_periodic_task(30.0, test.s('world'), expires=10)

    # Executes every Monday morning at 7:30 a.m.
    
    sender.add_periodic_task(
        # 30.0,
        crontab(minute=0, hour=8),
        dailyemails.s()
    )

    sender.add_periodic_task(
        # 10.0,
        crontab(minute=0, hour=8,day_of_month='1'),
        montlyemails.s()
    )

if __name__=='__main__':
  app.run(debug=True)