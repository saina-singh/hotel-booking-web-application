from flask import Flask
app = Flask(__name__)   #instatntiating flask app

@app.route('/')         #Decorator / route / View
def index():            #function associated with the decorator
   print ('Hello')      #output on server side only (good for debugging)
   return '<html><body><h1>Hello Flask - Web Development</h1></body></html>'
   #return sends the reponse to client 

@app.route('/progressreviews')         #Decorator / route / View
def prog_review_experience():            #function associated with the decorator   
   return '<html><body><h1>I felt I could do more for my progress review 2 but the feedback was useful</h1></body></html>'
   #return sends the reponse to client 

#if __name__ == '__main__':   
#   app.run(debug = True)
if __name__ == '__main__':    #you can skip this if running app on terminal window
    for i in range(13000, 18000):
      try:
         app.run(debug = True, port = i)
         break
      except OSError as e:
         print("Port {i} not available".format(i))