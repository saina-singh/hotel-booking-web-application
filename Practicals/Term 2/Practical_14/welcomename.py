from flask import Flask
app = Flask(__name__)   #instatntiating flask app

output = """
<!DOCTYPE html>
<html>
<head>
<title> Welcome User </title>
</head>
<body>
<h1 style='color:blue;'>Welcome <span style='color:green;'>{username}</span></h1>
</body>
</html>
"""

@app.route('/welcome/<name>')   #flask variable
def welcome(name):            #function associated with the decorator   
   return output.format(username=name)

#if __name__ == '__main__':   
#   app.run(debug = True)
if __name__ == '__main__':    #you can skip this if running app on terminal window
    for i in range(13000, 18000):
      try:
         app.run(debug = True, port = i)
         break
      except OSError as e:
         print("Port {i} not available".format(i))