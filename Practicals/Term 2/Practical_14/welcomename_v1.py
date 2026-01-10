from flask import Flask, render_template
app = Flask(__name__)   #instatntiating flask app

@app.route('/welcome/<name>')   #flask variable
def welcome(name):            #function associated with the decorator   
   return render_template('welcomeuser.html', username=name)

#if __name__ == '__main__':   
#   app.run(debug = True)
if __name__ == '__main__':    #you can skip this if running app on terminal window
    for i in range(13000, 18000):
      try:
         app.run(debug = True, port = i)
         break
      except OSError as e:
         print("Port {i} not available".format(i))