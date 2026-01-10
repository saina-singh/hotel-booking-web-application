from flask import Flask
app = Flask(__name__)   #instatntiating flask app

output = """
<!DOCTYPE html>
<html>
<head>
<style>
h1 {
	background-color:#6495ed;
}

p {
	background-color:#e0ffff;
	color:slategray
}

div {
	background-color:#b0c4de;
	color: red;
}
</style>

</head>

<body>

<h1>CSS background-color example!</h1>
<div>
This is a text inside a div element.
<p>This paragraph has its own background color.</p>
We are still in the div element.
</div>

</body>
</html>
"""

@app.route('/index')
@app.route('/')         #Decorator
def index():            #function associated with the decorator
   print ('Hello')        
   return output



#if __name__ == '__main__':   
#   app.run(debug = True)
if __name__ == '__main__': 
  #you can skip this if running app on terminal window
    for i in range(13000, 18000):
      try:
         app.run(debug = True, port = i)
         break
      except OSError as e:
         print("Port {i} not available".format(i))