from flask import Flask
app = Flask(__name__)   #instatntiating flask app

@app.route('/index')
@app.route('/')         #Decorator
def index():            #function associated with the decorator
   print ('Hello')        
   return '<html><body><h1>Hello Flask - Web Development</h1></body></html>'

@app.route('/welcome')
def welcome():
    return 'Welcome to my web application'

#if __name__ == '__main__':   
#   app.run(debug = True)
if __name__ == '__main__':    #you can skip this if running app on terminal window
    for i in range(13000, 18000):
      try:
         app.run(debug = True, port = i)
         break
      except OSError as e:
         print("Port {i} not available".format(i))