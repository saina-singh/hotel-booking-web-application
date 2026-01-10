from flask import Flask, redirect, url_for 
from datetime import datetime
app = Flask(__name__)   #instatntiating flask appx

#add full path to your text file
logfile = '/Users/za2-khan/Documents/VSCode/venv/workspace/2021/Practical15/Practicalsolutions/logs/logs.txt'

#@app.route('/adminusers/<adminuser>')
def for_adminusers(adminuser):
    #Here admin related tasks can be added
    output = 'Welcome ' + adminuser + ' as Admin'
    return output

#@app.route('/authorizedusers/<authorizeduser>')
def for_authorizedusers(authorizeduser):
    #Here authorized user related tasks can be added
    output = 'Welcome ' + authorizeduser + ' as an Authorized user'
    return output

#@app.route('/guests/<guestuser>')
def for_guests(guestuser):
    #Here guest user related tasks can be added
    output = 'Welcome ' + guest + ' as Guest'
    return output

@app.route('/<username>')
@app.route('/index/<username>')
def index(username):            #function associated with the decorator    
    adminusers = ['zaheer.khan','kamran.soomro']
    authorizedusers =['david.wyatt','barkha.javed','shelan.jeawak']
    fh = open(logfile,'a')
    fileoutput = ""
    if username in adminusers:
        fileoutput = "Admin; " + username + "; " +  str(datetime.now()) + "\n"
        fh.write(fileoutput)
        fh.close()                  
        #return redirect(url_for('adminusers', adminuser=username))
        output = for_adminusers(username)

    elif username in authorizedusers:
        fileoutput = "Authorized; " + username + "; " +  str(datetime.now()) + "\n"
        fh.write(fileoutput)
        fh.close()
        #return redirect(url_for('authorizedusers', authorizeduser=username))
        output = for_authorizedusers(username)
    else:
        fileoutput = "Guest; " + username + "; " +  str(datetime.now()) + "\n"
        fh.write(fileoutput)
        fh.close()
        #return redirect(url_for('guests', guestuser=username))   
        output = for_guests(username)
    
    return output



#if __name__ == '__main__':   
#   app.run(debug = True)
if __name__ == '__main__':    #you can skip this if running app on terminal window
    for i in range(13000, 18000):
      try:
         app.run(debug = True, port = i)
         break
      except OSError as e:
         print("Port {i} not available".format(i))