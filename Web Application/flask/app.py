from flask import Flask, request,render_template,flash,redirect,url_for,session
from flask_restful import  Api
from flaskext.mysql import MySQL
import json
from forms import RegistrationForm,LoginForm,RequestResetForm,ResetPasswordForm
from flask_bcrypt import Bcrypt
from flask_mail import Mail,Message
import traceback
import pandas
import geopy.distance
import datetime
import dateutil.parser
import uuid
import collections
import numpy as np
import math
import operator
import logging
from flask.logging import default_handler
from threading import Thread

app = Flask(__name__)
mysql = MySQL() 
bcrypt = Bcrypt()#For encrypting password

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'pythonproj'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

#required for using sessions
app.config['SECRET_KEY'] = '58458792afnki845'

#Email Configurations
app.config.update(
        DEBUG=True,
        MAIL_SERVER='smtp.googlemail.com',
        MAIL_PORT=465,
        MAIL_USE_SSL=True,
        MAIL_USERNAME=,#Set Email ID Here
        MAIL_PASSWORD='')#Set Password Here  


mail = Mail(app)
mysql.init_app(app)
api = Api(app)


if __name__ == 'app':
    #File handler. Remove default handler    
    logHandler = logging.FileHandler('application_logs.log')
    logHandler.setLevel(logging.INFO)
    logHandler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
    app.logger.removeHandler(default_handler)        
    app.logger.addHandler(logHandler)
    app.logger.setLevel(logging.INFO)
    app.run()


@app.route("/")
def default():
    return redirect(url_for('showLandingPage'))


@app.route("/landing_page")
def showLandingPage():
    return render_template('landing_page.html')

# =============================================================================
# Returns all the places which are present in the city which is passed as param
# guest users can also use this functionality. so no need for checking if
# user is logged in    
# =============================================================================
@app.route("/viewplace",methods=["GET"])
def viewPlace():
    db=None
    res=''    
    try:
        cityName= request.args['placeName']
        output={}
        db= mysql.connect()
        mycursor =db.cursor()
        mycursor.execute("select * from placedetails where City=%s",(cityName,))
        counter=1
        for row in mycursor:
            output.update({'place'+str(counter):{'placeid':row[0],'cityname':row[1],'name':row[2],'rating':row[3],'numofreview':row[4],'imagename':row[5],'desc':row[6],'shortdesc':row[7],'address':row[8],'review1':row[9],'review2':row[10],'review3':row[11]}})
            counter+=1
        res={'places':output}
    except:
         app.logger.error('Error occurred in '+request.url)
         app.logger.error(traceback.format_exc())
    finally:
        if(db!=None):
            db.close()
    return json.dumps(res)

# =============================================================================
# This function is used for populating the search box based on user input.
# Returns list of cities matching the search string  
# =============================================================================
@app.route("/searchCity",methods=["GET"])
def searchCity():
    db=None
    res=''    
    try:
        searchTerm= request.args['searchTerm']    
        output={}
        db= mysql.connect()
        mycursor =db.cursor()
        mycursor.execute("select distinct(City) from placedetails where upper(City) like '"+searchTerm+"%'")    
        for row in mycursor:
            output.update({row[0]:row[0]})        
        res={'places':output}   
    except:
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
    finally:
        if(db!=None):
            db.close()
    return json.dumps(res)

# =============================================================================
# Verify that user is logged in before making this request
# Only one active itinerary exist per city per user
# Check if itinerary id is passed in the request. If passed use it and add place
# to itinerary. Else check if active itinerary exist for the user for the city
# If itinerary exist, use that itinerary id and insert the place and return itinerary id in response
# If no active itinerary exist, create one and insert the place and return itinerary id in response    
# =============================================================================
@app.route("/addPlaceToItinerary",methods=["POST"])
def addPlaceToItinerary():
    db=None
    userid=session.get('username')
    if(userid==None or userid==''):
        return json.dumps('Unauthorized Access')
    try:
        placeid=request.form['placeid']        
        city=request.form['city']
        itineraryid=request.form['itinerary_id']
        db= mysql.connect()
        mycursor =db.cursor()
        
        if itineraryid=='':
            #check if active itinerary exist for this city and user
            mycursor.execute("select itinerary_id from itinerary where city=%s and email_id=%s and status='active'",(city,userid))    
            data=mycursor.fetchone()
            if(data!=None and len(data)>0 and data[0]!=None and data[0]!=0):
                #itinerary exist.use this itinerary id
                itineraryid=data[0]
                #old_data_present=True
            else:
                #create new itinerary
                mycursor.execute("insert into itinerary(city,email_id,status) values(%s,%s,%s)",(city,userid,'active'))    
                itineraryid=mycursor.lastrowid
             
        #insert into itinerary_places        
        mycursor.execute("insert into  itinerary_places(itinerary_id,placeid) values(%s,%s)",(itineraryid,placeid))              
        db.commit()
        res={'status':'200','itinerary_id':itineraryid}
    except Exception:
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
        res={'status':'500'}
    finally:        
        if(db!=None):
            db.close()
    return json.dumps(res)

# =============================================================================
# This function returns all the place ids which user has added in the active itinerary 
# for the city selected in the search box. This function is used for adding/removing the css class
# in the UI and for storing the itinerary id in hidden field    
# =============================================================================
@app.route("/fetchCitywiseWishlist",methods=["GET"])
def fetchCitywiseWishlist():
    userid=session.get('username')    
    if(userid==None or userid==''):
        return json.dumps('Unauthorized Access')
    db=None
    try:
        
        city=request.args['city']
        db= mysql.connect()
        mycursor =db.cursor()
        mycursor.execute("select ip.itinerary_id,ip.placeid from  itinerary i,itinerary_places ip where i.itinerary_id=ip.itinerary_id and i.status='active' and i.email_id=%s and i.city=%s",(userid,city))    
        data=mycursor.fetchall()
        items=[]
        itinerary_id=''
        for rec in data:
            itinerary_id=rec[0]
            items.append(rec[1])
        response={'status':'200','items':items,'itinerary_id':itinerary_id}
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
        response={'status':'500'}
    finally:        
        if(db!=None):
            db.close()
    
    
    return json.dumps(response)


@app.route("/removePlaceFromItinerary",methods=["POST"])
def removePlaceFromItinerary():
    userid=session.get('username')    
    if(userid==None or userid==''):
        return json.dumps('Unauthorized Access')
    db=None
    try:        
        placeid=request.form['placeid']        
        itineraryid=request.form['itinerary_id']
        db= mysql.connect()
        mycursor =db.cursor()
        mycursor.execute("delete from itinerary_places where itinerary_id=%s and placeid=%s",(itineraryid,placeid))    
        db.commit()
        response={'status':'200'}
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
        response={'status':'500'}
    finally:        
        if(db!=None):
            db.close()
    
    
    return json.dumps(response)

# =============================================================================
# Function used for populating the dialog box when user clicks on the fixed heart div on page
# Returns all the place ids which user has added in the active itinerary for the city    
# =============================================================================
@app.route("/populateItineraryModal",methods=["GET"])
def populateItineraryModal():
    userid=session.get('username')    
    if(userid==None or userid==''):
        return json.dumps('Unauthorized Access')
    db=None
    try:
        itineraryid=request.args['itinerary_id']
        db= mysql.connect()
        mycursor =db.cursor()
        mycursor.execute("select p.placeid,p.PlaceName from placedetails p,itinerary_places ip where ip.placeid=p.placeid and ip.itinerary_id=%s",(itineraryid))    
        data=mycursor.fetchall()
        places=dict()        
        for rec in data:
            placeid=rec[0]
            placename=rec[1]
            places.update({placeid:placename})
        response={'status':'200','places':places,'itinerary_id':itineraryid}
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
        response={'status':'500'}
    finally:
        if(db!=None):
            db.close()
    
    return json.dumps(response)

# =============================================================================
# Function returns the optimized route of place ids
# =============================================================================
@app.route("/optimizeItinerary",methods=["GET"])
def optimizeItinerary():
    userid=session.get('username')    
    if(userid==None or userid==''):
        return json.dumps('Unauthorized Access')    
    try:
        itineraryid=request.args['itinerary_id']
        starting_place=int(request.args['starting_place'])
        place_ids=request.args['place_ids']
        placesList=place_ids.split('~');
        placesList=[int(x) for x in placesList]
        placesList.remove(starting_place)
        #call function to optimize the route   
        placesListOptimized=find_optimized_route(placesList,starting_place)
        
        response={'status':'200','places':placesListOptimized,'itinerary_id':itineraryid}
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
        response={'status':'500'}
    
    
    return json.dumps(response)

   
@app.route("/register",methods=["POST","GET"])
def register():
    userid=session.get('username')
    if(userid!=None and userid!=''):
        return redirect(url_for('showLandingPage'))#user is already logged in
    form = RegistrationForm()
    con=None
    try:
        if request.method == 'POST' and form.validate_on_submit():
            userDetails = request.form
            fname = userDetails['fname']
            lname = userDetails['lname']
            city= userDetails['city']
            email = userDetails['email']
            password = bcrypt.generate_password_hash(str(userDetails['password'])).decode('utf-8')
            con = mysql.connect()
            cursor = con.cursor()
            res = cursor.execute("SELECT * from USERS WHERE Email = %s;",(email))
            if int(res) > 0:
                flash("Email Id already exists, please try another one",'danger')
                return render_template('register.html',form=form)
            else:
                cursor.execute("INSERT INTO USERS(FirstName,LastName,Email,Password,City,role) VALUES (%s, %s, %s, %s, %s,%s);",(fname,lname,email,password,city,'user'))
                con.commit()
                flash('Account created successfully {0}! You can now Login.'.format(form.fname.data),'success')
                return redirect(url_for('login'))
    except Exception:
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
    finally:
         if(con!=None):
            con.close()   
    return render_template('register.html',form=form)

@app.route("/login",methods=["POST","GET"])
def login():
    userid=session.get('username')
    if(userid!=None and userid!=''):
        return redirect(url_for('showLandingPage'))#user is already logged in
    form = LoginForm() 
    con=None
    try:
        if form.validate_on_submit():
            userDetails = request.form
            con = mysql.connect()
            cursor = con.cursor()
            cursor.execute("SELECT * from USERS WHERE Email = %s;",(userDetails['email']))
            res = cursor.fetchone()
            if res!=None and len(res) > 0:
                passw =res[3]            
                fname=res[0]
                role=res[5]
                if bcrypt.check_password_hash(passw,str(userDetails['password'])):
                    session['username']=userDetails['email']
                    session['fname']=fname
                    if(role=='user'):
                        app.logger.info('User {0} logged in'.format(userDetails['email']))  
                        return redirect(url_for('showLandingPage'))
                    else:
                        #Admin Role                        
                        app.logger.info('Admin {0} logged in'.format(userDetails['email']))  
                else:                    
                    flash("Incorrect password",'danger')
                    return render_template('login.html',form=form)
            else:
                flash('Please Sign Up','danger')
                return redirect(url_for('register'))
   
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
    finally:        
        if(con!=None):
            con.close()        
    return render_template('login.html',form=form)
        
           
@app.route("/logout")
def logout():
    userid=session.get('username')    
    if(userid!=None and userid!=''):
        app.logger.info('logging out {0}'.format(userid))        
        session.clear()        
    return redirect(url_for('showLandingPage'))


# =============================================================================
# This function is called on change of the date picker to check if any other
# itineraries exist for the selected date for that user    
# =============================================================================
@app.route("/checkIfOtherItineraryPresent",methods=["GET"])
def checkIfOtherItineraryPresent():
    userid=session.get('username')    
    if(userid==None or userid==''):
        return json.dumps('Unauthorized Access')
    db=None
    try:
        
        st_date=request.args['st_date']
        db= mysql.connect()
        mycursor =db.cursor()
        mycursor.execute("select count(*) from itinerary where email_id=%s and Date=%s",(userid,st_date))    
        data=mycursor.fetchone()
        if(data!=None and len(data)>0 and int(data[0])>0):
            msg='Present'
        else:
            msg='Absent'        
        response={'status':'200','msg':msg}
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
        response={'status':'500'}
    finally:
        if(db!=None):
            db.close()
    
    return json.dumps(response)

# =============================================================================
# Last step in creating the itinerary
# place ids received as input from request is the optimized one.
# Based on the position of the place id in the list, the sr_no for that 
# place in the itinerary is decided.
# In this step, the status of the itinerary changes to complete and no edits 
# can be made after this. Only delete will be allowed    
# =============================================================================
@app.route("/finalizeItinerary",methods=["POST"])
def finalizeItinerary():
    userid=session.get('username')    
    if(userid==None or userid==''):
        return json.dumps('Unauthorized Access')
    db=None
    try:
        
        st_date=request.form['st_date']
        itineraryid=request.form['itinerary_id']
        place_ids=request.form['place_ids']
        placesList=place_ids.split('~');
        
        db= mysql.connect()
        mycursor =db.cursor()
        mycursor.execute("delete from itinerary where email_id=%s and Date=%s",(userid,st_date))#delete any itinerary having the same date    
        mycursor.execute("update itinerary set Date=%s,status=%s where email_id=%s and itinerary_id=%s",(st_date,'complete',userid,itineraryid))    
        counter=1
        for places in placesList:
            mycursor.execute('update itinerary_places set sr_no=%s where itinerary_id=%s and placeid=%s',(counter,itineraryid,places))
            counter+=1
               
        db.commit()
        generateItineraryMail(mycursor,itineraryid)  
        mycursor.close()              
        response={'status':'200'}
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
        response={'status':'500'}
    finally:
        if(db!=None):
            db.close()
    
    return json.dumps(response)

# =============================================================================
# This function is called via an Async Ajax Call to populate the recommendations
# It is called on click of the fixed heart div    
# =============================================================================
@app.route("/getSuggestions", methods=['GET'])
def getSuggestions():
    userid=session.get('username')    
    if(userid==None or userid==''):
        return json.dumps('Unauthorized Access')    
    try:        
        city=request.args['city']
        place_ids=request.args['place_ids']
        placesList=place_ids.split('~');
        placesList=[int(x) for x in placesList]
        recommendations=recommend_places(placesList,city,userid)        
        response={'status':'200','recommendations':recommendations}
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())
        response={'status':'500'}
    
    return json.dumps(response)

# =============================================================================
# Returns all the itineraries with status as complete in ascending order 
# of Date. The returned object is a dict with the (date,city,id) tuple as key and the
# list of places as the value
# =============================================================================
@app.route("/mytrips", methods=['GET'])
def fetchUserItineraries():
    userid=session.get('username')
    if(userid==None or userid==''):
        return redirect(url_for('login'))#user is not logged in
    db=None
    toReturn={}
    try:        
        db= mysql.connect()
        data=pandas.read_sql('select i.itinerary_id,i.City,p.placeName,i.Date,ip.sr_no from  placedetails p,itinerary_places ip,itinerary i,users u where i.itinerary_id=ip.itinerary_id and p.placeid=ip.placeid and i.email_id=u.Email and i.Date is not null and i.Date>=sysdate() and u.Email="'+userid+'" order by i.Date asc,ip.sr_no asc',con=db)
        unique_itn=data.itinerary_id.unique()
        for itn in unique_itn:
            route=data.loc[data.itinerary_id==itn,:].reset_index(drop=True)
            if(len(route)>0):
                toReturn.update({(route.loc[0,'Date'].strftime('%d-%b-%Y'),route.loc[0,'City'],itn):route.loc[:,'placeName'].values.tolist()})
        return render_template('mytrips.html', title='My Trips', mytrips=toReturn)
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())       
    finally:
        if(db!=None):
            db.close()


@app.route("/delItinerary", methods=['POST'])
def deleteItinerary():
    userid=session.get('username')    
    if(userid==None or userid==''):
        return json.dumps('Unauthorized Access')
    db=None    
    try:        
        db= mysql.connect()
        itineraryid=request.form['itinerary_id']
        mycursor =db.cursor()
        mycursor.execute("delete from itinerary where itinerary_id=%s and email_id=%s",(itineraryid,userid))    
        db.commit()
        response={'status':'200'}
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc()) 
        response={'status':'500'}
    finally:
        if(db!=None):
            db.close()
    return json.dumps(response)



@app.route("/reset-password",methods=["POST","GET"])
def forgot_password():
    '''This function will generate a token once password reset request has been received. '''
    userid=session.get('username')
    if(userid!=None and userid!=''):
        return redirect(url_for('showLandingPage'))#user is already logged in
    con=None
    try:
        con = mysql.connect()
        cursor = con.cursor()
        form = RequestResetForm()
        if form.validate_on_submit():
            userDetails = request.form
            res = cursor.execute("SELECT * from USERS WHERE Email = %s;",(userDetails['email']))
            if int(res) > 0:
                recipient = userDetails['email']
                token = uuid.uuid4().hex#generate hexadecimal UUID
                ts=datetime.datetime.now()
                cursor.execute("INSERT INTO PASSWORD_RESET(Email,Token,Timestamp) VALUES (%s,%s,%s)",(recipient,token,ts))
                con.commit()
                msg = Message("Password Reset Request",
                              sender="voyager.pythonproj@gmail.com",
                              recipients=[recipient]) 
                msg.html = render_template('mail.html',token=token)
                mail.send(msg)
                app.logger.info('Password change request mail sent to {0}'.format(recipient))  
                flash("Mail Sent",'success')
            else:
                flash("User does not exist","danger")
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())      
    finally:
        if(con!=None):
            con.close()
    return render_template('reset_request.html', title='Reset Password', form=form)

@app.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    '''This function will update the new password for the user.'''
    userid=session.get('username')
    if(userid!=None and userid!=''):
        return redirect(url_for('showLandingPage'))#user is already logged in
    valid = verify_reset_token(token)#check if token is valid and not expired
    if valid is False:
        flash('This URL has expired or is invalid', 'warning')
        return redirect(url_for('forgot_password'))
    con=None
    try:
        con = mysql.connect()
        cursor = con.cursor()        
        form = ResetPasswordForm()
        userDetails = request.form
        if form.validate_on_submit():
            password = bcrypt.generate_password_hash(str(userDetails['password'])).decode('utf-8')
            cursor.execute("SELECT Email from PASSWORD_RESET WHERE Token = %s",(token))
            res=cursor.fetchone()
            if(res!=None and len(res)>0 and res[0]!=''):
                email=res[0]
                cursor.execute("UPDATE USERS SET Password = %s WHERE Email = %s",(password,email))
                #delete all the password request tokens for this user
                cursor.execute("delete from PASSWORD_RESET where Email= %s",(email))            
                con.commit()
                flash('Your password has been updated!', 'success')
                return redirect(url_for('login'))
            else:                
                flash("Token is not valid","error")
        
        return render_template('reset_token.html', title='Reset Password', form=form)
    except Exception:  
        app.logger.error('Error occurred in '+request.url)
        app.logger.error(traceback.format_exc())      
    finally:        
        if(con!=None):
            con.close()

# =============================================================================
# Verify that the token received in the request is valid and not expired.
# Token expires in 2 hours
# =============================================================================
def verify_reset_token(token):
    '''This function will validate the URL for resetting new password.
    It is active only for 2 hours '''
    toReturn=False
    con=None
    try:
        con = mysql.connect()
        cursor = con.cursor()
        cursor.execute("SELECT * from PASSWORD_RESET WHERE token = %s;",(token))
        old=None
        for row in cursor:
            if row[1] == token:
                old = row[2]
        if(old!=None):
            gend = dateutil.parser.parse(old, ignoretz=True)
            new =  datetime.datetime.now()
            diff = new-gend
            mins = divmod(diff.days*86400+diff.seconds,60)
            if mins[0] <= 120:
                toReturn=True        
        cursor.close()       
    except Exception:  
        app.logger.error('Error occurred in verify_reset_token')
        app.logger.error(traceback.format_exc())      
    finally:
        if(con!=None):
            con.close()
    return toReturn
    
        

# =============================================================================
# This function calculates the distance between the start placeid and other
#   place ids iteratively while reassigning the start id to the minimum 
#   distance place id at end of each loop        
# =============================================================================
def find_optimized_route(to_visit,start_id):
    db=None
    optimized_route=[]
    start_id_bkp=start_id
    if(len(to_visit)==1):
        return ([start_id]+to_visit)
    try:
        app.logger.info('TO VISIT:'+str(to_visit))
        app.logger.info('START ID:'+str(start_id))
        query=generateQuery(to_visit,start_id)        
        db=mysql.connect()
        df_places = pandas.read_sql(query, con=db)        
        df_places = df_places.set_index('placeid')
        counter=0
        optimized_route.append(start_id)
        while counter<len(to_visit)-1:            
            lat1 = float(df_places.loc[start_id,'Latitude'])
            long1 = float(df_places.loc[start_id,'Longitude'])
            start = (lat1,long1)            
            min_dist = 100000
            min_dist_id = 0
            for i in to_visit:
                if i not in optimized_route:
                    lat2 = float(df_places.loc[i,'Latitude'])
                    long2 = float(df_places.loc[i,'Longitude'])       
                    stop=(lat2,long2)
                    distance = geopy.distance.distance(start, stop).meters
                    app.logger.info('Distance between '+str(start_id)+' and '+str(i)+' : '+str(distance))
                    if distance < min_dist:
                        min_dist = distance
                        min_dist_id = i
            start_id=min_dist_id
            optimized_route.append(start_id)
            counter+=1
        last = list(set(to_visit)-set(optimized_route))
        optimized_route.extend(last)
        app.logger.info('OPTIMIZED ROUTE: '+str(optimized_route))
    except Exception:  
        app.logger.error('Error occurred in find_optimized_route')
        app.logger.error(traceback.format_exc())
        optimized_route=[start_id_bkp]+to_visit
    finally:
        if(db!=None):
            db.close()
            
    return optimized_route

# =============================================================================
# Create sql query using both the list passed as parameter
# =============================================================================
def generateQuery(to_visit,start_id):
    joint=to_visit+[start_id]
    query='SELECT placeid,Latitude,Longitude FROM placedetails where placeid in('
    for pl in joint:
        query+=str(pl)+','
    query=query[:len(query)-1]
    query+=')'
    return query

# =============================================================================
# Prepares the mail for the itinerary created by user. 
# Actual mail is sent in new thread
# =============================================================================
def generateItineraryMail(cursor,itineraryid):
    try:
        query='select p.placeName,p.address,u.FirstName,i.Date,i.City,u.Email from  placedetails p,itinerary_places ip,itinerary i,users u where i.itinerary_id=ip.itinerary_id and p.placeid=ip.placeid and i.email_id=u.Email and i.itinerary_id=%s order by ip.sr_no asc'
        cursor.execute(query,(itineraryid))
        res=cursor.fetchall()
        placeList=[]
        city=''
        Date=''
        firstname=''
        email=''
        if len(res)>0:
            city=res[0][4]
            Date=res[0][3]
            firstname=res[0][2]
            email=res[0][5]
            
            for rec in res:                
                placename=rec[0]
                address=rec[1]
                if(address=='Not Available'):
                    address=''
                placeList.append((placename,address))
        if(email!=''):
            msg = Message("Your trip to "+city,
                              sender="voyager.pythonproj@gmail.com",
                              recipients=[email]) 
    
            msg.html = render_template('itinerary_created.html',city=city,startDate=Date,username=firstname,placeList=placeList)
            thr = Thread(target=asyncMail, args=[app, msg,email])
            thr.start()
            
    except Exception:  
        app.logger.error('Error occurred in generateItineraryMail')
        app.logger.error(traceback.format_exc()) 


# =============================================================================
# Recommend the user the places according to how other users have created their
# itineraries. Most weightage will be given to those itineraries of which
# the users itinerary is a subset of. There should be atleast 70% common items
# between user itinerary and other users itineraries. If common items are not
# found then recommend the most popular places        
# =============================================================================
def recommend_places(places_list,city,emailid):
    mydb=None
    placeNames=[]
    try:
        query = "select ip.itinerary_id,ip.placeid,p.placename from  placedetails p,itinerary_places ip, itinerary i where i.itinerary_id=ip.itinerary_id and p.placeid=ip.placeid and i.city ="+"'"+str(city)+"' and i.email_id<>'"+emailid+"'"
        mydb=mysql.connect()
        df_it = pandas.read_sql(query, con=mydb)
        to_recommend = []
        if(len(df_it)>0 and len(places_list)>0):        
            itinerary_dict = dict(df_it.groupby('itinerary_id').apply(lambda x: list(x.placeid)))
            recommend = {}
            confidence = 0.70
            no_matches=0
            current_user_it = places_list
            cmplsub=[]
            partialsub=[]
            for key,value in itinerary_dict.items():
                no_matches=0
                if(set(current_user_it).issubset(set(value))):
                    places = np.setdiff1d(value,current_user_it)
                    cmplsub.extend(places)
                else:
                    min_placeids = math.floor(len(current_user_it)*confidence)
                    no_matches = len(list(filter(current_user_it.__contains__, value)))            
                    if no_matches>0 and no_matches >= min_placeids:
                        places = np.setdiff1d(value,current_user_it)
                        partialsub.extend(places)                
            
            recommend=dict(collections.Counter(cmplsub*2+partialsub))
            if(len(recommend)==0):
                #this place has not been visited before so add popular places in this city
                diff=np.setdiff1d(df_it.placeid,current_user_it)
                recommend=dict(collections.Counter(diff))
            
            recommend = sorted(recommend.items(),key=operator.itemgetter(1),reverse=True)
            size=len(recommend)
            
            if(size>0):
                top=2 if size>1 else 1                
                final_recommendation = recommend[:top]
                for plid,cnt in final_recommendation:                    
                    to_recommend.append(plid)
                
                fetch_names=df_it[['placeid','placename']].drop_duplicates()        
                placeNames=[fetch_names.loc[fetch_names.placeid==x,'placename'].values[0] for x in to_recommend]
            
    except Exception:  
        app.logger.error('Error occurred in recommend_places')
        app.logger.error(traceback.format_exc())        
    finally:
        if(mydb!=None):
            mydb.close() 
    return placeNames


# =============================================================================
# This function is called in a seperate thread for sending mail using the app context. It accepts
# message as parameter
# =============================================================================
def asyncMail(app,msg,email):
    with app.app_context():
        try:
            mail.send(msg)
            app.logger.info('Itinerary mail sent to {0}'.format(email)) 
        except Exception:
            app.logger.error('Failed to send itinerary mail to {0}'.format(email))
            app.logger.error(traceback.format_exc()) 
